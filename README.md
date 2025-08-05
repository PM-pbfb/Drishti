# Drishti - AI-Powered Insurance Analytics Bot

An intelligent Slack bot that provides real-time insurance analytics and business insights using natural language queries.

## 🚀 Quick Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Create Environment File
Create a `.env` file in the project root with the following variables:

```env
# Slack Configuration
SLACK_BOT_TOKEN=xoxb-your-bot-token-here
SLACK_APP_TOKEN=xapp-your-app-token-here
FEEDBACK_CHANNEL_ID=your-feedback-channel-id

# AI Configuration
GOOGLE_API_KEY=your-gemini-api-key-here

# Database Configuration
PRESTO_CONNECTION=your-presto-connection-string
```

### 3. Run the Bot
```bash
python main.py
```

## 💬 Usage

### Query Examples
```
@Drishti fire insurance bookings this month
@Drishti marine revenue last week
@Drishti group health leads today
@Drishti conversion rate for workmen compensation
@Drishti bookings by agent for fire insurance
```

### Features
- **Natural Language Queries**: Ask questions in plain English
- **Product Intelligence**: Automatically detects insurance products
- **Real-time Analytics**: Get instant business metrics
- **Excel Exports**: Download results as Excel files
- **Alert Subscriptions**: Set up automated metric alerts
- **Feedback System**: Improve bot responses through feedback

## 🔧 Configuration

The bot automatically handles:
- Product detection (Fire, Marine, Health, etc.)
- Time-based queries (today, yesterday, this week, etc.)
- Categorical filtering (by agent, by product, by marketing channel)
- Data masking for privacy compliance

## 🛡️ Security

- All sensitive data is masked before AI processing
- No PII data is exposed to AI models
- Environment variables for all credentials
- Secure database connections

## 📊 Supported Products

- Group Health Insurance
- Fire Insurance
- Marine Insurance
- Workmen Compensation
- Professional Indemnity
- And 100+ more insurance products

## 🆘 Support

For issues or feedback, use the feedback feature in Slack or contact the development team.