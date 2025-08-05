#!/usr/bin/env python3
"""
AI-Driven Intent Classifier for ThinkTank Bot
Uses AI to intelligently classify user intents beyond rigid patterns
"""

import json
import os
import google.generativeai as genai

# Initialize Gemini
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

class IntentClassifier:
    """AI-driven intent classification system"""
    
    def __init__(self):
        self.model = model
    
    def classify_intent(self, user_text, product_ids=None):
        """
        Use AI to intelligently classify user intent
        
        Returns:
            dict: {
                "intent": "metric_query" | "feedback" | "conversation" | "clarification",
                "confidence": float (0-1),
                "reasoning": str,
                "extracted_info": dict
            }
        """
        
        product_context = ""
        if product_ids:
            product_context = f"\n- User is asking about specific products: {product_ids}"
        
        prompt = f"""You are an intelligent intent classifier for a business analytics bot. Analyze the user's message and classify their intent.

**User Message**: "{user_text}"
{product_context}

**Intent Categories**:

1. **metric_query**: User wants business data, metrics, or analytics
   - Asking for numbers, counts, trends, comparisons
   - Requesting reports, dashboards, or specific data
   - Examples: "show me leads", "how many bookings", "revenue this month", "agent performance"

2. **feedback**: User is providing feedback, suggestions, or business rules
   - Correcting the bot's behavior or output
   - Suggesting improvements or new features
   - Providing business rules or requirements
   - Examples: "this is wrong", "good job", "always filter by X", "should include Y", "must have Z"

3. **conversation**: General chat, greetings, or complex multi-part requests
   - Greetings, thanks, general questions
   - Multiple unrelated requests in one message
   - Asking for help or clarification about bot capabilities
   - Examples: "hello", "thanks", "help", "what can you do"

4. **clarification**: User needs more information or is confused
   - Asking for explanations
   - Expressing confusion about results
   - Requesting more details
   - Examples: "what does this mean", "I don't understand", "explain this"

**Analysis Instructions**:
- Consider the user's tone, context, and specific words
- Look for business terminology vs casual conversation
- Identify if they're asking for data vs providing instructions
- Consider product context if provided
- Be flexible with natural language variations

**Response Format**:
```json
{{
    "intent": "metric_query|feedback|conversation|clarification",
    "confidence": 0.95,
    "reasoning": "Brief explanation of why this intent was chosen",
    "extracted_info": {{
        "business_terms": ["list", "of", "business", "terms"],
        "action_words": ["list", "of", "action", "words"],
        "tone": "professional|casual|frustrated|helpful",
        "specific_requests": ["any", "specific", "requests", "mentioned"]
    }}
}}
```

Analyze the user message and respond with the JSON object above."""

        try:
            response = self.model.generate_content(
                prompt,
                generation_config={"max_output_tokens": 500, "temperature": 0.1}
            )
            response_text = response.text.strip()
            
            # Clean up response
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            
            result = json.loads(response_text)
            
            # Validate intent
            valid_intents = ["metric_query", "feedback", "conversation", "clarification"]
            if result.get("intent") not in valid_intents:
                # Fallback to metric_query if AI gives invalid intent
                result["intent"] = "metric_query"
                result["confidence"] = 0.5
                result["reasoning"] = "Fallback to metric_query due to invalid AI response"
            
            return result
            
        except Exception as e:
            print(f"Intent classification failed: {e}")
            # Fallback classification
            return {
                "intent": "metric_query",
                "confidence": 0.3,
                "reasoning": f"Fallback due to AI error: {str(e)}",
                "extracted_info": {
                    "business_terms": [],
                    "action_words": [],
                    "tone": "unknown",
                    "specific_requests": []
                }
            }
    
    def is_feedback_intent(self, user_text, product_ids=None):
        """
        Quick check if user intent is feedback
        Returns True if feedback, False otherwise
        """
        classification = self.classify_intent(user_text, product_ids)
        return classification["intent"] == "feedback"
    
    def get_feedback_details(self, user_text, product_ids=None):
        """
        Extract detailed feedback information
        Returns dict with feedback type, message, and suggestions
        """
        classification = self.classify_intent(user_text, product_ids)
        
        if classification["intent"] != "feedback":
            return None
        
        # Use AI to extract feedback details
        prompt = f"""Extract detailed feedback information from this user message:

**User Message**: "{user_text}"

**Task**: Analyze the feedback and extract:
1. Type of feedback (correction, suggestion, business rule, praise, complaint)
2. Specific issue or request
3. Suggested solution or improvement
4. Priority level (high, medium, low)

**Response Format**:
```json
{{
    "feedback_type": "correction|suggestion|business_rule|praise|complaint",
    "specific_issue": "What specific issue or request is mentioned",
    "suggested_solution": "What solution or improvement is suggested",
    "priority": "high|medium|low",
    "business_impact": "How this affects business operations",
    "extracted_rule": "Any business rule or requirement mentioned"
}}
```

Analyze the feedback and respond with the JSON object above."""

        try:
            response = self.model.generate_content(
                prompt,
                generation_config={"max_output_tokens": 300, "temperature": 0.1}
            )
            response_text = response.text.strip()
            
            # Clean up response
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            
            feedback_details = json.loads(response_text)
            feedback_details["original_classification"] = classification
            
            return feedback_details
            
        except Exception as e:
            print(f"Feedback details extraction failed: {e}")
            return {
                "feedback_type": "suggestion",
                "specific_issue": "Unable to parse specific issue",
                "suggested_solution": "Review and improve feedback parsing",
                "priority": "medium",
                "business_impact": "Unknown",
                "extracted_rule": "",
                "original_classification": classification
            }

# Global instance
intent_classifier = IntentClassifier() 