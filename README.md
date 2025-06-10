# Finance Email Summarizer

AI-powered financial email processing system for Indian users. This application automatically extracts financial entities (subscriptions, bills, loans) from Gmail emails using CrewAI agents and provides structured JSON output.

## 🚀 Features

- **Gmail OAuth Integration**: Secure authentication and email access
- **AI-Powered Extraction**: Uses CrewAI agents with OpenAI GPT-4 for entity extraction
- **Financial Entity Recognition**: Identifies subscriptions, bills, and loans from Indian financial institutions
- **Structured Output**: Provides JSON results with extracted financial data
- **Robust Pipeline**: Email fetching → Preprocessing → Entity extraction → Validation → Deduplication

## 🏗️ Architecture

```
Gmail API → Email Fetcher → Preprocessor → Entity Extractor (LLM) 
→ Schema Validator → Classifier → Deduplicator → JSON Output
```

**Tech Stack:**
- **Backend**: FastAPI + Python 3.10+
- **AI Framework**: CrewAI + LangChain
- **LLM**: OpenAI GPT-4
- **Authentication**: Google OAuth 2.0
- **Email**: Gmail API

## 📋 Prerequisites

1. **Python 3.10+**
2. **OpenAI API Key** - Get from [OpenAI Platform](https://platform.openai.com/api-keys)
3. **Google Cloud Project** with Gmail API enabled:
   - Create project at [Google Cloud Console](https://console.cloud.google.com/)
   - Enable Gmail API
   - Create OAuth 2.0 credentials
   - Add `http://localhost:8000/auth/google/callback` as redirect URI

## ⚡ Quick Start

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd AgenticEdge
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   cp env.example .env
   # Edit .env with your API keys
   ```

4. **Configure environment variables in .env file**
   ```env
   OPENAI_API_KEY=your_openai_api_key_here
   GOOGLE_CLIENT_ID=your_google_client_id_here
   GOOGLE_CLIENT_SECRET=your_google_client_secret_here
   GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback
   MONGODB_URL=mongodb://localhost:27017
   DATABASE_NAME=finance_email_summarizer
   SECRET_KEY=your-secret-key-change-in-production
   API_BASE_URL=http://localhost:8000
   ```
   
   > **Note**: The project automatically loads all environment variables from the `.env` file. All Python scripts (backend, frontend, tests) are configured to use `python-dotenv` for seamless environment variable loading.

5. **Run the server**
   ```bash
   python run_server.py
   ```

6. **Access the API**
   - API Documentation: http://localhost:8000/docs
   - Health Check: http://localhost:8000/health

## 🔐 Authentication Flow

1. **Get Authorization URL**
   ```bash
   curl http://localhost:8000/auth/google
   ```

2. **Visit the returned URL** to authorize Gmail access

3. **Complete authentication** (automatically handled by callback)

4. **Process emails**
   ```bash
   curl -X POST http://localhost:8000/process/emails/{user_id} \
        -H "Content-Type: application/json" \
        -d '{"days_back": 180, "max_emails": 50}'
   ```

## 📊 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API information |
| `/health` | GET | Health check |
| `/auth/google` | GET | Initiate OAuth flow |
| `/auth/google/callback` | GET | OAuth callback |
| `/process/emails/{user_id}` | POST | Process financial emails |
| `/process/status/{run_id}` | GET | Get processing results |
| `/users/{user_id}/profile` | GET | Get user profile |

## 📁 Project Structure

```
AgenticEdge/
├── backend/
│   ├── agents/                 # CrewAI agents and tools
│   │   ├── finance_agents.py   # Main agent definitions
│   │   └── tools.py           # Agent tools
│   ├── models/                 # Data models
│   │   └── entities.py        # Pydantic models
│   ├── services/              # Business logic
│   │   ├── gmail_service.py   # Gmail API integration
│   │   └── email_processor.py # Main processing pipeline
│   ├── config.py              # Configuration
│   └── main.py               # FastAPI application
├── logs/                      # Processing logs (auto-created)
├── requirements.txt           # Dependencies
├── env.example               # Environment template
└── run_server.py            # Server startup script
```

## 🧠 AI Processing Pipeline

The system uses CrewAI agents to process emails through multiple stages:

1. **Email Fetcher**: Retrieves financial emails from Gmail
2. **Preprocessor**: Cleans HTML, removes noise, structures content
3. **Entity Extractor**: Uses LLM to extract financial information
4. **Schema Validator**: Validates extracted data against predefined schema
5. **Classifier**: Categorizes entities (subscription/bill/loan)
6. **Deduplicator**: Removes duplicate entries
7. **State Updater**: Stores final results

## 📈 Sample Output

```json
{
  "run_id": "run_20241215_143022_user1234",
  "status": "completed",
  "entities_extracted": 3,
  "entities": [
    {
      "merchant": "Netflix",
      "amount": 649.0,
      "currency": "INR",
      "due_date": "2024-02-15",
      "entity_type": "subscription",
      "category": "entertainment",
      "auto_debit": true,
      "confidence_score": 0.95
    }
  ],
  "summary": {
    "subscriptions": 1,
    "bills": 1,
    "loans": 1,
    "total_amount": 2500.0
  }
}
```

## 🔧 Development

**Run in development mode:**
```bash
python run_server.py
```

**Check logs:**
```bash
tail -f logs/app.log
```

**View processing results:**
```bash
ls logs/processing_*.json
```

## 🛡️ Security

- Uses OAuth 2.0 for secure Gmail access
- No raw email content is stored
- Processes only financial emails
- Automatic token refresh
- User data deletion endpoint available

## 📝 Supported Financial Institutions

**Banks**: HDFC, ICICI, SBI, Axis, Kotak, PNB, BOB, Canara
**Credit Cards**: Amex, Mastercard, Visa
**Digital Services**: Paytm, PhonePe, GPay, Razorpay
**Subscriptions**: Netflix, Amazon Prime, Hotstar, Spotify
**Utilities**: Airtel, Jio, Vodafone, BSES, Tata Power

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.
Finance Email Summarizer
