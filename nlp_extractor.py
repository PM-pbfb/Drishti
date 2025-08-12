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
- Extract dimensions only if explicitly asked for breakdowns (e.g., agent wise → leadassignedagentname; product wise → investmenttypeid).
- Extract filters like marketing categories (CRM, SEO) or platforms ONLY if clearly stated.
- If user indicates online bookings, set flags.online_only = true.
- If anything is ambiguous, include a short note in ambiguities.
- If the user asks for multiple metrics, put them in metrics []. If only one, set metric.
- If the user asks for top/bottom or most/least, include order.by (metric or dimension), order.direction, and order.top_n.
- Normalize 'product wise' to dimension "investmenttypeid".

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
            data = self._maybe_detect_agent_status(user_text, data)
            data = self._maybe_request_agent_summary(user_text, data)
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

        # Month-wise signals
        monthwise = any(k in text_l for k in ["month wise", "monthwise", "month-wise", "trend"])

        # Month names
        months = {
            "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
            "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12
        }

        # from <month> to <month> <year>
        m = re.search(r"from\s+([a-zA-Z]+)\s+to\s+([a-zA-Z]+)\s+(20\d{2})", text_l)
        if m:
            m1, m2, year = m.group(1), m.group(2), int(m.group(3))
            if m1 in months and m2 in months:
                start_date = f"{year}-{months[m1]:02d}-01"
                # compute end of end-month
                last_day = 31
                for d in [31, 30, 29, 28]:
                    try:
                        datetime(year, months[m2], d)
                        last_day = d
                        break
                    except Exception:
                        continue
                end_date = f"{year}-{months[m2]:02d}-{last_day:02d}"
                result["start_date"] = start_date
                result["end_date"] = end_date
                if monthwise:
                    result["granularity"] = "month"
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

            # Fallback: Prefer 'for|of' capture; avoid capturing the tail after 'agent '
            m = re.search(r"\b(?:for|of)\s+([A-Za-z\.\-\s]{2,40})", text or "", flags=re.IGNORECASE)
            if not name and m:
                candidate = (m.group(1) or "").strip()
                candidate = re.split(r"\b(in|on|at|etc)\b", candidate)[0].strip()
                if candidate and len(candidate) >= 2:
                    name = candidate
            # Last resort: after 'agent'
            m2 = re.search(r"\bagent\s+([A-Za-z\.\-\s]{2,40})", text or "", flags=re.IGNORECASE)
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


# Global instance
nlp_extractor = NLPExtractor()
