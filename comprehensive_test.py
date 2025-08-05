#!/usr/bin/env python3
"""
Comprehensive Test Script for ThinkTank Bot
Tests all functionality including product detection, SQL generation, feedback, alerts, clarification, etc.
"""

import os
import sys
import json
import time
import requests
from datetime import datetime, timedelta
import pandas as pd
from unittest.mock import Mock, patch
import sqlite3
from dotenv import load_dotenv

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Explicitly load .env from the script's directory
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)
else:
    print("⚠️ .env file not found, please ensure it exists in the project root.")


# Import bot modules
from config import PRODUCTS, TIME_PATTERNS, SQL_PATTERNS
from database import SimpleDatabase
from subscription_manager import subscription_manager
from business_logic_manager import business_logic_manager

class ComprehensiveBotTester:
    def __init__(self):
        self.test_results = []
        self.passed_tests = 0
        self.failed_tests = 0
        self.total_tests = 0
        
    def log_test(self, test_name, passed, details=""):
        """Log test results"""
        self.total_tests += 1
        if passed:
            self.passed_tests += 1
            status = "✅ PASS"
        else:
            self.failed_tests += 1
            status = "❌ FAIL"
            
        result = {
            "test": test_name,
            "status": status,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        # Write to file in real-time
        with open("test_log.txt", "a", encoding="utf-8") as f:
            f.write(f"{status} | {test_name}\n")
            if details:
                f.write(f"   Details: {details}\n")
            f.write("\n")

        print(f"{status} | {test_name}")
        if details:
            print(f"   Details: {details}")
        print()

    def test_product_detection(self):
        """Test product detection functionality"""
        print("🔍 Testing Product Detection...")
        
        # Import the bot class
        from main import SimplifiedBot
        
        # Mock database for testing
        mock_db = Mock()
        bot = SimplifiedBot(mock_db)
        
        # Test cases for product detection
        test_cases = [
            # Valid products
            ("number of leads in ghi", [1], "GHI should be detected as Group Health Insurance"),
            ("fire insurance bookings", [5], "Fire insurance should be detected"),
            ("marine leads", [13], "Marine should be detected"),
            ("wc bookings", [19], "WC should be detected as Workmen Compensation"),
            
            # Multiple products
            ("fire and marine bookings", [5, 13], "Multiple products should be detected"),
            ("ghi wc fire", [1, 5, 19], "Three products should be detected"),
            
            # Non-existent products (should return empty)
            ("number of leads in dws", [], "Non-existent product should return empty"),
            ("xyz bookings", [], "Non-existent product should return empty"),
            ("rest insurance", [], "Non-existent product should return empty"),
        ]
        
        for query, expected_products, description in test_cases:
            detected_products = bot.resolve_products(query)
            passed = detected_products == expected_products
            details = f"Expected: {expected_products}, Got: {detected_products} | {description}"
            self.log_test(f"Product Detection: '{query}'", passed, details)

    def test_sql_generation(self):
        """Test SQL generation patterns"""
        print("🔍 Testing SQL Generation...")
        
        # Test time patterns
        for time_key, expected_pattern in TIME_PATTERNS.items():
            passed = "CURRENT_DATE" in expected_pattern or "DATE_TRUNC" in expected_pattern
            details = f"Time pattern for '{time_key}': {expected_pattern}"
            self.log_test(f"Time Pattern: {time_key}", passed, details)
        
        # Test SQL patterns
        for metric_key, expected_pattern in SQL_PATTERNS.items():
            passed = "COUNT" in expected_pattern or "SUM" in expected_pattern or "AVG" in expected_pattern
            details = f"SQL pattern for '{metric_key}': {expected_pattern}"
            self.log_test(f"SQL Pattern: {metric_key}", passed, details)

    def test_configuration(self):
        """Test configuration loading"""
        print("🔍 Testing Configuration...")
        
        # Test environment variables
        required_env_vars = [
            "SLACK_BOT_TOKEN",
            "SLACK_SIGNING_SECRET", 
            "SLACK_APP_TOKEN",
            "GOOGLE_API_KEY",
            "PRESTO_CONNECTION",
            "FEEDBACK_CHANNEL_ID"
        ]
        
        for var in required_env_vars:
            value = os.getenv(var)
            passed = value is not None and value.strip() != ""
            details = f"Environment variable {var}: {'Set' if passed else 'Missing'}"
            self.log_test(f"Environment Variable: {var}", passed, details)
        
        # Test product mappings
        passed = len(PRODUCTS) > 50  # Should have many products
        details = f"Found {len(PRODUCTS)} product mappings"
        self.log_test("Product Mappings Count", passed, details)
        
        # Test specific product mappings
        test_products = {
            "ghi": 1,
            "fire": 5, 
            "marine": 13,
            "wc": 19
        }
        
        for alias, expected_id in test_products.items():
            actual_id = PRODUCTS.get(alias)
            passed = actual_id == expected_id
            details = f"Expected {alias} -> {expected_id}, Got: {actual_id}"
            self.log_test(f"Product Mapping: {alias}", passed, details)

    def test_subscription_manager(self):
        """Test subscription manager functionality"""
        print("🔍 Testing Subscription Manager...")
        
        # Test adding subscription
        test_user_id = "test_user_123"
        test_channel_id = "test_channel_123"
        test_query_context = {"sql": "SELECT COUNT(*) FROM test", "explanation": "Test query"}
        test_frequency = "daily"
        
        subscription_id = subscription_manager.add_subscription(
            test_user_id, test_channel_id, test_query_context, test_frequency
        )
        
        passed = subscription_id is not None
        details = f"Added subscription with ID: {subscription_id}"
        self.log_test("Add Subscription", passed, details)
        
        # Test getting user subscriptions
        subscriptions = subscription_manager.get_user_subscriptions(test_user_id)
        passed = len(subscriptions) > 0
        details = f"Found {len(subscriptions)} subscriptions for user"
        self.log_test("Get User Subscriptions", passed, details)
        
        # Test removing subscription
        if subscription_id:
            removed = subscription_manager.remove_subscription(subscription_id)
            passed = removed
            details = f"Removed subscription {subscription_id}: {removed}"
            self.log_test("Remove Subscription", passed, details)

    def test_business_logic_manager(self):
        """Test business logic manager functionality"""
        print("🔍 Testing Business Logic Manager...")
        
        # Test storing feedback
        test_user_id = "test_user_456"
        test_original_query = "test query"
        test_feedback = "This is test feedback"
        test_context = {"test": "context"}
        
        feedback_id = business_logic_manager.store_feedback(
            test_user_id, test_original_query, test_feedback, test_context
        )
        
        passed = feedback_id is not None
        details = f"Stored feedback with ID: {feedback_id}"
        self.log_test("Store Feedback", passed, details)
        
        # Test updating feedback status
        if feedback_id:
            updated = business_logic_manager.update_feedback_status(feedback_id, "approved")
            passed = updated
            details = f"Updated feedback {feedback_id} to approved: {updated}"
            self.log_test("Update Feedback Status", passed, details)
            
            # Test getting approved logic
            approved_logic = business_logic_manager.get_relevant_approved_logic("test")
            passed = isinstance(approved_logic, list)
            details = f"Retrieved {len(approved_logic)} approved logic entries"
            self.log_test("Get Approved Logic", passed, details)

    def test_file_structure(self):
        """Test required files and directories"""
        print("🔍 Testing File Structure...")
        
        required_files = [
            "main.py",
            "config.py", 
            "database.py",
            "subscription_manager.py",
            "business_logic_manager.py"
        ]
        
        for file_path in required_files:
            exists = os.path.exists(file_path)
            details = f"File {file_path}: {'Exists' if exists else 'Missing'}"
            self.log_test(f"Required File: {file_path}", exists, details)
        
        # Test directories
        required_dirs = [
            "query_results",
            "temp_exports"
        ]
        
        for dir_path in required_dirs:
            exists = os.path.exists(dir_path)
            details = f"Directory {dir_path}: {'Exists' if exists else 'Missing'}"
            self.log_test(f"Required Directory: {dir_path}", exists, details)

    def test_database_connection(self):
        """Test database connection (if possible)"""
        print("🔍 Testing Database Connection...")
        
        try:
            connection_string = os.getenv("PRESTO_CONNECTION")
            if connection_string:
                # Try to create database instance (don't actually connect)
                db = SimpleDatabase(connection_string)
                passed = db is not None
                details = "Database instance created successfully"
                self.log_test("Database Instance Creation", passed, details)
            else:
                self.log_test("Database Connection", False, "No connection string found")
        except Exception as e:
            self.log_test("Database Connection", False, f"Error: {str(e)}")

    def test_masking_service(self):
        """Test the data masking service"""
        print("🔍 Testing Data Masking Service...")
        from masking_service import MaskingService
        masking_service = MaskingService()
        
        # Create a sample DataFrame with PII
        data = {
            'leadid': [123, 456],
            'contact_person_name': ['John Doe', 'Jane Smith'],
            'premium': [1000, 2000],
            'revenue': [100, 200]
        }
        df = pd.DataFrame(data)
        
        # Mask the DataFrame
        masked_df = masking_service.mask_dataframe(df)
        
        # Test 1: Check if PII columns are masked
        # The names should not be the same as the original
        passed = 'John Doe' not in masked_df['contact_person_name'].values and \
                 'Jane Smith' not in masked_df['contact_person_name'].values
        details = f"Original Names: {df['contact_person_name'].tolist()}, Masked Names: {masked_df['contact_person_name'].tolist()}"
        self.log_test("Masking PII Data", passed, details)
        
        # Test 2: Check if non-PII columns are untouched
        passed = df['premium'].equals(masked_df['premium'])
        details = "Premium column should not be masked"
        self.log_test("Retaining Non-PII Data", passed, details)


    def generate_test_questions(self):
        """Generate comprehensive test questions for manual testing"""
        print("\n" + "="*80)
        print("🧪 MANUAL TEST QUESTIONS")
        print("="*80)
        print("Please ask the bot these questions in Slack to test functionality:")
        print()
        
        test_categories = {
            "Product Detection": [
                "number of leads in ghi",
                "fire insurance bookings today",
                "marine leads this week",
                "wc bookings yesterday",
                "number of leads in dws",  # Should trigger clarification
                "xyz bookings",  # Should trigger clarification
            ],
            
            "Multi-Product Queries": [
                "fire and marine bookings last week",
                "ghi wc fire leads this month",
                "marine fire revenue yesterday",
            ],
            
            "Product-wise Categorization": [
                "number of bookings in wc fire and marine for yesterday categorised product wise",
                "leads in ghi fire marine this week product wise",
                "revenue for fire marine wc last month categorised by product",
            ],
            
            "Agent-wise Categorization": [
                "number of bookings in ghi last week agent wise",
                "leads in fire this month by agent",
                "marine bookings yesterday agent wise",
            ],
            
            "Time-based Queries": [
                "leads today",
                "bookings yesterday",
                "revenue this week",
                "premium last month",
                "conversion rate this month",
            ],
            
            "Feedback Testing": [
                "when someone says product wise, rather than showing investment type id, show product name wise",
                "this query is wrong",
                "good job bot",
                "show me better results",
            ],
            
            "Conversation Testing": [
                "hello",
                "hi there",
                "how are you",
                "what can you do",
            ],
            
            "Complex Queries": [
                "conversion rate for fire and marine last week agent wise",
                "revenue and premium for ghi wc fire this month product wise",
                "leads bookings and revenue for marine yesterday",
            ],
            
            "Edge Cases": [
                "number of leads in rest",  # Non-existent product
                "bookings in xyz",  # Non-existent product
                "leads in dws",  # Non-existent product
                "",  # Empty query
                "   ",  # Whitespace only
            ]
        }
        
        for category, questions in test_categories.items():
            print(f"\n📋 {category}:")
            for i, question in enumerate(questions, 1):
                print(f"  {i}. \"{question}\"")
        
        print(f"\n📊 Expected Behaviors:")
        print("  • Product queries should detect correct products")
        print("  • Non-existent products should trigger clarification")
        print("  • Multi-product queries should work")
        print("  • Product-wise results should show product names, not IDs")
        print("  • Agent-wise results should group by agent")
        print("  • Feedback should be stored and sent to team")
        print("  • Conversation should be handled appropriately")
        print("  • Excel download and alert buttons should appear")
        print("  • Query should be displayed to user")

    def run_all_tests(self):
        """Run all automated tests"""
        print("🚀 Starting Comprehensive Bot Tests...")
        print("="*80)
        
        # Run all test categories
        self.test_file_structure()
        self.test_configuration()
        self.test_product_detection()
        self.test_sql_generation()
        self.test_subscription_manager()
        self.test_business_logic_manager()
        self.test_database_connection()
        self.test_masking_service()
        
        # Print summary
        print("="*80)
        print("📊 TEST SUMMARY")
        print("="*80)
        print(f"Total Tests: {self.total_tests}")
        print(f"Passed: {self.passed_tests} ✅")
        print(f"Failed: {self.failed_tests} ❌")
        
        success_rate = 0
        if self.total_tests > 0:
            success_rate = (self.passed_tests / self.total_tests) * 100
        
        print(f"Success Rate: {success_rate:.1f}%")
        
        # Save detailed results
        results_file = f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump({
                "summary": {
                    "total": self.total_tests,
                    "passed": self.passed_tests,
                    "failed": self.failed_tests,
                    "success_rate": success_rate
                },
                "results": self.test_results
            }, f, indent=2)
        
        print(f"\n📄 Detailed results saved to: {results_file}")
        
        # Generate manual test questions
        self.generate_test_questions()
        
        return self.failed_tests == 0

if __name__ == "__main__":
    tester = ComprehensiveBotTester()
    success = tester.run_all_tests()
    
    print("\n--- TEST EXECUTION FINISHED ---")
    
    # Read and print the log file
    with open("test_log.txt", "r", encoding="utf-8") as f:
        print(f.read())
        
    if success:
        print("\n🎉 All automated tests passed! Please run the manual tests above.")
        sys.exit(0)
    else:
        print("\n⚠️ Some tests failed. Please check the results above.")
        sys.exit(1) 