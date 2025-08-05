import json
import os
from typing import List, Dict, Optional
import time
from datetime import datetime, timedelta

SUBSCRIPTIONS_FILE = "subscriptions.json"

class SubscriptionManager:
    """Manages alert subscriptions stored in a JSON file."""

    def __init__(self):
        self.subscriptions = self._load_subscriptions()

    def _load_subscriptions(self) -> List[Dict]:
        """Loads subscriptions from the JSON file."""
        if not os.path.exists(SUBSCRIPTIONS_FILE):
            return []
        try:
            with open(SUBSCRIPTIONS_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _save_subscriptions(self):
        """Saves the current subscriptions to the JSON file."""
        with open(SUBSCRIPTIONS_FILE, "w") as f:
            json.dump(self.subscriptions, f, indent=4)

    def _calculate_next_run(self, frequency: str) -> float:
        """Calculates the next run timestamp based on frequency."""
        now = datetime.now()
        if frequency == "hourly":
            return (now + timedelta(hours=1)).timestamp()
        elif frequency == "daily":
            # Schedule for 9 AM the next day
            target_time = now.replace(hour=9, minute=0, second=0, microsecond=0)
            if now >= target_time:
                target_time += timedelta(days=1)
            return target_time.timestamp()
        elif frequency == "weekly":
            # Schedule for next Monday at 9 AM
            target_time = now.replace(hour=9, minute=0, second=0, microsecond=0)
            days_until_monday = (7 - now.weekday()) % 7
            if days_until_monday == 0 and now.hour >= 9:
                days_until_monday = 7 # If it's Monday past 9am, schedule for next week
            target_time += timedelta(days=days_until_monday)
            return target_time.timestamp()
        
        # Fallback to a default if frequency is unknown
        return (now + timedelta(days=1)).timestamp()

    def add_subscription(self, user_id: str, channel_id: str, query_context: Dict, frequency: str) -> int:
        """Adds a new subscription and returns its ID."""
        new_id = int(time.time())
        next_run_time = self._calculate_next_run(frequency)
        
        subscription = {
            "id": new_id,
            "user_id": user_id,
            "channel_id": channel_id,
            "sql": query_context.get("sql"),
            "explanation": query_context.get("explanation"),
            "frequency": frequency,
            "created_at": time.time(),
            "last_run_at": None,
            "next_run_at": next_run_time
        }
        self.subscriptions.append(subscription)
        self._save_subscriptions()
        return new_id

    def remove_subscription(self, subscription_id: int) -> bool:
        """Removes a subscription by its ID."""
        original_count = len(self.subscriptions)
        self.subscriptions = [s for s in self.subscriptions if s.get("id") != subscription_id]
        if len(self.subscriptions) < original_count:
            self._save_subscriptions()
            return True
        return False

    def get_user_subscriptions(self, user_id: str) -> List[Dict]:
        """Retrieves all subscriptions for a specific user."""
        return [s for s in self.subscriptions if s.get("user_id") == user_id]

    def get_due_subscriptions(self) -> List[Dict]:
        """Retrieves all subscriptions that are due to run."""
        now = time.time()
        return [s for s in self.subscriptions if s.get("next_run_at") and s["next_run_at"] <= now]

    def update_subscription_run_time(self, subscription_id: int):
        """Updates the last_run_at and next_run_at for a subscription."""
        for sub in self.subscriptions:
            if sub.get("id") == subscription_id:
                sub["last_run_at"] = time.time()
                sub["next_run_at"] = self._calculate_next_run(sub["frequency"])
                break
        self._save_subscriptions()

    def get_all_subscriptions(self) -> List[Dict]:
        """Retrieves all active subscriptions."""
        return self.subscriptions

subscription_manager = SubscriptionManager()
