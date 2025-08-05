import pandas as pd
from sqlalchemy import create_engine
import json
import time
import hashlib
from typing import Dict, Optional
import re

from config import PRESTO_CONNECTION, CACHE_TTL

class SimpleDatabase:
    """Simplified database manager with basic caching"""
    
    def __init__(self, connection_string):
        self.engine = self._create_engine(connection_string)
        self.query_cache = {}
    
    def _create_engine(self, connection_string):
        """Create database engine"""
        if not connection_string:
            print("❌ Database connection string is missing.")
            return None
        try:
            engine = create_engine(connection_string)
            print("✅ Database connection established")
            return engine
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            return None
    
    def _get_cache_key(self, sql: str) -> str:
        """Generate cache key"""
        return hashlib.md5(sql.encode()).hexdigest()
    
    def _is_cache_valid(self, timestamp: float) -> bool:
        """Check if cache is still valid"""
        return time.time() - timestamp < CACHE_TTL
    
    def _validate_sql(self, sql: str) -> bool:
        """Basic SQL validation for security"""
        sql_upper = sql.upper().strip()
        
        # Must be SELECT only
        if not sql_upper.startswith('SELECT'):
            print("❌ Only SELECT queries allowed")
            return False
        
        # Check for dangerous keywords
        dangerous = ['DROP', 'DELETE', 'INSERT', 'UPDATE', 'ALTER', 'CREATE', 'TRUNCATE']
        for keyword in dangerous:
            if keyword in sql_upper:
                print(f"❌ Dangerous keyword detected: {keyword}")
                return False
        
        # Must access allowed table
        if 'sme_analytics.sme_leadbookingrevenue' not in sql.lower():
            print("❌ Must query allowed table: sme_analytics.sme_leadbookingrevenue")
            return False
        
        return True
    
    def run_query(self, sql: str, use_cache: bool = True) -> pd.DataFrame:
        """Execute SQL query with caching and validation"""
        
        if not sql or not sql.strip():
            raise ValueError("Empty SQL query")
        
        if not self._validate_sql(sql):
            raise ValueError("SQL query failed security validation")
        
        # Check cache
        cache_key = self._get_cache_key(sql)
        if use_cache and cache_key in self.query_cache:
            cached_data, timestamp = self.query_cache[cache_key]
            if self._is_cache_valid(timestamp):
                print(f"✅ Cache hit - returning cached data ({len(cached_data)} rows)")
                return cached_data
        
        # Execute query
        if not self.engine:
            raise ConnectionError("Database engine not available")
        
        try:
            print(f"🚀 Executing SQL query...")
            start_time = time.time()
            df = pd.read_sql(sql, self.engine)
            end_time = time.time()
            
            print(f"✅ Query completed in {end_time - start_time:.2f}s - {len(df)} rows returned")
            
            # Cache result
            if use_cache:
                self.query_cache[cache_key] = (df.copy(), time.time())
            
            return df
            
        except Exception as e:
            print(f"❌ Query execution failed: {e}")
            raise e
    
    def clear_cache(self):
        """Clear query cache"""
        self.query_cache.clear()
        print("🧹 Query cache cleared")
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        return {
            "cached_queries": len(self.query_cache),
            "cache_size_mb": sum(len(str(data)) for data, _ in self.query_cache.values()) / 1024 / 1024
        }