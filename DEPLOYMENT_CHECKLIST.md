# ✅ Deployment Checklist

## Pre-Deployment Setup

### Google Cloud Setup
- [ ] Google Cloud Project created
- [ ] Google Sheets API enabled
- [ ] Google Drive API enabled  
- [ ] Service Account created with JSON credentials downloaded
- [ ] Service Account email noted for spreadsheet sharing

### Google Sheets Setup
- [ ] "Church Attendance System" spreadsheet created
- [ ] Spreadsheet shared with service account email (Editor permissions)
- [ ] Spreadsheet name matches exactly: "Church Attendance System"

### Code Preparation
- [ ] All code tested locally and working
- [ ] requirements.txt file present and complete
- [ ] Application runs without errors locally

## Deployment Process

### GitHub Repository (if using Streamlit Cloud)
- [ ] GitHub repository created
- [ ] All files pushed to repository
- [ ] Repository is public or Streamlit Cloud has access

### Streamlit Cloud Setup
- [ ] Streamlit Cloud account created (share.streamlit.io)
- [ ] GitHub account connected to Streamlit Cloud
- [ ] New app deployed from repository
- [ ] Main file set to: `church_attendance_optimized.py`

### Secrets Configuration
- [ ] Service account JSON credentials added to Streamlit Cloud secrets
- [ ] Spreadsheet name configured in secrets
- [ ] All required fields in secrets.toml format added
- [ ] Secrets saved and app restarted

## Post-Deployment Testing

### Basic Functionality
- [ ] App loads without errors
- [ ] Login screen appears
- [ ] Can connect to Google Sheets (green status in sidebar)
- [ ] Default admin login works: `admin` / `admin123`

### User Management
- [ ] Default admin account created automatically
- [ ] Can access User Management page as super admin
- [ ] Can create new users
- [ ] Role-based navigation working (different users see different pages)

### Core Features
- [ ] Dashboard displays (with or without data)
- [ ] Can navigate to all accessible pages
- [ ] Attendance marking interface loads
- [ ] Member management interface loads
- [ ] Admin panel accessible
- [ ] Cache controls working

### Data Operations
- [ ] Can add test member
- [ ] Can mark test attendance
- [ ] Data appears in Google Sheets
- [ ] Analytics and reports generate (if data available)
- [ ] Export functions work

## Security Setup

### Immediate Security Tasks
- [ ] **CRITICAL:** Change default admin password from `admin123`
- [ ] Create additional admin users as needed
- [ ] Create staff/viewer users as appropriate
- [ ] Test that each user role has appropriate access

### Ongoing Security
- [ ] Service account permissions are minimal (only needs Sheets access)
- [ ] Spreadsheet is not publicly accessible
- [ ] Only authorized service account has access to spreadsheet
- [ ] User accounts created only for authorized personnel

## User Training & Handoff

### Documentation
- [ ] DEPLOYMENT.md guide provided
- [ ] CLAUDE.md system documentation available  
- [ ] Default login credentials provided securely
- [ ] User role explanations provided

### Training Completed
- [ ] Super admin trained on user management
- [ ] Staff trained on attendance marking
- [ ] Users understand their role permissions
- [ ] Backup/export procedures explained

## Go-Live Confirmation

### Final Verification
- [ ] All tests passed
- [ ] Real church data can be entered
- [ ] Multiple users can access simultaneously
- [ ] System performance is acceptable
- [ ] Mobile access works properly

### Monitoring Setup
- [ ] Admin panel monitoring explained
- [ ] Error reporting process established
- [ ] Backup procedures scheduled
- [ ] Update process documented

---

## 🚨 If Any Item Fails

**STOP** - Do not proceed to next section until issue is resolved

**Common Solutions:**
- Double-check all credentials and service account setup
- Verify spreadsheet name spelling and sharing permissions
- Check Streamlit Cloud logs for detailed error messages
- Test connection locally first before troubleshooting deployment

---

## ✅ Deployment Complete!

When all items are checked:

**🎉 Your Church Attendance Management System is LIVE!**

**Production URL:** `https://[your-app-name].streamlit.app`

**Default Access:** Username: `admin` / Password: `admin123` *(Change immediately!)*

**Support:** Reference DEPLOYMENT.md for troubleshooting and maintenance guidance.