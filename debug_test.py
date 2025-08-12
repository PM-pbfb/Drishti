#!/usr/bin/env python3
"""
Debug Test Script for ThinkTank Bot
This script helps troubleshoot common issues with the bot system.
"""

import os
import sys
from datetime import datetime

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_environment():
    """Test if all required environment variables are set"""
    print("🔍 Testing Environment Variables...")
    
    required_vars = [
        "SLACK_BOT_TOKEN",
        "SLACK_APP_TOKEN", 
        "GOOGLE_API_KEY",
        "PRESTO_CONNECTION",
        "FEEDBACK_CHANNEL_ID"
    ]
    
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: {'*' * min(len(value), 10)}...")
        else:
            print(f"❌ {var}: MISSING")
            missing_vars.append(var)
    
    if missing_vars:
        print(f"\n⚠️  Missing environment variables: {', '.join(missing_vars)}")
        print("Please create a .env file with these variables.")
        return False
    else:
        print("\n✅ All environment variables are set!")
        return True

def test_database_connection():
    """Test database connection"""
    print("\n🔍 Testing Database Connection...")
    
    try:
        from database import SimpleDatabase
        from config import PRESTO_CONNECTION
        
        if not PRESTO_CONNECTION:
            print("❌ PRESTO_CONNECTION is not set")
            return False
            
        db = SimpleDatabase(PRESTO_CONNECTION)
        if not db.engine:
            print("❌ Database engine creation failed")
            return False
            
        # Test a simple query
        test_sql = "SELECT COUNT(*) as total_records FROM sme_analytics.sme_leadbookingrevenue LIMIT 1"
        try:
            df = db.run_query(test_sql)
            print(f"✅ Database connection successful! Total records: {df.iloc[0, 0]:,}")
            return True
        except Exception as e:
            print(f"❌ Database query failed: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Database connection test failed: {e}")
        return False

def test_product_resolution():
    """Test product resolution logic"""
    print("\n🔍 Testing Product Resolution...")
    
    try:
        from main import SimplifiedBot
        from database import SimpleDatabase
        from config import PRESTO_CONNECTION
        
        db = SimpleDatabase(PRESTO_CONNECTION)
        bot = SimplifiedBot(db)
        
        test_queries = [
            "Tell me Numbers of leads agent wise for Marine product for april month",
            "number of bookings for marine insurance",
            "fire insurance leads",
            "group health insurance bookings"
        ]
        
        for query in test_queries:
            print(f"\nTesting: '{query}'")
            products = bot.resolve_products(query)
            print(f"Found products: {products}")
            
    except Exception as e:
        print(f"❌ Product resolution test failed: {e}")

def test_sample_queries():
    """Test some sample queries to see if they return data"""
    print("\n🔍 Testing Sample Queries...")
    
    try:
        from database import SimpleDatabase
        from config import PRESTO_CONNECTION
        
        db = SimpleDatabase(PRESTO_CONNECTION)
        current_year = datetime.now().year
        
        test_queries = [
            f"SELECT COUNT(*) as total_leads FROM sme_analytics.sme_leadbookingrevenue",
            f"SELECT COUNT(*) as marine_leads FROM sme_analytics.sme_leadbookingrevenue WHERE investmenttypeid = 13",
            f"SELECT COUNT(*) as april_leads FROM sme_analytics.sme_leadbookingrevenue WHERE leadmonth = 'April-{current_year}'",
            f"SELECT COUNT(*) as marine_april FROM sme_analytics.sme_leadbookingrevenue WHERE investmenttypeid = 13 AND leadmonth = 'April-{current_year}'",
            f"SELECT DISTINCT leadmonth FROM sme_analytics.sme_leadbookingrevenue ORDER BY leadmonth DESC LIMIT 10"
        ]
        
        for i, sql in enumerate(test_queries, 1):
            print(f"\nQuery {i}: {sql}")
            try:
                df = db.run_query(sql)
                if not df.empty:
                    print(f"✅ Result: {df.to_string(index=False)}")
                else:
                    print("⚠️  No data returned")
            except Exception as e:
                print(f"❌ Query failed: {e}")
                
    except Exception as e:
        print(f"❌ Sample queries test failed: {e}")

def test_ai_initialization():
    """Test AI model initialization"""
    print("\n🔍 Testing AI Model Initialization...")
    
    try:
        from main import initialize_gemini
        
        model = initialize_gemini()
        if model:
            print("✅ AI model initialized successfully")
            
            # Test a simple prompt
            test_prompt = "Hello, this is a test."
            try:
                response = model.generate_content(test_prompt)
                print("✅ AI model can generate responses")
                return True
            except Exception as e:
                print(f"❌ AI response generation failed: {e}")
                return False
        else:
            print("❌ AI model initialization failed")
            return False
            
    except Exception as e:
        print(f"❌ AI initialization test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 ThinkTank Bot Debug Test Suite")
    print("=" * 50)
    
    # Test environment
    env_ok = test_environment()
    
    # Test database
    db_ok = test_database_connection()
    
    # Test AI
    ai_ok = test_ai_initialization()
    
    # Test product resolution
    test_product_resolution()
    
    # Test sample queries
    test_sample_queries()
    
    print("\n" + "=" * 50)
    print("📊 Test Summary:")
    print(f"Environment: {'✅' if env_ok else '❌'}")
    print(f"Database: {'✅' if db_ok else '❌'}")
    print(f"AI Model: {'✅' if ai_ok else '❌'}")
    
    if all([env_ok, db_ok, ai_ok]):
        print("\n🎉 All critical components are working!")
    else:
        print("\n⚠️  Some components need attention. Check the errors above.")

if __name__ == "__main__":
    main() 