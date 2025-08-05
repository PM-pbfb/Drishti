from dotenv import load_dotenv
import os

# Explicitly load .env from the script's directory
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)
else:
    print("⚠️ .env file not found, please ensure it exists in the project root.")

import time
import pandas as pd
import json
import hashlib
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import google.generativeai as genai
from datetime import datetime
import re
from rapidfuzz import process as fuzzy_process, fuzz

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
from intent_classifier import intent_classifier

from masking_service import masking_service

# Simple caching for user contexts and pending clarifications
user_contexts = {}
pending_clarifications = {}

class SimplifiedBot:
    def __init__(self, db_manager):
        self.model = model
        self.db = db_manager
        
    def resolve_products(self, text):
        """
        Intelligently resolves MULTIPLE products from text.
        It scans the text for all known aliases and returns a list of all product IDs found.
        """
        print(f"DEBUG: Resolving all products for text: '{text}'")
        text_lower = text.lower()
        
        # A more comprehensive list of stop words
        stop_words = ['for', 'a', 'an', 'the', 'is', 'are', 'was', 'were', 'tell', 'me', 'what', 'how', 'many', 'much', 'in', 'of', 'on', 'at', 'by', 'show', 'leads', 'bookings', 'revenue', 'premium', 'conversion', 'rate', 'today', 'yesterday', 'this', 'last', 'week', 'month', 'year', 'insurance', 'policy', 'comp', 'about', 'and', 'also', 'number', 'count']
        
        # Marketing channels that should NOT be treated as products
        marketing_channels = ['seo', 'crm', 'direct', 'referral', 'brand', 'paid', 'fos', 'mobile', 'app', 'marketing', 'campaigns', 'channel', 'system', 'team', 'from', 'came', 'through', 'via', 'using', 'with', 'by', 'get', 'gets', 'getting']
        
        words = [word for word in re.findall(r'\b\w+\b', text_lower) if word not in stop_words and word not in marketing_channels]
        
        found_products = set()
        
        
        # First, check for exact phrases (most specific matches)
        exact_phrases = ['fire insurance', 'marine insurance', 'workmen compensation', 'group health insurance']
        exact_match_found = False
        for phrase in exact_phrases:
            if phrase in text_lower:
                if phrase in PRODUCTS:
                    found_products.add(PRODUCTS[phrase])
                    exact_match_found = True
                    break  # Found exact match, don't look for more general ones
        
        # If no exact phrase found, do the general alias matching
        if not exact_match_found:
            # Sort aliases by length, longest first, to prioritize more specific matches
            sorted_aliases = sorted(PRODUCTS.keys(), key=len, reverse=True)
            
            # Do a simple substring check for direct alias matches
            for alias in sorted_aliases:
                # Use word boundaries to avoid matching parts of other words (e.g., 'fire' in 'firewall')
                if re.search(r'\b' + re.escape(alias) + r'\b', text_lower):
                    found_products.add(PRODUCTS[alias])


        # Then, use fuzzy matching on the remaining words to catch typos/variations (only if no exact match)
        if not exact_match_found and words:
            search_phrase = " ".join(words)
            matches = fuzzy_process.extract(search_phrase, PRODUCTS.keys(), scorer=fuzz.token_set_ratio, score_cutoff=75)
            for match, score, _ in matches:
                found_products.add(PRODUCTS[match])

        if not found_products:
            print("DEBUG: No products found.")
            return []
            
        product_id_list = sorted(list(found_products))
        print(f"DEBUG: All products found: {product_id_list}")
        return product_id_list

    def generate_response(self, user_text, user_id, product_ids=None):
        """Single AI call to handle all user requests with a more robust prompt."""
        
        product_context = "No specific product filter has been identified."
        if product_ids:
            names = []
            for pid in product_ids:
                best_name = "Unknown"
                for alias, p_id in PRODUCTS.items():
                    if p_id == pid:
                        if len(alias) > len(best_name) or best_name == "Unknown":
                            best_name = alias
                names.append(best_name.title())
            
            product_names_str = ", ".join(sorted(list(set(names))))
            product_context = f"**Product Filter**: The user is asking about **{product_names_str}**. You MUST use these exact IDs in your query: `{product_ids}`."

        approved_logic = business_logic_manager.get_relevant_approved_logic(user_text)
        logic_context = ""
        if approved_logic:
            logic_context = "\n\n**CRITICAL INSTRUCTIONS FROM HUMAN EXPERTS:**\n" + "\n".join(f"- {logic}" for logic in approved_logic)
            
        time_syntax_examples = "\n".join([f"- For '{name}', use this SQL: `{syntax}`" for name, syntax in TIME_PATTERNS.items()])
        
        # Dynamically build the column details from the enhanced TABLE_SCHEMA
        column_details = []
        for col, meta in TABLE_SCHEMA.items():
            details = f"- `{col}` ({meta.get('data_type', 'unknown')}): {meta.get('description', '')}"
            if meta.get('pii_level', 'none') != 'none':
                details += f" PII: {meta['pii_level']}, Strategy: {meta['masking_strategy']}."
            column_details.append(details)
        available_columns_context = "\n".join(column_details)

        # Get categorical values context
        categorical_values_context = self.get_categorical_values_context()

        prompt = f"""You are ThinkTank, a specialized AI analyst. Your task is to respond to user queries about insurance data by generating a single, precise JSON object.

**User Query**: "{user_text}"

**Contextual Analysis**:
{product_context}

**CRITICAL DATABASE RULES**:
- **ONLY use this table**: `sme_analytics.sme_leadbookingrevenue`
- **NEVER invent or use other table names** like ghi_bookings, fire_bookings, product_lookup, etc.
- **NEVER use JOIN statements** - only use the single table mentioned above
- **For date comparisons**: Always cast date columns using `CAST(column_name AS DATE)` or `DATE(column_name)` before comparison
- **Available columns**: 
{available_columns_context}
- **For product names**: Use CASE statements to map investmenttypeid to product names, like: `CASE WHEN investmenttypeid = 5 THEN 'Fire Insurance' WHEN investmenttypeid = 13 THEN 'Marine Insurance' END`
{categorical_values_context}

**Your Task**: Respond with a JSON object for ONE of the following intents.

1.  **"metric_query"**: For any request about business data.
    - **CRITICAL**: If the Contextual Analysis provides `Product Filter` IDs, you MUST use those exact IDs in a `WHERE investmenttypeid IN (...)` clause.
    - **CRITICAL**: You MUST use the correct SQL time syntax provided in the examples below. Do NOT use functions like `DATE('yesterday')`.
    - **CRITICAL**: The SQL query must be valid Presto SQL and NEVER end with a semicolon `;`.
    - **For categorization requests** (like "agent wise", "product wise"): Use `GROUP BY` with the appropriate column (e.g., `GROUP BY leadassignedagentname` for agent-wise, `GROUP BY investmenttypeid` for product-wise).
    - **For product-wise results**: Use CASE statements to show product names instead of IDs in the SELECT clause. **CRITICAL**: When using CASE statements with GROUP BY, you MUST repeat the full CASE expression in GROUP BY, not use the alias.
    - **For categorical value filters**: If the user mentions specific values (like "SEO", "Google Ads", "Direct", etc.), check the Available Categorical Values above and add appropriate WHERE clauses (e.g., `WHERE mkt_category = 'SEO'`).
    - **IMPORTANT**: For marketing channels like "SEO", "CRM", "Direct", "Referral", "Brand Paid", "Non Brand Paid", "FOS" - use `mkt_category` column. For system/platform sources, use `leadcreationsource` column.
    - **CRITICAL**: "CRM" in user queries refers to the marketing category, so always use `mkt_category = 'CRM'`, not `leadcreationsource = 'CRM'`.
    - **For online bookings**: When users ask about "online bookings", always add `AND paymentstatus = 300` to filter for completed online payments.
    - **For date ranges**: Use proper date casting and the correct time patterns provided below.
    - Provide a simple `explanation` of what the query does.
    - Example: `{{"intent": "metric_query", "sql": "SELECT CASE WHEN investmenttypeid = 5 THEN 'Fire Insurance' WHEN investmenttypeid = 13 THEN 'Marine Insurance' END as product_name, COUNT(*) FROM sme_analytics.sme_leadbookingrevenue WHERE investmenttypeid IN (5, 13) GROUP BY CASE WHEN investmenttypeid = 5 THEN 'Fire Insurance' WHEN investmenttypeid = 13 THEN 'Marine Insurance' END", "explanation": "This query counts leads for Fire and Marine products, grouped by product."}}`
    - Example with marketing filter: `{{"intent": "metric_query", "sql": "SELECT COUNT(*) FROM sme_analytics.sme_leadbookingrevenue WHERE investmenttypeid IN (1) AND mkt_category = 'CRM' AND CAST(leaddate AS DATE) >= DATE_TRUNC('month', CURRENT_DATE) - INTERVAL '3' MONTH", "explanation": "This query counts leads for Group Health Insurance from CRM source in the last 3 months."}}`

2.  **"conversation"**: For simple greetings, chit-chat, or if the user asks for multiple, distinct things in a single query.
    - Example for complex query: `{{"intent": "conversation", "response": "I can only handle one request at a time. Please ask about GHI leads or Fire bookings separately."}}`
    - Example for greeting: `{{"intent": "conversation", "response": "Hello! How can I help you with your business metrics today?"}}`

3.  **"feedback"**: If the user provides feedback, suggestions, or asks for improvements (e.g., "this is wrong," "good job", "show product names instead of IDs", "when someone says product wise", "payment status should be 300", "always filter by", "should include", "must have").
    - Example: `{{"intent": "feedback", "message": "The user wants to see product names instead of investmenttypeid in results."}}`
    - Example: `{{"intent": "feedback", "message": "User provided business rule: payment status should be 300 for online bookings."}}`

**Reference: Correct SQL Time Syntax**:
{time_syntax_examples}
{logic_context}

Respond now with only the JSON object."""

        print("DEBUG: ----- GENERATING AI PROMPT -----")
        try:
            response = self.model.generate_content(
                prompt,
                generation_config={"max_output_tokens": MAX_OUTPUT_TOKENS, "temperature": TEMPERATURE}
            )
            response_text = response.text.strip().replace('```json', '').replace('```', '')
            print(f"DEBUG: ----- RAW AI RESPONSE -----\n{response_text}\nDEBUG: ---------------------------")
            
            ai_obj = json.loads(response_text)

            if "metric_query" in ai_obj and "intent" not in ai_obj:
                inner = ai_obj["metric_query"]
                ai_obj = {
                    "intent":      "metric_query",
                    "sql":         inner.get("query") or inner.get("sql"),
                    "explanation": inner.get("explanation", "Query generated based on your request.")
                }
            
            return ai_obj
        except Exception as e:
            print(f"AI Error or JSON parsing failed: {e}")
            return {"intent": "conversation", "response": "Sorry, I'm having a little trouble thinking right now. Could you please rephrase your request?"}
    
    def execute_sql_query(self, sql_query, explanation):
        sql_query = sql_query.strip().rstrip(';')
        print(f"DEBUG: ----- EXECUTING SQL -----\n{sql_query}\nDEBUG: -------------------------")
        try:
            df = self.db.run_query(sql_query)
            if df.empty:
                return "No data found for your query.", None, None

            # Generate a masked version of the DataFrame for AI context
            df_masked = masking_service.mask_dataframe(df)
            
            query_id = hashlib.md5(sql_query.encode()).hexdigest()[:8]
            self.save_query_result(query_id, df_masked, sql_query, explanation)

            # Format the original (unmasked) DataFrame for Slack
            if len(df) == 1 and len(df.columns) == 1:
                value = df.iloc[0, 0]
                result_text = f"📊 **Result**: {value:,}\n\n💡 {explanation}\n\n🔍 **Query**:\n```\n{sql_query}\n```"
            else:
                table = df.to_string(index=False, max_rows=20)
                result_text = f"📊 **Results**:\n```\n{table}\n```\n\n💡 {explanation}\n\n📎 Query ID: {query_id}\n\n🔍 **Query**:\n```\n{sql_query}\n```"
            
            # Return both the unmasked text for Slack and the masked DataFrame for context
            return result_text, query_id, df_masked

        except Exception as e:
            return f"❌ Query failed: {str(e)}", None, None
    
    def save_query_result(self, query_id, df, sql_query, explanation):
        try:
            os.makedirs("query_results", exist_ok=True)
            # Save the masked data to the query results
            with open(f"query_results/{query_id}.json", "w") as f:
                json.dump({"data": df.to_dict('records'), "sql": sql_query, "explanation": explanation}, f)
        except Exception as e:
            print(f"Failed to save query result: {e}")

    def get_categorical_values_context(self):
        """Get distinct values from categorical columns to help AI understand user queries"""
        try:
            # Get categorical columns from schema
            categorical_columns = []
            for col, meta in TABLE_SCHEMA.items():
                if meta.get("is_categorical", False) and meta.get("pii_level", "none") != "high":
                    categorical_columns.append(col)
            
            if not categorical_columns:
                return ""
            
            # Build context for categorical columns
            context_parts = []
            for col in categorical_columns:
                # Use sample values from config for now (we could fetch real distincts if needed)
                sample_values = TABLE_SCHEMA[col].get("sample_values", [])
                if sample_values:
                    # Take first 10 values to keep context manageable
                    values_str = ", ".join([f"'{v}'" for v in sample_values[:10]])
                    context_parts.append(f"- `{col}`: {values_str}")
            
            if context_parts:
                return "\n**Available Categorical Values:**\n" + "\n".join(context_parts)
            return ""
            
        except Exception as e:
            print(f"Error getting categorical values context: {e}")
            return ""

bot = SimplifiedBot(db_manager)

def run_main_logic(text, user_id, say, product_ids=None):
    try:
        # First, use AI to classify intent intelligently
        intent_classification = intent_classifier.classify_intent(text, product_ids)
        print(f"DEBUG: AI Intent Classification: {intent_classification}")
        
        intent = intent_classification.get("intent")
        confidence = intent_classification.get("confidence", 0.5)
        
        # If it's feedback, handle it immediately with detailed extraction
        if intent == "feedback":
            feedback_details = intent_classifier.get_feedback_details(text, product_ids)
            print(f"DEBUG: Feedback Details: {feedback_details}")
            
            # Store feedback and notify the team
            feedback_message = feedback_details.get("specific_issue", "User provided feedback")
            feedback_id = business_logic_manager.store_feedback(
                user_id=user_id, 
                original_query=text, 
                feedback_text=feedback_message, 
                context={
                    **user_contexts.get(user_id, {}),
                    "feedback_type": feedback_details.get("feedback_type"),
                    "priority": feedback_details.get("priority"),
                    "business_impact": feedback_details.get("business_impact"),
                    "extracted_rule": feedback_details.get("extracted_rule")
                }
            )
            
            # Send notification to feedback channel
            notification = f"""🔔 *New Feedback for Review* | ID: `{feedback_id}`
*User*: <@{user_id}>
*Original Query*: `{text}`
*Feedback Type*: {feedback_details.get('feedback_type', 'Unknown')}
*Priority*: {feedback_details.get('priority', 'Medium')}
*Specific Issue*: {feedback_details.get('specific_issue', 'No specific issue mentioned')}
*Suggested Solution*: {feedback_details.get('suggested_solution', 'No solution suggested')}
*Business Impact*: {feedback_details.get('business_impact', 'Unknown')}
*Extracted Rule*: {feedback_details.get('extracted_rule', 'None')}"""
            
            blocks = [
                {"type": "section", "text": {"type": "mrkdwn", "text": notification}},
                {"type": "actions", "block_id": f"feedback_actions_{feedback_id}", "elements": [
                    {"type": "button", "text": {"type": "plain_text", "text": "✅ Approve Logic"}, "action_id": "approve_feedback", "value": str(feedback_id), "style": "primary"},
                    {"type": "button", "text": {"type": "plain_text", "text": "❌ Reject"}, "action_id": "reject_feedback", "value": str(feedback_id), "style": "danger"}
                ]}
            ]
            
            app.client.chat_postMessage(
                channel=FEEDBACK_CHANNEL_ID, 
                text="New feedback received", 
                blocks=blocks
            )
            
            say("✅ Thank you for your feedback! It has been submitted for review by the team.")
            return
        
        # For other intents, proceed with the original AI response generation
        ai_response = bot.generate_response(text, user_id, product_ids=product_ids)
        intent = ai_response.get("intent")
        
        if intent == "metric_query":
            sql = ai_response.get("sql")
            explanation = ai_response.get("explanation", "Query executed")
            if sql:
                result_text, query_id, df_masked = bot.execute_sql_query(sql, explanation)
                
                if query_id:
                    blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": result_text}}, {"type": "actions", "elements": [{"type": "button", "text": {"type": "plain_text", "text": "📥 Download Excel"}, "action_id": "download_excel", "value": query_id}, {"type": "button", "text": {"type": "plain_text", "text": "🔔 Subscribe to Alerts"}, "action_id": "subscribe_alerts", "value": query_id, "style": "primary"}]}]
                    say(blocks=blocks, text=result_text)
                else:
                    say(result_text)
                    
                # Store the masked result in the user context
                if df_masked is not None:
                    user_contexts[user_id] = {"last_query": text, "last_sql": sql, "last_result": df_masked.to_string()}
                else:
                    user_contexts[user_id] = {"last_query": text, "last_sql": sql, "last_result": "Query failed"}
            else:
                say("❌ I couldn't generate a query for that request.")
        elif intent == "conversation":
            say(f"💭 {ai_response.get('response', 'I am here to help!')}")
        elif intent == "clarification":
            say(f"🤔 {ai_response.get('response', 'Could you please clarify your request?')}")
        elif intent == "help":
            say("Here's how I can help...")
        else:
            say("🤔 I'm not sure how to help. Try asking about business metrics.")
    
    except Exception as e:
        print(f"Error in run_main_logic: {e}")
        say("❌ Something went wrong. Please try again.")

@app.event("app_mention")
def handle_message(event, say):
    user_id = event["user"]
    text = re.sub(r'^<@\w+>\s*', '', event.get("text", "")).strip()
    print(f"\n\nDEBUG: ----- NEW MESSAGE RECEIVED -----\nUser: {user_id}\nText: '{text}'\n------------------------------------")
    
    if not text:
        say("👋 Hi! I can help with business metrics or just chat.")
        return
    
    say("🤖 Processing...")
    
    product_ids = bot.resolve_products(text)
    
    # If no products found, ask for clarification
    if not product_ids:
        # Check if this might be a product query that we couldn't match
        words = re.findall(r'\b\w+\b', text.lower())
        stop_words = ['leads', 'bookings', 'revenue', 'premium', 'today', 'yesterday', 'week', 'month', 'year', 'this', 'last', 'for', 'in', 'of', 'the', 'a', 'an', 'and', 'or', 'but', 'is', 'are', 'was', 'were', 'have', 'has', 'had', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'tell', 'me', 'what', 'how', 'many', 'much', 'show', 'give', 'get', 'find', 'count', 'sum', 'total', 'average', 'avg', 'max', 'min', 'number', 'seo', 'direct', 'referral', 'brand', 'paid', 'crm', 'fos', 'mobile', 'app', 'marketing', 'campaigns', 'channel', 'system', 'team', 'from', 'came', 'came', 'through', 'via', 'using', 'with', 'by', 'gets', 'getting']
        potential_products = [word for word in words if len(word) >= 2 and word not in stop_words]
        
        if potential_products:
            # Store the original query for clarification
            pending_clarifications[user_id] = {
                "original_query": text,
                "potential_products": potential_products,
                "timestamp": time.time()
            }
            
            blocks = [
                {"type": "section", "text": {"type": "mrkdwn", "text": f"🤔 I'm not sure which product you mean by '{potential_products[0]}'. Could you clarify?"}},
                {"type": "actions", "elements": [
                    {"type": "button", "text": {"type": "plain_text", "text": "❌ No, let me rephrase"}, "action_id": "clarification_no", "value": user_id},
                    {"type": "button", "text": {"type": "plain_text", "text": "💡 Show me available products"}, "action_id": "show_products", "value": user_id}
                ]}
            ]
            say(blocks=blocks, text=f"I'm not sure which product you mean by '{potential_products[0]}'. Could you clarify?")
            return
        else:
            # No potential products found, run without filter
            run_main_logic(text, user_id, say)
            return
    
    # If multiple products found, run with all of them
    if len(product_ids) > 1:
        run_main_logic(text, user_id, say, product_ids=product_ids)
        return
    
    # For single product, proceed normally
    run_main_logic(text, user_id, say, product_ids=product_ids)

@app.action("download_excel")
def handle_download_excel(ack, body, say):
    ack()
    query_id = body["actions"][0]["value"]
    try:
        with open(f"query_results/{query_id}.json", "r") as f:
            df = pd.DataFrame(json.load(f)["data"])
        excel_path = f"temp_exports/{query_id}.xlsx"
        df.to_excel(excel_path, index=False)
        app.client.files_upload_v2(channel=body["channel"]["id"], file=excel_path, filename=f"query_result_{query_id}.xlsx", initial_comment="📊 Here's your data!", thread_ts=body["message"]["ts"])
        os.remove(excel_path)
    except Exception as e:
        say(f"❌ Failed to generate Excel file: {e}", thread_ts=body["message"]["ts"])

@app.action("subscribe_alerts")
def handle_subscribe_alerts(ack, body, client):
    ack()
    try:
        client.views_open(trigger_id=body["trigger_id"], view={"type": "modal", "callback_id": "submit_subscription", "title": {"type": "plain_text", "text": "Subscribe to Alerts"}, "submit": {"type": "plain_text", "text": "Subscribe"}, "blocks": [{"type": "input", "block_id": "frequency_block", "label": {"type": "plain_text", "text": "How often?"}, "element": {"type": "static_select", "action_id": "frequency_select", "options": [{"text": {"type": "plain_text", "text": "Hourly"}, "value": "hourly"}, {"text": {"type": "plain_text", "text": "Daily (at 9 AM)"}, "value": "daily"}, {"text": {"type": "plain_text", "text": "Weekly (Mondays at 9 AM)"}, "value": "weekly"}]}}], "private_metadata": json.dumps({"query_id": body["actions"][0]["value"], "channel_id": body["channel"]["id"]})})
    except Exception as e:
        print(f"Error opening view: {e}")

@app.view("submit_subscription")
def handle_subscription_submission(ack, body, say):
    ack()
    user_id = body["user"]["id"]
    try:
        metadata = json.loads(body["view"]["private_metadata"])
        query_id = metadata["query_id"]
        channel_id = metadata["channel_id"]
        selected_frequency = body["view"]["state"]["values"]["frequency_block"]["frequency_select"]["selected_option"]["value"]
        with open(f"query_results/{query_id}.json", "r") as f:
            query_context = json.load(f)
        subscription_id = subscription_manager.add_subscription(user_id, channel_id, query_context, selected_frequency)
        if subscription_id:
            say(channel=channel_id, text=f"✅ You are now subscribed to **{selected_frequency}** alerts for this metric. Your subscription ID is `{subscription_id}`.")
        else:
            say(channel=channel_id, text="❌ Unable to create your subscription.")
    except Exception as e:
        print(f"Error creating subscription: {e}")
        say(channel=metadata.get("channel_id", user_id), text="An error occurred.")

@app.command("/unsubscribe")
def handle_unsubscribe_command(ack, say, command):
    ack()
    user_id = command["user_id"]
    subscriptions = subscription_manager.get_user_subscriptions(user_id)
    if not subscriptions:
        say("You have no active subscriptions.")
        return
    blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": "Here are your active subscriptions. Click to unsubscribe."}}]
    for sub in subscriptions:
        blocks.append({"type": "divider"})
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": f"ID: {sub['id']} - {sub.get('metric')} for {sub.get('product')}"}, "accessory": {"type": "button", "text": {"type": "plain_text", "text": "Unsubscribe"}, "value": str(sub['id']), "action_id": "unsubscribe"}})
    say(blocks=blocks)

@app.action("unsubscribe")
def handle_unsubscribe(ack, body, say):
    ack()
    subscription_id = int(body["actions"][0]["value"])
    if subscription_manager.remove_subscription(subscription_id):
        say(f"✅ Unsubscribed from alert {subscription_id}.", thread_ts=body["message"]["ts"])
    else:
        say(f"❌ Unable to remove subscription.", thread_ts=body["message"]["ts"])

@app.action("approve_feedback")
def handle_approve_feedback(ack, body, say):
    ack()
    feedback_id = int(body["actions"][0]["value"])
    if business_logic_manager.update_feedback_status(feedback_id, "approved"):
        say(text=f"✅ Feedback ID `{feedback_id}` has been approved.", thread_ts=body["message"]["ts"])
    else:
        say(text=f"❌ Could not find feedback with ID `{feedback_id}`.", thread_ts=body["message"]["ts"])

@app.action("reject_feedback")
def handle_reject_feedback(ack, body, say):
    ack()
    feedback_id = int(body["actions"][0]["value"])
    if business_logic_manager.update_feedback_status(feedback_id, "rejected"):
        say(text=f"❌ Feedback ID `{feedback_id}` has been rejected.", thread_ts=body["message"]["ts"])
    else:
        say(text=f"❌ Could not find feedback with ID `{feedback_id}`.", thread_ts=body["message"]["ts"])

@app.action("clarification_no")
def handle_clarification_no(ack, body, say):
    ack()
    user_id = body["actions"][0]["value"]
    if user_id in pending_clarifications:
        del pending_clarifications[user_id]
    say("👍 No problem! Please rephrase your question with a clearer product name.")

@app.action("show_products")
def handle_show_products(ack, body, say):
    ack()
    user_id = body["actions"][0]["value"]
    
    # Show available products
    product_list = []
    for alias, product_id in PRODUCTS.items():
        if len(alias) > 2:  # Skip very short aliases
            product_list.append(f"• {alias}")
    
    # Take first 20 products to avoid message too long
    product_text = "\n".join(product_list[:20])
    
    say(f"📋 Here are some available products you can ask about:\n\n{product_text}\n\n💡 You can also use abbreviations like 'ghi', 'wc', 'fire', 'marine', etc.")

# --- All other handlers (subscribe, feedback, etc.) would go here ---

if __name__ == "__main__":
    import threading

    def run_scheduler(db_manager):
        while True:
            time.sleep(60)

    print("🚀 Starting Simplified ThinkTank Bot...")
    os.makedirs("query_results", exist_ok=True)
    os.makedirs("temp_exports", exist_ok=True)

    scheduler_thread = threading.Thread(target=run_scheduler, args=(db_manager,), daemon=True)
    scheduler_thread.start()

    print("🎯 Bot ready to serve!")
    handler = SocketModeHandler(app, os.getenv("SLACK_APP_TOKEN"))
    handler.start()
