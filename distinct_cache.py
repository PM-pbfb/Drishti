#!/usr/bin/env python3
"""
Distinct values cache for categorical columns
Fetches and caches limited distincts to power better AI understanding
"""

import os
import json
import time
from typing import Dict, List, Optional
import threading

from database import SimpleDatabase
from config import TABLE_SCHEMA, PRESTO_CONNECTION


class DistinctCache:
    def __init__(self, ttl_seconds: int = 21600, limit: int = 200, max_columns: int = 12, columns_whitelist: Optional[List[str]] = None):  # 6h TTL
        self.ttl = ttl_seconds
        self.limit = limit
        self.max_columns = max_columns
        self.columns_whitelist = columns_whitelist or []
        self.cache_path = os.path.join(os.getcwd(), "temp_exports", "distinct_cache.json")
        self._last_loaded = 0.0
        self._data: Dict[str, List[str]] = {}
        self._db = SimpleDatabase(PRESTO_CONNECTION)
        os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
        self._lock = threading.Lock()
        self._prewarming = False

    def _load(self):
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, "r") as f:
                    payload = json.load(f)
                self._data = payload.get("data", {})
                self._last_loaded = payload.get("timestamp", 0)
            except Exception:
                self._data = {}
                self._last_loaded = 0

    def _save(self):
        try:
            with open(self.cache_path, "w") as f:
                json.dump({"timestamp": time.time(), "data": self._data}, f)
        except Exception:
            pass

    def _is_fresh(self) -> bool:
        return (time.time() - self._last_loaded) < self.ttl

    def _pick_columns(self) -> List[str]:
        # Use whitelist if provided and exists in schema
        if self.columns_whitelist:
            cols = [c for c in self.columns_whitelist if c in TABLE_SCHEMA]
        else:
            # Default shortlist of common dimensions/filters if present
            defaults = [
                "mkt_category",
                "leadcreationsource",
                "booking_status",
                "leadassignedagentname",  # may be large; include only if needed
            ]
            cols = [c for c in defaults if c in TABLE_SCHEMA]

            # Fill remaining slots with other categoricals (excluding high PII)
            others = [
                col for col, meta in TABLE_SCHEMA.items()
                if meta.get("is_categorical", False) and meta.get("pii_level", "none") != "high" and col not in cols
            ]
            cols.extend(others)

        return cols[: self.max_columns]

    def _build_fresh(self) -> Dict[str, List[str]]:
        categoricals = self._pick_columns()
        fresh: Dict[str, List[str]] = {}
        for col in categoricals:
            try:
                sql = f"SELECT DISTINCT {col} FROM sme_analytics.sme_leadbookingrevenue WHERE {col} IS NOT NULL LIMIT {self.limit}"
                df = self._db.run_query(sql)
                values = []
                if not df.empty:
                    for v in df.iloc[:, 0].tolist():
                        if v is None:
                            continue
                        s = str(v)
                        if s and s.lower() != "null":
                            values.append(s)
                fresh[col] = values
            except Exception:
                fresh[col] = []
        return fresh

    def prewarm_async(self):
        with self._lock:
            if self._prewarming:
                return
            self._prewarming = True

        def _run():
            try:
                fresh = self._build_fresh()
                with self._lock:
                    self._data = fresh
                    self._save()
            finally:
                with self._lock:
                    self._prewarming = False

        t = threading.Thread(target=_run, daemon=True)
        t.start()

    def get(self) -> Dict[str, List[str]]:
        # Load from disk if available and fresh
        if not self._data or not self._is_fresh():
            self._load()
        if self._data and self._is_fresh():
            return self._data

        # If not fresh and not prewarmed, trigger async prewarm and return last known
        self.prewarm_async()
        return self._data or {}

    def get_effective_columns(self) -> List[str]:
        """Return the columns we consider for distincts/guessing."""
        try:
            return self._pick_columns()
        except Exception:
            return []


distinct_cache = DistinctCache(
    ttl_seconds=2592000,  # 30 days
    limit=100,
    max_columns=10,
    columns_whitelist=['mkt_category', 'leadcreationsource', 'booking_status', 'insurername', 'insurerfullname', 'booking_occupancy', 'lead_occupancy']
)

