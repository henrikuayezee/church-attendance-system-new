# 🚀 Deployment Guide - Church Attendance Management System

## Deployment Overview

This guide will walk you through deploying your Church Attendance Management System to Streamlit Cloud for production use.

## Prerequisites

✅ Google Cloud Project with Sheets API enabled  
✅ Google Service Account JSON credentials  
✅ Google Sheets spreadsheet created and shared with service account  
✅ GitHub repository (optional but recommended)  

## Deployment Options

### Option 1: Streamlit Cloud (Recommended) ⭐

**Advantages:**
- ✅ Free hosting for public apps
- ✅ Easy deployment from GitHub
- ✅ Automatic updates when code changes
- ✅ Built-in secrets management
- ✅ HTTPS by default

#### Step-by-Step Streamlit Cloud Deployment:

### 1. **Prepare Your Repository** 📂

If you haven't already, push your code to GitHub:

```bash
# Initialize git repository (if not done)
git init
git add .
git commit -m "Initial commit - Church Attendance System"

# Add GitHub remote and push
git branch -M main
git remote add origin https://github.com/yourusername/church-attendance-system.git
git push -u origin main
```

### 2. **Sign up for Streamlit Cloud** 🌐

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Sign in with your GitHub account
3. Authorize Streamlit Cloud to access your repositories

### 3. **Deploy Your App** 🚀

1. **Click "New app"**
2. **Select your repository:** `yourusername/church-attendance-system`
3. **Set main file:** `church_attendance_optimized.py`
4. **Choose branch:** `main`
5. **Click "Deploy!"**

### 4. **Configure Secrets** 🔐

In Streamlit Cloud dashboard:

1. **Go to your app settings**
2. **Click "Secrets"**
3. **Add your secrets in TOML format:**

```toml
[google_sheets]
type = "service_account"
project_id = "your-project-id"
private_key_id = "your-private-key-id"
private_key = "-----BEGIN PRIVATE KEY-----\nYOUR-PRIVATE-KEY-HERE\n-----END PRIVATE KEY-----\n"
client_email = "your-service-account@project.iam.gserviceaccount.com"
client_id = "your-client-id"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/your-service-account%40project.iam.gserviceaccount.com"

spreadsheet_name = "Church Attendance System"
```

**⚠️ Important Notes:**
- Replace all `your-*` placeholders with actual values from your service account JSON
- The private_key must include `\n` characters for line breaks
- Double-check spelling of `spreadsheet_name` - it must match exactly

### 5. **Test Your Deployment** ✅

1. **Visit your app URL** (provided by Streamlit Cloud)
2. **Test login:** Username: `admin` / Password: `admin123`
3. **Verify all features work:**
   - Dashboard loads with data
   - Attendance marking functions
   - User management accessible
   - All pages navigate properly

---

## Option 2: Self-Hosting 🖥️

If you prefer to host on your own server:

### Using Docker (Advanced)

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "church_attendance_optimized.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

### Direct Server Deployment

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
streamlit run church_attendance_optimized.py --server.port 8501
```

---

## Post-Deployment Setup

### 1. **Initial System Configuration** ⚙️

After successful deployment:

1. **Login as admin:** `admin` / `admin123`
2. **Change default password immediately**
3. **Create additional users** in User Management
4. **Test all functionality** with different user roles
5. **Add your church members** to get started

### 2. **Security Checklist** 🛡️

- ✅ Default admin password changed
- ✅ Google Sheets properly secured (shared only with service account)
- ✅ Service account has minimal necessary permissions
- ✅ Only authorized users have system access
- ✅ All secrets properly configured in Streamlit Cloud

### 3. **User Training** 👥

**For Super Admins:**
- How to create and manage users
- How to assign appropriate roles
- How to monitor system usage

**For Regular Users:**
- How to log in and navigate
- How to mark attendance
- How to generate reports

---

## Troubleshooting

### Common Issues and Solutions

#### ❌ "Failed to connect to Google Sheets"
- **Check:** Service account email is added to your Google Sheet with Editor permissions
- **Check:** All credentials in secrets are correct and properly formatted
- **Check:** Google Sheets API is enabled in your Google Cloud project

#### ❌ "Module not found" errors
- **Check:** All dependencies listed in `requirements.txt`
- **Solution:** Add missing packages to requirements.txt and redeploy

#### ❌ "Login not working"
- **Check:** Google Sheets connection is working first
- **Check:** Users worksheet was created properly
- **Try:** Clear cache and refresh the page

#### ❌ "Permission denied" errors
- **Check:** User has proper role assigned
- **Check:** User account is active
- **Try:** Logout and login again

### Getting Help

1. **Check the Admin Panel** for system status and diagnostics
2. **Review connection status** in the sidebar
3. **Check Streamlit Cloud logs** for detailed error messages
4. **Verify Google Sheets data** manually to ensure it's being written correctly

---

## Maintenance

### Regular Tasks
- **Monitor user activity** in User Management
- **Review system performance** in Admin Panel
- **Backup data** using export functions
- **Update user permissions** as needed

### Updates
- **Code changes:** Push to GitHub → Streamlit Cloud auto-deploys
- **Dependency updates:** Update requirements.txt as needed
- **Security updates:** Review and rotate service account keys annually

---

## Success! 🎉

Your Church Attendance Management System is now deployed and ready for production use!

**Your system includes:**
- ✅ Secure user authentication
- ✅ Role-based access control  
- ✅ Comprehensive attendance tracking
- ✅ Advanced analytics and reporting
- ✅ Professional admin panel
- ✅ Export capabilities
- ✅ Mobile-responsive design

**Default Login:** `admin` / `admin123` (change immediately!)

**Next Steps:**
1. Change default password
2. Create user accounts for your church staff
3. Add your member list
4. Start tracking attendance!

---

*Need help? Check the troubleshooting section above or review the system documentation in CLAUDE.md*