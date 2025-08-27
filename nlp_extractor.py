#!/usr/bin/env python3
"""
AI-driven NLP extractor for ThinkTank Bot
Extracts: intent, products, metric, time, dimensions, and filters from user text
"""

import os
import json
from typing import Dict, Any
import re
from datetime import datetime
from dotenv import load_dotenv
import google.generativeai as genai

# Local config
from config import PRODUCTS, SQL_PATTERNS

# Load env
load_dotenv()

# Initialize Gemini
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
_MODEL = genai.GenerativeModel('gemini-1.5-flash')


class NLPExtractor:
    """Single-responsibility class for AI-based extraction only (no SQL here)."""

    def __init__(self):
        self.model = _MODEL

    def extract(self, user_text: str) -> Dict[str, Any]:
        """
        Returns a strict JSON dict with:
        {
          intent: metric_query|feedback|conversation|clarification|help|agent_status,
          confidence: float,
          products: [int],              # ONLY canonical product IDs if explicitly stated
          metric: str|null,             # one of keys in SQL_PATTERNS (e.g., leads, bookings, revenue)
          metrics: [str]|null,          # optional multi-metric list (e.g., ["bookings","revenue"])
          time: { key: str|null },      # normalized time key (e.g., 'today', 'yesterday', 'this month')
          dimensions: [str],            # columns for GROUP BY (e.g., leadassignedagentname)
          filters: { col: [values], _fuzzy_value: str|null },   # additional filters (+ optional fuzzy)
          order: { by: str|null, direction: "asc|desc"|null, top_n: int|null },
          flags: { online_only: bool }, # special flags like online payments = 300
          ambiguities: [str],           # if anything is unclear for quick clarification
          explanation: str,
          agent: {
            name: str|null,
            codes: [str],
            mode: "single"|"summary"|null,
            status_filters: [str],
            fields: [str],
            scan: "sample"|"full"|null
          }
        }
        """

        # Present only top aliases for compactness
        product_lines = []
        seen = set()
        for alias, pid in PRODUCTS.items():
            if pid in seen:
                continue
            seen.add(pid)
            product_lines.append(f"- ID {pid}: {alias}")
            if len(product_lines) >= 40:  # cap to keep prompt short
                break
        product_context = "\n".join(product_lines)

        metric_options = ", ".join(SQL_PATTERNS.keys())

        prompt = f"""You are a precise, literal information extractor for an insurance analytics bot.
Analyze the user message and extract structured fields. Do NOT generate SQL.

User Message: "{user_text}"

Known Insurance Products (id: alias):
{product_context}

Rules:
- Be LITERAL. If the user says "fire insurance", return ONLY product id 5.
- Do NOT add related or variant products unless explicitly named.
- If no product is named, return an empty products list.
- Infer the metric only if clearly stated (supported metrics: {metric_options}).
- Normalize time into a key like: today, yesterday, this week, last week, this month, last month.
- CRITICAL: If the user provides a direct column condition (e.g., "where referral id is not null", "referralid is 0", "status is not 'Closed'"), extract it LITERALLY. PRESERVE negative words like "not", "isn't", "!=". Example: "referral id is not 0" should be {{"referralid": ["not 0"]}}.
- If user indicates online bookings, set flags.online_only = true.
- If anything is ambiguous, include a short note in ambiguities.
- If the user asks for multiple metrics, put them in metrics []. If only one, set metric.
- If the user asks for top/bottom or most/least, include order.by (metric or dimension), order.direction, and order.top_n.
- Normalize 'product wise' to dimension "investmenttypeid".
- **FINAL CHECK**: It is better to return fewer extracted fields than to return incorrect or hallucinated fields. If you are not confident, leave the field empty.

Special handling:
- If the user asks about agent status (e.g., "what is my agent doing", "agent status", "is <agent name> free/on call"), set intent to agent_status.
- For single agent: fill agent.name and/or agent.codes.
- For summaries like "agents active now": set agent.mode="summary". If user asks for exact/full, set agent.scan="full" else "sample".
- If user mentions statuses (pause, busy, idle, available, ready, on call, ringing), set agent.status_filters accordingly.
- If user asks for specific fields from the agent JSON (AgentName, AgentCode, Status, ConnectedDials, TotalTalkTime, LastUpdatedOn, etc.), list them in agent.fields.

If the user mentions a company/brand or category value but not a clear column, put it in filters._fuzzy_value.
Output strictly as JSON:
{{
  "intent": "metric_query|feedback|conversation|clarification|help|agent_status",
  "confidence": 0.95,
  "products": [5],
  "metric": "leads|bookings|revenue|premium|brokerage|avg_premium|sum_insured|lives_covered|null",
  "time": {{ "key": "today|yesterday|this week|last week|this month|last month|null" }},
  "dimensions": ["leadassignedagentname"],
  "filters": {{ "mkt_category": ["CRM"], "_fuzzy_value": null }},
  "flags": {{ "online_only": false }},
  "ambiguities": ["..."],
  "explanation": "...",
  "agent": {{
    "name": null,
    "codes": [],
    "mode": null,
    "status_filters": [],
    "fields": [],
    "scan": null
  }}
}}
"""

        try:
            response = self.model.generate_content(
                prompt,
                generation_config={"max_output_tokens": 600, "temperature": 0.0},
            )
            resp = response.text.strip().replace('```json', '').replace('```', '')
            data = json.loads(resp)

            # Basic validation
            if data.get("intent") not in ["metric_query", "feedback", "conversation", "clarification", "help", "agent_status"]:
                data["intent"] = "metric_query"

            # Ensure products are integers and unique
            products = data.get("products", []) or []
            data["products"] = sorted(list({int(p) for p in products if isinstance(p, (int, float, str)) and str(p).isdigit()}))

            # Coerce shapes
            data.setdefault("confidence", 0.7)
            data.setdefault("metric", None)
            data.setdefault("time", {"key": None})
            data.setdefault("dimensions", [])
            data.setdefault("filters", {})
            data.setdefault("flags", {"online_only": False})
            data.setdefault("ambiguities", [])
            data.setdefault("explanation", "")
            agent = data.setdefault("agent", {"name": None})
            if not isinstance(agent, dict):
                agent = {}
                data["agent"] = agent
            agent.setdefault("name", None)
            agent.setdefault("codes", [])
            agent.setdefault("mode", None)
            agent.setdefault("status_filters", [])
            agent.setdefault("fields", [])
            agent.setdefault("scan", None)

            # Heuristic post-processing for time ranges/granularity from raw text
            data["time"] = self._augment_time_from_text(user_text, data.get("time") or {})
            # Post-validate product IDs: keep only if an alias phrase appears verbatim in the text
            try:
                text_l = (user_text or "").lower()
                # Build alias list per product id
                id_to_aliases: dict[int, list[str]] = {}
                for alias, pid in PRODUCTS.items():
                    try:
                        pid_int = int(pid)
                    except Exception:
                        continue
                    id_to_aliases.setdefault(pid_int, []).append(str(alias).lower())

                validated_products: list[int] = []
                for pid in (data.get("products") or []):
                    aliases = id_to_aliases.get(int(pid), [])
                    # Match only if any multi-word alias occurs as a phrase with word boundaries
                    found = False
                    for a in aliases:
                        if not a:
                            continue
                        if len(a) < 3:
                            continue
                        import re as _re
                        pattern = r"\b" + _re.escape(a) + r"\b"
                        if _re.search(pattern, text_l):
                            found = True
                            break
                    if found:
                        validated_products.append(int(pid))
                data["products"] = sorted(list({int(p) for p in validated_products}))
                # If the user explicitly asks for all products/subproducts, clear any product filters
                if any(phrase in text_l for phrase in [
                    "all products", "all subproducts", "across products", "overall products", "overall subproducts"
                ]):
                    data["products"] = []
            except Exception:
                try:
                    data["products"] = []
                except Exception:
                    pass
            data = self._maybe_detect_agent_status(user_text, data)
            data = self._maybe_request_agent_summary(user_text, data)
            data = self._apply_wise_group_by(user_text, data)
            # Normalize agent.status_filters to upper
            try:
                if isinstance(data.get("agent", {}).get("status_filters"), list):
                    data["agent"]["status_filters"] = [str(s).upper() for s in data["agent"]["status_filters"] if s]
            except Exception:
                pass
            # Map agent.mode/scan to legacy flags to avoid breaking metric flow
            if (data.get("agent", {}).get("mode") == "summary"):
                flags = data.get("flags") or {}
                flags["agent_active_summary"] = True
                data["flags"] = flags
            if (data.get("agent", {}).get("scan") == "full"):
                flags = data.get("flags") or {}
                flags["agent_active_summary_full"] = True
                data["flags"] = flags
            return data
        except Exception as e:
            return {
                "intent": "metric_query",
                "confidence": 0.3,
                "products": [],
                "metric": None,
                "time": {"key": None},
                "dimensions": [],
                "filters": {},
                "flags": {"online_only": False},
                "ambiguities": [f"Extractor error: {e}"],
                "explanation": "Fallback extraction due to AI error",
                "agent": {"name": None}
            }

    def _augment_time_from_text(self, text: str, time_obj: Dict[str, Any]) -> Dict[str, Any]:
        """Infer year/month-range and granularity from phrases like 'month wise 2025' or 'from jan to aug 2025'."""
        text_l = (text or "").lower()
        result = dict(time_obj) if isinstance(time_obj, dict) else {"key": None}

        # If explicit start/end already set, keep them
        if result.get("start_date") and result.get("end_date"):
            return result

        # Month-wise signals (expanded)
        monthwise = any(k in text_l for k in [
            "month wise", "monthwise", "month-wise", "month on month", "month-on-month", "month over month", "mom", "trend"
        ])

        # Month names and common abbreviations
        months = {
            "january": 1, "jan": 1,
            "february": 2, "feb": 2,
            "march": 3, "mar": 3,
            "april": 4, "apr": 4,
            "may": 5,
            "june": 6, "jun": 6,
            "july": 7, "jul": 7,
            "august": 8, "aug": 8,
            "september": 9, "sept": 9, "sep": 9,
            "october": 10, "oct": 10,
            "november": 11, "nov": 11,
            "december": 12, "dec": 12,
        }

        # Helper: resolve possibly misspelled month using fuzzy matching
        def _resolve_month_token(token: str) -> int | None:
            try:
                t = (token or "").strip().lower()
                if t in months:
                    return months[t]
                # Fuzzy resolve with rapidfuzz if available
                try:
                    from rapidfuzz import process
                    keys = list(months.keys())
                    cand = process.extractOne(t, keys, score_cutoff=80)
                    if cand and cand[0] in months:
                        return months[cand[0]]
                except Exception:
                    pass
            except Exception:
                pass
            return None

        # from/between <month> to <month> <year> (supports 2-digit year)
        m = re.search(r"(?:from|between)\s+([a-zA-Z]+)\s+to\s+([a-zA-Z]+)\s+((?:20)?\d{2})", text_l)
        if m:
            m1, m2, ytxt = m.group(1), m.group(2), m.group(3)
            year = int(ytxt)
            if year < 100:
                year = 2000 + year
            mm1 = months.get(m1) or _resolve_month_token(m1)
            mm2 = months.get(m2) or _resolve_month_token(m2)
            if mm1 and mm2:
                start_date = f"{year}-{mm1:02d}-01"
                last_day = 31
                for d in [31, 30, 29, 28]:
                    try:
                        datetime(year, mm2, d)
                        last_day = d
                        break
                    except Exception:
                        continue
                end_date = f"{year}-{mm2:02d}-{last_day:02d}"
                result["start_date"] = start_date
                result["end_date"] = end_date
                if monthwise:
                    result["granularity"] = "month"
                return result

        # <month> to <month> <year> without leading 'from/between'
        m2 = re.search(r"([a-zA-Z]+)\s+to\s+([a-zA-Z]+)\s+((?:20)?\d{2})", text_l)
        if m2:
            m1, m_end, ytxt = m2.group(1), m2.group(2), m2.group(3)
            year = int(ytxt)
            if year < 100:
                year = 2000 + year
            mm1 = months.get(m1) or _resolve_month_token(m1)
            mm2 = months.get(m_end) or _resolve_month_token(m_end)
            if mm1 and mm2:
                start_date = f"{year}-{mm1:02d}-01"
                last_day = 31
                for d in [31, 30, 29, 28]:
                    try:
                        datetime(year, mm2, d)
                        last_day = d
                        break
                    except Exception:
                        continue
                end_date = f"{year}-{mm2:02d}-{last_day:02d}"
                result["start_date"] = start_date
                result["end_date"] = end_date
                if monthwise:
                    result["granularity"] = "month"
                return result

        # since <month> [<year>] → start at month start until today
        ms = re.search(r"\bsince\s+([a-zA-Z]+)(?:\s+((?:20)?\d{2}))?", text_l)
        if ms:
            m_tok = ms.group(1)
            ytxt = ms.group(2)
            mm = months.get(m_tok) or _resolve_month_token(m_tok)
            if mm:
                from datetime import date as _date
                today = _date.today()
                year = None
                if ytxt:
                    try:
                        year = int(ytxt)
                        if year < 100:
                            year = 2000 + year
                    except Exception:
                        year = None
                if year is None:
                    year = today.year
                    try:
                        # If the month start would be in the future, roll back a year
                        if _date(year, mm, 1) > today:
                            year -= 1
                    except Exception:
                        pass
                # Compute end-of-today
                start_date = f"{year}-{mm:02d}-01"
                result["start_date"] = start_date
                result["end_date"] = today.strftime("%Y-%m-%d")
                if monthwise:
                    result["granularity"] = "month"
                result["key"] = None
                return result

        # <year> with month-wise intent
        y = re.search(r"\b(20\d{2})\b", text_l)
        if y and monthwise:
            year = int(y.group(1))
            result["start_date"] = f"{year}-01-01"
            result["end_date"] = f"{year}-12-31"
            result["granularity"] = "month"
            # Clear generic key if present
            result["key"] = None
            return result

        # 'this year' phrase with or without explicit year
        if "this year" in text_l:
            from datetime import datetime as _dt
            cy = _dt.now().year
            result["start_date"] = f"{cy}-01-01"
            result["end_date"] = f"{cy}-12-31"
            if monthwise:
                result["granularity"] = "month"
            result["key"] = None
            return result

        return result

    def _maybe_detect_agent_status(self, text: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Lightweight heuristic to detect agent status queries and extract name if present."""
        try:
            t = (text or "").lower()
            # Trigger phrases even without the word 'agent'
            if any(k in t for k in [
                "agent status", "what is my agent", "what's my agent", "is my agent", "is agent",
                "what is agent doing", "on call", "idle", "busy", "available"
            ]):
                data["intent"] = "agent_status"

            # Regex patterns to catch e.g. "what is prityush doing?", "is prityush free?", "status of prityush"
            name = None
            m_doing = re.search(r"\bwhat(?:\s+is|'s)\s+([A-Za-z\.\-\s]{2,40})\s+doing\b", text or "", flags=re.IGNORECASE)
            if m_doing:
                data["intent"] = "agent_status"
                name = m_doing.group(1).strip()

            m_is_free = re.search(r"\bis\s+([A-Za-z\.\-\s]{2,40})\s+(?:free|busy|available|on\s+call)\b", text or "", flags=re.IGNORECASE)
            if not name and m_is_free:
                data["intent"] = "agent_status"
                name = m_is_free.group(1).strip()

            m_status_of = re.search(r"\bstatus\s+of\s+([A-Za-z\.\-\s]{2,40})\b", text or "", flags=re.IGNORECASE)
            if not name and m_status_of:
                data["intent"] = "agent_status"
                name = m_status_of.group(1).strip()

            # Fallback: Prefer 'for|of' capture; allow codes with digits too
            m = re.search(r"\b(?:for|of)\s+([A-Za-z0-9\.\-\s]{2,40})", text or "", flags=re.IGNORECASE)
            if not name and m:
                candidate = (m.group(1) or "").strip()
                candidate = re.split(r"\b(in|on|at|etc)\b", candidate)[0].strip()
                if candidate and len(candidate) >= 2:
                    name = candidate
            # Last resort: after 'agent'
            m2 = re.search(r"\bagent\s+([A-Za-z0-9\.\-\s]{2,40})", text or "", flags=re.IGNORECASE)
            if not name and m2:
                candidate = (m2.group(1) or "").strip()
                # Trim trailing stop words
                candidate = re.split(r"\b(status|doing|in|on|at|etc)\b", candidate)[0].strip()
                if candidate and len(candidate) >= 2:
                    name = candidate
            if "agent" not in data:
                data["agent"] = {"name": None}
            if name:
                data["agent"]["name"] = name

            # Extract explicit agent codes like PW56362 and store them
            try:
                codes = re.findall(r"\b[A-Za-z]{1,6}\d{2,8}\b", text or "")
                if codes:
                    # ensure array exists
                    if not isinstance(data.get("agent"), dict):
                        data["agent"] = {"name": None}
                    existing = data["agent"].get("codes") or []
                    # de-duplicate while preserving order
                    seen = set(str(c) for c in existing)
                    for c in codes:
                        if c not in seen:
                            existing.append(c)
                            seen.add(c)
                    data["agent"]["codes"] = existing
            except Exception:
                pass
            return data
        except Exception:
            return data

    def _maybe_request_agent_summary(self, text: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Detect requests like 'how many agents active right now (per product)' and set a flag."""
        try:
            t = (text or "").lower()
            if any(phrase in t for phrase in [
                "agents active",
                "active agents",
                "how many agents",
                "agents online",
                "agents available",
            ]):
                flags = data.get("flags") or {}
                flags["agent_active_summary"] = True
                # Full scan triggers
                if any(k in t for k in ["exact", "full", "complete", "all agents"]):
                    flags["agent_active_summary_full"] = True
                data["flags"] = flags
            return data
        except Exception:
            return data

    def _apply_wise_group_by(self, text: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generalize '<token> wise' and 'group by <token>' to dimensions or time granularity."""
        try:
            t = (text or "").lower()
            tokens: list[str] = []
            wise_matches = re.findall(r"([a-zA-Z\s&,-]+?)\s*(?:wise|\-wise)\b", t)
            for m in wise_matches:
                parts = re.split(r"\s*(?:,|and|&|\/)\s*", m)
                for p in parts:
                    p = p.strip()
                    if p:
                        tokens.append(p)
            gb = re.findall(r"group\s+by\s+([a-zA-Z\s,&/]+)", t)
            for m in gb:
                parts = re.split(r"\s*(?:,|and|&|\/)\s*", m)
                for p in parts:
                    p = p.strip()
                    if p:
                        tokens.append(p)

            if not tokens:
                return data

            alias_map = {
                "agent": "leadassignedagentname",
                "product": "investmenttypeid",
                "city": "city",
                "state": "state",
                "insurer": "insurername",
                "status": "booking_status",
            }

            dims = list(data.get("dimensions") or [])
            time_obj = dict(data.get("time") or {})

            candidates = [
                col for col, meta in TABLE_SCHEMA.items()
                if meta.get("is_categorical") and meta.get("pii_level", "none") != "high"
            ]

            for tok in tokens:
                tok_norm = tok.strip().lower()
                if not tok_norm:
                    continue
                if tok_norm in ("month", "monthly", "month on month", "month-on-month", "mom"):
                    time_obj["granularity"] = "month"
                    continue
                if tok_norm in ("week", "weekly"):
                    time_obj["granularity"] = "week"
                    continue
                mapped = alias_map.get(tok_norm)
                if mapped and mapped in TABLE_SCHEMA:
                    if mapped not in dims:
                        dims.append(mapped)
                    continue
                matches = process.extract(tok_norm, candidates, scorer=fuzz.WRatio, limit=3)
                for name, score, _ in matches:
                    if score >= 90 and name not in dims:
                        dims.append(name)
                        break

            if dims:
                data["dimensions"] = dims
            if time_obj:
                data["time"] = time_obj
            return data
        except Exception:
            return data


# Global instance
nlp_extractor = NLPExtractor()
