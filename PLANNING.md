# PLANNING.md - Church Attendance Management System
## Project Planning and Architecture Document

---

## Vision Statement

### Primary Vision
Create a user-friendly, cloud-based attendance management solution that eliminates manual paper-based tracking for churches while providing actionable insights for ministry planning and member engagement.

### Long-term Vision
Develop a comprehensive church management ecosystem that integrates attendance tracking with member relationship management, event planning, and ministry analytics to support data-driven church growth and community building.

### Success Criteria
- Reduce attendance recording time by 75%
- Eliminate manual data entry errors
- Provide real-time access to attendance data for all authorized users
- Generate actionable insights for ministry leaders
- Support churches of varying sizes (50-1000+ members)

---

## Architecture Overview

### System Architecture Pattern
**Monolithic Web Application** with external data persistence

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Web Browser   │◄──►│  Streamlit App   │◄──►│  Google Sheets  │
│                 │    │                  │    │                 │
│ - User Interface│    │ - Business Logic │    │ - Data Storage  │
│ - Form Handling │    │ - Data Processing│    │ - Backup        │
│ - Visualizations│    │ - API Management │    │ - Collaboration │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌──────────────────┐
                       │   Local Cache    │
                       │                  │
                       │ - Session Data   │
                       │ - Performance    │
                       └──────────────────┘
```

### Component Architecture

#### Presentation Layer
- **Streamlit Framework**: Handles UI rendering, user interactions, and session management
- **Plotly Visualizations**: Charts, graphs, and interactive data displays
- **Custom CSS**: Styling and responsive design elements

#### Business Logic Layer
- **GoogleSheetsManager Class**: Core data operations and API management
- **Page Controllers**: Individual page logic and workflow management
- **Data Validators**: Input validation and business rule enforcement
- **Analytics Engine**: Data processing and insight generation

#### Data Access Layer
- **Google Sheets API**: Primary data persistence
- **Cache Manager**: In-memory data caching for performance
- **Rate Limiter**: API quota management and error handling

#### Integration Layer
- **Authentication Handler**: Google Service Account management
- **Export/Import Utilities**: CSV processing and data migration tools
- **Notification System**: User feedback and error messaging

---

## Technology Stack

### Core Technologies

#### Frontend
- **Streamlit 1.28+**
  - Reason: Rapid development, built-in components, easy deployment
  - Trade-offs: Limited customization vs development speed
  - Alternatives considered: Flask/Django (more complex), Dash (similar but less mature)

#### Backend/Data Processing
- **Python 3.9+**
  - Reason: Excellent data science ecosystem, Streamlit compatibility
  - Key libraries: pandas, numpy for data manipulation
  
- **pandas 2.0+**
  - Reason: Powerful data manipulation, CSV processing, analysis capabilities
  - Trade-offs: Memory usage vs functionality

#### Data Storage
- **Google Sheets via gspread**
  - Reason: Zero-setup database, familiar interface, collaboration features
  - Trade-offs: API limits vs setup complexity
  - Alternatives: PostgreSQL (more complex), SQLite (no collaboration)

#### Authentication
- **Google Service Account**
  - Reason: Secure, server-to-server authentication without user intervention
  - Trade-offs: Setup complexity vs security

#### Visualization
- **Plotly Express/Graph Objects**
  - Reason: Interactive charts, Streamlit integration, professional appearance
  - Alternatives: Matplotlib (static), Altair (simpler but less flexible)

### Supporting Libraries

#### Data Management
```python
gspread==5.11.3           # Google Sheets API client
google-auth==2.23.4       # Authentication library
pandas==2.1.3             # Data manipulation
numpy==1.25.2             # Numerical operations
```

#### Web Framework
```python
streamlit==1.28.1         # Web application framework
plotly==5.17.0            # Interactive visualizations
```

#### Utilities
```python
python-dateutil==2.8.2   # Date handling
pytz==2023.3              # Timezone management
```

### Infrastructure

#### Hosting Platform
- **Streamlit Cloud**
  - Reason: Native Streamlit support, GitHub integration, free tier
  - Alternatives: Heroku, AWS EC2, Google Cloud Run

#### Domain and SSL
- **Streamlit Cloud subdomain** (free tier)
- **Custom domain** (premium option)

#### Monitoring and Analytics
- **Streamlit Cloud built-in metrics**
- **Google Sheets audit trail**
- **Custom application logging**

---

## Required Tools and Setup

### Development Environment

#### Essential Software
1. **Python 3.9 or higher**
   - Installation: python.org or pyenv for version management
   - Virtual environment: venv or conda

2. **Code Editor/IDE**
   - Recommended: VS Code with Python extension
   - Alternatives: PyCharm, Sublime Text, Vim

3. **Git Version Control**
   - For code management and deployment
   - GitHub account for repository hosting

4. **Web Browser**
   - Chrome/Firefox for development and testing
   - Developer tools for debugging

#### Python Package Installation
```bash
# Create virtual environment
python -m venv church_attendance_env
source church_attendance_env/bin/activate  # Linux/Mac
# or
church_attendance_env\Scripts\activate  # Windows

# Install required packages
pip install streamlit pandas gspread plotly google-auth python-dateutil pytz
```

### Google Cloud Setup

#### Google Cloud Console
1. **Create Project**
   - Project name: "Church Attendance System"
   - Enable billing (required for API access)

2. **Enable APIs**
   - Google Sheets API
   - Google Drive API

3. **Create Service Account**
   - Name: church-attendance-service
   - Role: Editor (for sheet creation)
   - Download JSON credentials file

#### Google Sheets Preparation
1. **Create Spreadsheet**
   - Name: "Church Attendance System"
   - Share with service account email (Editor permissions)

2. **Initial Setup**
   - Application will auto-create worksheets
   - Manual setup not required

### Configuration Files

#### Streamlit Secrets
Create `.streamlit/secrets.toml`:
```toml
[google_sheets]
type = "service_account"
project_id = "your-project-id"
private_key_id = "key-id"
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "service-account@project.iam.gserviceaccount.com"
client_id = "client-id"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "cert-url"

spreadsheet_name = "Church Attendance System"
```

#### Requirements File
Create `requirements.txt`:
```
streamlit==1.28.1
pandas==2.1.3
gspread==5.11.3
google-auth==2.23.4
plotly==5.17.0
python-dateutil==2.8.2
pytz==2023.3
```

### Development Tools

#### Version Control
```bash
# Initialize repository
git init
git add .
git commit -m "Initial commit"

# Connect to GitHub
git remote add origin https://github.com/username/church-attendance-system.git
git push -u origin main
```

#### Local Testing
```bash
# Run application locally
streamlit run church_attendance_optimized.py

# Access at http://localhost:8501
```

### Deployment Tools

#### Streamlit Cloud
1. **Account Setup**
   - Link GitHub account
   - Connect repository

2. **Deployment Configuration**
   - Python version: 3.9
   - Main file: church_attendance_optimized.py
   - Requirements: requirements.txt

3. **Secrets Management**
   - Add Google Sheets credentials in dashboard
   - Configure environment variables

#### Alternative Deployment Options

##### Docker (Advanced)
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8501

CMD ["streamlit", "run", "church_attendance_optimized.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

##### Heroku
- Procfile: `web: sh setup.sh && streamlit run church_attendance_optimized.py`
- Runtime: `python-3.9.18`

---

## Development Workflow

### Local Development Process
1. **Setup Environment**
   - Clone repository
   - Create virtual environment
   - Install dependencies
   - Configure secrets

2. **Development Cycle**
   - Create feature branch
   - Implement changes
   - Test locally
   - Commit changes
   - Push to GitHub

3. **Testing Process**
   - Manual testing checklist
   - Google Sheets integration testing
   - Performance testing with sample data
   - Error scenario testing

### Deployment Process
1. **Code Review**
   - Review changes
   - Test critical paths
   - Check dependencies

2. **Deployment**
   - Merge to main branch
   - Automatic deployment via Streamlit Cloud
   - Verify production functionality

3. **Monitoring**
   - Check application health
   - Monitor error logs
   - Validate data integrity

---

## Risk Assessment and Mitigation

### Technical Risks

#### High Priority
- **Google Sheets API Rate Limits**
  - Mitigation: Implemented rate limiting and caching
  - Backup: Consider database migration path

- **Service Account Security**
  - Mitigation: Secure credential storage, regular rotation
  - Monitoring: Access logging and alerts

#### Medium Priority
- **Data Loss**
  - Mitigation: Google Sheets built-in versioning
  - Backup: Regular CSV exports

- **Performance Degradation**
  - Mitigation: Caching strategy, batch operations
  - Monitoring: Response time tracking

#### Low Priority
- **UI/UX Issues**
  - Mitigation: User testing and feedback
  - Resolution: Iterative improvements

### Operational Risks

- **User Adoption**
  - Mitigation: Training materials, intuitive design
- **Data Migration**
  - Mitigation: CSV import/export functionality
- **Maintenance Burden**
  - Mitigation: Documentation, simple architecture

---

## Future Enhancements Roadmap

### Phase 1: Foundation (Current)
- Core attendance tracking
- Basic member management
- Google Sheets integration
- Simple analytics

### Phase 2: Enhanced Features
- Advanced search and filtering
- Bulk operations
- Improved error handling
- Performance optimization

### Phase 3: Advanced Analytics
- Predictive attendance models
- Member engagement scoring
- Automated reporting
- Dashboard customization

### Phase 4: Platform Integration
- Multi-church support
- User authentication
- Mobile application
- Third-party integrations

---

This planning document serves as the foundation for development, deployment, and maintenance of the Church Attendance Management System. Regular updates should reflect changing requirements and technological improvements.