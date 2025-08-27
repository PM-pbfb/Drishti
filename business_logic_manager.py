
import os
import json
import google.generativeai as genai
from typing import Dict, Any
import time
from datetime import datetime

from config import get_db_schema_details, TIME_PATTERNS, PRODUCTS

# Initialize Gemini
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
_MODEL = genai.GenerativeModel('gemini-1.5-flash')

BUSINESS_LOGIC_FILE = 'business_logic.json'
FEEDBACK_FILE = 'feedback.json'


class BusinessLogicManager:
    """Handles complex queries by translating them directly to SQL and storing the logic."""

    def __init__(self):
        self.model = _MODEL
        self.business_logics = self._load_logics(BUSINESS_LOGIC_FILE)
        self.feedback_log = self._load_logics(FEEDBACK_FILE)

    def _load_logics(self, file_path: str) -> list:
        """Load saved logics from a JSON file."""
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return []
        return []

    def _save_logics(self, file_path: str, data: list):
        """Save the current logics to the JSON file."""
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=4)

    def generate_sql_from_logic(self, user_query: str) -> Dict[str, Any]:
        """
        Uses a powerful AI prompt to convert a user's complex query directly into SQL.
        """
        schema_details = get_db_schema_details()
        time_syntax_examples = "\\n".join([f"- For '{name}', use this SQL syntax: `{syntax}`" for name, syntax in TIME_PATTERNS.items()])
        
        # Create product context to prevent hallucination
        product_lines = []
        seen = set()
        for alias, pid in PRODUCTS.items():
            if pid in seen:
                continue
            seen.add(pid)
            product_lines.append(f"- ID {pid}: {alias}")
            if len(product_lines) >= 40:
                break
        product_context = "\\n".join(product_lines)

        prompt = f"""
        You are an expert SQL analyst. Your task is to convert the user's business question into a precise and executable Presto SQL query.

        **CRITICAL RULES:**
        1.  **ONLY use the table `sme_analytics.sme_leadbookingrevenue`.** Do NOT use any other table.
        2.  **NEVER invent column names.** If you are not sure of a column name, do not guess. If the user's request cannot be fulfilled with the available columns, you must indicate an error.
        3.  The generated SQL query must be a SINGLE statement.
        4.  NEVER produce a query that modifies the database (no INSERT, UPDATE, DELETE, etc.). Only `SELECT` statements are allowed.
        5.  The SQL query must NOT end with a semicolon.
        6.  Analyze the user's request carefully to understand all conditions, filters, and calculations.
        7.  **TIME HANDLING**: When the user mentions relative times like 'today', 'yesterday', or 'this month', you MUST use the correct Presto SQL syntax provided in the examples below.
        8.  **PRODUCT MAPPING**: When a product name is mentioned, you MUST use the correct `investmenttypeid` from the list provided below.

        **Database Schema:**
        Here are the relevant columns for the `sme_analytics.sme_leadbookingrevenue` table:
        {schema_details}

        **Known Insurance Products (use these IDs for `investmenttypeid`):**
        {product_context}

        **Correct Time Syntax Examples:**
        {time_syntax_examples}

        **Examples of Good Queries:**
        - User Query: "what is the total revenue for fire insurance this month"
          {{
            "sql": "SELECT SUM(revenue) as total_revenue FROM sme_analytics.sme_leadbookingrevenue WHERE investmenttypeid IN (5) AND leaddate >= DATE_TRUNC('month', CURRENT_DATE)",
            "explanation": "This query calculates the total revenue for Fire Insurance (ID 5) for the current month."
          }}
        - User Query: "show me the agents who have not booked anything and their lead count"
          {{
            "sql": "SELECT leadassignedagentname, COUNT(*) as lead_count FROM sme_analytics.sme_leadbookingrevenue WHERE booking_status = 'notbooked' GROUP BY leadassignedagentname ORDER BY lead_count DESC LIMIT 10",
            "explanation": "This query lists the top 10 agents with the most leads that have not resulted in a booking."
          }}

        **User Query:**
        "{user_query}"

        Now, based on the user's query, generate a JSON object with the SQL query and a brief explanation. If the query is impossible with the given schema, return an error in the explanation.

        **JSON Output format:**
        {{
          "sql": "SELECT ... FROM sme_analytics.sme_leadbookingrevenue WHERE ...",
          "explanation": "This query calculates..."
        }}
        """

        try:
            response = self.model.generate_content(
                prompt,
                generation_config={"max_output_tokens": 1024, "temperature": 0.0},
            )
            print("Gemini raw output:", response.text)
            resp_text = (response.text or '').strip().replace('```json', '').replace('```', '')
            data = json.loads(resp_text)

            sql = (data.get("sql") or "").strip()
            # Basic validation to ensure safety
            if not sql.lower().startswith("select"):
                raise ValueError("Generated query is not a SELECT statement.")
            if any(keyword in sql.lower() for keyword in ["delete", "insert", "update", "drop", "truncate"]):
                 raise ValueError("Generated query contains forbidden keywords.")

            return data
        except Exception as e:
            print(f"Error in SQL generation: {e}")
            return {"error": str(e)}

    def get_relevant_approved_logic(self, user_query: str) -> list:
        """(Future) Find relevant approved logic to inject into prompts."""
        # TODO: Implement semantic search for better matching
        return []

    def store_feedback(self, user_id: str, original_query: str, feedback_text: str, context: dict) -> int:
        """Stores user feedback for expert review."""
        feedback_id = int(time.time())
        self.feedback_log.append({
            "id": feedback_id,
            "user_id": user_id,
            "original_query": original_query,
            "feedback_text": feedback_text,
            "context": context,
            "status": "pending", # pending, approved, rejected
            "timestamp": datetime.now().isoformat()
        })
        self._save_logics(FEEDBACK_FILE, self.feedback_log)
        return feedback_id

    def update_feedback_status(self, feedback_id: int, status: str) -> bool:
        """Updates the status of a feedback item and saves logic if approved."""
        for item in self.feedback_log:
            if item.get("id") == feedback_id:
                item["status"] = status
                # If approved, also add it to the main business logic store
                if status == "approved" and item.get("context", {}).get("sql"):
                    self.business_logics.append({
                        "original_query": item.get("original_query"),
                        "logic_statement": item.get("feedback_text"),
                        "sql": item["context"]["sql"],
                        "explanation": item["context"].get("explanation"),
                        "approved_by": "human_expert",
                        "approved_at": datetime.now().isoformat()
                    })
                    self._save_logics(BUSINESS_LOGIC_FILE, self.business_logics)
                self._save_logics(FEEDBACK_FILE, self.feedback_log)
                return True
        return False

    def save_logic(self, user_query: str, sql_query: str, explanation: str):
        """Saves a new piece of business logic to the store."""
        self.business_logics.append({
            "original_query": user_query,
            "sql": sql_query,
            "explanation": explanation,
            "created_at": self.get_current_timestamp()
        })
        self._save_logics(BUSINESS_LOGIC_FILE, self.business_logics)

    def find_matching_logic(self, user_query: str):
        """
        (Future implementation) Finds a similar, previously saved logic.
        For now, this is a placeholder. A real implementation would use vector similarity.
        """
        # TODO: Implement semantic search or vector similarity
        return None
