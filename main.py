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
db_manager = SimpleDatabase(os.getenv("PRESTO_CONNECTION"))
from subscription_manager import subscription_manager
from business_logic_manager import business_logic_manager
from masking_service import masking_service
from nlp_extractor import nlp_extractor
from sql_builder import build_sql
from distinct_cache import distinct_cache

# Simple in-memory session store for per-user mode
USER_SESSIONS = {}

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
        """Return a list of candidate agents as dicts: {code: lead_agentid, name: display_name} matching the name."""
        candidates = []
        if not agent_name:
            return candidates
        try:
            name_safe = str(agent_name).replace("'", "''").strip().lower()
            name_columns = [
                'leadassignedagentname', 'currentlyassigneduser', 'leadreportingmanagername',
                'leadreportingmanagername2', 'first_assigned_agent', 'booking_agent',
                'booking_agent_manager', 'booking_agent_manager2'
            ]
            like_clauses = [
                f"LOWER(CAST({col} AS VARCHAR)) LIKE CONCAT('%%', '{name_safe}', '%%')" for col in name_columns
            ]
            name_predicate = "( " + " OR ".join(like_clauses) + " )"

            prod_filter = ""
            if products:
                ids_csv = ", ".join(str(p) for p in products)
                prod_filter = f" AND investmenttypeid IN ({ids_csv})"

            # Build canonical name using COALESCE across name columns
            coalesce_name = (
                "COALESCE(leadassignedagentname, currentlyassigneduser, leadreportingmanagername, "
                "leadreportingmanagername2, first_assigned_agent, booking_agent, "
                "booking_agent_manager, booking_agent_manager2)"
            )
            sql = (
                "SELECT lead_agentid AS code, " + coalesce_name + " AS name, MAX(COALESCE(bookingdate, leaddate)) AS last_dt "
                "FROM sme_analytics.sme_leadbookingrevenue "
                f"WHERE lead_agentid IS NOT NULL AND TRIM(lead_agentid) <> '' AND {name_predicate}{prod_filter} "
                "GROUP BY lead_agentid, " + coalesce_name + " "
                "ORDER BY last_dt DESC "
                f"LIMIT {int(max(1, limit))}"
            )
            df = self.db.run_query(sql, use_cache=True)
            if not df.empty:
                for _, row in df.iterrows():
                    code = str(row.get('code', '')).strip()
                    name = str(row.get('name', '')).strip()
                    if code:
                        candidates.append({"code": code, "name": name or None})
        except Exception as e:
            print(f"Agent candidate resolution failed: {e}")
        return candidates

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
            matches = process.extract(name_query, names, scorer=fuzz.WRatio, limit=top_k)
            # matches: list of tuples (name, score, index)
            return [m[0] for m in matches if m[1] >= 70]
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
        """Return dict product_id -> all distinct lead_agentid values (no sampling). Potentially slow."""
        results = {}
        try:
            if not products:
                sql = (
                    "SELECT DISTINCT lead_agentid FROM sme_analytics.sme_leadbookingrevenue "
                    "WHERE lead_agentid IS NOT NULL AND TRIM(lead_agentid) <> ''"
                )
                print("DEBUG: Fetching ALL agent codes (no product filter)")
                df = self.db.run_query(sql, use_cache=False)
                results[None] = [str(x) for x in df.iloc[:, 0].tolist() if str(x).strip()]
                return results
            for pid in products:
                sql = (
                    "SELECT DISTINCT lead_agentid FROM sme_analytics.sme_leadbookingrevenue "
                    f"WHERE investmenttypeid = {int(pid)} AND lead_agentid IS NOT NULL AND TRIM(lead_agentid) <> ''"
                )
                print(f"DEBUG: Fetching ALL agent codes for product {pid}")
                df = self.db.run_query(sql, use_cache=False)
                results[int(pid)] = [str(x) for x in df.iloc[:, 0].tolist() if str(x).strip()]
        except Exception as e:
            print(f"Agent ALL ID listing failed: {e}")
        return results
    
    def execute_sql_query(self, sql_query, explanation):
        sql_query = sql_query.strip().rstrip(';')
        print(f"DEBUG: ----- EXECUTING SQL -----\n{sql_query}\nDEBUG: -------------------------")
        try:
            df = self.db.run_query(sql_query)
            if df.empty:
                return "No data found for your query.", None, None

            df_masked = masking_service.mask_dataframe(df)
            query_id = hashlib.md5(sql_query.encode()).hexdigest()[:8]
            self.save_query_result(query_id, df_masked, sql_query, explanation)

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
    
    def save_query_result(self, query_id, df, sql_query, explanation):
        os.makedirs("query_results", exist_ok=True)
        with open(f"query_results/{query_id}.json", "w") as f:
            json.dump({"data": df.to_dict('records'), "sql": sql_query, "explanation": explanation}, f)

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

bot = SimplifiedBot(db_manager)


def looks_like_feedback(message: str) -> bool:
    text = (message or "").lower()
    keywords = [
        "should", "must", "always", "include", "exclude", "prefer",
        "use like", "use regex", "wrong", "incorrect", "show",
        "please add", "please use", "make sure"
    ]
    return any(k in text for k in keywords)


def send_feedback_to_channel(feedback_id: int, user_id: str, original_text: str, entities: dict):
    try:
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

def run_main_logic(text, user_id, say):
    try:
        # If user requests main menu/reset within a session
        lower_text = (text or "").strip().lower()
        if lower_text in ("menu", "main menu", "start over", "restart", "end session"):
            if lower_text in ("end session",):
                USER_SESSIONS.pop(user_id, None)
                say("✅ Session ended.")
                debug(f"User {user_id} ended session")
            show_main_menu(user_id, say)
            return

        # Route by chosen session mode first (two distinct workflows)
        mode = (USER_SESSIONS.get(user_id) or {}).get("mode")
        # Hard route: if the user asks about agent activity, go to agent mode handler regardless
        if mode == "agent" or any(k in lower_text for k in ["agents active", "active agents", "agents online", "how many agents"]):
            debug(f"Routing to agent mode (mode={mode}) for user {user_id}")
            return handle_agent_mode(text, user_id, say)

        # Default/metrics workflow (legacy behavior + clarifications/feedback)
        entities = bot.process_query_with_ai(text)
        debug(f"Entities extracted: {entities}")

        # Confidence-based clarification for products
        if entities.get("intent") == "metric_query" and entities.get("confidence", 0) < 0.6:
            say("🤔 I might be unsure about your request. Could you specify the product or metric?")
            return

        # Shortcut: treat suggestions/instructions as feedback even if extractor says clarification
        if entities.get("intent") == "feedback" or looks_like_feedback(text):
            try:
                feedback_id = business_logic_manager.store_feedback(
                    user_id=user_id,
                    original_query=text,
                    feedback_text="User suggestion/feedback",
                    context={"entities": entities},
                )
                if feedback_id:
                    send_feedback_to_channel(feedback_id, user_id, text, entities)
            except Exception:
                pass
            say("✅ Thanks for the feedback! We'll review and improve this behavior.")
            return

        # Handle agent status intent
        if entities.get("intent") == "agent_status":
            agent_name = ((entities.get("agent") or {}).get("name")) or None
            if not agent_name:
                # Try AI-assisted extraction
                agent_name = bot.ai_assisted_agent_name(text)
            if agent_name:
                # Remove trailing "in <something>" fragments and standalone time tokens misparsed as name
                agent_name = re.sub(r"\bin\s+[A-Za-z\s]+$", "", agent_name, flags=re.IGNORECASE).strip()
                if agent_name.lower() in ("today", "yesterday", "this week", "this month"):
                    agent_name = None
            products = entities.get("products") or []
            if not agent_name:
                say("Please specify the agent name, e.g., 'agent status for Sahil Sharma'.")
                return
            # If user provided an agent code directly, use it
            if re.fullmatch(r"[A-Za-z]{1,6}\d{2,8}", agent_name):
                lead_agentid = agent_name
                candidate_label = None
            else:
                candidates = bot.resolve_agent_candidates(agent_name, products, limit=5)
                if not candidates:
                    suggestions = bot.suggest_agent_names(agent_name)
                    if suggestions:
                        suggest_text = ", ".join(suggestions)
                        say(f"Couldn't find any agent for '{agent_name}'. Did you mean: {suggest_text}?")
                    else:
                        say(f"Couldn't find any agent for '{agent_name}'. Try the exact name used in CRM or provide agent code.")
                    return
                if len(candidates) > 1:
                    lines = [f"- {c['name'] or 'Unknown'} (code: `{c['code']}`)" for c in candidates]
                    say("Multiple agents match that name. Please specify the agent code from below:\n" + "\n".join(lines))
                    return
                lead_agentid = candidates[0]["code"]
                candidate_label = candidates[0].get("name")

            status_list = bot.fetch_agent_status(lead_agentid)
            if not status_list:
                label = candidate_label or agent_name
                say(f"No live status found for agent '{label}' (ID: {lead_agentid}).")
                return
            s = status_list[0]
            # Build a concise Slack message
            fields = []
            def add_field(title, key):
                if s.get(key) is not None and s.get(key) != "":
                    fields.append({"type": "mrkdwn", "text": f"*{title}:* {s.get(key)}"})
            add_field("Agent", "AgentName")
            add_field("Code", "AgentCode")
            add_field("Status", "Status")
            add_field("Last Updated", "LastUpdatedOn")
            add_field("On WFH", "IsWFH")
            add_field("Company", "CallingCompany")
            add_field("Total Calls", "TotalCalls")
            add_field("Connected", "ConnectedDials")
            add_field("Talk Time (s)", "TotalTalkTime")
            detail_block = {"type": "section", "fields": fields[:10]} if fields else {"type": "section", "text": {"type": "mrkdwn", "text": "No additional details available."}}
            blocks = [
                {"type": "section", "text": {"type": "mrkdwn", "text": f"🔎 Agent live status for *{agent_name}* (ID: `{lead_agentid}`)"}},
                detail_block,
            ]
            say(blocks=blocks, text=f"Agent status for {agent_name}")
            return

        ai_response = bot.generate_response(text, user_id, product_ids=entities)
        intent = ai_response.get("intent")
        
        if intent == "metric_query":
            # If the user primarily asked for agent active summary (and no explicit metric), serve that directly
            wants_agent_summary = (entities.get("flags") or {}).get("agent_active_summary")
            wants_full = (entities.get("flags") or {}).get("agent_active_summary_full")
            explicit_metric = ai_response.get("sql") and (entities.get("metric") or entities.get("metrics"))
            if wants_agent_summary and not explicit_metric:
                products = entities.get("products") or []
                if wants_full:
                    print("DEBUG: Running FULL agent activity scan")
                    pid_to_agents = bot.get_all_agent_ids_for_products(products)
                else:
                    pid_to_agents = bot.get_recent_agent_ids_for_products(products, limit_per_product=15)
                summary_lines = []
                for pid, agent_ids in pid_to_agents.items():
                    active_count = 0
                    check_ids = agent_ids if wants_full else agent_ids[:15]
                    print(f"DEBUG: Checking {len(check_ids)} agent codes for product {pid}")
                    for aid in check_ids:
                        print(f"DEBUG: Calling status API for {aid}")
                        status_list = bot.fetch_agent_status(aid)
                        if not status_list:
                            continue
                        s = status_list[0] if isinstance(status_list, list) else status_list
                        status = str(s.get("Status", "")).upper()
                        print(f"DEBUG: {aid} -> {status}")
                        if status in ("READY", "AVAILABLE", "IDLE", "ONCALL", "ON CALL", "BUSY"):
                            active_count += 1
                    label = f"Product {pid}" if pid is not None else "All Products"
                    summary_lines.append(f"- {label}: {active_count} active now (sampled)")
                text_out = "👥 Agent activity (quick check):\n" + ("\n".join(summary_lines) if summary_lines else "No agents found in recent activity.")
                say(text_out)
                return
            sql = ai_response.get("sql")
            explanation = ai_response.get("explanation", "Query executed")
            if sql:
                result_text, query_id, df_masked = bot.execute_sql_query(sql, explanation)
                # If the user asked for agent active summary, augment the message
                if (entities.get("flags") or {}).get("agent_active_summary"):
                    products = entities.get("products") or []
                    wants_full = (entities.get("flags") or {}).get("agent_active_summary_full")
                    if wants_full:
                        print("DEBUG: Running FULL agent activity scan (augment)")
                        pid_to_agents = bot.get_all_agent_ids_for_products(products)
                    else:
                        pid_to_agents = bot.get_recent_agent_ids_for_products(products, limit_per_product=15)
                    summary_lines = []
                    total_active = 0
                    for pid, agent_ids in pid_to_agents.items():
                        active_count = 0
                        check_ids = agent_ids if wants_full else agent_ids[:15]
                        print(f"DEBUG: Checking {len(check_ids)} agent codes for product {pid}")
                        for aid in check_ids:
                            print(f"DEBUG: Calling status API for {aid}")
                            status_list = bot.fetch_agent_status(aid)
                            if not status_list:
                                continue
                            s = status_list[0] if isinstance(status_list, list) else status_list
                            status = str(s.get("Status", "")).upper()
                            print(f"DEBUG: {aid} -> {status}")
                            if status in ("READY", "AVAILABLE", "IDLE", "ONCALL", "ON CALL", "BUSY"):
                                active_count += 1
                        total_active += active_count
                        label = f"Product {pid}" if pid is not None else "All Products"
                        summary_lines.append(f"- {label}: {active_count} active now (sampled)")
                    if summary_lines:
                        result_text += "\n\n👥 Agent activity (quick check):\n" + "\n".join(summary_lines)
                
                if query_id:
                    blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": result_text}}, {"type": "actions", "elements": [{"type": "button", "text": {"type": "plain_text", "text": "📥 Download Excel"}, "action_id": "download_excel", "value": query_id}, {"type": "button", "text": {"type": "plain_text", "text": "🔔 Subscribe"}, "action_id": "subscribe_alerts", "value": query_id}]}]
                    say(blocks=blocks, text=result_text)
                else:
                    say(result_text)
            else:
                say("❌ I couldn't generate a query for that request.")
        elif intent == "conversation":
            say(f"💭 {ai_response.get('response', 'I am here to help!')}")
        elif intent == "feedback":
            try:
                feedback_id = business_logic_manager.store_feedback(user_id, text, "User provided feedback", context={})
                if feedback_id:
                    send_feedback_to_channel(feedback_id, user_id, text, {})
            except Exception:
                pass
            say("✅ Thank you for your feedback!")
        elif intent == "clarification":
            say("🤔 Noted. I can log this as a suggestion to improve product/insurer matching.")
        else:
            say("🤔 I'm not sure how to help. Try asking about business metrics.")
    
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
            wants_full = (agent_ai.get("scan") == "full") or ((ents.get("flags") or {}).get("agent_active_summary_full"))
            pid_to_agents = (
                bot.get_all_agent_ids_for_products(products)
                if wants_full else bot.get_recent_agent_ids_for_products(products, limit_per_product=15)
            )
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
                check_ids = explicit_codes or (agent_ids if wants_full else agent_ids[:15])
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
                    summary_lines.append(f"- {label}: {active_count} with status {status_label}" + (" (sampled)" if not wants_full and not explicit_codes else ""))
                else:
                    summary_lines.append(f"- {label}: {active_count} active now" + (" (sampled)" if not wants_full and not explicit_codes else ""))
            header = "👥 Agent activity:\n" + ("\n".join(summary_lines) if summary_lines else "No agents found.")
            # Append details if any
            if details_lines:
                # Limit to avoid Slack overflow
                detail_preview = "\n".join(details_lines[:30])
                header += "\n\n👤 Active agents (sample):\n" + detail_preview
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
        # Direct code support
        if re.fullmatch(r"[A-Za-z]{1,6}\d{2,8}", agent_name):
            lead_agentid = agent_name
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

@app.event("app_mention")
def handle_message(event, say):
    user_id = event["user"]
    text = re.sub(r'^<@\w+>\s*', '', event.get("text", "")).strip()
    print(f"\n\nDEBUG: ----- NEW MESSAGE RECEIVED -----\nUser: {user_id}\nText: '{text}'\n------------------------------------")
    
    if not text:
        show_main_menu(user_id, say)
        return
    
    # If text equals 'menu', show menu; otherwise process
    if text.strip().lower() in ("menu", "main menu", "start over", "restart"):
        show_main_menu(user_id, say)
        return

    # If no mode chosen yet, route smartly or show menu
    mode = (USER_SESSIONS.get(user_id) or {}).get("mode")
    if not mode:
        tl = text.lower()
        if any(k in tl for k in ["agents active", "active agents", "agents online", "how many agents"]):
            return handle_agent_mode(text, user_id, say)
        show_main_menu(user_id, say)
        return

    debug(f"Routing to run_main_logic for user {user_id} (mode={mode})")
    say("🤖 Processing...")
    run_main_logic(text, user_id, say)

# All other handlers (subscribe, feedback, etc.) remain the same

# Action: Download Excel for last query result
@app.action("download_excel")
def handle_download_excel(ack, body, say):
    ack()
    try:
        query_id = body["actions"][0]["value"]
        with open(f"query_results/{query_id}.json", "r") as f:
            payload = json.load(f)
        df = pd.DataFrame(payload.get("data", []))
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
    USER_SESSIONS[user_id] = {"mode": "metrics"}
    say("✅ Metrics mode selected. Ask your question (e.g., 'marine bookings yesterday'). Type 'menu' anytime to switch.")

@app.action("choose_agent_status")
def handle_choose_agent_status(ack, body, say):
    ack()
    user_id = body.get("user", {}).get("id") or body.get("user", {}).get("user_id")
    USER_SESSIONS[user_id] = {"mode": "agent"}
    say("✅ Agent mode selected. Ask 'agent status for <name>' or 'agents active now'. Type 'menu' anytime to switch.")

@app.action("show_help")
def handle_show_help(ack, body, say):
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
    handler = SocketModeHandler(app, os.getenv("SLACK_APP_TOKEN"))
    handler.start()
