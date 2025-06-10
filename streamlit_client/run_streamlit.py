#!/usr/bin/env python3
"""
Script to run the Streamlit Finance Email Processor client
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    """Run the Streamlit application."""
    
    # Get the directory of this script
    current_dir = Path(__file__).parent
    
    # Path to the main Streamlit app
    app_path = current_dir / "streamlit_app.py"
    
    if not app_path.exists():
        print("❌ Error: streamlit_app.py not found!")
        print(f"Expected location: {app_path}")
        return 1
    
    print("🚀 Starting Streamlit Finance Email Processor...")
    print("📧 Client for testing and visualization")
    print()
    print("🌐 The app will be available at:")
    print("   - Local URL: http://localhost:8501")
    print("   - Network URL: http://your-ip:8501")
    print()
    print("🔧 Make sure your FastAPI backend is running on:")
    print("   - Backend URL: http://localhost:8000")
    print()
    print("=" * 60)
    
    try:
        # Run Streamlit
        cmd = [
            sys.executable, "-m", "streamlit", "run", 
            str(app_path),
            "--server.port=8501",
            "--server.address=0.0.0.0",
            "--browser.gatherUsageStats=false"
        ]
        
        subprocess.run(cmd, cwd=current_dir)
        
    except KeyboardInterrupt:
        print("\n👋 Streamlit app stopped by user")
        return 0
    except Exception as e:
        print(f"❌ Error running Streamlit: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 