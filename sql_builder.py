#!/usr/bin/env python3
"""
Deterministic SQL builder for ThinkTank Bot
Takes extracted entities and produces safe Presto SQL
"""

from typing import Dict, Any, List, Tuple
import re

from config import TABLE_SCHEMA, TIME_PATTERNS, SQL_PATTERNS, PRODUCTS
from distinct_cache import distinct_cache


def _build_time_where(time_key: str, date_column: str) -> List[str]:
    if not time_key:
        return []
    pattern = TIME_PATTERNS.get(time_key)
    if not pattern:
        return []
    # Normalize to selected date column (replace any date column mentions)
    replaced = pattern.replace('leaddate', date_column).replace('bookingdate', date_column)
    return [replaced]


def _validate_dimension(column: str) -> bool:
    return column in TABLE_SCHEMA and TABLE_SCHEMA[column].get("pii_level", "none") != "high"


def _validate_filter_column(column: str) -> bool:
    return column in TABLE_SCHEMA and TABLE_SCHEMA[column].get("is_categorical", False)


def build_sql(entities: Dict[str, Any]) -> Dict[str, str]:
    """
    Input entities from NLP extractor, output dict with sql and explanation or an error message.
    """
    intent = entities.get("intent", "metric_query")
    if intent != "metric_query":
        return {"intent": intent}

    metric_key = entities.get("metric")
    metrics = entities.get("metrics") or []
    metric_expr = SQL_PATTERNS.get(metric_key) if metric_key else None
    # If multiple metrics requested, ignore single metric_key
    if metrics and isinstance(metrics, list):
        metric_selects = [SQL_PATTERNS.get(m) for m in metrics if SQL_PATTERNS.get(m)]
        # Fallback default if none valid
        if not metric_selects:
            metric_selects = [SQL_PATTERNS.get("leads", "COUNT(*) as leads")]
    else:
        if not metric_expr:
            metric_key = "leads"
            metric_expr = SQL_PATTERNS.get("leads", "COUNT(*) as leads")

    products = entities.get("products", [])

    time_info = (entities.get("time") or {})
    time_key = time_info.get("key")
    start_date = time_info.get("start_date")
    end_date = time_info.get("end_date")
    granularity = time_info.get("granularity")
    # Choose date column: bookings -> bookingdate, otherwise default to leaddate
    date_column = 'leaddate'
    try:
        if (metric_key == 'bookings') or (isinstance(metrics, list) and 'bookings' in metrics):
            date_column = 'bookingdate'
    except Exception:
        date_column = 'leaddate'
    where_clauses: List[str] = []

    # Product filter
    if products:
        ids_csv = ", ".join(str(p) for p in products)
        where_clauses.append(f"investmenttypeid IN ({ids_csv})")

    # Time filter: custom range takes precedence, otherwise use named pattern
    if start_date and end_date:
        where_clauses.append(f"DATE({date_column}) >= DATE '{start_date}'")
        where_clauses.append(f"DATE({date_column}) <= DATE '{end_date}'")
    else:
        # Time filter from configured patterns with chosen date column
        where_clauses.extend(_build_time_where(time_key, date_column))

    # Special flags
    flags = entities.get("flags", {}) or {}
    if flags.get("online_only"):
        where_clauses.append("paymentstatus = 300")

    # Additional filters (categoricals only); may include fuzzy_value
    filters = entities.get("filters", {}) or {}
    fuzzy_value = None
    if isinstance(filters, dict) and "_fuzzy_value" in filters:
        fuzzy_value = filters.pop("_fuzzy_value")

    for col, values in filters.items():
        if not _validate_filter_column(col):
            # Allow column if it's explicitly in the table schema, even if not "categorical"
            if col not in TABLE_SCHEMA:
                continue

        # Handle "not null" case
        if isinstance(values, str) and values.lower().strip() == 'not null':
            where_clauses.append(f"{col} IS NOT NULL")
            continue
        
        # Handle "is null" case
        if isinstance(values, str) and values.lower().strip() == 'null':
            where_clauses.append(f"{col} IS NULL")
            continue

        # Ensure values are in a list for consistent processing
        if not isinstance(values, list):
            values = [values]

        safe_values = [str(v).replace("'", "''") for v in values if v is not None]
        if not safe_values:
            continue
        
        # Handle mixed "not null" and other values, e.g., "is not null or 0"
        is_not_null_present = any(str(v).lower().strip() == 'not null' for v in values)
        is_null_present = any(str(v).lower().strip() == 'null' for v in values)

        # Filter out the 'not null'/'null' strings to process other values
        other_values = [v for v in safe_values if str(v).lower().strip() not in ('not null', 'null')]

        sub_clauses = []
        if other_values:
            # Differentiate between numbers and strings for quoting
            numeric_vals, string_vals = [], []
            not_numeric_vals, not_string_vals = [], []

            for v in other_values:
                val_str = str(v).strip()
                is_negative = val_str.lower().startswith(('not ', '!=', '<>'))
                
                val_part = re.sub(r"^(not\s*|!=\s*|<>\s*)", "", val_str, flags=re.IGNORECASE).strip()

                if re.fullmatch(r"-?\d+(\.\d+)?", val_part):
                    if is_negative:
                        not_numeric_vals.append(val_part)
                    else:
                        numeric_vals.append(val_part)
                else:
                    # It's a string, add quotes
                    if is_negative:
                        not_string_vals.append(f"'{val_part}'")
                    else:
                        string_vals.append(f"'{val_part}'")
            
            # Positive conditions
            if numeric_vals:
                sub_clauses.append(f"{col} IN ({', '.join(numeric_vals)})")
            if string_vals:
                sub_clauses.append(f"{col} IN ({', '.join(string_vals)})")
            
            # Negative conditions
            if not_numeric_vals:
                sub_clauses.append(f"{col} NOT IN ({', '.join(not_numeric_vals)})")
            if not_string_vals:
                sub_clauses.append(f"{col} NOT IN ({', '.join(not_string_vals)})")

        if is_not_null_present:
            sub_clauses.append(f"{col} IS NOT NULL")
        
        if is_null_present:
            sub_clauses.append(f"{col} IS NULL")

        if sub_clauses:
            where_clauses.append(f"({ ' OR '.join(sub_clauses) })")

    # Fallback fuzzy search: if a fuzzy_value is provided and no prior categorical filter used it
    if fuzzy_value and not any(k for k in filters.keys()):
        # Normalize fuzzy_value to a string
        if isinstance(fuzzy_value, list) and fuzzy_value:
            fuzzy_value = fuzzy_value[0]
        if isinstance(fuzzy_value, dict):
            # Join dict values best-effort
            try:
                fuzzy_value = " ".join(str(v) for v in fuzzy_value.values())
            except Exception:
                fuzzy_value = str(fuzzy_value)

        guess_cols: List[str] = distinct_cache.get_effective_columns()
        # Ensure agent name is considered for fuzzy matching
        if 'leadassignedagentname' in TABLE_SCHEMA and 'leadassignedagentname' not in guess_cols:
            guess_cols.append('leadassignedagentname')
        lowered = str(fuzzy_value).lower().replace("'", "''")
        # Only attempt string-like columns
        string_cols = [c for c in guess_cols if TABLE_SCHEMA.get(c, {}).get("data_type", "").lower().startswith("varchar") or TABLE_SCHEMA.get(c, {}).get("data_type", "").lower() in ("string", "text")]
        like_clauses = [f"LOWER(CAST({c} AS VARCHAR)) LIKE '%%{lowered}%%'" for c in string_cols]
        if like_clauses:
            where_clauses.append("( " + " OR ".join(like_clauses) + " )")

    # Base SELECT
    # SELECT parts
    if metrics and isinstance(metrics, list) and len(metrics) > 0:
        select_parts: List[str] = metric_selects
    else:
        select_parts = [metric_expr]

    # Dimensions (GROUP BY)
    dimensions = [d for d in (entities.get("dimensions") or []) if _validate_dimension(d)]
    group_by: List[str] = []

    # Add dimensions to SELECT/GROUP BY
    if dimensions:
        # Replace select_parts with dimensions + metrics
        if metrics and isinstance(metrics, list) and len(metrics) > 0:
            select_parts = dimensions + select_parts
        else:
            select_parts = dimensions + [metric_expr]
        group_by = dimensions[:]

    # Time granularity bucketing (e.g., month-wise trend)
    if granularity in ("month", "week"):
        if granularity == "month":
            bucket_expr = f"DATE_TRUNC('month', {date_column})"
            bucket_alias = "month"
        else:
            bucket_expr = f"DATE_TRUNC('week', {date_column})"
            bucket_alias = "week"
        # Prepend bucket to SELECT and add to group by
        # Avoid duplicate bucket if user already explicitly requested 'month' dimension
        if all(part.find(" AS month") == -1 for part in select_parts):
            select_parts = [f"{bucket_expr} AS {bucket_alias}"] + select_parts
        if bucket_expr not in group_by:
            group_by.append(bucket_expr)

    # Special handling: show product name with product-wise results
    if 'investmenttypeid' in dimensions:
        # Build CASE for product names from PRODUCTS alias map
        id_to_name: Dict[int, str] = {}
        for alias, pid in PRODUCTS.items():
            try:
                pid_int = int(pid)
            except Exception:
                continue
            best = id_to_name.get(pid_int)
            if not best or len(alias) > len(best):
                id_to_name[pid_int] = alias.title()
        if id_to_name:
            cases = ' '.join([f"WHEN investmenttypeid = {pid} THEN '{name.replace("'", "''")}'" for pid, name in id_to_name.items()])
            product_case_select = f"CASE {cases} END AS product_name"
            product_case_group = f"CASE {cases} END"
            # Prepend product_name to SELECT
            select_parts = ['investmenttypeid', product_case_select] + [p for p in select_parts if p != 'investmenttypeid']
            # Ensure grouping by the CASE expression (Presto requires full expr)
            if product_case_group not in group_by:
                group_by.append(product_case_group)

    select_sql = ", ".join(select_parts)
    sql = f"SELECT {select_sql} FROM sme_analytics.sme_leadbookingrevenue"
    if where_clauses:
        sql += " WHERE " + " AND ".join(where_clauses)
    if group_by:
        sql += " GROUP BY " + ", ".join(group_by)

    explanation = _build_explanation(metric_key or metrics, products, time_key, dimensions, filters, flags)
    return {"intent": "metric_query", "sql": sql, "explanation": explanation}


def _build_explanation(metric_key, products, time_key, dimensions, filters, flags) -> str:
    parts: List[str] = []
    parts.append(f"Metric: {metric_key}")
    if products:
        parts.append(f"Products: {products}")
    if time_key:
        parts.append(f"Time: {time_key}")
    if dimensions:
        parts.append(f"Grouped by: {', '.join(dimensions)}")
    for col, vals in (filters or {}).items():
        parts.append(f"Filter {col} in {vals}")
    if flags.get("online_only"):
        parts.append("Online payments only (paymentstatus=300)")
    return "; ".join(parts)

