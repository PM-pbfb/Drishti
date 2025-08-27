from dotenv import load_dotenv
import os

# Explicitly load .env from the script's directory
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)

import time
import pandas as pd
import json
import hashlib
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import google.generativeai as genai
from datetime import datetime
import re
import requests
from rapidfuzz import fuzz, process
from typing import Dict, Any
import threading
from flask import Flask, request, jsonify, send_file
from slack_sdk import WebClient
from flask_cors import CORS

# Import configurations
from config import *

# Initialize Slack App
app = App(token=os.getenv("SLACK_BOT_TOKEN"))

# Initialize Gemini
def initialize_gemini():
    try:
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        model = genai.GenerativeModel(model_name=MODEL_NAME)
        return model
    except Exception as e:
        print(f"Failed to initialize Gemini: {e}")
        return None

model = initialize_gemini()

# Database connection
from database import SimpleDatabase
from subscription_manager import subscription_manager
from business_logic_manager import BusinessLogicManager
from masking_service import masking_service
from nlp_extractor import nlp_extractor
from sql_builder import build_sql
from distinct_cache import distinct_cache
from intent_classifier import classify_intent

# Simple in-memory session store for per-user mode
USER_SESSIONS = {}
# Per-user query cache keyed by sql hash (query_id)
USER_QUERY_CACHE = {}


def build_schema_markdown() -> str:
    """Return a markdown representation of the allowed table schema."""
    try:
        header = "📚 Database Schema for `sme_analytics.sme_leadbookingrevenue`:"
        lines = []
        for col, meta in TABLE_SCHEMA.items():
            data_type = meta.get("data_type", "unknown")
            pii = meta.get("pii_level", "none")
            desc = meta.get("description", "")
            lines.append(f"- `{col}` ({data_type}) [pii: {pii}] - {desc}")
        return header + "\n" + "\n".join(lines)
    except Exception as e:
        return f"❌ Failed to render schema: {e}"


def send_schema(say):
    """Send schema to Slack with a download action."""
    text = build_schema_markdown()
    def chunk_text(s: str, limit: int = 2500):
        parts = []
        while s:
            parts.append(s[:limit])
            s = s[limit:]
        return parts
    chunks = chunk_text(text)
    blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": ch}} for ch in chunks]
    blocks.append({
        "type": "actions",
        "elements": [
            {"type": "button", "text": {"type": "plain_text", "text": "📥 Download Schema (CSV)"}, "action_id": "download_schema", "value": "schema_csv"}
        ]
    })
    say(blocks=blocks, text=chunks[0] if chunks else text)

def merge_entities_for_correction(base: dict, delta: dict, feedback_text: str) -> dict:
    """Merge user feedback-derived entities (delta) into the last query entities (base)."""
    result = dict(base or {})
    t = (feedback_text or "").lower()

    # Helper to deep copy nested maps
    def _clone_map(m):
        return {k: (v.copy() if isinstance(v, dict) else (v[:] if isinstance(v, list) else v)) for k, v in (m or {}).items()}

    # Products
    if any(k in t for k in ["all products", "all subproducts", "across products", "remove product", "remove products", "overall products", "overall subproducts"]):
        result["products"] = []
    elif delta.get("products"):
        result["products"] = list(delta.get("products") or [])

    # Metric / metrics
    if delta.get("metrics"):
        result["metrics"] = list(delta.get("metrics") or [])
        result.pop("metric", None)
    elif delta.get("metric"):
        result["metric"] = delta.get("metric")
        result.pop("metrics", None)

    # Time
    time_new = dict(result.get("time") or {})
    for k in ("key", "start_date", "end_date", "granularity"):
        if (delta.get("time") or {}).get(k) is not None:
            time_new[k] = (delta.get("time") or {}).get(k)
    result["time"] = time_new

    # Dimensions
    if delta.get("dimensions"):
        result["dimensions"] = list(delta.get("dimensions") or [])

    # Flags
    flags_new = _clone_map(result.get("flags") or {})
    for k, v in (delta.get("flags") or {}).items():
        flags_new[k] = v
    result["flags"] = flags_new

    # Filters
    filters_new = _clone_map(result.get("filters") or {})
    for k, v in (delta.get("filters") or {}).items():
        if k == "_fuzzy_value":
            # Overwrite fuzzy value with the latest user guidance
            filters_new[k] = v
        else:
            # Merge lists for categorical filters
            existing = set(filters_new.get(k) or [])
            for item in (v or []):
                existing.add(item)
            filters_new[k] = list(existing)
    result["filters"] = filters_new

    return result

# Lightweight debug logger
def debug(message: str):
    try:
        ts = datetime.now().strftime('%H:%M:%S')
        print(f"[DEBUG {ts}] {message}")
    except Exception:
        print(f"DEBUG: {message}")

class SimplifiedBot:
    def __init__(self, db_manager):
        self.model = model
        self.db = db_manager
        
    def process_query_with_ai(self, text):
        # Two-stage: extract entities only
        entities = nlp_extractor.extract(text)
        return entities

    def resolve_products(self, text: str) -> list:
        """Return list of canonical product IDs extracted from text using deterministic alias matching."""
        try:
            t = (text or "").lower()
            # Normalize separators
            import re as _re
            # Collect aliases grouped by product id
            pid_to_aliases: dict[int, list[str]] = {}
            for alias, pid in PRODUCTS.items():
                try:
                    pid_int = int(pid)
                except Exception:
                    continue
                pid_to_aliases.setdefault(pid_int, []).append(str(alias).lower())

            found: set[int] = set()
            # Check longer aliases first to avoid partial overshadow
            for pid, aliases in pid_to_aliases.items():
                aliases_sorted = sorted(aliases, key=lambda a: len(a), reverse=True)
                for a in aliases_sorted:
                    if not a:
                        continue
                    # Build word-boundary regex. Allow spaces and hyphens inside alias tokens
                    pattern = r"\\b" + _re.escape(a).replace("\\ ", "\\s+") + r"\\b"
                    if _re.search(pattern, t, flags=_re.IGNORECASE):
                        found.add(pid)
                        break
            return sorted(list(found))
        except Exception:
            return []

    def generate_response(self, user_text, user_id, product_ids=None):
        """Single AI call to handle all user requests with a more robust prompt."""
        
        # Entities provided from process_query_with_ai
        entities = product_ids if isinstance(product_ids, dict) else {}
        products = entities.get("products", []) if entities else []
        product_context = "No specific product filter has been identified."
        if products:
            names = [name for name, pid in PRODUCTS.items() if pid in products]
            product_names_str = ", ".join(sorted(list(set(names))))
            product_context = f"**Product Filter**: The user is asking about **{product_names_str}**. You MUST use these exact IDs in your query: `{products}`."

        approved_logic = business_logic_manager.get_relevant_approved_logic(user_text)
        logic_context = ""
        if approved_logic:
            logic_context = "\n\n**CRITICAL INSTRUCTIONS FROM HUMAN EXPERTS:**\n" + "\n".join(f"- {logic}" for logic in approved_logic)
            
        time_syntax_examples = "\n".join([f"- For '{name}', use this SQL: `{syntax}`" for name, syntax in TIME_PATTERNS.items()])
        current_year = datetime.now().year
        time_syntax_examples += f"\n- For 'april month' or 'april', use: `leadmonth = 'April-{current_year}'`"

        column_details = "\n".join([f"- `{col}` ({meta.get('data_type', 'unknown')}): {meta.get('description', '')}" for col, meta in TABLE_SCHEMA.items()])
        # Merge static samples with dynamic distincts
        distincts = distinct_cache.get()
        categorical_values_context = self.get_categorical_values_context(distincts)

        prompt = f"""You are ThinkTank, a specialized AI analyst. Your task is to generate a single, precise JSON object to answer the user's query.

        **User Query**: "{user_text}"
        {product_context}

        **CRITICAL DATABASE RULES**:
        -   **ONLY use this table**: `sme_analytics.sme_leadbookingrevenue`
        -   **DATE FORMAT**: The `leadmonth` column is a string like 'April-2024'.
        -   **Available columns**: {column_details}
        {categorical_values_context}
        {logic_context}

        **Your Task**: Respond with a JSON object for ONE of the following intents.
        1.  **"metric_query"**: For any request about business data.
            -   The SQL query must be valid Presto SQL and NEVER end with a semicolon.
            -   Example: `{{"intent": "metric_query", "sql": "SELECT COUNT(*) FROM sme_analytics.sme_leadbookingrevenue WHERE investmenttypeid IN (5)", "explanation": "This query counts leads for Fire product."}}`
        2.  **"feedback"**: If the user provides feedback (e.g., "this is wrong," "good job").
            -   Example: `{{"intent": "feedback", "message": "User provided feedback."}}`
        3.  **"conversation"**: For greetings or simple chat.
            -   Example: `{{"intent": "conversation", "response": "Hello! How can I help?"}}`

        **Time Syntax**:
        {time_syntax_examples}
        
        Respond now with only the JSON object."""
        
        # Deterministic SQL building
        sql_payload = build_sql(entities or {})
        if sql_payload.get("intent") != "metric_query":
            # Non-metric intents fallback to conversation/feedback
            if sql_payload.get("intent") == "feedback":
                return {"intent": "feedback", "message": "Thanks for the feedback."}
            return {"intent": "conversation", "response": "Could you clarify what you need?"}
        return sql_payload
    
    def resolve_agent_lead_id(self, agent_name: str, products=None):
        """Find a representative lead_agentid for the given agent name, optionally within product IDs."""
        if not agent_name:
            return None
        try:
            name_safe = str(agent_name).replace("'", "''").strip().lower()
            # Build OR predicate across multiple possible agent name columns
            name_columns = [
                'leadassignedagentname', 'currentlyassigneduser', 'leadreportingmanagername',
                'leadreportingmanagername2', 'first_assigned_agent', 'booking_agent',
                'booking_agent_manager', 'booking_agent_manager2'
            ]
            like_clauses = [
                f"LOWER(CAST({col} AS VARCHAR)) LIKE CONCAT('%%', '{name_safe}', '%%')" for col in name_columns
            ]
            name_predicate = "( " + " OR ".join(like_clauses) + " )"

            where_parts = [
                "lead_agentid IS NOT NULL",
                "lead_agentid <> ''",
                name_predicate,
            ]
            if products:
                ids_csv = ", ".join(str(p) for p in products)
                where_parts.append(f"investmenttypeid IN ({ids_csv})")
            where_sql = " AND ".join(where_parts)
            sql = (
                "SELECT lead_agentid "
                "FROM sme_analytics.sme_leadbookingrevenue "
                f"WHERE {where_sql} "
                "ORDER BY COALESCE(bookingdate, leaddate) DESC "
                "LIMIT 1"
            )
            df = self.db.run_query(sql, use_cache=True)
            if not df.empty:
                return str(df.iloc[0, 0])

            # Retry without product filter if none found
            if products:
                where_sql = " AND ".join([
                    "lead_agentid IS NOT NULL",
                    "lead_agentid <> ''",
                    name_predicate,
                ])
                sql = (
                    "SELECT lead_agentid FROM sme_analytics.sme_leadbookingrevenue "
                    f"WHERE {where_sql} ORDER BY COALESCE(bookingdate, leaddate) DESC LIMIT 1"
                )
                df = self.db.run_query(sql, use_cache=True)
                if not df.empty:
                    return str(df.iloc[0, 0])

            # Find the most common matching agent name across columns as a candidate
            unions = []
            for col in name_columns:
                unions.append(
                    f"SELECT {col} AS name FROM sme_analytics.sme_leadbookingrevenue "
                    f"WHERE {col} IS NOT NULL AND TRIM(CAST({col} AS VARCHAR)) <> '' "
                    f"AND LOWER(CAST({col} AS VARCHAR)) LIKE CONCAT('%%', '{name_safe}', '%%')"
                )
            union_sql = " UNION ALL ".join(unions)
            candidate_sql = (
                f"SELECT name FROM ( {union_sql} ) t WHERE name IS NOT NULL AND TRIM(CAST(name AS VARCHAR)) <> '' "
                "GROUP BY name ORDER BY COUNT(*) DESC LIMIT 1"
            )
            df_names = self.db.run_query(candidate_sql, use_cache=True)
            if not df_names.empty:
                best_name = str(df_names.iloc[0, 0]).replace("'", "''").strip().lower()
                eq_clauses = [f"LOWER(CAST({col} AS VARCHAR)) = '{best_name}'" for col in name_columns]
                eq_predicate = "( " + " OR ".join(eq_clauses) + " )"
                sql = (
                    "SELECT lead_agentid FROM sme_analytics.sme_leadbookingrevenue "
                    f"WHERE lead_agentid IS NOT NULL AND lead_agentid <> '' AND {eq_predicate} "
                    "ORDER BY COALESCE(bookingdate, leaddate) DESC LIMIT 1"
                )
                df = self.db.run_query(sql, use_cache=True)
                if not df.empty:
                    return str(df.iloc[0, 0])
        except Exception as e:
            print(f"Agent ID resolution failed: {e}")
        return None

    def resolve_agent_candidates(self, agent_name: str, products=None, limit: int = 5):
        """Return a list of candidate agents using fuzzy name selection, then resolve to codes.
        Output: [{code, name}]"""
        results: list[dict] = []
        if not agent_name:
            return results
        try:
            # 1) Fetch recent distinct agent names (agent-centric columns only)
            name_columns = [
                'leadassignedagentname', 'currentlyassigneduser', 'first_assigned_agent',
                'booking_agent', 'booking_agent_manager', 'booking_agent_manager2'
            ]
            unions = []
            for col in name_columns:
                unions.append(
                    f"SELECT {col} AS name, MAX(COALESCE(bookingdate, leaddate)) AS last_dt FROM sme_analytics.sme_leadbookingrevenue "
                    f"WHERE {col} IS NOT NULL AND TRIM(CAST({col} AS VARCHAR)) <> '' GROUP BY {col}"
                )
            union_sql = " UNION ALL ".join(unions)
            pool_sql = (
                f"SELECT name FROM ( {union_sql} ) t WHERE name IS NOT NULL GROUP BY name ORDER BY MAX(last_dt) DESC LIMIT {max(200, limit*50)}"
            )
            df_pool = self.db.run_query(pool_sql, use_cache=True)
            all_names = [str(x) for x in df_pool['name'].tolist() if str(x).strip()]
            if not all_names:
                return []

            # 2) Fuzzy score against the pool
            query_norm = " ".join(str(agent_name).lower().split())
            is_single_word_query = len(query_norm.split()) == 1

            def trigrams(s: str) -> set:
                s2 = s.replace(" ", "").lower()
                return {s2[i:i+3] for i in range(len(s2)-2)} if len(s2) >= 3 else set()
            q_tris = trigrams(query_norm)
            scored = []
            for nm in all_names:
                nm_norm = " ".join(nm.lower().split())
                
                # ADDED: Stricter check for single-name queries
                if is_single_word_query and query_norm not in nm_norm:
                    continue

                score = max(fuzz.WRatio(query_norm, nm_norm), fuzz.token_set_ratio(query_norm, nm_norm))
                if len(query_norm) >= 5 and nm_norm[:1] != query_norm[:1]:
                    if not (q_tris and (q_tris & trigrams(nm_norm))):
                        continue
                if score >= 88:
                    scored.append((nm, score))
            scored.sort(key=lambda x: x[1], reverse=True)
            top_names = [n for n, _ in scored[:limit]]
            if not top_names:
                return []

            # 3) Resolve each top name to the freshest code
            for nm in top_names:
                nm_safe = nm.replace("'", "''")
                equals = [f"LOWER(CAST({col} AS VARCHAR)) = '{nm_safe.lower()}'" for col in name_columns]
                prod_filter = ""
                if products:
                    ids_csv = ", ".join(str(p) for p in products)
                    prod_filter = f" AND investmenttypeid IN ({ids_csv})"
                sql = (
                    "SELECT lead_agentid AS code FROM sme_analytics.sme_leadbookingrevenue "
                    f"WHERE lead_agentid IS NOT NULL AND TRIM(lead_agentid) <> '' AND (" + " OR ".join(equals) + f"){prod_filter} "
                    "ORDER BY COALESCE(bookingdate, leaddate) DESC LIMIT 1"
                )
                try:
                    df_code = self.db.run_query(sql, use_cache=True)
                    if not df_code.empty:
                        code = str(df_code.iloc[0, 0]).strip()
                        if code:
                            results.append({"code": code, "name": nm})
                except Exception:
                    continue
            return results[:limit]
        except Exception as e:
            print(f"Agent candidate resolution failed: {e}")
            return results

    def ai_assisted_agent_name(self, user_text: str) -> str:
        """Use the AI model to extract the most likely agent name if extractor failed."""
        try:
            prompt = f"Extract the agent's full name from this message if present; otherwise return empty. Message: '{user_text}'. Respond with JSON: {{\"name\": \"...\"}}"
            response = model.generate_content(prompt)
            txt = (response.text or "").strip().replace('```json','').replace('```','')
            data = json.loads(txt)
            name = (data or {}).get('name')
            if isinstance(name, str) and len(name.strip()) >= 2:
                return name.strip()
        except Exception:
            pass
        return None

    def fetch_agent_status(self, lead_agentid: str):
        """Call internal agent tracker API and return parsed JSON list or None."""
        try:
            url = f"https://internalagenttracker.policybazaar.com/agentstatus/getagentrealtime/{lead_agentid}"
            resp = requests.get(url, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list):
                    return data
                if isinstance(data, dict):
                    return [data]
        except Exception as e:
            print(f"Agent status API error: {e}")
        return None

    def suggest_agent_names(self, name_query: str, limit_names: int = 400, top_k: int = 5):
        """Suggest closest agent names across known name columns using fuzzy matching."""
        try:
            name_query = (name_query or "").strip()
            if not name_query:
                return []
            name_columns = [
                'leadassignedagentname', 'currentlyassigneduser', 'leadreportingmanagername',
                'leadreportingmanagername2', 'first_assigned_agent', 'booking_agent',
                'booking_agent_manager', 'booking_agent_manager2'
            ]
            unions = []
            for col in name_columns:
                unions.append(
                    f"SELECT {col} AS name, MAX(COALESCE(bookingdate, leaddate)) AS last_dt FROM sme_analytics.sme_leadbookingrevenue "
                    f"WHERE {col} IS NOT NULL AND TRIM(CAST({col} AS VARCHAR)) <> '' GROUP BY {col}"
                )
            union_sql = " UNION ALL ".join(unions)
            sql = f"SELECT name FROM ( {union_sql} ) t WHERE name IS NOT NULL GROUP BY name ORDER BY MAX(last_dt) DESC LIMIT {int(limit_names)}"
            df = self.db.run_query(sql, use_cache=True)
            names = [str(x) for x in df['name'].tolist() if str(x).strip()]
            if not names:
                return []
            # Normalize
            q_norm = name_query.lower().strip()
            def norm(s: str) -> str:
                return " ".join(str(s).lower().split())
            # Pre-compute trigrams for stricter similarity
            def trigrams(s: str) -> set:
                s2 = s.replace(" ", "")
                return {s2[i:i+3] for i in range(len(s2)-2)} if len(s2) >= 3 else set()
            q_tris = trigrams(q_norm)

            scored = []
            for n in names:
                n_norm = norm(n)
                score_a = fuzz.WRatio(q_norm, n_norm)
                score_b = fuzz.token_set_ratio(q_norm, n_norm)
                score = max(score_a, score_b)
                # Additional guards to avoid poor suggestions like very short or different initials
                if len(q_norm) >= 5:
                    if n_norm[:1] != q_norm[:1]:
                        # Allow if there is decent trigram overlap
                        if not (q_tris and (q_tris & trigrams(n_norm))):
                            continue
                if score >= 85:
                    scored.append((n, score))
            scored.sort(key=lambda x: x[1], reverse=True)
            return [n for n, _ in scored[:top_k]]
        except Exception as e:
            print(f"Agent name suggestion failed: {e}")
            return []

    def get_recent_agent_ids_for_products(self, products, limit_per_product=20):
        """Return a dict product_id -> list of recent distinct lead_agentid values."""
        results = {}
        try:
            if not products:
                # All products: pick the most recently active distinct agents
                sql = (
                    "SELECT lead_agentid, MAX(COALESCE(bookingdate, leaddate)) AS last_dt "
                    "FROM sme_analytics.sme_leadbookingrevenue "
                    "WHERE lead_agentid IS NOT NULL AND TRIM(lead_agentid) <> '' "
                    "GROUP BY lead_agentid "
                    "ORDER BY last_dt DESC "
                    f"LIMIT {int(max(1, limit_per_product*3))}"
                )
                df = self.db.run_query(sql, use_cache=True)
                results[None] = [str(x) for x in df['lead_agentid'].tolist() if str(x).strip()]
                return results
            for pid in products:
                sql = (
                    "SELECT lead_agentid, MAX(COALESCE(bookingdate, leaddate)) AS last_dt "
                    "FROM sme_analytics.sme_leadbookingrevenue "
                    f"WHERE investmenttypeid = {int(pid)} AND lead_agentid IS NOT NULL AND TRIM(lead_agentid) <> '' "
                    "GROUP BY lead_agentid "
                    "ORDER BY last_dt DESC "
                    f"LIMIT {int(limit_per_product)}"
                )
                df = self.db.run_query(sql, use_cache=True)
                results[int(pid)] = [str(x) for x in df['lead_agentid'].tolist() if str(x).strip()]
        except Exception as e:
            print(f"Agent ID listing failed: {e}")
        return results

    def extract_agent_codes_from_text(self, text: str, products=None) -> list:
        """Extract explicit agent codes and resolve any mentioned names to codes."""
        codes: list = []
        try:
            # Explicit codes like PW32306
            code_tokens = re.findall(r"\b[A-Za-z]{1,6}\d{2,8}\b", text or "")
            codes.extend(code_tokens)
            # Naive multi-name extraction after 'for' or comma/and separated
            names = []
            m = re.search(r"for\s+(.+)$", text or "", flags=re.IGNORECASE)
            if m:
                tail = m.group(1)
                parts = re.split(r",| and ", tail, flags=re.IGNORECASE)
                for p in parts:
                    n = p.strip()
                    if n and not re.fullmatch(r"[A-Za-z]{1,6}\d{2,8}", n):
                        names.append(n)
            # Resolve names to codes (pick the freshest candidate)
            for name in names:
                cands = self.resolve_agent_candidates(name, products, limit=1)
                if cands:
                    codes.append(cands[0]["code"])
        except Exception as e:
            print(f"Agent code extraction failed: {e}")
        # Deduplicate
        uniq = []
        for c in codes:
            if c not in uniq:
                uniq.append(c)
        return uniq

    def parse_agent_fields(self, text: str) -> list:
        """Parse requested fields from text based on known API keys; default set if none specified."""
        known = [
            "AgentCode", "AgentName", "Status", "LastUpdatedOn", "Asterisk_Url", "AgentIP", "CallingCompany",
            "IsWFH", "IsCustAnswered", "Grade", "Context", "TLName", "VCCount", "VCConnectCount", "UniqueVCCount",
            "TotalCalls", "UniqueDials", "ConnectedDials", "TotalTalkTime", "OpenLeadCount", "Callableleads", "FutureCB"
        ]
        text_l = (text or "").lower()
        requested = [k for k in known if k.lower() in text_l]
        if not requested:
            requested = ["AgentName", "AgentCode", "Status", "ConnectedDials", "TotalTalkTime", "LastUpdatedOn"]
        return requested

    def parse_status_filter(self, text: str) -> set:
        """Return a set of desired statuses parsed from text (normalized to upper). Empty means default 'active' set."""
        t = (text or "").lower()
        want = set()
        # Map common words/phrases to status values
        mapping = {
            "pause": "PAUSE",
            "on pause": "PAUSE",
            "busy": "BUSY",
            "idle": "IDLE",
            "available": "AVAILABLE",
            "ready": "READY",
            "oncall": "ONCALL",
            "on call": "ON CALL",
            "ringing": "RINGING",
            "tea": "TEA",
            "unavailable": "UNAVAILABLE",
        }
        for key, status in mapping.items():
            if key in t:
                want.add(status)
        return want

    def get_all_agent_ids_for_products(self, products):
        """
        Return dict product_id -> all distinct lead_agentid values.
        MODIFIED: Fetches only agents with bookings in the current or previous month.
        """
        results = {}
        try:
            # Common WHERE clause for active agents based on recent bookings
            active_agent_filter = (
                "lead_agentid IS NOT NULL AND TRIM(lead_agentid) <> '' "
                "AND booking_status = 'IssuedBusiness' "
                "AND bookingdate >= DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '1' MONTH"
            )

            if not products:
                sql = (
                    "SELECT DISTINCT lead_agentid FROM sme_analytics.sme_leadbookingrevenue "
                    f"WHERE {active_agent_filter}"
                )
                print("DEBUG: Fetching ACTIVE agent codes (this/last month bookings, no product filter)")
                df = self.db.run_query(sql, use_cache=False)
                results[None] = [str(x) for x in df.iloc[:, 0].tolist() if str(x).strip()]
                return results

            for pid in products:
                sql = (
                    "SELECT DISTINCT lead_agentid FROM sme_analytics.sme_leadbookingrevenue "
                    f"WHERE investmenttypeid = {int(pid)} AND {active_agent_filter}"
                )
                print(f"DEBUG: Fetching ACTIVE agent codes for product {pid}")
                df = self.db.run_query(sql, use_cache=False)
                results[int(pid)] = [str(x) for x in df.iloc[:, 0].tolist() if str(x).strip()]
        except Exception as e:
            print(f"Agent ALL ID listing failed: {e}")
        return results
    
    def execute_sql_query(self, sql_query, explanation, user_id: str = None, allow_personal_cache: bool = True):
        sql_query = sql_query.strip().rstrip(';')
        print(f"DEBUG: ----- EXECUTING SQL -----\n{sql_query}\nDEBUG: -------------------------")
        try:
            # Use per-user cache only if explicitly allowed and present
            query_id = hashlib.md5(sql_query.encode()).hexdigest()[:8]
            if allow_personal_cache and user_id and USER_QUERY_CACHE.get(user_id, {}).get(query_id):
                cached = USER_QUERY_CACHE[user_id][query_id]
                df_masked = pd.DataFrame(cached.get("data", []))
                result_text = cached.get("result_text")
                explanation = cached.get("explanation", explanation)
                return result_text, query_id, df_masked

            # Always bypass global cache for interactive user queries
            df = self.db.run_query(sql_query, use_cache=False)
            if df.empty:
                return "No data found for your query.", None, None

            df_masked = masking_service.mask_dataframe(df)
            self.save_query_result(query_id, df, df_masked, sql_query, explanation)

            if len(df) == 1 and len(df.columns) == 1:
                value = df.iloc[0, 0]
                result_text = (
                    f"📊 **Result**: {value:,}\n\n"
                    f"💡 {explanation}\n\n"
                    f"🔍 **Query**:\n```\n{sql_query}\n```\n"
                    f"📎 Query ID: `{query_id}`"
                )
            else:
                table = df.to_string(index=False, max_rows=20)
                result_text = (
                    f"📊 **Results**:\n```\n{table}\n```\n\n"
                    f"💡 {explanation}\n\n"
                    f"🔍 **Query**:\n```\n{sql_query}\n```\n"
                    f"📎 Query ID: `{query_id}`"
                )
            
            return result_text, query_id, df_masked

        except Exception as e:
            return f"❌ Query failed: {str(e)}", None, None
    
    def save_query_result(self, query_id, df_original, df_masked, sql_query, explanation):
        os.makedirs("query_results", exist_ok=True)
        with open(f"query_results/{query_id}.json", "w") as f:
            json.dump({
                "data_unmasked": df_original.to_dict('records'),
                "data": df_masked.to_dict('records'), 
                "sql": sql_query, 
                "explanation": explanation
            }, f)

    def get_categorical_values_context(self, dynamic_distincts: dict):
        context_parts = []
        for col, meta in TABLE_SCHEMA.items():
            if meta.get("is_categorical") and meta.get("pii_level") != "high":
                values = (dynamic_distincts or {}).get(col) or meta.get("sample_values", [])
                if values:
                    values_str = ", ".join([f"'{v}'" for v in values[:8]])
                    context_parts.append(f"- `{col}` can be: {values_str}")
        if context_parts:
            return "\n**Categorical Values**:\n" + "\n".join(context_parts)
        return ""

# Globals
db_manager = SimpleDatabase(os.getenv("PRESTO_CONNECTION"))
bot = SimplifiedBot(db_manager)
subscription_manager = subscription_manager
business_logic_manager = BusinessLogicManager()
USER_SESSIONS: Dict[str, Dict[str, Any]] = {}
USER_QUERY_CACHE: Dict[str, Dict[str, Any]] = {}


def looks_like_feedback(message: str) -> bool:
    text = (message or "").lower()
    keywords = [
        "should", "should have", "supposed to", "must", "always", "include", "exclude", "prefer",
        "use like", "use regex", "use ", "filter by", "group by", "remove product", "wrong", "incorrect", "show",
        "please add", "please use", "make sure", "instead"
    ]
    return any(k in text for k in keywords)


def send_feedback_to_channel(feedback_id: int, user_id: str, original_text: str, entities: dict, context: dict | None = None):
    try:
        ctx = context or {}
        summary_lines = []
        if entities:
            if entities.get("products"):
                summary_lines.append(f"Products: {entities.get('products')}")
            if entities.get("metric"):
                summary_lines.append(f"Metric: {entities.get('metric')}")
            if (entities.get("time") or {}).get("key"):
                summary_lines.append(f"Time: {(entities.get('time') or {}).get('key')}")
            if entities.get("dimensions"):
                summary_lines.append(f"Dimensions: {entities.get('dimensions')}")
            if entities.get("filters"):
                summary_lines.append(f"Filters: {entities.get('filters')}")
        # Include SQL/explanation/reason if present in context
        if ctx.get("sql"):
            summary_lines.append(f"SQL: ```{ctx.get('sql')}```")
        if ctx.get("explanation"):
            summary_lines.append(f"Explanation: {ctx.get('explanation')}")
        if ctx.get("reason"):
            summary_lines.append(f"Reason: {ctx.get('reason')}")
        if ctx.get("query_id"):
            summary_lines.append(f"Query ID: `{ctx.get('query_id')}`")
        summary = "\n".join(f"• {line}" for line in summary_lines if line)

        notification = (
            f"🔔 *New Feedback for Review* | ID: `{feedback_id}`\n"
            f"*User*: <@{user_id}>\n"
            f"*Original Message*: `{original_text}`\n"
            f"{summary}"
        )
        blocks = [
            {"type": "section", "text": {"type": "mrkdwn", "text": notification}},
            {
                "type": "actions",
                "block_id": f"feedback_actions_{feedback_id}",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "✅ Approve Logic"},
                        "action_id": "approve_feedback",
                        "value": str(feedback_id),
                        "style": "primary",
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "❌ Reject"},
                        "action_id": "reject_feedback",
                        "value": str(feedback_id),
                        "style": "danger",
                    },
                ],
            },
        ]
        app.client.chat_postMessage(channel=FEEDBACK_CHANNEL_ID, text="New feedback received", blocks=blocks)
    except Exception as e:
        print(f"Failed to post feedback to channel: {e}")

def run_main_logic(text: str, user_id: str, say):
    """Main logic router: classifies intent and routes to the correct handler."""
    try:
        # 1. Classify the intent of the query
        intent = classify_intent(text)

        if intent == 'business_logic':
            debug(f"Routing to BusinessLogicManager for user {user_id}")
            say("🧠 This seems like a complex query. Let me think...")
            result = business_logic_manager.generate_sql_from_logic(text)
            if "error" in result or "sql" not in result:
                say(f"❌ I had trouble understanding that logic. Error: {result.get('error', 'Unknown')}")
                return
            # Always execute the SQL if present
            sql_query = result.get("sql")
            explanation = result.get("explanation")
            result_text, query_id, df = bot.execute_sql_query(sql_query, explanation, user_id)
            say(result_text)
            # Ask to save the logic (optional)
            if df is not None and not df.empty:
                pass  # TODO: Implement a block kit action to ask user to save
        else: # Handle simple_metric and other intents
            debug(f"Routing to standard logic for user {user_id}")
            entities = nlp_extractor.extract(text)
            sql_payload = build_sql(entities)
            if sql_payload.get("intent") != "metric_query":
                say("I'm sorry, I'm not sure how to handle that request.")
                return
            sql_query = sql_payload.get("sql")
            explanation = sql_payload.get("explanation")
            result_text, query_id, df = bot.execute_sql_query(sql_query, explanation, user_id)
            say(result_text)
        # After any query, check for embedded feedback
        feedback_keywords = ["for future understand", "remember that", "the logic should be", "for future reference"]
        text_lower = text.lower()
        for keyword in feedback_keywords:
            if keyword in text_lower:
                feedback_text = text.split(keyword, 1)[1].strip()
                if feedback_text:
                    say(f"📝 Noted for expert review:\n> _{feedback_text}_")
                    feedback_id = business_logic_manager.store_feedback(
                        user_id=user_id,
                        original_query=text,
                        feedback_text=feedback_text,
                        context={"query_id": query_id, "sql": sql_query, "explanation": explanation}
                    )
                if feedback_id:
                        send_feedback_to_channel(
                            feedback_id,
                            user_id,
                            text,
                            {},
                            context={"query_id": query_id, "sql": sql_query, "explanation": explanation, "reason": feedback_text}
                        )
                break # Stop after finding the first keyword
    except Exception as e:
        debug(f"Error in run_main_logic: {e}")
        say("❌ Something went wrong. Please try again.")


def show_main_menu(user_id: str, say):
    """Present the main menu to select workflow mode."""
    debug(f"Showing main menu to user {user_id}")
    blocks = [
        {"type": "section", "text": {"type": "mrkdwn", "text": "👋 What would you like to do?"}},
        {
            "type": "actions",
            "block_id": f"main_menu_{user_id}",
            "elements": [
                {"type": "button", "text": {"type": "plain_text", "text": "📈 Metrics"}, "action_id": "choose_metrics", "style": "primary"},
                {"type": "button", "text": {"type": "plain_text", "text": "🧑‍💼 Agent Status"}, "action_id": "choose_agent_status"},
                {"type": "button", "text": {"type": "plain_text", "text": "ℹ️ Help"}, "action_id": "show_help"},
                {"type": "button", "text": {"type": "plain_text", "text": "🛑 End Session"}, "action_id": "end_session"}
            ],
        },
    ]
    say(blocks=blocks, text="Choose a mode")


def handle_agent_mode(text: str, user_id: str, say):
    """Dedicated agent-status workflow: supports single-agent or active summary."""
    try:
        t = (text or "").lower()
        debug(f"Agent mode input: '{text}' (user {user_id})")
        # Quick summary intent in agent mode: prefer AI agent.mode if present
        ents = nlp_extractor.extract(text)
        agent_ai = ents.get("agent") or {}
        ai_mode = (agent_ai or {}).get("mode")
        is_summary = ai_mode == "summary" or any(k in t for k in ["agents active", "active agents", "agents online", "how many agents", "how many agents are on", "number of agents"])
        if is_summary:
            # Parse products if present, otherwise all
            products = ents.get("products") or []
            # MODIFIED: Always fetch all agents, do not sample
            pid_to_agents = bot.get_all_agent_ids_for_products(products)
            # Optional: specific agent codes or names requested
            explicit_codes = list(agent_ai.get("codes") or []) or bot.extract_agent_codes_from_text(text, products)
            requested_fields = list(agent_ai.get("fields") or []) or bot.parse_agent_fields(text)
            if ("name" in t or "names" in t) and "AgentName" not in requested_fields:
                requested_fields = ["AgentName", "AgentCode", "Status"] + [f for f in requested_fields if f not in ("AgentName", "AgentCode", "Status")]
            summary_lines = []
            details_lines = []
            desired_statuses = set([str(s).upper() for s in (agent_ai.get("status_filters") or [])]) or set(bot.parse_status_filter(text))
            for pid, agent_ids in pid_to_agents.items():
                active_count = 0
                check_ids = explicit_codes or agent_ids
                debug(f"Agent summary - product={pid} checking {len(check_ids)} codes")
                for aid in check_ids:
                    debug(f"Calling status API for {aid}")
                    status_list = bot.fetch_agent_status(aid)
                    if not status_list:
                        continue
                    s = status_list[0] if isinstance(status_list, list) else status_list
                    status = str(s.get("Status", "")).upper()
                    debug(f"{aid} -> {status}")
                    # If user specified statuses (e.g., 'pause'), count only those; else count the default active set
                    default_active = {"READY", "AVAILABLE", "IDLE", "ONCALL", "ON CALL", "BUSY"}
                    if desired_statuses:
                        if status in desired_statuses:
                            active_count += 1
                    else:
                        if status in default_active:
                            active_count += 1
                        # Build a detail line with requested fields
                        parts = []
                        for key in requested_fields:
                            val = s.get(key)
                            if val is not None and val != "":
                                if key == "AgentName" and s.get("AgentCode"):
                                    parts.append(f"{val} ({s.get('AgentCode')})")
                                elif key not in ("AgentCode",):
                                    parts.append(f"{key}: {val}")
                        if parts:
                            details_lines.append(" - " + " | ".join(parts))
                label = f"Product {pid}" if pid is not None else "All Products"
                if desired_statuses:
                    status_label = "/".join(sorted(desired_statuses))
                    summary_lines.append(f"- {label}: {active_count} with status {status_label}")
                else:
                    summary_lines.append(f"- {label}: {active_count} active now")
            header = "👥 Agent activity:\n" + ("\n".join(summary_lines) if summary_lines else "No agents found.")
            # Append details if any
            if details_lines:
                # Limit to avoid Slack overflow
                total = len(details_lines)
                preview_count = min(30, total)
                detail_preview = "\n".join(details_lines[:preview_count])
                if total > preview_count:
                    header += f"\n\n👤 Active agents (showing {preview_count} of {total}):\n" + detail_preview
                else:
                    header += "\n\n👤 Active agents:\n" + detail_preview
            say(header)
            return

        # Otherwise: single-agent lookup flow (reuse existing logic)
        entities = nlp_extractor.extract(text)
        agent_name = ((entities.get("agent") or {}).get("name")) or None
        if not agent_name:
            agent_name = bot.ai_assisted_agent_name(text)
        if agent_name:
            agent_name = re.sub(r"\bin\s+[A-Za-z\s]+$", "", agent_name, flags=re.IGNORECASE).strip()
            if agent_name.lower() in ("today", "yesterday", "this week", "this month"):
                agent_name = None
        products = entities.get("products") or []
        if not agent_name:
            say("Please provide the agent name or code (e.g., 'PW32306').")
            return
        # Direct code support or codes from AI
        ai_codes = (ents.get("agent") or {}).get("codes") or []
        if re.fullmatch(r"[A-Za-z]{1,6}\d{2,8}", agent_name):
            ai_codes = [agent_name]
        if ai_codes:
            # If multiple codes provided, ask to pick one
            if len(ai_codes) > 1:
                lines = [f"- `{c}`" for c in ai_codes]
                say("Multiple agent codes provided. Please specify one:\n" + "\n".join(lines))
                return
            lead_agentid = ai_codes[0]
            candidate_label = None
        else:
            candidates = bot.resolve_agent_candidates(agent_name, products, limit=5)
            if not candidates:
                suggestions = bot.suggest_agent_names(agent_name)
                if suggestions:
                    say("Couldn't find any agent for that name. Did you mean: " + ", ".join(suggestions) + "?")
                else:
                    say("Couldn't find any agent for that name. Try exact CRM name or provide agent code.")
                return
            if len(candidates) > 1:
                lines = [f"- {c['name'] or 'Unknown'} (code: `{c['code']}`)" for c in candidates]
                say("Multiple agents match that name. Please specify the agent code from below:\n" + "\n".join(lines))
                return
            lead_agentid = candidates[0]["code"]
            candidate_label = candidates[0].get("name")

        status_list = bot.fetch_agent_status(lead_agentid)
        if not status_list:
            say(f"No live status found for agent (ID: {lead_agentid}).")
            return
        s = status_list[0]
        # Build dynamic fields based on user request
        requested_fields = bot.parse_agent_fields(text)
        fields = []
        for key in requested_fields:
            if s.get(key) is not None and s.get(key) != "":
                fields.append({"type": "mrkdwn", "text": f"*{key}:* {s.get(key)}"})
        blocks = [
            {"type": "section", "text": {"type": "mrkdwn", "text": f"🔎 Agent live status (ID: `{lead_agentid}`)"}},
            {"type": "section", "fields": fields[:10]} if fields else {"type": "section", "text": {"type": "mrkdwn", "text": "No additional details available."}},
            {"type": "actions", "elements": [{"type": "button", "text": {"type": "plain_text", "text": "🏠 Main Menu"}, "action_id": "show_menu"}]}
        ]
        say(blocks=blocks, text="Agent status")
        return
    except Exception as e:
        print(f"Error in handle_agent_mode: {e}")
        say("❌ Something went wrong in agent mode.")

# --- Web Chat Integration ---
web_app = Flask(__name__)
CORS(web_app)
slack_web_client = WebClient(token=os.getenv("SLACK_BOT_TOKEN"))
WEB_CHAT_CHANNEL = "C098DTBQZ8E"
web_replies_store = []  # [{id, text}]
web_message_counter = 0

# Add this function to run the Flask app

def run_web_app():
    import os
    port = int(os.environ.get("PORT", 5000))
    web_app.run(host='0.0.0.0', port=port)

# Store last query_id for web_user
WEB_USER_LAST_QUERY_ID = None

@web_app.route('/api/chat', methods=['POST'])
def web_chat():
    global WEB_USER_LAST_QUERY_ID
    data = request.json
    user_message = data.get('message', '')
    action_id = data.get('action_id')
    user_id = data.get('user_id') or 'web_user'
    responses = []

    def say(msg=None, **kwargs):
        global WEB_USER_LAST_QUERY_ID
        # If this is a query result, add Subscribe and Feedback buttons
        if msg is not None and 'Query ID:' in msg:
            # Extract query_id from the message
            import re
            m = re.search(r'Query ID: `?(\w+)`?', msg)
            query_id = m.group(1) if m else None
            if query_id:
                WEB_USER_LAST_QUERY_ID = query_id
                # Add buttons for download, subscribe, feedback
                blocks = [
                    {"type": "section", "text": {"type": "mrkdwn", "text": msg}},
                    {"type": "actions", "elements": [
                        {"type": "button", "text": {"type": "plain_text", "text": "📥 Download Excel"}, "action_id": "download_excel", "value": query_id},
                        {"type": "button", "text": {"type": "plain_text", "text": "🔔 Subscribe"}, "action_id": "subscribe_alerts", "value": query_id},
                        {"type": "button", "text": {"type": "plain_text", "text": "📝 Feedback"}, "action_id": "feedback", "value": query_id}
                    ]}
                ]
                responses.append({'type': 'blocks', 'blocks': blocks, 'text': msg})
                return
        if msg is not None:
            responses.append({'type': 'text', 'text': msg})
        elif 'blocks' in kwargs:
            blocks = kwargs['blocks']
            for block in blocks:
                if block.get('type') == 'actions':
                    for el in block.get('elements', []):
                        if el.get('action_id') == 'download_excel' and 'value' in el:
                            WEB_USER_LAST_QUERY_ID = el['value']
            responses.append({'type': 'blocks', 'blocks': blocks, 'text': kwargs.get('text', '')})
        elif 'text' in kwargs:
            responses.append({'type': 'text', 'text': kwargs['text']})

    # Handle action_id (button click)
    if action_id:
        if action_id == 'show_menu':
            show_main_menu(user_id, say)
        elif action_id == 'choose_metrics':
            say('Please enter your metrics query (e.g., "fire insurance bookings this month").')
        elif action_id == 'choose_agent_status':
            USER_SESSIONS[user_id] = {"mode": "agent"}
            say('Please enter your agent status query (e.g., "agents active now").')
        elif action_id == 'show_help':
            say('ℹ️ You can ask me about insurance metrics, agent status, or set up alerts. Try: "fire insurance bookings this month" or "agents active now".')
        elif action_id == 'end_session':
            say('🛑 Session ended. Type anything to start again.');
        elif action_id == 'download_excel':
            if WEB_USER_LAST_QUERY_ID:
                download_url = f"/download_excel/{WEB_USER_LAST_QUERY_ID}"
                responses.append({'type': 'download', 'url': download_url, 'label': 'Download Excel'})
            else:
                responses.append({'type': 'text', 'text': 'No query result available for download.'})
        elif action_id == 'subscribe_alerts':
            # Ask for frequency if not provided
            frequency = data.get('frequency')
            if not frequency:
                # Show frequency options as buttons
                freq_blocks = [
                    {"type": "section", "text": {"type": "mrkdwn", "text": "How often do you want to receive alerts for this query?"}},
                    {"type": "actions", "elements": [
                        {"type": "button", "text": {"type": "plain_text", "text": "Hourly"}, "action_id": "subscribe_alerts", "value": "hourly"},
                        {"type": "button", "text": {"type": "plain_text", "text": "Daily (9 AM)"}, "action_id": "subscribe_alerts", "value": "daily"},
                        {"type": "button", "text": {"type": "plain_text", "text": "Weekly (Mon 9 AM)"}, "action_id": "subscribe_alerts", "value": "weekly"}
                    ]}
                ]
                responses.append({'type': 'blocks', 'blocks': freq_blocks, 'text': ''})
            else:
                # Actually add the subscription
                # Find the last query context for this user
                last_query_id = WEB_USER_LAST_QUERY_ID
                query_context = None
                if last_query_id and os.path.exists(f"query_results/{last_query_id}.json"):
                    with open(f"query_results/{last_query_id}.json", "r") as f:
                        payload = json.load(f)
                    query_context = {
                        "sql": payload.get("sql"),
                        "explanation": payload.get("explanation")
                    }
                else:
                    query_context = {"sql": None, "explanation": None}
                subscription_manager.add_subscription(user_id, 'web_chat', query_context, frequency)
                responses.append({'type': 'text', 'text': f'🔔 You are now subscribed to {frequency} alerts for this query!'})
        elif action_id == 'feedback':
            responses.append({'type': 'feedback_form', 'query_id': WEB_USER_LAST_QUERY_ID})
        elif action_id == 'submit_feedback':
            feedback = data.get('feedback', '')
            query_id = data.get('query_id', '')
            business_logic_manager.store_feedback(
                user_id=user_id,
                original_query=f"Query ID: {query_id}",
                feedback_text=feedback,
                context={"query_id": query_id, "feedback": feedback}
            )
            responses.append({'type': 'text', 'text': '✅ Thank you for your feedback!'})
        else:
            say(f'Action: {action_id}')
    else:
        # If user_message is empty, only show main menu
        if not user_message or user_message.strip() == '':
            show_main_menu(user_id, say)
        elif user_message.strip().lower() in ("menu", "main menu", "start over", "restart"):
            show_main_menu(user_id, say)
        else:
            intent = classify_intent(user_message)
            if intent == 'agent_status' or USER_SESSIONS.get(user_id, {}).get("mode") == "agent":
                handle_agent_mode(user_message, user_id, say)
            else:
                run_main_logic(user_message, user_id, say)

    if responses:
        return jsonify({'responses': responses})
    else:
        return jsonify({'responses': [{'type': 'text', 'text': "Sorry, I didn't understand that."}]})

@web_app.route('/api/replies', methods=['GET'])
def web_get_replies():
    since = int(request.args.get('since', 0))
    # Return all replies with id > since
    new_replies = [msg for msg in web_replies_store if msg['id'] > since]
    return jsonify(new_replies)

@web_app.route('/download_excel/<query_id>')
def download_excel(query_id):
    # Serve the Excel file for download
    export_path = f"temp_exports/{query_id}.xlsx"
    if not os.path.exists(export_path):
        # Try to generate the file from the cached query result
        try:
            with open(f"query_results/{query_id}.json", "r") as f:
                payload = json.load(f)
            df = pd.DataFrame(payload.get("data_unmasked") or payload.get("data", []))
            os.makedirs("temp_exports", exist_ok=True)
            df.to_excel(export_path, index=False)
        except Exception as e:
            return f"Failed to generate Excel file: {e}", 404
    return send_file(export_path, as_attachment=True)

# --- Listen for bot replies in the channel ---
from slack_bolt.context.say import Say

def store_web_reply(text):
    global web_message_counter
    web_message_counter += 1
    web_replies_store.append({'id': web_message_counter, 'text': text})

# Remove old_handle_message logic (not needed)

@app.event("app_mention")
def handle_message(event, say: Say):
    user_id = event["user"]
    text = re.sub(r'^<@\w+>\s*', '', event.get("text", "")).strip()
    print(f"\n\nDEBUG: ----- NEW MESSAGE RECEIVED -----\nUser: {user_id}\nText: '{text}'\n------------------------------------")
    if not text:
        show_main_menu(user_id, say)
        return
    if text.strip().lower() in ("menu", "main menu", "start over", "restart"):
        show_main_menu(user_id, say)
        return
    mode = (USER_SESSIONS.get(user_id) or {}).get("mode")
    if not mode:
        tl = text.lower()
        if any(k in tl for k in ["agent", "agents"]):
            USER_SESSIONS[user_id] = {"mode": "agent"}
            return handle_agent_mode(text, user_id, say)
        show_main_menu(user_id, say)
        return
    if mode == 'agent':
        debug(f"Routing to agent mode for user {user_id}")
        return handle_agent_mode(text, user_id, say)
    debug(f"Routing to run_main_logic for user {user_id} (mode={mode})")
    say("🤖 Processing...")
    # Capture the say function to also store web replies
    def say_and_store(msg=None, **kwargs):
        if msg:
            say(msg, **kwargs)
            store_web_reply(msg)
        elif 'text' in kwargs:
            say(kwargs['text'], **kwargs)
            store_web_reply(kwargs['text'])
    run_main_logic(text, user_id, say_and_store)

# All other handlers (subscribe, feedback, etc.) remain the same

# Action: Download Excel for last query result
@app.action("download_excel")
def handle_download_excel(ack, body, say):
    ack()
    try:
        query_id = body["actions"][0]["value"]
        with open(f"query_results/{query_id}.json", "r") as f:
            payload = json.load(f)
        # Use unmasked data if available, otherwise fall back to masked (legacy)
        df = pd.DataFrame(payload.get("data_unmasked") or payload.get("data", []))
        export_path = f"temp_exports/{query_id}.xlsx"
        os.makedirs("temp_exports", exist_ok=True)
        df.to_excel(export_path, index=False)
        app.client.files_upload_v2(
            channel=body["channel"]["id"],
            file=export_path,
            filename=f"query_result_{query_id}.xlsx",
            initial_comment="📊 Here's your data!",
            thread_ts=body["message"]["ts"],
        )
        try:
            os.remove(export_path)
        except Exception:
            pass
    except Exception as e:
        say(f"❌ Failed to generate Excel file: {e}", thread_ts=body.get("message", {}).get("ts"))


# Action: Subscribe to alerts
@app.action("subscribe_alerts")
def handle_subscribe_alerts(ack, body, client):
    ack()
    try:
        client.views_open(
            trigger_id=body["trigger_id"],
            view={
                "type": "modal",
                "callback_id": "submit_subscription",
                "title": {"type": "plain_text", "text": "Subscribe to Alerts"},
                "submit": {"type": "plain_text", "text": "Subscribe"},
                "blocks": [
                    {
                        "type": "input",
                        "block_id": "frequency_block",
                        "label": {"type": "plain_text", "text": "How often?"},
                        "element": {
                            "type": "static_select",
                            "action_id": "frequency_select",
                            "options": [
                                {"text": {"type": "plain_text", "text": "Hourly"}, "value": "hourly"},
                                {"text": {"type": "plain_text", "text": "Daily (9 AM)"}, "value": "daily"},
                                {"text": {"type": "plain_text", "text": "Weekly (Mon 9 AM)"}, "value": "weekly"},
                            ],
                        },
                    }
                ],
                "private_metadata": json.dumps(
                    {
                        "query_id": body["actions"][0]["value"],
                        "channel_id": body["channel"]["id"],
                    }
                ),
            },
        )
    except Exception as e:
        print(f"Error opening subscription view: {e}")


@app.action("show_menu")
def handle_show_menu(ack, body, say):
    """Handler for the 'show_menu' action button."""
    ack()
    user_id = body["user"]["id"]
    show_main_menu(user_id, say)


@app.action("show_help")
def handle_show_help(ack, body, say):
    """Show detailed help text for users."""
    ack()
    help_text = (
        "• Metrics: ask for leads/bookings/revenue with products/time/dimensions.\n"
        "• Agent: ask for 'agent status for <name>' or 'agents active now'.\n"
        "• Type 'menu' to switch modes; 'end session' to reset."
    )
    say(help_text)

@app.action("end_session")
def handle_end_session(ack, body, say):
    ack()
    user_id = body.get("user", {}).get("id") or body.get("user", {}).get("user_id")
    USER_SESSIONS.pop(user_id, None)
    say("🛑 Session ended.")


@app.action("download_schema")
def handle_download_schema(ack, body, say):
    ack()
    try:
        import csv
        os.makedirs("temp_exports", exist_ok=True)
        csv_path = os.path.join("temp_exports", "schema.csv")
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["column", "data_type", "is_categorical", "pii_level", "description"])
            for col, meta in TABLE_SCHEMA.items():
                writer.writerow([
                    col,
                    meta.get("data_type", ""),
                    meta.get("is_categorical", False),
                    meta.get("pii_level", "none"),
                    meta.get("description", ""),
                ])
        app.client.files_upload_v2(
            channel=body["channel"]["id"],
            file=csv_path,
            filename="schema.csv",
            initial_comment="📚 Database schema",
            thread_ts=body["message"]["ts"],
        )
        try:
            os.remove(csv_path)
        except Exception:
            pass
    except Exception as e:
        say(text=f"❌ Failed to download schema: {e}", thread_ts=body.get("message", {}).get("ts"))


# Action: Mark result as Correct (store per-user cache and notify experts)
@app.action("mark_correct")
def handle_mark_correct(ack, body, say):
    ack()
    try:
        user_id = body.get("user", {}).get("id") or body.get("user", {}).get("user_id")
        query_id = body["actions"][0]["value"]
        # Load result context to cache per-user
        with open(f"query_results/{query_id}.json", "r") as f:
            payload = json.load(f)
        result_text = "Cached personal result"
        # Persist in per-user cache
        USER_QUERY_CACHE.setdefault(user_id, {})[query_id] = {
            "data": payload.get("data", []),
            "sql": payload.get("sql"),
            "explanation": payload.get("explanation"),
            "result_text": None,  # full text is regenerated as needed
            "created_at": time.time(),
        }
        say(text="✅ Marked as correct. I will reuse this result for you if you ask the same thing again.", thread_ts=body.get("message", {}).get("ts"))
        # Notify experts for potential approval for global logic
        try:
            feedback_id = business_logic_manager.store_feedback(
                user_id=user_id,
                original_query=body.get("message", {}).get("text", ""),
                feedback_text=f"User marked query `{query_id}` as correct. Consider approving logic for broader use.",
                context={"query_id": query_id, "sql": payload.get("sql"), "explanation": payload.get("explanation")},
            )
            if feedback_id:
                send_feedback_to_channel(
                    feedback_id,
                    user_id,
                    body.get("message", {}).get("text", ""),
                    {},
                    context={"query_id": query_id, "sql": payload.get("sql"), "explanation": payload.get("explanation")},
                )
        except Exception:
            pass
    except Exception as e:
        say(text=f"❌ Could not mark as correct: {e}", thread_ts=body.get("message", {}).get("ts"))


# Action: Mark result as Wrong (collect feedback and notify experts)
@app.action("mark_wrong")
def handle_mark_wrong(ack, body, client, say):
    ack()
    try:
        user_id = body.get("user", {}).get("id") or body.get("user", {}).get("user_id")
        query_id = body["actions"][0]["value"]
        # Open a modal to capture what went wrong
        client.views_open(
            trigger_id=body["trigger_id"],
            view={
                "type": "modal",
                "callback_id": "submit_wrong_feedback",
                "title": {"type": "plain_text", "text": "What was wrong?"},
                "submit": {"type": "plain_text", "text": "Submit"},
                "blocks": [
                    {
                        "type": "input",
                        "block_id": "wrong_reason_block",
                        "element": {"type": "plain_text_input", "action_id": "wrong_reason", "multiline": True},
                        "label": {"type": "plain_text", "text": "Please describe the issue"},
                    }
                ],
                "private_metadata": json.dumps({"query_id": query_id, "channel_id": body["channel"]["id"]}),
            },
        )
    except Exception as e:
        say(text=f"❌ Could not open feedback form: {e}", thread_ts=body.get("message", {}).get("ts"))


@app.view("submit_wrong_feedback")
def handle_wrong_feedback_submission(ack, body, say):
    ack()
    user_id = body["user"]["id"]
    try:
        metadata = json.loads(body["view"]["private_metadata"])
        query_id = metadata["query_id"]
        channel_id = metadata["channel_id"]
        reason = body["view"]["state"]["values"]["wrong_reason_block"]["wrong_reason"]["value"]
        # Store feedback and notify experts
        feedback_id = business_logic_manager.store_feedback(
            user_id=user_id,
            original_query=f"Query ID: {query_id}",
            feedback_text=reason or "User marked result as wrong",
            context={"query_id": query_id, "reason": reason},
        )
        if feedback_id:
            send_feedback_to_channel(
                feedback_id,
                user_id,
                f"Query marked wrong: {query_id}",
                {},
                context={"query_id": query_id, "reason": reason},
            )
        say(channel=channel_id, text="✅ Thanks for the feedback. Our experts will review it.")
    except Exception as e:
        say(text=f"❌ Error submitting feedback: {e}")

@app.view("submit_subscription")
def handle_subscription_submission(ack, body, say):
    ack()
    user_id = body["user"]["id"]
    try:
        metadata = json.loads(body["view"]["private_metadata"])
        query_id = metadata["query_id"]
        channel_id = metadata["channel_id"]
        selected_frequency = (
            body["view"]["state"]["values"]["frequency_block"]["frequency_select"]["selected_option"]["value"]
        )
        with open(f"query_results/{query_id}.json", "r") as f:
            query_context = json.load(f)
        sub_id = subscription_manager.add_subscription(user_id, channel_id, query_context, selected_frequency)
        if sub_id:
            say(channel=channel_id, text=f"✅ Subscribed to {selected_frequency} alerts. ID: `{sub_id}`")
        else:
            say(channel=channel_id, text="❌ Unable to create your subscription.")
    except Exception as e:
        print(f"Error creating subscription: {e}")
        say(channel=user_id, text="An error occurred creating your subscription.")


# Approve/Reject feedback actions
@app.action("approve_feedback")
def handle_approve_feedback(ack, body, say):
    ack()
    try:
        feedback_id = int(body["actions"][0]["value"])
        ok = business_logic_manager.update_feedback_status(feedback_id, "approved")
        say(text=("✅ Feedback approved." if ok else "❌ Could not approve feedback."), thread_ts=body.get("message", {}).get("ts"))
    except Exception as e:
        say(text=f"❌ Error approving feedback: {e}", thread_ts=body.get("message", {}).get("ts"))


@app.action("reject_feedback")
def handle_reject_feedback(ack, body, say):
    ack()
    try:
        feedback_id = int(body["actions"][0]["value"])
        ok = business_logic_manager.update_feedback_status(feedback_id, "rejected")
        say(text=("🗑️ Feedback rejected." if ok else "❌ Could not reject feedback."), thread_ts=body.get("message", {}).get("ts"))
    except Exception as e:
        say(text=f"❌ Error rejecting feedback: {e}", thread_ts=body.get("message", {}).get("ts"))

# Main menu actions
@app.action("choose_metrics")
def handle_choose_metrics(ack, body, say):
    ack()
    user_id = body.get("user", {}).get("id") or body.get("user", {}).get("user_id")
    if not USER_SESSIONS.get(user_id):
        USER_SESSIONS[user_id] = {}
    USER_SESSIONS[user_id]["mode"] = "metrics"
    say("✅ Metrics mode selected. Ask your question (e.g., 'marine bookings yesterday'). Type 'menu' anytime to switch.")

@app.action("choose_agent_status")
def handle_choose_agent_status(ack, body, say):
    ack()
    user_id = body.get("user", {}).get("id") or body.get("user", {}).get("user_id")
    if not USER_SESSIONS.get(user_id):
        USER_SESSIONS[user_id] = {}
    USER_SESSIONS[user_id]["mode"] = "agent"
    say("✅ Agent mode selected. Ask 'agent status for <name>' or 'agents active now'. Type 'menu' anytime to switch.")

if __name__ == "__main__":
    print("🚀 Starting Simplified ThinkTank Bot...")
    os.makedirs("query_results", exist_ok=True)
    os.makedirs("temp_exports", exist_ok=True)
    # Optional prewarm controlled by env
    try:
        if os.getenv('PREWARM_DISTINCTS', 'false').lower() == 'true':
            distinct_cache.prewarm_async()
    except Exception:
        pass
    flask_thread = threading.Thread(target=run_web_app, daemon=True)
    flask_thread.start()
    handler = SocketModeHandler(app, os.getenv("SLACK_APP_TOKEN"))
    handler.start()
