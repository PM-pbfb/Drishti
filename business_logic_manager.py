import json
import os
from typing import List, Dict, Optional
import time

BUSINESS_LOGIC_FILE = "business_logic.json"

class BusinessLogicManager:
    """Manages the storage and retrieval of business logic learned from feedback."""

    def __init__(self):
        self.business_logic = self._load_logic()

    def _load_logic(self) -> List[Dict]:
        """Loads business logic from the JSON file."""
        if not os.path.exists(BUSINESS_LOGIC_FILE):
            return []
        try:
            with open(BUSINESS_LOGIC_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _save_logic(self):
        """Saves the current business logic to the JSON file."""
        with open(BUSINESS_LOGIC_FILE, "w") as f:
            json.dump(self.business_logic, f, indent=4)

    def store_feedback(self, user_id: str, original_query: str, feedback_text: str, context: Dict) -> int:
        """Stores new feedback from a user with a 'pending' status."""
        new_id = int(time.time())
        feedback_entry = {
            "id": new_id,
            "user_id": user_id,
            "original_query": original_query,
            "feedback_text": feedback_text,
            "context": context,
            "status": "pending",  # Status can be 'pending', 'approved', 'rejected'
            "created_at": time.time()
        }
        self.business_logic.append(feedback_entry)
        self._save_logic()
        return new_id

    def update_feedback_status(self, feedback_id: int, status: str) -> bool:
        """Updates the status of a feedback entry (e.g., to 'approved')."""
        for entry in self.business_logic:
            if entry.get("id") == feedback_id:
                entry["status"] = status
                self._save_logic()
                return True
        return False

    def get_relevant_approved_logic(self, user_query: str) -> List[str]:
        """
        Retrieves approved business logic relevant to the user's query.
        This is a simple keyword-based retrieval for now.
        """
        approved_logic = []
        user_query_lower = user_query.lower()
        
        for entry in self.business_logic:
            if entry.get("status") == "approved":
                # Simple check if any word from the original query appears in the new query
                original_query_words = entry.get("original_query", "").lower().split()
                if any(word in user_query_lower for word in original_query_words if len(word) > 3):
                    approved_logic.append(entry["feedback_text"])
        
        return approved_logic

business_logic_manager = BusinessLogicManager()
