# ⛪ Church Attendance Management System

A comprehensive, secure web application for managing church attendance records with advanced analytics, user management, and professional reporting capabilities. Built with Streamlit and Google Sheets integration.

## ✨ Features

### 🔐 **User Management & Security**
- **Role-Based Access Control**: Super Admin, Admin, Staff, and Viewer roles
- **Secure Authentication**: Password hashing with salt, session management
- **User Administration**: Create/manage users, track activity, control permissions

### 📝 **Attendance Management** 
- **Smart Attendance Marking**: Group filtering, member search, bulk selection
- **Real-time Validation**: Duplicate detection, data integrity checks
- **Flexible Interface**: Mobile-responsive design, intuitive workflow

### 👥 **Member Management**
- **Complete CRUD Operations**: Add, edit, view, import/export members
- **Advanced Search & Filtering**: Find members quickly across groups
- **Data Validation**: Prevent duplicates, ensure data quality

### 📊 **Advanced Analytics**
- **Comprehensive Dashboard**: 8 key metrics, trending data, visual insights  
- **4-Tab Analytics System**: Group analysis, member engagement, patterns, growth
- **Interactive Charts**: Plotly visualizations with drill-down capabilities

### 📋 **Professional Reporting**
- **6 Report Types**: Monthly summaries, group performance, member engagement, trends, executive summaries
- **Export Capabilities**: CSV, JSON, comprehensive backups
- **Customizable Date Ranges**: Flexible reporting periods

### 📜 **History & Data Management**
- **Advanced Search**: Multi-criteria filtering, pagination, detailed record views
- **Data Quality Tools**: Integrity checks, duplicate detection, cleanup utilities
- **Comprehensive Admin Panel**: System monitoring, cache management, diagnostics

### ☁️ **Enterprise Features**
- **Google Sheets Integration**: Reliable cloud storage with real-time sync
- **Caching System**: Optimized performance with intelligent caching
- **Rate Limiting**: API quota management and automatic retry logic
- **Professional UI**: Modern interface with consistent design patterns

## Quick Start

### Prerequisites

- Python 3.9 or higher
- Google Cloud Project with Sheets API enabled
- Google Sheets spreadsheet for data storage

### Installation

1. **Clone/Download the project**
   ```bash
   git clone <repository-url>
   cd church-attendance-system
   ```

2. **Create virtual environment**
   ```bash
   python -m venv church_attendance_env
   
   # Windows
   church_attendance_env\Scripts\activate
   
   # macOS/Linux
   source church_attendance_env/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Google Sheets connection**
   - Copy `.streamlit/secrets.toml` template
   - Add your Google Service Account credentials
   - Set your spreadsheet name

5. **Run the application**
   ```bash
   streamlit run church_attendance_optimized.py
   ```

6. **Access the application**
   - Open your browser to `http://localhost:8501`

## Google Cloud Setup

### 1. Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project: "Church Attendance System"
3. Enable billing (required for API access)

### 2. Enable Required APIs

1. Navigate to "APIs & Services" > "Library"
2. Enable the following APIs:
   - Google Sheets API
   - Google Drive API

### 3. Create Service Account

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "Service Account"
3. Name: `church-attendance-service`
4. Role: `Editor`
5. Create and download the JSON key file

### 4. Setup Google Sheets

1. Create a new Google Sheets spreadsheet
2. Name it: "Church Attendance System"
3. Share the spreadsheet with your service account email (found in the JSON file)
4. Give "Editor" permissions

### 5. Configure Secrets

Edit `.streamlit/secrets.toml` with your service account credentials:

```toml
[google_sheets]
type = "service_account"
project_id = "your-project-id"
private_key_id = "your-private-key-id"
private_key = "-----BEGIN PRIVATE KEY-----\nYOUR_PRIVATE_KEY\n-----END PRIVATE KEY-----\n"
client_email = "your-service-account@project.iam.gserviceaccount.com"
client_id = "your-client-id"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "your-cert-url"

spreadsheet_name = "Church Attendance System"
```

## Usage Guide

### Adding Members

1. Navigate to "Manage Members" tab
2. Click "Add Member" 
3. Fill in member information:
   - **Full Name** (required)
   - **Group** (required - e.g., Youth, Adults, Children)
   - Membership Number (optional)
   - Email (optional)
   - Phone (optional)
4. Click "Add Member" to save

### Marking Attendance

1. Navigate to "Mark Attendance" tab
2. Select the date (defaults to today)
3. Choose a group or "All Groups"
4. Check boxes for members who are present
5. Click "Mark Attendance" to save

### Viewing Analytics

1. Navigate to "Analytics" tab
2. View attendance trends and insights
3. Filter by date ranges and groups
4. Export charts and data as needed

### Generating Reports

1. Navigate to "Reports" tab
2. Select report type and date range
3. Generate and download reports
4. Share with ministry leaders

## Data Schema

### Members Table
- **Membership Number**: Optional unique identifier
- **Full Name**: Required full name of member
- **Group**: Required group assignment (Youth, Adults, etc.)
- **Email**: Optional email address
- **Phone**: Optional phone number

### Attendance Table
- **Date**: Attendance date (YYYY-MM-DD)
- **Membership Number**: Links to member record
- **Full Name**: Member's full name
- **Group**: Member's group assignment
- **Status**: Always "Present" for recorded attendance
- **Timestamp**: Auto-generated timestamp

## Troubleshooting

### Common Issues

**Connection Failed**
- Verify Google Cloud project setup
- Check service account permissions
- Ensure spreadsheet is shared with service account
- Verify API credentials in secrets.toml

**Slow Performance**
- Clear cache using sidebar controls
- Check internet connection
- Monitor Google Sheets API quota

**Data Not Saving**
- Check connection status in sidebar
- Verify write permissions on spreadsheet
- Try refreshing the connection

**Import Errors**
- Ensure CSV format matches expected schema
- Check for special characters in data
- Validate required fields are present

### Getting Help

1. Check the connection status in the sidebar
2. Use cache controls to refresh data
3. Review Google Cloud Console for API errors
4. Verify spreadsheet permissions

## 🚀 Deployment

### Production Deployment (Streamlit Cloud) - Recommended ⭐

**Quick Deployment:**
1. **Push to GitHub** - Upload your code to a GitHub repository
2. **Deploy to Streamlit Cloud** - Go to [share.streamlit.io](https://share.streamlit.io)
3. **Configure Secrets** - Add your Google Service Account credentials
4. **Go Live!** - Your app will be available at `https://yourapp.streamlit.app`

**📋 Detailed Instructions:** See `DEPLOYMENT.md` for complete step-by-step guide

**✅ Use Deployment Checklist:** Follow `DEPLOYMENT_CHECKLIST.md` for zero-error deployment

### Default Login Credentials
- **Username:** `admin`
- **Password:** `admin123`
- **⚠️ IMPORTANT:** Change default password immediately after first login!

### User Roles
- **Super Admin** - Full access + user management
- **Admin** - Full church data access (no user management)  
- **Staff** - Attendance + member management + viewing
- **Viewer** - Read-only dashboard and reports access

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
streamlit run church_attendance_optimized.py

# Access at: http://localhost:8501
```

### Production Features
- ✅ **Secure Authentication** - Role-based access control
- ✅ **Auto-SSL** - HTTPS encryption by default  
- ✅ **Automatic Backups** - Data stored in Google Sheets
- ✅ **Mobile Responsive** - Works on all devices
- ✅ **Zero Downtime** - Cloud hosting with high availability

## Architecture

- **Frontend**: Streamlit web framework
- **Backend**: Python with pandas for data processing
- **Database**: Google Sheets via gspread API
- **Authentication**: Google Service Account
- **Visualization**: Plotly charts and graphs
- **Caching**: Built-in memory caching with TTL
- **Rate Limiting**: Automatic API rate limiting

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes following existing patterns
4. Test thoroughly
5. Submit a pull request

## License

This project is open source and available under the MIT License.

## Support

For support and questions:
1. Check the troubleshooting section
2. Review Google Cloud documentation
3. Submit issues through the repository issue tracker

## Security

- Service account credentials are stored securely
- No sensitive data in source code
- HTTPS encryption for all web traffic
- Regular credential rotation recommended