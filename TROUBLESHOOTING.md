# ThinkTank Bot Troubleshooting Guide

## Common Issues and Solutions

### 1. No Data Returned for Queries

**Problem**: Queries return 0 rows even when they should have data.

**Solutions**:
- **Date Format Issue**: The `leadmonth` column uses format 'Month-YYYY' (e.g., 'April-2024')
  - ❌ Wrong: `leadmonth = 'April'`
  - ✅ Correct: `leadmonth = 'April-2024'`

- **Product ID Issue**: Verify the correct product IDs are being used
  - Marine Insurance: ID 13
  - Fire Insurance: ID 5
  - Group Health Insurance: ID 1

### 2. Multiple Products Found

**Problem**: System finds multiple products for a single query (e.g., [10, 13, 47] for "marine insurance")

**Solutions**:
- The system now prioritizes exact phrase matches
- "marine insurance" should only match ID 13
- Check if there are conflicting aliases in the PRODUCTS dictionary

### 3. Environment Variables Missing

**Problem**: Bot fails to start due to missing environment variables

**Required Variables**:
```
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_APP_TOKEN=xapp-your-app-token
GOOGLE_API_KEY=your-google-api-key
PRESTO_CONNECTION=presto://user:pass@host:port/catalog/schema
FEEDBACK_CHANNEL_ID=C1234567890
```

### 4. Database Connection Issues

**Problem**: Cannot connect to Presto database

**Solutions**:
- Verify PRESTO_CONNECTION string format
- Check network connectivity to database server
- Ensure database credentials are correct
- Test connection with a simple query

### 5. AI Model Issues

**Problem**: Gemini AI model fails to initialize or respond

**Solutions**:
- Verify GOOGLE_API_KEY is valid and has proper permissions
- Check internet connectivity
- Ensure the API key has access to Gemini models

## Debug Steps

### Step 1: Run Debug Test
```bash
python debug_test.py
```

This will test:
- Environment variables
- Database connection
- AI model initialization
- Product resolution
- Sample queries

### Step 1.5: Test AI Processor (New)
```bash
python test_ai_processor.py
```

This will test the new AI-driven approach:
- Unified intent classification and product resolution
- Feedback extraction
- Product details retrieval
- Various query scenarios

### Step 2: Check Logs
Look for these debug messages in the console:
- `DEBUG: Resolving all products for text: '...'`
- `DEBUG: Found exact phrase match: '...'`
- `DEBUG: ----- EXECUTING SQL -----`

### Step 3: Test Individual Components

**Test Database**:
```sql
SELECT COUNT(*) FROM sme_analytics.sme_leadbookingrevenue;
SELECT DISTINCT leadmonth FROM sme_analytics.sme_leadbookingrevenue ORDER BY leadmonth DESC LIMIT 5;
SELECT DISTINCT investmenttypeid FROM sme_analytics.sme_leadbookingrevenue WHERE investmenttypeid IN (13, 5, 1);
```

**Test Product Resolution**:
```python
from main import SimplifiedBot
from database import SimpleDatabase

db = SimpleDatabase(os.getenv("PRESTO_CONNECTION"))
bot = SimplifiedBot(db)

# Test product resolution
products = bot.resolve_products("marine insurance leads")
print(f"Found products: {products}")
```

## Quick Fixes

### Fix Date Format Issues
The AI prompt now includes explicit instructions about date formats:
- For month queries: Use `leadmonth = 'April-2024'` (not just 'April')
- Current year is automatically added to the prompt

### AI-Driven Product Resolution
The system now uses AI for intelligent product resolution:
- **Unified Processing**: Both intent classification and product resolution in one AI call
- **Better Context Understanding**: AI considers business context and terminology
- **Improved Ambiguity Handling**: Better suggestions when products are unclear
- **Natural Language**: Handles variations, abbreviations, and complex queries

### Fix SQL Generation
The AI prompt now includes:
- Explicit table name requirements
- Date format examples
- Product ID mapping examples

### New AI Processor Benefits
- **Single AI Call**: More efficient processing
- **Better Accuracy**: AI understands context better than rule-based matching
- **Flexible Matching**: Handles typos, abbreviations, and natural language
- **Intelligent Suggestions**: Provides helpful clarification when needed

## Performance Tips

1. **Use Caching**: The system caches query results for 5 minutes by default
2. **Limit Results**: For large datasets, consider adding LIMIT clauses
3. **Optimize Queries**: Use specific date ranges instead of scanning all data

## Getting Help

If you're still having issues:

1. Run the debug test script
2. Check the console output for error messages
3. Verify all environment variables are set
4. Test database connectivity manually
5. Check if the issue is with specific queries or the entire system

## Common Query Patterns

**Leads by Product**:
```sql
SELECT COUNT(*) FROM sme_analytics.sme_leadbookingrevenue 
WHERE investmenttypeid = 13
```

**Leads by Month**:
```sql
SELECT COUNT(*) FROM sme_analytics.sme_leadbookingrevenue 
WHERE leadmonth = 'April-2024'
```

**Agent-wise Leads**:
```sql
SELECT leadassignedagentname, COUNT(*) 
FROM sme_analytics.sme_leadbookingrevenue 
WHERE investmenttypeid = 13 
GROUP BY leadassignedagentname
``` 