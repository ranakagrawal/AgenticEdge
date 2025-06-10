# Finance Email Processor - Streamlit Client

A simple and intuitive Streamlit interface for testing and using the Finance Email Processor system.

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- FastAPI backend running on `http://localhost:8000`
- Required dependencies installed

### Installation
```bash
# Install dependencies
pip install -r ../requirements.txt

# Run the Streamlit app
python run_streamlit.py
```

The app will be available at: `http://localhost:8501`

## 📋 Features

### 🔐 Authentication
- Google OAuth integration
- Session management
- User profile display

### 📧 Email Processing
- Configure processing parameters
- Real-time progress monitoring
- Processing status tracking

### 📋 Results Viewing
- Display extracted financial entities
- Filter and sort results
- Export data (CSV/JSON)

### 🧪 API Testing
- Test individual endpoints
- Debug API responses
- System health monitoring

## 🗂️ File Structure

```
streamlit_client/
├── streamlit_app.py           # Main Streamlit app
├── run_streamlit.py           # App runner script
├── config.py                  # Configuration settings
├── pages/
│   ├── 1_🔐_Authentication.py   # OAuth and user management
│   ├── 2_📧_Process_Emails.py   # Email processing interface
│   ├── 3_📋_View_Results.py     # Results visualization
│   └── 4_🧪_API_Testing.py      # API testing tools
├── utils/
│   ├── api_client.py          # FastAPI communication
│   ├── auth_handler.py        # Authentication management
│   └── __init__.py            # Package initialization
└── README.md                  # This file
```

## ⚙️ Configuration

### Environment Variables
```bash
# Optional: Override default backend URL
export API_BASE_URL="http://localhost:8000"
```

### Settings
Configuration is handled in `config.py`:
- API endpoints
- Session state keys
- UI messages and settings

## 🔧 Usage

### 1. Authentication
1. Go to **🔐 Authentication** page
2. Click **"Authenticate with Google"**
3. Follow OAuth flow
4. Complete authentication

### 2. Process Emails
1. Navigate to **📧 Process Emails**
2. Configure processing parameters
3. Click **"Start Processing"**
4. Monitor progress in real-time

### 3. View Results
1. Go to **📋 View Results**
2. Filter and sort data as needed
3. Export results if required

### 4. Debug Issues
1. Use **🧪 API Testing** page
2. Test individual endpoints
3. Check system health

## 🐛 Troubleshooting

### Common Issues

**"Backend Offline"**
- Ensure FastAPI server is running on port 8000
- Check `http://localhost:8000/health`

**"Authentication Failed"**
- Verify Google OAuth credentials in backend
- Check authorization code is entered correctly

**"No Data Found"**
- Process emails first using the Process Emails page
- Check if your Gmail has financial emails

### Debug Steps
1. Check backend health in API Testing page
2. Verify authentication status
3. Test individual endpoints
4. Check browser console for errors

## 🔌 API Integration

The client communicates with these FastAPI endpoints:
- `GET /health` - System health check
- `GET /auth/google` - Get OAuth URL
- `GET /auth/google/callback` - Handle OAuth callback
- `POST /process/emails/{user_id}` - Start processing
- `GET /process/status/{run_id}` - Check status
- `GET /users/{user_id}/profile` - User profile
- `GET /users/{user_id}/entities` - Get entities

## 📝 Development

### Adding New Features
1. Create new page in `pages/` directory
2. Add utility functions in `utils/`
3. Update configuration in `config.py`
4. Test with API Testing page

### Code Structure
- **Pages**: Individual Streamlit pages for different features
- **Utils**: Reusable components (API client, auth handler)
- **Config**: Centralized configuration management

## 🤝 Support

For issues or questions:
1. Check the **🧪 API Testing** page for system diagnostics
2. Review the troubleshooting section above
3. Check backend logs for detailed error information 