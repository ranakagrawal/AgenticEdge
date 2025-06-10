#!/usr/bin/env python3
"""
Finance Email Summarizer - Server Startup Script
"""

import os
import sys
import logging
from pathlib import Path

# Add the current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    """Main function to start the server."""
    
    # Create necessary directories
    logs_dir = current_dir / "logs"
    logs_dir.mkdir(exist_ok=True)
    
    print("🚀 Starting Finance Email Summarizer API Server...")
    print("📧 Email Processing Pipeline: Gmail → CrewAI Agents → Entity Extraction")
    print("🔧 Tech Stack: FastAPI + CrewAI + LangChain + OpenAI")
    print()
    
    # Check environment variables
    required_env_vars = [
        "OPENAI_API_KEY",
        "GOOGLE_CLIENT_ID", 
        "GOOGLE_CLIENT_SECRET"
    ]
    
    missing_vars = []
    for var in required_env_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print()
        print("📋 Please create a .env file or set these environment variables:")
        print("   OPENAI_API_KEY=your_openai_api_key")
        print("   GOOGLE_CLIENT_ID=your_google_client_id")
        print("   GOOGLE_CLIENT_SECRET=your_google_client_secret")
        print()
        print("💡 You can copy env.example to .env and fill in your values")
        return 1
    
    print("✅ Environment variables configured")
    print()
    print("🌐 Server will be available at:")
    print("   - API Docs: http://localhost:8000/docs")
    print("   - API Root: http://localhost:8000")
    print("   - Health Check: http://localhost:8000/health")
    print()
    print("🔐 OAuth Flow:")
    print("   1. GET /auth/google - Get authorization URL")
    print("   2. User authorizes Gmail access")
    print("   3. GET /auth/google/callback - Complete authentication")
    print("   4. POST /process/emails/{user_id} - Process emails")
    print()
    print("📊 Check processing results in logs/ directory")
    print("=" * 60)
    
    # Import and run the FastAPI app
    try:
        import uvicorn
        
        print("🔄 Starting uvicorn server...")
        
        uvicorn.run(
            "backend.main:app",  # Use import string for reload mode
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Make sure you've installed dependencies: pip install -r requirements.txt")
        return 1
    except Exception as e:
        print(f"❌ Server error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 