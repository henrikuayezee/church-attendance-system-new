"""
Church Attendance Management System
A Streamlit-based web application for managing church attendance records using Google Sheets.
"""

import streamlit as st
import pandas as pd
import gspread
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
import time
from functools import wraps
from typing import Dict, List, Optional, Tuple
import json
import hashlib
import secrets
import io
import base64
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os

# Configure Streamlit page
st.set_page_config(
    page_title="Church Attendance System",
    page_icon="⛪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Rate limiting decorator
def rate_limit(delay_seconds: float = 1.0):
    """Decorator to add delay between API calls for rate limiting"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if hasattr(wrapper, '_last_call'):
                time_since_last = time.time() - wrapper._last_call
                if time_since_last < delay_seconds:
                    time.sleep(delay_seconds - time_since_last)
            
            result = func(*args, **kwargs)
            wrapper._last_call = time.time()
            return result
        return wrapper
    return decorator


class UserManager:
    """Manages user authentication, roles, and permissions"""
    
    # Define user roles and their permissions
    ROLES = {
        'super_admin': {
            'name': 'Super Admin',
            'permissions': ['all'],  # Full access
            'description': 'Complete system access including user management'
        },
        'admin': {
            'name': 'Admin', 
            'permissions': ['view_dashboard', 'mark_attendance', 'manage_members', 'view_analytics', 
                          'generate_reports', 'view_history', 'admin_panel'],
            'description': 'Full church data access, cannot manage users'
        },
        'staff': {
            'name': 'Staff',
            'permissions': ['view_dashboard', 'mark_attendance', 'manage_members', 'view_analytics', 'view_history'],
            'description': 'Can mark attendance, manage members, view reports'
        },
        'viewer': {
            'name': 'Viewer',
            'permissions': ['view_dashboard', 'view_analytics', 'view_history'],
            'description': 'Read-only access to dashboards and reports'
        }
    }
    
    def __init__(self, sheets_manager):
        self.sheets_manager = sheets_manager
    
    def _clear_cache(self, cache_key: str):
        """Clear cache for a specific key"""
        if hasattr(self.sheets_manager, '_clear_cache'):
            self.sheets_manager._clear_cache(cache_key)
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache is valid"""
        if hasattr(self.sheets_manager, '_is_cache_valid'):
            return self.sheets_manager._is_cache_valid(cache_key)
        return False
    
    def _get_cache(self, cache_key: str):
        """Get cached data"""
        if hasattr(self.sheets_manager, '_get_cache'):
            return self.sheets_manager._get_cache(cache_key)
        return None
    
    def _set_cache(self, cache_key: str, data):
        """Set cache data"""
        if hasattr(self.sheets_manager, '_set_cache'):
            self.sheets_manager._set_cache(cache_key, data)
    
    @staticmethod
    def hash_password(password: str, salt: str = None) -> Tuple[str, str]:
        """Hash a password with a salt"""
        if salt is None:
            salt = secrets.token_hex(32)
        
        # Create hash using password + salt
        password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
        return password_hash, salt
    
    @staticmethod
    def verify_password(password: str, hashed_password: str, salt: str) -> bool:
        """Verify a password against its hash"""
        test_hash, _ = UserManager.hash_password(password, salt)
        return test_hash == hashed_password
    
    def create_default_admin(self):
        """Create default admin user if no users exist"""
        try:
            users_df = self.load_users()
            
            # Check if users table is truly empty AND no admin user exists
            if users_df.empty or (not users_df.empty and 'admin' not in users_df['username'].values):
                # Only create if no admin user exists at all
                if users_df.empty or users_df[users_df['username'] == 'admin'].empty:
                    # Create default admin user
                    password_hash, salt = self.hash_password("admin123")  # Default password
                    
                    default_admin = {
                        'username': 'admin',
                        'password_hash': password_hash,
                        'salt': salt,
                        'role': 'super_admin',
                        'full_name': 'System Administrator',
                        'email': 'admin@church.local',
                        'created_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'last_login': '',
                        'is_active': True,
                        'must_change_password': True
                    }
                    
                    self.save_user(default_admin)
                    return True
        except Exception as e:
            # Silently handle errors to prevent login disruption
            pass
        
        return False
    
    @rate_limit(1.0)
    def load_users(self) -> pd.DataFrame:
        """Load users from Google Sheets"""
        cache_key = "load_users"
        
        if self._is_cache_valid(cache_key):
            return self._get_cache(cache_key)
        
        try:
            # Get or create users worksheet
            try:
                worksheet = self.sheets_manager.spreadsheet.worksheet("Users")
            except:
                worksheet = self.sheets_manager.spreadsheet.add_worksheet(title="Users", rows=1000, cols=10)
                # Add headers
                headers = ['username', 'password_hash', 'salt', 'role', 'full_name', 
                          'email', 'created_date', 'last_login', 'is_active', 'must_change_password']
                worksheet.append_row(headers)
            
            # Get all records
            records = worksheet.get_all_records()
            
            if not records:
                users_df = pd.DataFrame(columns=['username', 'password_hash', 'salt', 'role', 'full_name', 
                                               'email', 'created_date', 'last_login', 'is_active', 'must_change_password'])
            else:
                users_df = pd.DataFrame(records)
                # Convert boolean columns properly
                if 'is_active' in users_df.columns:
                    users_df['is_active'] = users_df['is_active'].apply(lambda x: str(x).lower() in ['true', '1', 'yes'] if x != '' else True)
                if 'must_change_password' in users_df.columns:
                    users_df['must_change_password'] = users_df['must_change_password'].apply(lambda x: str(x).lower() in ['true', '1', 'yes'] if x != '' else False)
            
            self._set_cache(cache_key, users_df)
            return users_df
            
        except Exception as e:
            st.error(f"Error loading users: {str(e)}")
            return pd.DataFrame()
    
    @rate_limit(2.0)
    def save_user(self, user_data: dict) -> bool:
        """Save a single user to Google Sheets"""
        try:
            worksheet = self.sheets_manager.spreadsheet.worksheet("Users")
            
            # Convert user data to list for appending
            user_row = [
                user_data.get('username', ''),
                user_data.get('password_hash', ''),
                user_data.get('salt', ''),
                user_data.get('role', ''),
                user_data.get('full_name', ''),
                user_data.get('email', ''),
                user_data.get('created_date', ''),
                user_data.get('last_login', ''),
                user_data.get('is_active', True),
                user_data.get('must_change_password', False)
            ]
            
            worksheet.append_row(user_row)
            
            # Clear cache to force reload
            self._clear_cache("load_users")
            
            return True
            
        except Exception as e:
            st.error(f"Error saving user: {str(e)}")
            return False
    
    @rate_limit(2.0)
    def update_user_role(self, username: str, new_role: str) -> bool:
        """Update a user's role"""
        try:
            worksheet = self.sheets_manager.spreadsheet.worksheet("Users")
            users_data = worksheet.get_all_records()
            
            for i, user_record in enumerate(users_data, start=2):
                if user_record['username'] == username:
                    # Update role column (column 4)
                    worksheet.update_cell(i, 4, new_role)
                    
                    # Clear cache to force reload
                    self._clear_cache("load_users")
                    return True
            
            return False
            
        except Exception as e:
            st.error(f"Error updating user role: {str(e)}")
            return False
    
    @rate_limit(2.0)
    def toggle_user_active(self, username: str) -> bool:
        """Toggle user active status"""
        try:
            worksheet = self.sheets_manager.spreadsheet.worksheet("Users")
            users_data = worksheet.get_all_records()
            
            for i, user_record in enumerate(users_data, start=2):
                if user_record['username'] == username:
                    current_status = str(user_record.get('is_active', 'True')).lower() in ['true', '1', 'yes']
                    new_status = not current_status
                    
                    # Update is_active column (column 9)
                    worksheet.update_cell(i, 9, new_status)
                    
                    # Clear cache to force reload
                    self._clear_cache("load_users")
                    return True
            
            return False
            
        except Exception as e:
            st.error(f"Error toggling user status: {str(e)}")
            return False
    
    @rate_limit(2.0)
    def delete_user(self, username: str) -> bool:
        """Delete a user (cannot delete super_admin users if they're the last one)"""
        try:
            # Load current users
            users_df = self.load_users(use_cache=False)
            
            # Find user to delete
            user_to_delete = users_df[users_df['username'] == username]
            if user_to_delete.empty:
                st.error("User not found")
                return False
            
            # Check if this is the last super_admin
            if user_to_delete.iloc[0]['role'] == 'super_admin':
                super_admins = users_df[users_df['role'] == 'super_admin']
                if len(super_admins) <= 1:
                    st.error("Cannot delete the last Super Admin user")
                    return False
            
            # Delete from spreadsheet
            worksheet = self.sheets_manager.spreadsheet.worksheet("Users")
            users_data = worksheet.get_all_records()
            
            for i, user_record in enumerate(users_data, start=2):
                if user_record['username'] == username:
                    worksheet.delete_rows(i)
                    
                    # Clear cache to force reload
                    self._clear_cache("load_users")
                    return True
            
            return False
            
        except Exception as e:
            st.error(f"Error deleting user: {str(e)}")
            return False
    
    def authenticate_user(self, username: str, password: str) -> Optional[dict]:
        """Authenticate a user and return their data if successful"""
        users_df = self.load_users()
        
        if users_df.empty:
            return None
        
        # Find user
        user_row = users_df[users_df['username'] == username]
        
        if user_row.empty:
            return None
        
        user_data = user_row.iloc[0].to_dict()
        
        # Check if user is active
        if not user_data.get('is_active', False):
            return None
        
        # Verify password
        if self.verify_password(password, user_data['password_hash'], user_data['salt']):
            # Update last login time
            self.update_last_login(username)
            
            return {
                'username': user_data['username'],
                'role': user_data['role'],
                'full_name': user_data['full_name'],
                'email': user_data['email'],
                'must_change_password': user_data.get('must_change_password', False)
            }
        
        return None
    
    def update_last_login(self, username: str):
        """Update user's last login timestamp"""
        try:
            worksheet = self.sheets_manager.spreadsheet.worksheet("Users")
            users_data = worksheet.get_all_records()
            
            for i, user in enumerate(users_data, start=2):  # Start at row 2 (after headers)
                if user['username'] == username:
                    # Update last login timestamp
                    worksheet.update_cell(i, 8, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                    break
                    
            # Clear cache
            self._clear_cache("load_users")
            
        except Exception as e:
            pass  # Silently fail for login timestamp updates
    
    def has_permission(self, user_role: str, permission: str) -> bool:
        """Check if a user role has a specific permission"""
        if user_role not in self.ROLES:
            return False
        
        role_permissions = self.ROLES[user_role]['permissions']
        
        # Super admin has all permissions
        if 'all' in role_permissions:
            return True
        
        return permission in role_permissions
    
    def get_user_role_info(self, role: str) -> dict:
        """Get role information"""
        return self.ROLES.get(role, {})
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache entry is still valid"""
        if cache_key not in self.sheets_manager.cache:
            return False
        
        cached_time, _ = self.sheets_manager.cache[cache_key]
        return time.time() - cached_time < self.sheets_manager.cache_timeout
    
    def _get_cache(self, cache_key: str):
        """Get data from cache"""
        if cache_key in self.sheets_manager.cache:
            _, data = self.sheets_manager.cache[cache_key]
            return data
        return None
    
    def _set_cache(self, cache_key: str, data):
        """Set data in cache"""
        self.sheets_manager.cache[cache_key] = (time.time(), data)
    
    def _clear_cache(self, cache_key: str):
        """Clear specific cache entry"""
        if cache_key in self.sheets_manager.cache:
            del self.sheets_manager.cache[cache_key]


class GoogleSheetsManager:
    """Central manager for all Google Sheets operations with caching and rate limiting"""
    
    def __init__(self):
        self.client = None
        self.spreadsheet = None
        self.cache = {}
        self.cache_timeout = 300  # 5 minutes
        self.connection_status = False
        self.connection_timestamp = None
        self.connection_timeout = 3600  # 1 hour before re-authentication
        
    def is_connection_valid(self):
        """Check if current connection is still valid"""
        if not self.connection_status or self.client is None or self.spreadsheet is None:
            return False
            
        # Check if connection has timed out
        if self.connection_timestamp:
            time_since_connection = time.time() - self.connection_timestamp
            if time_since_connection > self.connection_timeout:
                return False
        
        # Test connection with a simple API call
        try:
            # Try to access spreadsheet properties (lightweight call)
            _ = self.spreadsheet.title
            return True
        except Exception:
            return False
    
    def ensure_connection(self):
        """Ensure connection is active, reconnect if necessary"""
        if self.is_connection_valid():
            return True
        return self.initialize_connection()
        
    def initialize_connection(self):
        """Initialize Google Sheets connection using service account credentials"""
        try:
            # Get credentials from Streamlit secrets
            credentials_dict = dict(st.secrets["google_sheets"])
            
            # Initialize gspread client
            self.client = gspread.service_account_from_dict(credentials_dict)
            
            # Open spreadsheet
            spreadsheet_name = st.secrets["google_sheets"]["spreadsheet_name"]
            self.spreadsheet = self.client.open(spreadsheet_name)
            
            self.connection_status = True
            self.connection_timestamp = time.time()
            return True
            
        except Exception as e:
            st.error(f"Failed to connect to Google Sheets: {str(e)}")
            self.connection_status = False
            self.connection_timestamp = None
            return False
    
    def _get_cache_key(self, method_name: str, *args) -> str:
        """Generate cache key for method and parameters"""
        return f"{method_name}_{hash(str(args))}"
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid"""
        if cache_key not in self.cache:
            return False
        
        cached_time, _ = self.cache[cache_key]
        return time.time() - cached_time < self.cache_timeout
    
    def _get_cache(self, cache_key: str):
        """Retrieve data from cache"""
        _, data = self.cache[cache_key]
        return data
    
    def _set_cache(self, cache_key: str, data):
        """Store data in cache"""
        self.cache[cache_key] = (time.time(), data)
    
    def clear_cache(self):
        """Clear all cached data"""
        self.cache = {}
    
    def setup_worksheets(self):
        """Create required worksheets if they don't exist"""
        # Ensure connection is active
        if not self.ensure_connection():
            st.error("Unable to connect to Google Sheets for worksheet setup")
            return False
            
        try:
            required_sheets = {
                'Members': ['Membership Number', 'Full Name', 'Group', 'Email', 'Phone'],
                'Attendance': ['Date', 'Membership Number', 'Full Name', 'Group', 'Status', 'Timestamp']
            }
            
            for sheet_name, headers in required_sheets.items():
                try:
                    worksheet = self.spreadsheet.worksheet(sheet_name)
                except gspread.WorksheetNotFound:
                    worksheet = self.spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=10)
                    worksheet.append_row(headers)
                    
            return True
        except Exception as e:
            st.error(f"Failed to setup worksheets: {str(e)}")
            # Connection might have failed, reset status
            self.connection_status = False
            return False
    
    @rate_limit(1.0)
    def load_members(self, use_cache: bool = True) -> pd.DataFrame:
        """Load members data from Google Sheets with caching"""
        cache_key = self._get_cache_key("load_members")
        
        if use_cache and self._is_cache_valid(cache_key):
            return self._get_cache(cache_key)
        
        # Ensure connection is active
        if not self.ensure_connection():
            st.error("Unable to connect to Google Sheets")
            return pd.DataFrame()
        
        try:
            worksheet = self.spreadsheet.worksheet('Members')
            data = worksheet.get_all_records()
            df = pd.DataFrame(data)
            
            # Clean data
            if not df.empty:
                df = df.fillna('')
                # Ensure required columns exist
                required_cols = ['Membership Number', 'Full Name', 'Group', 'Email', 'Phone']
                for col in required_cols:
                    if col not in df.columns:
                        df[col] = ''
            
            self._set_cache(cache_key, df)
            return df
            
        except Exception as e:
            st.error(f"Failed to load members: {str(e)}")
            # Connection might have failed, reset status
            self.connection_status = False
            return pd.DataFrame()
    
    @rate_limit(2.0)
    def save_members(self, df: pd.DataFrame) -> bool:
        """Save members data to Google Sheets"""
        # Ensure connection is active
        if not self.ensure_connection():
            st.error("Unable to connect to Google Sheets")
            return False
            
        try:
            worksheet = self.spreadsheet.worksheet('Members')
            
            # Clear existing data (except headers)
            worksheet.clear()
            
            # Set headers
            headers = ['Membership Number', 'Full Name', 'Group', 'Email', 'Phone']
            worksheet.append_row(headers)
            
            # Add data
            if not df.empty:
                # Ensure all required columns exist
                for col in headers:
                    if col not in df.columns:
                        df[col] = ''
                
                # Convert to list of lists
                data = df[headers].fillna('').values.tolist()
                
                # Batch update
                if data:
                    worksheet.append_rows(data)
            
            # Clear cache
            self.clear_cache()
            return True
            
        except Exception as e:
            st.error(f"Failed to save members: {str(e)}")
            # Connection might have failed, reset status
            self.connection_status = False
            return False
    
    @rate_limit(1.0)
    def load_attendance(self, use_cache: bool = True) -> pd.DataFrame:
        """Load attendance data from Google Sheets with caching"""
        cache_key = self._get_cache_key("load_attendance")
        
        if use_cache and self._is_cache_valid(cache_key):
            return self._get_cache(cache_key)
        
        # Ensure connection is active
        if not self.ensure_connection():
            st.error("Unable to connect to Google Sheets")
            return pd.DataFrame()
        
        try:
            worksheet = self.spreadsheet.worksheet('Attendance')
            data = worksheet.get_all_records()
            df = pd.DataFrame(data)
            
            if not df.empty:
                df = df.fillna('')
                # Convert date column to datetime
                if 'Date' in df.columns:
                    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            
            self._set_cache(cache_key, df)
            return df
            
        except Exception as e:
            st.error(f"Failed to load attendance: {str(e)}")
            # Connection might have failed, reset status
            self.connection_status = False
            return pd.DataFrame()
    
    @rate_limit(2.0)
    def save_attendance(self, attendance_records: List[Dict]) -> bool:
        """Save attendance records to Google Sheets"""
        # Ensure connection is active
        if not self.ensure_connection():
            st.error("Unable to connect to Google Sheets")
            return False
            
        try:
            worksheet = self.spreadsheet.worksheet('Attendance')
            
            # Prepare data for insertion
            rows_to_add = []
            for record in attendance_records:
                row = [
                    record.get('Date', ''),
                    record.get('Membership Number', ''),
                    record.get('Full Name', ''),
                    record.get('Group', ''),
                    record.get('Status', 'Present'),
                    record.get('Timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                ]
                rows_to_add.append(row)
            
            # Batch insert
            if rows_to_add:
                worksheet.append_rows(rows_to_add)
            
            # Clear cache
            self.clear_cache()
            return True
            
        except Exception as e:
            st.error(f"Failed to save attendance: {str(e)}")
            # Connection might have failed, reset status
            self.connection_status = False
            return False
    
    @rate_limit(2.0)
    def update_attendance_record(self, original_record: dict, updated_record: dict) -> bool:
        """Update a specific attendance record"""
        # Ensure connection is active
        if not self.ensure_connection():
            st.error("Unable to connect to Google Sheets")
            return False
            
        try:
            worksheet = self.spreadsheet.worksheet('Attendance')
            all_records = worksheet.get_all_records()
            
            # Find the matching record to update
            for i, record in enumerate(all_records, start=2):  # Start at 2 to account for headers
                # Match by date, name, and timestamp for uniqueness
                if (str(record.get('Date', '')) == str(original_record.get('Date', '')) and
                    str(record.get('Full Name', '')) == str(original_record.get('Full Name', '')) and
                    str(record.get('Timestamp', '')) == str(original_record.get('Timestamp', ''))):
                    
                    # Update the record
                    worksheet.update_cell(i, 1, updated_record.get('Date', ''))  # Date
                    worksheet.update_cell(i, 2, updated_record.get('Membership Number', ''))  # Membership Number
                    worksheet.update_cell(i, 3, updated_record.get('Full Name', ''))  # Full Name
                    worksheet.update_cell(i, 4, updated_record.get('Group', ''))  # Group
                    worksheet.update_cell(i, 5, updated_record.get('Status', 'Present'))  # Status
                    worksheet.update_cell(i, 6, updated_record.get('Timestamp', ''))  # Timestamp
                    
                    # Clear cache
                    self.clear_cache()
                    return True
            
            return False
            
        except Exception as e:
            st.error(f"Failed to update attendance record: {str(e)}")
            # Connection might have failed, reset status
            self.connection_status = False
            return False
    
    @rate_limit(2.0)
    def delete_attendance_record(self, record_to_delete: dict) -> bool:
        """Delete a specific attendance record"""
        # Ensure connection is active
        if not self.ensure_connection():
            st.error("Unable to connect to Google Sheets")
            return False
            
        try:
            worksheet = self.spreadsheet.worksheet('Attendance')
            all_records = worksheet.get_all_records()
            
            # Find the matching record to delete
            for i, record in enumerate(all_records, start=2):  # Start at 2 to account for headers
                # Match by date, name, and timestamp for uniqueness
                if (str(record.get('Date', '')) == str(record_to_delete.get('Date', '')) and
                    str(record.get('Full Name', '')) == str(record_to_delete.get('Full Name', '')) and
                    str(record.get('Timestamp', '')) == str(record_to_delete.get('Timestamp', ''))):
                    
                    # Delete the row
                    worksheet.delete_rows(i)
                    
                    # Clear cache
                    self.clear_cache()
                    return True
            
            return False
            
        except Exception as e:
            st.error(f"Failed to delete attendance record: {str(e)}")
            # Connection might have failed, reset status
            self.connection_status = False
            return False


def show_login():
    """Display login interface"""
    st.title("🔐 Login to Church Attendance System")
    st.markdown("Please enter your credentials to access the system")
    
    # Initialize managers if needed
    if 'sheets_manager' not in st.session_state:
        st.session_state.sheets_manager = GoogleSheetsManager()
    
    if 'user_manager' not in st.session_state:
        st.session_state.user_manager = UserManager(st.session_state.sheets_manager)
    
    # Ensure connection (this will connect only if needed)
    if not st.session_state.sheets_manager.ensure_connection():
        st.error("❌ System not connected to Google Sheets")
        if st.button("🔄 Connect to Google Sheets", use_container_width=True):
            with st.spinner("Connecting..."):
                if st.session_state.sheets_manager.initialize_connection():
                    st.session_state.sheets_manager.setup_worksheets()
                    # Create default admin if no users exist
                    st.session_state.user_manager.create_default_admin()
                    st.rerun()
        return
    
    # Create default admin only if needed (check once per session)
    if 'admin_check_done' not in st.session_state:
        try:
            st.session_state.user_manager.create_default_admin()
            st.session_state.admin_check_done = True
        except:
            pass  # Silently continue if there's an issue
    
    # Login form
    with st.form("login_form"):
        st.subheader("Sign In")
        
        username = st.text_input("Username", placeholder="Enter your username")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        
        submitted = st.form_submit_button("🔑 Sign In", use_container_width=True, type="primary")
        
        if submitted:
            if not username or not password:
                st.error("Please enter both username and password")
                return
            
            with st.spinner("Authenticating..."):
                user_data = st.session_state.user_manager.authenticate_user(username, password)
                
                if user_data:
                    # Set session state for authenticated user
                    st.session_state.authenticated = True
                    st.session_state.user = user_data
                    st.session_state.login_time = datetime.now()
                    
                    st.success(f"Welcome, {user_data['full_name']}!")
                    time.sleep(1)  # Brief pause to show success message
                    st.rerun()
                else:
                    st.error("Invalid username or password")
    
    # System information
    st.divider()
    st.subheader("ℹ️ System Information")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**User Roles Available:**")
        for role_key, role_info in UserManager.ROLES.items():
            st.write(f"• **{role_info['name']}**: {role_info['description']}")
    
    with col2:
        st.write("**System Status:**")
        if st.session_state.sheets_manager.connection_status:
            st.write("✅ Connected to Google Sheets")
        else:
            st.write("❌ Not connected to Google Sheets")
        
        st.write("**Version:** Church Attendance System v1.0")
        st.write("**Security:** Password-protected access")


def main():
    """Main application function with authentication"""
    
    # Initialize session state
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    
    if 'user' not in st.session_state:
        st.session_state.user = None
    
    # Show login if not authenticated
    if not st.session_state.authenticated:
        show_login()
        return
    
    # Initialize managers
    if 'sheets_manager' not in st.session_state:
        st.session_state.sheets_manager = GoogleSheetsManager()
    
    if 'user_manager' not in st.session_state:
        st.session_state.user_manager = UserManager(st.session_state.sheets_manager)
    
    # Check for password change requirement
    if st.session_state.user.get('must_change_password', False):
        show_password_change()
        return
    
    # Sidebar with user info
    st.sidebar.title("⛪ Church Attendance")
    
    # User information section
    user = st.session_state.user
    role_info = st.session_state.user_manager.get_user_role_info(user['role'])
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("👤 User Info")
    st.sidebar.write(f"**{user['full_name']}**")
    st.sidebar.write(f"Role: {role_info.get('name', user['role'])}")
    st.sidebar.write(f"Username: {user['username']}")
    
    # Logout button
    if st.sidebar.button("🚪 Logout", use_container_width=True):
        # Clear session state
        for key in list(st.session_state.keys()):
            if key not in ['sheets_manager']:  # Keep sheets manager
                del st.session_state[key]
        st.rerun()
    
    st.sidebar.markdown("---")
    
    # Connection status - check and maintain connection
    if st.session_state.sheets_manager.ensure_connection():
        st.sidebar.success("✅ Connected to Google Sheets")
        # Show connection duration if available
        if st.session_state.sheets_manager.connection_timestamp:
            duration = time.time() - st.session_state.sheets_manager.connection_timestamp
            st.sidebar.caption(f"Connected for {duration/60:.1f} minutes")
    else:
        st.sidebar.error("❌ Not connected to Google Sheets")
        if st.sidebar.button("🔄 Try to Connect"):
            with st.spinner("Connecting..."):
                if st.session_state.sheets_manager.initialize_connection():
                    st.session_state.sheets_manager.setup_worksheets()
                    st.rerun()
    
    # Role-based navigation
    user_role = st.session_state.user['role']
    user_manager = st.session_state.user_manager
    
    # Define pages with their required permissions
    all_pages = [
        ("🏠 Dashboard", "view_dashboard"),
        ("📝 Mark Attendance", "mark_attendance"), 
        ("👥 Manage Members", "manage_members"),
        ("📊 Analytics", "view_analytics"),
        ("📋 Reports", "generate_reports"),
        ("📜 History", "view_history"),
        ("🔧 Admin Panel", "admin_panel"),
        ("👤 User Management", "all")  # Only super admin
    ]
    
    # Filter pages based on user permissions
    accessible_pages = []
    for page_name, required_permission in all_pages:
        if user_manager.has_permission(user_role, required_permission):
            accessible_pages.append(page_name)
    
    # Handle quick action navigation from session state
    if 'selected_page' not in st.session_state:
        st.session_state.selected_page = accessible_pages[0] if accessible_pages else "🏠 Dashboard"
    
    # Ensure selected page is accessible to current user
    if st.session_state.selected_page not in accessible_pages:
        st.session_state.selected_page = accessible_pages[0] if accessible_pages else "🏠 Dashboard"
    
    # Get the current page from session state or radio
    current_page_index = 0
    if st.session_state.selected_page in accessible_pages:
        current_page_index = accessible_pages.index(st.session_state.selected_page)
    
    selected_page = st.sidebar.radio("Navigation", accessible_pages, index=current_page_index)
    
    # Update session state if radio selection changed
    if selected_page != st.session_state.selected_page:
        st.session_state.selected_page = selected_page
    
    # Cache controls
    st.sidebar.markdown("---")
    st.sidebar.subheader("Cache Controls")
    if st.sidebar.button("🗑️ Clear Cache"):
        st.session_state.sheets_manager.clear_cache()
        st.sidebar.success("Cache cleared!")
    
    # Main content area
    if not st.session_state.sheets_manager.connection_status:
        st.title("⛪ Church Attendance Management System")
        st.warning("Please configure your Google Sheets connection in the sidebar to get started.")
        
        st.subheader("Setup Instructions")
        st.markdown("""
        1. Create a Google Cloud Project and enable the Google Sheets API
        2. Create a service account and download the JSON credentials
        3. Create a Google Sheets spreadsheet named 'Church Attendance System'
        4. Share the spreadsheet with your service account email
        5. Configure your credentials in `.streamlit/secrets.toml`
        """)
        
        return
    
    # Route to selected page (use session state for consistency with quick actions)
    current_page = st.session_state.selected_page
    
    if current_page == "🏠 Dashboard":
        show_dashboard()
    elif current_page == "📝 Mark Attendance":
        show_attendance_marking()
    elif current_page == "👥 Manage Members":
        show_member_management()
    elif current_page == "📊 Analytics":
        show_analytics()
    elif current_page == "📋 Reports":
        show_reports()
    elif current_page == "📜 History":
        show_history()
    elif current_page == "🔧 Admin Panel":
        show_admin_panel()
    elif current_page == "👤 User Management":
        show_user_management()


def show_password_change():
    """Display password change interface for users who must change password"""
    st.title("🔐 Password Change Required")
    st.warning("You must change your password before accessing the system.")
    
    user = st.session_state.user
    
    with st.form("password_change_form"):
        st.subheader("Change Your Password")
        
        current_password = st.text_input("Current Password", type="password")
        new_password = st.text_input("New Password", type="password")
        confirm_password = st.text_input("Confirm New Password", type="password")
        
        # Password requirements
        st.info("""
        **Password Requirements:**
        - At least 8 characters long
        - Contains both letters and numbers
        - Not the same as current password
        """)
        
        submitted = st.form_submit_button("🔄 Change Password", use_container_width=True, type="primary")
        
        if submitted:
            # Validate inputs
            if not all([current_password, new_password, confirm_password]):
                st.error("Please fill in all fields")
                return
            
            if new_password != confirm_password:
                st.error("New passwords do not match")
                return
            
            if len(new_password) < 8:
                st.error("Password must be at least 8 characters long")
                return
            
            if new_password == current_password:
                st.error("New password must be different from current password")
                return
            
            # Verify current password
            users_df = st.session_state.user_manager.load_users()
            user_row = users_df[users_df['username'] == user['username']]
            
            if user_row.empty:
                st.error("User not found")
                return
            
            user_data = user_row.iloc[0].to_dict()
            
            if not st.session_state.user_manager.verify_password(current_password, user_data['password_hash'], user_data['salt']):
                st.error("Current password is incorrect")
                return
            
            # Update password
            new_hash, new_salt = st.session_state.user_manager.hash_password(new_password)
            
            try:
                worksheet = st.session_state.sheets_manager.spreadsheet.worksheet("Users")
                users_data = worksheet.get_all_records()
                
                for i, user_record in enumerate(users_data, start=2):
                    if user_record['username'] == user['username']:
                        # Update password hash, salt, and remove password change requirement
                        worksheet.update_cell(i, 2, new_hash)  # password_hash column
                        worksheet.update_cell(i, 3, new_salt)  # salt column
                        worksheet.update_cell(i, 10, False)    # must_change_password column
                        break
                
                # Update session user data
                st.session_state.user['must_change_password'] = False
                st.session_state.user['password_hash'] = new_hash
                st.session_state.user['salt'] = new_salt
                
                # Clear user cache to force refresh
                if hasattr(st.session_state.user_manager, '_clear_cache'):
                    st.session_state.user_manager._clear_cache("load_users")
                
                # Reset admin check to prevent recreation
                if 'admin_check_done' in st.session_state:
                    del st.session_state.admin_check_done
                
                st.success("Password changed successfully! You can now access the system.")
                time.sleep(2)
                st.rerun()
                
            except Exception as e:
                st.error(f"Failed to update password: {str(e)}")


def show_user_management():
    """Display user management interface (Super Admin only)"""
    st.title("👤 User Management")
    st.markdown("Manage system users, roles, and permissions")
    
    # Verify super admin access
    if st.session_state.user['role'] != 'super_admin':
        st.error("Access denied. This page requires Super Admin privileges.")
        return
    
    user_manager = st.session_state.user_manager
    users_df = user_manager.load_users()
    
    tab1, tab2, tab3, tab4 = st.tabs(["View Users", "Add User", "Manage Users", "User Activity"])
    
    with tab1:
        st.subheader("👥 Current Users")
        
        if users_df.empty:
            st.info("No users found in the system.")
        else:
            # Display users (excluding sensitive data)
            display_df = users_df[['username', 'role', 'full_name', 'email', 'created_date', 'last_login', 'is_active']].copy()
            display_df['last_login'] = display_df['last_login'].fillna('Never')
            
            # Add role names
            display_df['role_name'] = display_df['role'].apply(
                lambda x: user_manager.get_user_role_info(x).get('name', x)
            )
            
            st.dataframe(
                display_df[['username', 'full_name', 'role_name', 'email', 'created_date', 'last_login', 'is_active']],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "username": "Username",
                    "full_name": "Full Name", 
                    "role_name": "Role",
                    "email": "Email",
                    "created_date": "Created",
                    "last_login": "Last Login",
                    "is_active": st.column_config.CheckboxColumn("Active")
                }
            )
        
        # User statistics
        if not users_df.empty:
            st.subheader("📊 User Statistics")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Users", len(users_df))
            with col2:
                active_users = len(users_df[users_df['is_active'] == True])
                st.metric("Active Users", active_users)
            with col3:
                role_counts = users_df['role'].value_counts()
                most_common_role = role_counts.index[0] if not role_counts.empty else "None"
                role_name = user_manager.get_user_role_info(most_common_role).get('name', most_common_role)
                st.metric("Most Common Role", role_name)
            with col4:
                recent_logins = len(users_df[users_df['last_login'] != ''])
                st.metric("Users with Logins", recent_logins)
    
    with tab2:
        st.subheader("➕ Add New User")
        
        with st.form("add_user_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                new_username = st.text_input("Username*", placeholder="Enter username")
                new_full_name = st.text_input("Full Name*", placeholder="Enter full name")
                new_email = st.text_input("Email", placeholder="Enter email address")
            
            with col2:
                new_role = st.selectbox(
                    "Role*",
                    options=list(UserManager.ROLES.keys()),
                    format_func=lambda x: f"{UserManager.ROLES[x]['name']} - {UserManager.ROLES[x]['description']}"
                )
                new_password = st.text_input("Temporary Password*", type="password", placeholder="Enter temporary password")
                require_password_change = st.checkbox("Require password change on first login", value=True)
            
            st.markdown("*Required fields")
            
            submitted = st.form_submit_button("👤 Create User", use_container_width=True, type="primary")
            
            if submitted:
                # Validation
                if not all([new_username, new_full_name, new_password]):
                    st.error("Please fill in all required fields")
                elif len(new_password) < 8:
                    st.error("Password must be at least 8 characters long")
                elif not users_df.empty and new_username in users_df['username'].values:
                    st.error("Username already exists")
                else:
                    # Create new user
                    password_hash, salt = user_manager.hash_password(new_password)
                    
                    new_user = {
                        'username': new_username,
                        'password_hash': password_hash,
                        'salt': salt,
                        'role': new_role,
                        'full_name': new_full_name,
                        'email': new_email,
                        'created_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'last_login': '',
                        'is_active': True,
                        'must_change_password': require_password_change
                    }
                    
                    if user_manager.save_user(new_user):
                        st.success(f"User '{new_username}' created successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to create user")
    
    with tab3:
        st.subheader("⚙️ Manage Existing Users")
        
        if users_df.empty:
            st.info("No users to manage.")
        else:
            # Filter out the current user from management options
            current_username = st.session_state.user['username']
            manageable_users = users_df[users_df['username'] != current_username]
            
            if manageable_users.empty:
                st.info("No other users to manage.")
            else:
                # Select user to manage
                selected_user = st.selectbox(
                    "Select User to Manage",
                    options=manageable_users['username'].tolist(),
                    format_func=lambda x: f"{x} ({manageable_users[manageable_users['username']==x]['full_name'].iloc[0]}) - {user_manager.get_user_role_info(manageable_users[manageable_users['username']==x]['role'].iloc[0]).get('name', 'Unknown')}"
                )
                
                if selected_user:
                    user_data = manageable_users[manageable_users['username'] == selected_user].iloc[0]
                    current_role = user_data['role']
                    is_active = user_data['is_active']
                    
                    st.divider()
                    st.subheader(f"👤 Managing User: {user_data['full_name']} ({selected_user})")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write("**Current Information:**")
                        st.write(f"• **Username:** {selected_user}")
                        st.write(f"• **Full Name:** {user_data['full_name']}")
                        st.write(f"• **Email:** {user_data.get('email', 'Not set')}")
                        st.write(f"• **Role:** {user_manager.get_user_role_info(current_role).get('name', current_role)}")
                        st.write(f"• **Status:** {'🟢 Active' if is_active else '🔴 Inactive'}")
                        st.write(f"• **Created:** {user_data.get('created_date', 'Unknown')}")
                        st.write(f"• **Last Login:** {user_data.get('last_login', 'Never')}")
                    
                    with col2:
                        st.write("**Management Actions:**")
                        
                        # Role Management
                        st.write("**Change Role:**")
                        new_role = st.selectbox(
                            "Select New Role",
                            options=list(UserManager.ROLES.keys()),
                            index=list(UserManager.ROLES.keys()).index(current_role),
                            format_func=lambda x: f"{UserManager.ROLES[x]['name']} - {UserManager.ROLES[x]['description']}",
                            key=f"role_{selected_user}"
                        )
                        
                        if new_role != current_role:
                            if st.button(f"🔄 Update Role to {UserManager.ROLES[new_role]['name']}", key=f"update_role_{selected_user}"):
                                if user_manager.update_user_role(selected_user, new_role):
                                    st.success(f"Role updated successfully!")
                                    st.rerun()
                                else:
                                    st.error("Failed to update role")
                        
                        # Status Management
                        status_action = "Deactivate" if is_active else "Activate"
                        status_color = "🔴" if is_active else "🟢"
                        
                        if st.button(f"{status_color} {status_action} User", key=f"toggle_status_{selected_user}"):
                            if user_manager.toggle_user_active(selected_user):
                                st.success(f"User {status_action.lower()}d successfully!")
                                st.rerun()
                            else:
                                st.error(f"Failed to {status_action.lower()} user")
                        
                        # Delete User
                        st.write("**Danger Zone:**")
                        if st.button("🗑️ Delete User", key=f"delete_{selected_user}", type="secondary"):
                            # Confirmation in session state
                            st.session_state[f'confirm_delete_{selected_user}'] = True
                        
                        # Confirmation dialog
                        if st.session_state.get(f'confirm_delete_{selected_user}', False):
                            st.warning(f"⚠️ Are you sure you want to delete user '{selected_user}'?")
                            st.write("This action cannot be undone.")
                            
                            col_yes, col_no = st.columns(2)
                            
                            with col_yes:
                                if st.button("✅ Yes, Delete", key=f"confirm_yes_{selected_user}", type="primary"):
                                    if user_manager.delete_user(selected_user):
                                        st.success("User deleted successfully!")
                                        if f'confirm_delete_{selected_user}' in st.session_state:
                                            del st.session_state[f'confirm_delete_{selected_user}']
                                        st.rerun()
                                    else:
                                        st.error("Failed to delete user")
                            
                            with col_no:
                                if st.button("❌ Cancel", key=f"confirm_no_{selected_user}"):
                                    if f'confirm_delete_{selected_user}' in st.session_state:
                                        del st.session_state[f'confirm_delete_{selected_user}']
                                    st.rerun()
                    
                    # Security warnings
                    st.divider()
                    st.info("💡 **Security Notes:**\n"
                           "• You cannot manage your own account\n"
                           "• Cannot delete the last Super Admin user\n" 
                           "• Inactive users cannot log in\n"
                           "• Role changes take effect immediately")
    
    with tab4:
        st.subheader("📈 User Activity")
        
        if users_df.empty or users_df['last_login'].isna().all():
            st.info("No user activity data available.")
        else:
            # Recent logins
            recent_users = users_df[users_df['last_login'] != ''].copy()
            if not recent_users.empty:
                recent_users['last_login_dt'] = pd.to_datetime(recent_users['last_login'])
                recent_users = recent_users.sort_values('last_login_dt', ascending=False)
                
                st.write("**Recent User Logins:**")
                display_recent = recent_users[['username', 'full_name', 'role', 'last_login']].head(10)
                st.dataframe(display_recent, use_container_width=True, hide_index=True)
            
            # Role distribution
            role_dist = users_df['role'].value_counts()
            role_dist.index = [user_manager.get_user_role_info(role).get('name', role) for role in role_dist.index]
            
            st.subheader("👥 Role Distribution")
            fig = px.pie(values=role_dist.values, names=role_dist.index, title="Users by Role")
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)


def show_dashboard():
    """Display the main dashboard with comprehensive metrics and visualizations"""
    st.title("🏠 Dashboard")
    st.markdown("Welcome to the Church Attendance Management System")
    
    # Load data
    members_df = st.session_state.sheets_manager.load_members()
    attendance_df = st.session_state.sheets_manager.load_attendance()
    
    if members_df.empty and attendance_df.empty:
        st.info("📊 Start by adding members and marking attendance to see dashboard insights!")
        return
    
    # Calculate key metrics
    total_members = len(members_df) if not members_df.empty else 0
    today_attendance = 0
    weekly_attendance = 0
    monthly_attendance = 0
    avg_weekly_attendance = 0
    total_groups = 0
    
    if not attendance_df.empty:
        today = date.today()
        today_attendance = len(attendance_df[attendance_df['Date'].dt.date == today])
        
        last_week = today - timedelta(days=7)
        weekly_attendance = len(attendance_df[attendance_df['Date'].dt.date >= last_week])
        
        last_month = today - timedelta(days=30)
        monthly_attendance = len(attendance_df[attendance_df['Date'].dt.date >= last_month])
        
        # Calculate average weekly attendance over last 8 weeks
        last_8_weeks = today - timedelta(days=56)
        recent_attendance = attendance_df[attendance_df['Date'].dt.date >= last_8_weeks]
        if not recent_attendance.empty:
            avg_weekly_attendance = len(recent_attendance) / 8
    
    if not members_df.empty and 'Group' in members_df.columns:
        total_groups = members_df['Group'].nunique()
    
    # Top metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Members", total_members)
    
    with col2:
        st.metric("Today's Attendance", today_attendance)
    
    with col3:
        st.metric("Weekly Attendance", weekly_attendance, 
                  delta=f"{weekly_attendance - int(avg_weekly_attendance):+.0f} vs avg" if avg_weekly_attendance > 0 else None)
    
    with col4:
        attendance_rate = (weekly_attendance / total_members * 100) if total_members > 0 else 0
        st.metric("Weekly Rate", f"{attendance_rate:.1f}%")
    
    # Second metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Groups", total_groups)
    
    with col2:
        st.metric("Monthly Attendance", monthly_attendance)
    
    with col3:
        if not attendance_df.empty:
            unique_attendees = attendance_df['Full Name'].nunique()
            st.metric("Active Members", unique_attendees)
        else:
            st.metric("Active Members", 0)
    
    with col4:
        engagement_rate = (unique_attendees / total_members * 100) if total_members > 0 and not attendance_df.empty else 0
        st.metric("Engagement Rate", f"{engagement_rate:.1f}%")
    
    # Charts section
    if not attendance_df.empty:
        st.divider()
        
        # Attendance trends
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📈 Attendance Trends (Last 30 Days)")
            
            # Daily attendance trend
            last_30_days = date.today() - timedelta(days=30)
            recent_attendance = attendance_df[attendance_df['Date'].dt.date >= last_30_days].copy()
            
            if not recent_attendance.empty:
                daily_counts = recent_attendance.groupby('Date').size().reset_index(name='Count')
                daily_counts['Date'] = pd.to_datetime(daily_counts['Date'])
                
                fig = px.line(daily_counts, x='Date', y='Count', 
                            title="Daily Attendance",
                            markers=True)
                fig.update_layout(
                    height=300, 
                    showlegend=False,
                    xaxis_title="Date",
                    yaxis_title="Attendees"
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No attendance data in the last 30 days")
        
        with col2:
            st.subheader("👥 Group Performance")
            
            if not members_df.empty and 'Group' in members_df.columns:
                # Group attendance comparison
                group_attendance = attendance_df.groupby('Group').size().reset_index(name='Total Attendance')
                group_members = members_df.groupby('Group').size().reset_index(name='Total Members')
                group_stats = pd.merge(group_attendance, group_members, on='Group', how='outer').fillna(0)
                group_stats['Attendance Rate'] = (group_stats['Total Attendance'] / group_stats['Total Members'] * 100).round(1)
                
                fig = px.bar(group_stats, x='Group', y='Attendance Rate',
                           title="Group Attendance Rates (%)",
                           color='Attendance Rate',
                           color_continuous_scale='viridis')
                fig.update_layout(
                    height=300, 
                    showlegend=False,
                    xaxis_title="Group",
                    yaxis_title="Attendance Rate (%)"
                )
                st.plotly_chart(fig, use_container_width=True)
        
        # Weekly pattern analysis
        st.subheader("📊 Weekly Attendance Patterns")
        col1, col2 = st.columns(2)
        
        with col1:
            # Day of week analysis
            if not attendance_df.empty:
                attendance_df['Day of Week'] = attendance_df['Date'].dt.day_name()
                day_counts = attendance_df.groupby('Day of Week').size().reset_index(name='Count')
                
                # Order days properly
                day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
                day_counts['Day of Week'] = pd.Categorical(day_counts['Day of Week'], categories=day_order, ordered=True)
                day_counts = day_counts.sort_values('Day of Week')
                
                fig = px.bar(day_counts, x='Day of Week', y='Count',
                           title="Attendance by Day of Week",
                           color='Count',
                           color_continuous_scale='blues')
                fig.update_layout(height=300, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Top attendees
            st.subheader("🌟 Most Active Members")
            member_attendance = attendance_df.groupby('Full Name').size().reset_index(name='Attendance Count')
            member_attendance = member_attendance.sort_values('Attendance Count', ascending=False).head(10)
            
            if not member_attendance.empty:
                fig = px.bar(member_attendance, x='Attendance Count', y='Full Name',
                           title="Top 10 Most Active Members",
                           orientation='h',
                           color='Attendance Count',
                           color_continuous_scale='greens')
                fig.update_layout(
                    height=300, 
                    showlegend=False,
                    yaxis={'categoryorder': 'total ascending'}
                )
                st.plotly_chart(fig, use_container_width=True)
    
    # Quick actions
    st.divider()
    st.subheader("⚡ Quick Actions")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📝 Mark Attendance", use_container_width=True, type="primary"):
            st.session_state.selected_page = "📝 Mark Attendance"
            st.rerun()
    
    with col2:
        if st.button("➕ Add Member", use_container_width=True):
            st.session_state.selected_page = "👥 Manage Members"
            st.rerun()
    
    with col3:
        if st.button("📊 View Analytics", use_container_width=True):
            st.session_state.selected_page = "📊 Analytics"
            st.rerun()
    
    with col4:
        if st.button("📋 Generate Report", use_container_width=True):
            st.session_state.selected_page = "📋 Reports"
            st.rerun()
    
    # Recent activity
    if not attendance_df.empty:
        st.divider()
        st.subheader("🕒 Recent Activity")
        
        recent_records = attendance_df.sort_values('Timestamp', ascending=False).head(10)
        recent_records['Date'] = recent_records['Date'].dt.strftime('%Y-%m-%d')
        recent_records['Time'] = pd.to_datetime(recent_records['Timestamp']).dt.strftime('%H:%M')
        
        display_recent = recent_records[['Date', 'Time', 'Full Name', 'Group']].copy()
        st.dataframe(display_recent, use_container_width=True, hide_index=True)


def show_attendance_marking():
    """Display attendance marking interface"""
    st.title("📝 Mark Attendance")
    
    members_df = st.session_state.sheets_manager.load_members()
    
    if members_df.empty:
        st.warning("No members found. Please add members first.")
        return
    
    # Group and date selection outside form for better reactivity
    st.subheader("Select Date and Group")
    
    col1, col2 = st.columns(2)
    with col1:
        selected_date = st.date_input("Date", value=date.today())
    
    with col2:
        groups = sorted(members_df['Group'].unique()) if 'Group' in members_df.columns else []
        selected_group = st.selectbox("Group", options=['All Groups'] + list(groups))
    
    # Filter members by group
    if selected_group == 'All Groups':
        filtered_members = members_df
    else:
        filtered_members = members_df[members_df['Group'] == selected_group]
    
    if filtered_members.empty:
        st.warning(f"No members found in group: {selected_group}")
        return
    
    # Search functionality
    st.subheader("🔍 Search Members")
    col1, col2 = st.columns([3, 1])
    
    with col1:
        search_term = st.text_input(
            "Search by name:",
            placeholder="Type member name to search...",
            help="Search will filter the member list in real-time",
            key="member_search"
        )
    
    with col2:
        if st.button("🗑️ Clear Search", use_container_width=True):
            # Clear the search by rerunning without the search term
            if 'member_search' in st.session_state:
                st.session_state.member_search = ""
            st.rerun()
    
    # Apply search filter
    if search_term:
        # Case-insensitive search in member names
        search_mask = filtered_members['Full Name'].str.contains(search_term, case=False, na=False)
        filtered_members = filtered_members[search_mask]
        
        if filtered_members.empty:
            st.warning(f"No members found matching '{search_term}' in {'all groups' if selected_group == 'All Groups' else selected_group}")
            return
    
    # Show member count for selected group and search
    search_info = f" matching '{search_term}'" if search_term else ""
    group_info = 'all groups' if selected_group == 'All Groups' else selected_group
    st.info(f"📊 {len(filtered_members)} member(s){search_info} in {group_info}")
    
    # Attendance form with filtered members
    with st.form("attendance_form"):
        # Dynamic header showing search results
        if search_term:
            st.subheader(f"Select Members Present ({len(filtered_members)} found for '{search_term}')")
            if len(filtered_members) <= 10:
                st.success(f"🎯 Perfect! Found {len(filtered_members)} member(s) matching your search.")
            elif len(filtered_members) <= 20:
                st.info(f"📝 Found {len(filtered_members)} members. You can refine your search further if needed.")
            else:
                st.warning(f"📋 Found {len(filtered_members)} members. Consider refining your search for easier selection.")
        else:
            st.subheader(f"Select Members Present ({len(filtered_members)} available)")
        
        # Add select all/none buttons
        col1, col2, col3 = st.columns(3)
        with col1:
            select_all = st.checkbox("🔲 Select All Members", key="select_all")
        with col2:
            if st.form_submit_button("🔄 Clear Selections", use_container_width=True):
                # This will reset the form
                st.rerun()
        with col3:
            # Show quick stats
            if search_term:
                st.write(f"🔍 **Filtered by:** '{search_term}'")
            else:
                st.write(f"👥 **Showing:** All in {group_info}")
        
        st.divider()
        
        # Create checkboxes for each member
        selected_members = []
        
        # Sort members by name for better UX
        filtered_members_sorted = filtered_members.sort_values('Full Name')
        
        for idx, member in filtered_members_sorted.iterrows():
            member_name = member.get('Full Name', f"Member {idx}")
            member_id = member.get('Membership Number', '')
            member_group = member.get('Group', '')
            
            # Build display name with search highlighting
            display_name = f"{member_name}"
            if member_id:
                display_name += f" (ID: {member_id})"
            if selected_group == 'All Groups':
                display_name += f" - {member_group}"
            
            # Add search match indicator
            if search_term and search_term.lower() in member_name.lower():
                display_name = f"🔍 {display_name}"
            
            # Use select_all to determine initial state
            initial_checked = select_all if 'select_all' in st.session_state else False
            
            if st.checkbox(display_name, key=f"member_{idx}", value=initial_checked):
                selected_members.append({
                    'Membership Number': member_id,
                    'Full Name': member_name,
                    'Group': member_group,
                    'Date': selected_date.strftime('%Y-%m-%d'),
                    'Status': 'Present'
                })
        
        st.divider()
        
        # Show summary of selected members
        if selected_members:
            st.success(f"✅ {len(selected_members)} member(s) selected for attendance")
        
        submitted = st.form_submit_button("📝 Mark Attendance", use_container_width=True, type="primary")
        
        if submitted:
            if not selected_members:
                st.error("Please select at least one member.")
            else:
                with st.spinner("Saving attendance..."):
                    success = st.session_state.sheets_manager.save_attendance(selected_members)
                    
                    if success:
                        st.success(f"✅ Attendance marked for {len(selected_members)} members on {selected_date.strftime('%Y-%m-%d')}!")
                        st.balloons()
                        
                        # Show summary of marked attendance
                        st.subheader("📋 Attendance Summary")
                        summary_df = pd.DataFrame(selected_members)
                        st.dataframe(
                            summary_df[['Full Name', 'Group', 'Date']],
                            use_container_width=True,
                            hide_index=True
                        )
                    else:
                        st.error("Failed to save attendance. Please try again.")


def show_member_management():
    """Display member management interface"""
    st.title("👥 Member Management")
    
    tab1, tab2, tab3 = st.tabs(["View Members", "Add Member", "Import Members"])
    
    with tab1:
        st.subheader("Current Members")
        members_df = st.session_state.sheets_manager.load_members()
        
        if members_df.empty:
            st.info("No members found. Add some members to get started!")
        else:
            st.dataframe(members_df, use_container_width=True)
            
            # Export functionality
            if st.button("📥 Export Members CSV"):
                csv = members_df.to_csv(index=False)
                st.download_button(
                    label="⬇️ Download CSV",
                    data=csv,
                    file_name=f"members_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
    
    with tab2:
        st.subheader("Add New Member")
        
        with st.form("add_member_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                membership_number = st.text_input("Membership Number (Optional)")
                full_name = st.text_input("Full Name *", placeholder="Enter full name")
                group = st.text_input("Group *", placeholder="e.g., Youth, Adults, Children")
            
            with col2:
                email = st.text_input("Email (Optional)", placeholder="email@example.com")
                phone = st.text_input("Phone (Optional)", placeholder="+1234567890")
            
            submitted = st.form_submit_button("➕ Add Member", use_container_width=True)
            
            if submitted:
                if not full_name or not group:
                    st.error("Full Name and Group are required!")
                else:
                    # Load existing members
                    members_df = st.session_state.sheets_manager.load_members()
                    
                    # Create new member record
                    new_member = {
                        'Membership Number': membership_number,
                        'Full Name': full_name,
                        'Group': group,
                        'Email': email,
                        'Phone': phone
                    }
                    
                    # Add to DataFrame
                    if members_df.empty:
                        members_df = pd.DataFrame([new_member])
                    else:
                        members_df = pd.concat([members_df, pd.DataFrame([new_member])], ignore_index=True)
                    
                    # Save to Google Sheets
                    with st.spinner("Adding member..."):
                        success = st.session_state.sheets_manager.save_members(members_df)
                        
                        if success:
                            st.success(f"✅ Member '{full_name}' added successfully!")
                            st.rerun()
                        else:
                            st.error("Failed to add member. Please try again.")
    
    with tab3:
        st.subheader("Import Members from CSV")
        st.info("Upload a CSV file with columns: Membership Number, Full Name, Group, Email, Phone")
        
        uploaded_file = st.file_uploader("Choose CSV file", type="csv")
        
        if uploaded_file is not None:
            try:
                import_df = pd.read_csv(uploaded_file)
                
                st.subheader("Preview Import Data")
                st.dataframe(import_df.head())
                
                if st.button("📤 Import Members"):
                    with st.spinner("Importing members..."):
                        success = st.session_state.sheets_manager.save_members(import_df)
                        
                        if success:
                            st.success(f"✅ Imported {len(import_df)} members successfully!")
                            st.rerun()
                        else:
                            st.error("Failed to import members. Please try again.")
            
            except Exception as e:
                st.error(f"Error reading CSV file: {str(e)}")


def show_analytics():
    """Display comprehensive analytics and insights"""
    st.title("📊 Analytics & Insights")
    st.markdown("Detailed analytics and trends for church attendance data")
    
    # Load data
    members_df = st.session_state.sheets_manager.load_members()
    attendance_df = st.session_state.sheets_manager.load_attendance()
    
    if attendance_df.empty:
        st.warning("📈 No attendance data available. Start marking attendance to see analytics!")
        return
    
    # Time period selector
    st.subheader("📅 Analysis Period")
    col1, col2 = st.columns(2)
    
    with col1:
        time_period = st.selectbox(
            "Select Analysis Period",
            ["Last 30 Days", "Last 60 Days", "Last 90 Days", "Last 6 Months", "Last Year", "All Time"],
            index=2
        )
    
    with col2:
        # Custom date range option
        if st.checkbox("Custom Date Range"):
            date_range = st.date_input(
                "Select Date Range",
                value=(date.today() - timedelta(days=90), date.today()),
                key="analytics_date_range"
            )
            if len(date_range) == 2:
                start_date, end_date = date_range
            else:
                start_date = date.today() - timedelta(days=90)
                end_date = date.today()
            days = 0  # Custom range, no day limit
        else:
            # Map time period to days
            period_days = {
                "Last 30 Days": 30,
                "Last 60 Days": 60,
                "Last 90 Days": 90,
                "Last 6 Months": 180,
                "Last Year": 365,
                "All Time": 9999
            }
            days = period_days[time_period]
            start_date = date.today() - timedelta(days=days)
            end_date = date.today()
    
    # Filter data by selected period
    if days < 9999 and days > 0:
        filtered_attendance = attendance_df[
            (attendance_df['Date'].dt.date >= start_date) & 
            (attendance_df['Date'].dt.date <= end_date)
        ].copy()
    else:
        filtered_attendance = attendance_df.copy()
    
    if filtered_attendance.empty:
        st.warning("No attendance data found for the selected period.")
        return
    
    # Summary statistics
    st.subheader("📊 Summary Statistics")
    col1, col2, col3, col4 = st.columns(4)
    
    total_attendance_records = len(filtered_attendance)
    unique_attendees = filtered_attendance['Full Name'].nunique()
    unique_days = filtered_attendance['Date'].dt.date.nunique()
    avg_daily_attendance = total_attendance_records / unique_days if unique_days > 0 else 0
    
    with col1:
        st.metric("Total Attendance Records", total_attendance_records)
    with col2:
        st.metric("Unique Attendees", unique_attendees)
    with col3:
        st.metric("Days with Attendance", unique_days)
    with col4:
        st.metric("Avg Daily Attendance", f"{avg_daily_attendance:.1f}")
    
    # Attendance trends over time
    st.subheader("📈 Attendance Trends")
    
    # Group by time periods for trend analysis
    col1, col2 = st.columns(2)
    
    with col1:
        # Weekly trends
        st.subheader("Weekly Trends")
        filtered_attendance['Week'] = filtered_attendance['Date'].dt.to_period('W')
        weekly_counts = filtered_attendance.groupby('Week').size().reset_index(name='Count')
        weekly_counts['Week'] = weekly_counts['Week'].dt.start_time
        
        if len(weekly_counts) > 1:
            fig = px.line(weekly_counts, x='Week', y='Count',
                         title="Weekly Attendance Trend",
                         markers=True)
            fig.update_layout(
                height=400,
                xaxis_title="Week Starting",
                yaxis_title="Total Attendees"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Need data from multiple weeks to show trend")
    
    with col2:
        # Monthly trends (if data spans multiple months)
        st.subheader("Monthly Trends")
        filtered_attendance['Month'] = filtered_attendance['Date'].dt.to_period('M')
        monthly_counts = filtered_attendance.groupby('Month').size().reset_index(name='Count')
        monthly_counts['Month'] = monthly_counts['Month'].dt.start_time
        
        if len(monthly_counts) > 1:
            fig = px.bar(monthly_counts, x='Month', y='Count',
                        title="Monthly Attendance",
                        color='Count',
                        color_continuous_scale='blues')
            fig.update_layout(
                height=400,
                xaxis_title="Month",
                yaxis_title="Total Attendees"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Need data from multiple months to show trend")
    
    # Advanced Analytics
    st.subheader("🔍 Advanced Analytics")
    
    tab1, tab2, tab3, tab4 = st.tabs(["Group Analysis", "Member Engagement", "Attendance Patterns", "Growth Analysis"])
    
    with tab1:
        st.subheader("👥 Group Performance Analysis")
        
        if not members_df.empty and 'Group' in members_df.columns:
            # Group statistics
            group_stats = []
            for group in members_df['Group'].unique():
                group_members = members_df[members_df['Group'] == group]
                group_attendance = filtered_attendance[filtered_attendance['Group'] == group]
                
                total_members = len(group_members)
                total_attendance = len(group_attendance)
                unique_attendees = group_attendance['Full Name'].nunique()
                
                participation_rate = (unique_attendees / total_members * 100) if total_members > 0 else 0
                avg_attendance_per_service = total_attendance / unique_days if unique_days > 0 else 0
                
                group_stats.append({
                    'Group': group,
                    'Total Members': total_members,
                    'Active Members': unique_attendees,
                    'Participation Rate (%)': round(participation_rate, 1),
                    'Total Attendance': total_attendance,
                    'Avg per Service': round(avg_attendance_per_service, 1)
                })
            
            group_df = pd.DataFrame(group_stats)
            
            col1, col2 = st.columns(2)
            with col1:
                st.dataframe(group_df, use_container_width=True, hide_index=True)
            
            with col2:
                if len(group_df) > 1:
                    fig = px.pie(group_df, values='Total Attendance', names='Group',
                               title="Attendance Distribution by Group")
                    fig.update_layout(height=400)
                    st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        st.subheader("🌟 Member Engagement Analysis")
        
        # Member attendance frequency
        member_stats = filtered_attendance.groupby('Full Name').agg({
            'Date': 'count',
            'Group': 'first'
        }).reset_index()
        member_stats.columns = ['Full Name', 'Attendance Count', 'Group']
        member_stats = member_stats.sort_values('Attendance Count', ascending=False)
        
        # Categorize engagement levels
        def categorize_engagement(count, total_services):
            if total_services == 0:
                return "No Data"
            percentage = (count / total_services) * 100
            if percentage >= 80:
                return "Highly Engaged (80%+)"
            elif percentage >= 50:
                return "Moderately Engaged (50-79%)"
            elif percentage >= 25:
                return "Occasionally Engaged (25-49%)"
            else:
                return "Low Engagement (<25%)"
        
        member_stats['Engagement Level'] = member_stats['Attendance Count'].apply(
            lambda x: categorize_engagement(x, unique_days)
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Top 15 most engaged members
            st.subheader("Top 15 Most Engaged Members")
            top_members = member_stats.head(15)
            
            fig = px.bar(top_members, x='Attendance Count', y='Full Name',
                        title="Most Engaged Members",
                        orientation='h',
                        color='Attendance Count',
                        color_continuous_scale='greens')
            fig.update_layout(
                height=500,
                yaxis={'categoryorder': 'total ascending'}
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Engagement level distribution
            engagement_counts = member_stats['Engagement Level'].value_counts()
            
            fig = px.pie(values=engagement_counts.values, names=engagement_counts.index,
                        title="Member Engagement Level Distribution")
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
            
            # Engagement statistics
            st.subheader("Engagement Statistics")
            avg_attendance = member_stats['Attendance Count'].mean()
            median_attendance = member_stats['Attendance Count'].median()
            
            st.metric("Average Attendance per Member", f"{avg_attendance:.1f}")
            st.metric("Median Attendance per Member", f"{median_attendance:.1f}")
    
    with tab3:
        st.subheader("📅 Attendance Patterns")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Day of week patterns
            filtered_attendance['Day of Week'] = filtered_attendance['Date'].dt.day_name()
            day_counts = filtered_attendance.groupby('Day of Week').size().reset_index(name='Count')
            
            # Order days properly
            day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            day_counts['Day of Week'] = pd.Categorical(day_counts['Day of Week'], categories=day_order, ordered=True)
            day_counts = day_counts.sort_values('Day of Week')
            
            fig = px.bar(day_counts, x='Day of Week', y='Count',
                        title="Attendance by Day of Week",
                        color='Count',
                        color_continuous_scale='viridis')
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Time of day patterns (if timestamp data available)
            if 'Timestamp' in filtered_attendance.columns:
                filtered_attendance['Hour'] = pd.to_datetime(filtered_attendance['Timestamp']).dt.hour
                hour_counts = filtered_attendance.groupby('Hour').size().reset_index(name='Count')
                
                fig = px.line(hour_counts, x='Hour', y='Count',
                            title="Attendance by Hour of Day",
                            markers=True)
                fig.update_layout(
                    height=400,
                    xaxis_title="Hour (24-hour format)",
                    yaxis_title="Attendance Count"
                )
                st.plotly_chart(fig, use_container_width=True)
    
    with tab4:
        st.subheader("📊 Growth Analysis")
        
        if unique_days > 7:  # Need sufficient data for growth analysis
            # Calculate rolling averages
            daily_attendance = filtered_attendance.groupby('Date').size().reset_index(name='Count')
            daily_attendance = daily_attendance.sort_values('Date')
            
            # 7-day rolling average
            daily_attendance['Rolling_7_Day'] = daily_attendance['Count'].rolling(window=7, center=True).mean()
            
            col1, col2 = st.columns(2)
            
            with col1:
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=daily_attendance['Date'],
                    y=daily_attendance['Count'],
                    mode='markers',
                    name='Daily Attendance',
                    opacity=0.6
                ))
                fig.add_trace(go.Scatter(
                    x=daily_attendance['Date'],
                    y=daily_attendance['Rolling_7_Day'],
                    mode='lines',
                    name='7-Day Average',
                    line=dict(width=3)
                ))
                fig.update_layout(
                    title="Attendance Trend with 7-Day Average",
                    xaxis_title="Date",
                    yaxis_title="Attendance Count",
                    height=400
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # Growth metrics
                first_week_avg = daily_attendance.head(7)['Count'].mean()
                last_week_avg = daily_attendance.tail(7)['Count'].mean()
                growth_rate = ((last_week_avg - first_week_avg) / first_week_avg * 100) if first_week_avg > 0 else 0
                
                st.metric("First Week Average", f"{first_week_avg:.1f}")
                st.metric("Recent Week Average", f"{last_week_avg:.1f}", 
                         delta=f"{growth_rate:+.1f}%" if growth_rate != 0 else None)
                
                # New vs returning attendees
                first_attendance = filtered_attendance.groupby('Full Name')['Date'].min()
                filtered_attendance['Is_New_Attendee'] = filtered_attendance.apply(
                    lambda row: first_attendance[row['Full Name']] == row['Date'], axis=1
                )
                
                new_attendees_by_week = filtered_attendance[filtered_attendance['Is_New_Attendee']].groupby(
                    filtered_attendance['Date'].dt.to_period('W')
                ).size().reset_index(name='New Attendees')
                
                if len(new_attendees_by_week) > 0:
                    st.subheader("New Attendees by Week")
                    new_attendees_by_week['Week'] = new_attendees_by_week['Date'].dt.start_time
                    
                    fig = px.bar(new_attendees_by_week, x='Week', y='New Attendees',
                               title="New Attendees Each Week")
                    fig.update_layout(height=300)
                    st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Need more attendance data (at least 1 week) to show growth analysis.")
    
    # Export options
    st.subheader("📤 Export Analytics")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📊 Export Summary Stats", use_container_width=True):
            summary_data = {
                'Metric': ['Total Records', 'Unique Attendees', 'Days with Attendance', 'Avg Daily Attendance'],
                'Value': [total_attendance_records, unique_attendees, unique_days, f"{avg_daily_attendance:.1f}"]
            }
            csv = pd.DataFrame(summary_data).to_csv(index=False)
            st.download_button(
                label="Download Summary CSV",
                data=csv,
                file_name=f"attendance_summary_{start_date}_{end_date}.csv",
                mime="text/csv"
            )
    
    with col2:
        if st.button("👥 Export Member Stats", use_container_width=True):
            if 'member_stats' in locals():
                csv = member_stats.to_csv(index=False)
                st.download_button(
                    label="Download Member Stats CSV",
                    data=csv,
                    file_name=f"member_engagement_{start_date}_{end_date}.csv",
                    mime="text/csv"
                )
    
    with col3:
        if st.button("📈 Export Trend Data", use_container_width=True):
            if 'weekly_counts' in locals():
                csv = weekly_counts.to_csv(index=False)
                st.download_button(
                    label="Download Trend Data CSV",
                    data=csv,
                    file_name=f"attendance_trends_{start_date}_{end_date}.csv",
                    mime="text/csv"
                )


def show_reports():
    """Display comprehensive reporting interface"""
    st.title("📋 Reports & Export")
    st.markdown("Generate detailed reports and export attendance data")
    
    # Load data
    members_df = st.session_state.sheets_manager.load_members()
    attendance_df = st.session_state.sheets_manager.load_attendance()
    
    if attendance_df.empty and members_df.empty:
        st.warning("📄 No data available for reports. Add members and mark attendance to generate reports.")
        return
    
    # Report type selection
    st.subheader("📊 Select Report Type")
    report_type = st.selectbox(
        "Choose the type of report to generate:",
        ["Monthly Summary Report", "Group Performance Report", "Member Engagement Report", 
         "Attendance Trend Report", "Executive Summary", "Custom Date Range Report"]
    )
    
    # Date range selection
    st.subheader("📅 Report Period")
    col1, col2 = st.columns(2)
    
    with col1:
        if report_type == "Monthly Summary Report":
            # Month/Year selector for monthly reports
            current_date = datetime.now()
            selected_month = st.selectbox(
                "Select Month",
                range(1, 13),
                index=current_date.month - 1,
                format_func=lambda x: datetime(2023, x, 1).strftime("%B")
            )
            selected_year = st.selectbox(
                "Select Year",
                range(current_date.year - 5, current_date.year + 1),
                index=5
            )
            # Calculate date range for the selected month
            start_date = date(selected_year, selected_month, 1)
            if selected_month == 12:
                end_date = date(selected_year + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = date(selected_year, selected_month + 1, 1) - timedelta(days=1)
        else:
            # Custom date range
            date_range = st.date_input(
                "Select Date Range",
                value=(date.today() - timedelta(days=30), date.today()),
                key="report_date_range"
            )
            if len(date_range) == 2:
                start_date, end_date = date_range
            else:
                start_date = date.today() - timedelta(days=30)
                end_date = date.today()
    
    with col2:
        # Additional filters
        if not members_df.empty and 'Group' in members_df.columns:
            selected_groups = st.multiselect(
                "Filter by Groups (optional)",
                options=members_df['Group'].unique(),
                default=members_df['Group'].unique()
            )
        else:
            selected_groups = []
    
    # Filter attendance data
    if not attendance_df.empty:
        filtered_attendance = attendance_df[
            (attendance_df['Date'].dt.date >= start_date) & 
            (attendance_df['Date'].dt.date <= end_date)
        ].copy()
        
        if selected_groups:
            filtered_attendance = filtered_attendance[filtered_attendance['Group'].isin(selected_groups)]
        
        if filtered_attendance.empty:
            st.warning("No attendance data found for the selected criteria.")
            return
    else:
        filtered_attendance = pd.DataFrame()
    
    # Generate report button
    if st.button("📋 Generate Report", type="primary", use_container_width=True):
        
        # Report generation based on type
        if report_type == "Monthly Summary Report":
            generate_monthly_summary_report(filtered_attendance, members_df, start_date, end_date, selected_groups)
            
        elif report_type == "Group Performance Report":
            generate_group_performance_report(filtered_attendance, members_df, start_date, end_date, selected_groups)
            
        elif report_type == "Member Engagement Report":
            generate_member_engagement_report(filtered_attendance, members_df, start_date, end_date, selected_groups)
            
        elif report_type == "Attendance Trend Report":
            generate_attendance_trend_report(filtered_attendance, start_date, end_date)
            
        elif report_type == "Executive Summary":
            generate_executive_summary_report(filtered_attendance, members_df, start_date, end_date)
            
        elif report_type == "Custom Date Range Report":
            generate_custom_date_range_report(filtered_attendance, members_df, start_date, end_date, selected_groups)


def generate_monthly_summary_report(attendance_df, members_df, start_date, end_date, selected_groups):
    """Generate monthly summary report"""
    st.subheader(f"📊 Monthly Summary Report - {start_date.strftime('%B %Y')}")
    
    if attendance_df.empty:
        st.warning("No attendance data for this period.")
        return
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    total_attendance = len(attendance_df)
    unique_attendees = attendance_df['Full Name'].nunique()
    unique_days = attendance_df['Date'].dt.date.nunique()
    avg_daily_attendance = total_attendance / unique_days if unique_days > 0 else 0
    
    with col1:
        st.metric("Total Attendance", total_attendance)
    with col2:
        st.metric("Unique Attendees", unique_attendees)
    with col3:
        st.metric("Active Days", unique_days)
    with col4:
        st.metric("Avg Daily Attendance", f"{avg_daily_attendance:.1f}")
    
    # Daily attendance chart
    st.subheader("📈 Daily Attendance Breakdown")
    daily_attendance = attendance_df.groupby('Date').size().reset_index(name='Count')
    
    fig = px.bar(daily_attendance, x='Date', y='Count',
                title=f"Daily Attendance - {start_date.strftime('%B %Y')}",
                color='Count',
                color_continuous_scale='blues')
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)
    
    # Group breakdown
    if 'Group' in attendance_df.columns:
        st.subheader("👥 Group Performance")
        group_summary = attendance_df.groupby('Group').agg({
            'Full Name': 'nunique',
            'Date': 'count'
        }).reset_index()
        group_summary.columns = ['Group', 'Unique Members', 'Total Attendance']
        
        col1, col2 = st.columns(2)
        with col1:
            st.dataframe(group_summary, use_container_width=True, hide_index=True)
        with col2:
            fig = px.pie(group_summary, values='Total Attendance', names='Group',
                        title="Attendance by Group")
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
    
    # Top attendees
    st.subheader("🌟 Top Attendees")
    top_attendees = attendance_df.groupby(['Full Name', 'Group']).size().reset_index(name='Attendance Count')
    top_attendees = top_attendees.sort_values('Attendance Count', ascending=False).head(10)
    
    col1, col2 = st.columns(2)
    with col1:
        st.dataframe(top_attendees, use_container_width=True, hide_index=True)
    with col2:
        fig = px.bar(top_attendees, x='Attendance Count', y='Full Name',
                    title="Top 10 Attendees",
                    orientation='h',
                    color='Attendance Count',
                    color_continuous_scale='greens')
        fig.update_layout(
            height=400,
            yaxis={'categoryorder': 'total ascending'}
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Export options using universal export section
    csv_exports = {
        "Daily Attendance": pd.DataFrame({
            'Date': daily_attendance['Date'].dt.strftime('%Y-%m-%d'),
            'Attendance Count': daily_attendance['Count']
        }).to_csv(index=False)
    }
    
    if 'Group' in attendance_df.columns and not group_summary.empty:
        csv_exports["Group Summary"] = group_summary.to_csv(index=False)
    
    csv_exports["Top Attendees"] = top_attendees.to_csv(index=False)
    
    create_universal_export_section(
        attendance_df, members_df, start_date, end_date, 
        "Monthly Summary Report", selected_groups, csv_exports
    )


def generate_group_performance_report(attendance_df, members_df, start_date, end_date, selected_groups):
    """Generate group performance report"""
    st.subheader(f"👥 Group Performance Report ({start_date} to {end_date})")
    
    if attendance_df.empty or members_df.empty:
        st.warning("Insufficient data for group performance report.")
        return
    
    # Calculate group statistics
    group_stats = []
    for group in selected_groups:
        group_members = members_df[members_df['Group'] == group]
        group_attendance = attendance_df[attendance_df['Group'] == group]
        
        total_members = len(group_members)
        active_members = group_attendance['Full Name'].nunique()
        total_attendance = len(group_attendance)
        unique_days = attendance_df['Date'].dt.date.nunique()
        
        participation_rate = (active_members / total_members * 100) if total_members > 0 else 0
        avg_attendance_per_service = total_attendance / unique_days if unique_days > 0 else 0
        consistency_score = (total_attendance / (active_members * unique_days) * 100) if active_members > 0 and unique_days > 0 else 0
        
        group_stats.append({
            'Group': group,
            'Total Members': total_members,
            'Active Members': active_members,
            'Participation Rate (%)': round(participation_rate, 1),
            'Total Attendance': total_attendance,
            'Avg per Service': round(avg_attendance_per_service, 1),
            'Consistency Score (%)': round(consistency_score, 1)
        })
    
    group_df = pd.DataFrame(group_stats)
    
    # Display group statistics table
    st.dataframe(group_df, use_container_width=True, hide_index=True)
    
    # Visualizations
    col1, col2 = st.columns(2)
    
    with col1:
        # Participation rates comparison
        fig = px.bar(group_df, x='Group', y='Participation Rate (%)',
                    title="Group Participation Rates",
                    color='Participation Rate (%)',
                    color_continuous_scale='viridis')
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Total attendance comparison
        fig = px.bar(group_df, x='Group', y='Total Attendance',
                    title="Total Attendance by Group",
                    color='Total Attendance',
                    color_continuous_scale='blues')
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    # Detailed group analysis
    for group in selected_groups:
        with st.expander(f"📊 Detailed Analysis: {group}"):
            group_attendance = attendance_df[attendance_df['Group'] == group]
            if not group_attendance.empty:
                # Weekly trend for this group
                group_attendance_copy = group_attendance.copy()
                group_attendance_copy['Week'] = group_attendance_copy['Date'].dt.to_period('W')
                weekly_counts = group_attendance_copy.groupby('Week').size().reset_index(name='Count')
                weekly_counts['Week'] = weekly_counts['Week'].dt.start_time
                
                if len(weekly_counts) > 1:
                    fig = px.line(weekly_counts, x='Week', y='Count',
                                 title=f"Weekly Attendance Trend - {group}",
                                 markers=True)
                    fig.update_layout(height=300)
                    st.plotly_chart(fig, use_container_width=True)
                
                # Top members in this group
                group_member_stats = group_attendance.groupby('Full Name').size().reset_index(name='Attendance Count')
                group_member_stats = group_member_stats.sort_values('Attendance Count', ascending=False).head(5)
                
                st.subheader(f"Top 5 Members in {group}")
                st.dataframe(group_member_stats, use_container_width=True, hide_index=True)
    
    # Export group report using universal export section
    csv_exports = {
        "Group Performance": group_df.to_csv(index=False)
    }
    
    create_universal_export_section(
        attendance_df, members_df, start_date, end_date, 
        "Group Performance Report", selected_groups, csv_exports
    )


def generate_member_engagement_report(attendance_df, members_df, start_date, end_date, selected_groups):
    """Generate member engagement report"""
    st.subheader(f"🌟 Member Engagement Report ({start_date} to {end_date})")
    
    if attendance_df.empty:
        st.warning("No attendance data for member engagement analysis.")
        return
    
    # Calculate member engagement statistics
    total_services = attendance_df['Date'].dt.date.nunique()
    member_stats = attendance_df.groupby(['Full Name', 'Group']).agg({
        'Date': 'count'
    }).reset_index()
    member_stats.columns = ['Full Name', 'Group', 'Attendance Count']
    member_stats['Attendance Rate (%)'] = (member_stats['Attendance Count'] / total_services * 100).round(1)
    
    # Categorize engagement levels
    def get_engagement_level(rate):
        if rate >= 80:
            return "Highly Engaged (80%+)"
        elif rate >= 50:
            return "Moderately Engaged (50-79%)"
        elif rate >= 25:
            return "Occasionally Engaged (25-49%)"
        else:
            return "Low Engagement (<25%)"
    
    member_stats['Engagement Level'] = member_stats['Attendance Rate (%)'].apply(get_engagement_level)
    member_stats = member_stats.sort_values('Attendance Rate (%)', ascending=False)
    
    # Display engagement summary
    engagement_summary = member_stats['Engagement Level'].value_counts()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Engagement Level Distribution")
        st.dataframe(engagement_summary.reset_index(), use_container_width=True, hide_index=True)
        
        # Engagement level pie chart
        fig = px.pie(values=engagement_summary.values, names=engagement_summary.index,
                    title="Member Engagement Distribution")
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("📈 Engagement Statistics")
        avg_engagement = member_stats['Attendance Rate (%)'].mean()
        median_engagement = member_stats['Attendance Rate (%)'].median()
        
        st.metric("Average Engagement Rate", f"{avg_engagement:.1f}%")
        st.metric("Median Engagement Rate", f"{median_engagement:.1f}%")
        st.metric("Total Active Members", len(member_stats))
        st.metric("Highly Engaged Members", len(member_stats[member_stats['Attendance Rate (%)'] >= 80]))
    
    # Detailed member list
    st.subheader("📋 Detailed Member Engagement")
    
    # Filter options
    col1, col2 = st.columns(2)
    with col1:
        engagement_filter = st.selectbox(
            "Filter by Engagement Level",
            ["All"] + list(member_stats['Engagement Level'].unique())
        )
    with col2:
        min_attendance = st.slider("Minimum Attendance Count", 0, int(member_stats['Attendance Count'].max()), 0)
    
    # Apply filters
    filtered_members = member_stats.copy()
    if engagement_filter != "All":
        filtered_members = filtered_members[filtered_members['Engagement Level'] == engagement_filter]
    filtered_members = filtered_members[filtered_members['Attendance Count'] >= min_attendance]
    
    st.dataframe(filtered_members, use_container_width=True, hide_index=True)
    
    # Top and bottom performers
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🏆 Top 10 Most Engaged Members")
        top_members = member_stats.head(10)
        fig = px.bar(top_members, x='Attendance Rate (%)', y='Full Name',
                    title="Top 10 Most Engaged Members",
                    orientation='h',
                    color='Attendance Rate (%)',
                    color_continuous_scale='greens')
        fig.update_layout(
            height=400,
            yaxis={'categoryorder': 'total ascending'}
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("⚠️ Members Needing Engagement")
        low_engagement = member_stats[member_stats['Attendance Rate (%)'] < 25].head(10)
        if not low_engagement.empty:
            fig = px.bar(low_engagement, x='Attendance Rate (%)', y='Full Name',
                        title="Members with Low Engagement (<25%)",
                        orientation='h',
                        color='Attendance Rate (%)',
                        color_continuous_scale='reds')
            fig.update_layout(
                height=400,
                yaxis={'categoryorder': 'total ascending'}
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("All members have good engagement levels!")
    
    # Export member engagement report using universal export section
    csv_exports = {
        "Member Engagement": member_stats.to_csv(index=False)
    }
    
    # Add low engagement data if it exists
    low_engagement_full = member_stats[member_stats['Attendance Rate (%)'] < 50]
    if not low_engagement_full.empty:
        csv_exports["Low Engagement Members"] = low_engagement_full.to_csv(index=False)
    
    create_universal_export_section(
        attendance_df, members_df, start_date, end_date, 
        "Member Engagement Report", selected_groups, csv_exports
    )


def generate_attendance_trend_report(attendance_df, start_date, end_date):
    """Generate attendance trend analysis report"""
    st.subheader(f"📈 Attendance Trend Report ({start_date} to {end_date})")
    
    if attendance_df.empty:
        st.warning("No attendance data for trend analysis.")
        return
    
    # Daily attendance trends
    daily_attendance = attendance_df.groupby('Date').size().reset_index(name='Count')
    daily_attendance = daily_attendance.sort_values('Date')
    
    # Calculate moving averages
    daily_attendance['7_Day_MA'] = daily_attendance['Count'].rolling(window=7, center=True).mean()
    daily_attendance['14_Day_MA'] = daily_attendance['Count'].rolling(window=14, center=True).mean()
    
    # Trend visualization
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=daily_attendance['Date'],
        y=daily_attendance['Count'],
        mode='markers',
        name='Daily Attendance',
        opacity=0.6
    ))
    
    fig.add_trace(go.Scatter(
        x=daily_attendance['Date'],
        y=daily_attendance['7_Day_MA'],
        mode='lines',
        name='7-Day Average',
        line=dict(width=2)
    ))
    
    fig.add_trace(go.Scatter(
        x=daily_attendance['Date'],
        y=daily_attendance['14_Day_MA'],
        mode='lines',
        name='14-Day Average',
        line=dict(width=2)
    ))
    
    fig.update_layout(
        title="Attendance Trends with Moving Averages",
        xaxis_title="Date",
        yaxis_title="Attendance Count",
        height=500
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Trend statistics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        avg_attendance = daily_attendance['Count'].mean()
        st.metric("Average Daily Attendance", f"{avg_attendance:.1f}")
    
    with col2:
        max_attendance = daily_attendance['Count'].max()
        max_date = daily_attendance[daily_attendance['Count'] == max_attendance]['Date'].iloc[0]
        st.metric("Highest Attendance", max_attendance, delta=f"on {max_date.strftime('%Y-%m-%d')}")
    
    with col3:
        min_attendance = daily_attendance['Count'].min()
        min_date = daily_attendance[daily_attendance['Count'] == min_attendance]['Date'].iloc[0]
        st.metric("Lowest Attendance", min_attendance, delta=f"on {min_date.strftime('%Y-%m-%d')}")
    
    with col4:
        std_attendance = daily_attendance['Count'].std()
        st.metric("Attendance Variability", f"{std_attendance:.1f}")
    
    # Weekly and monthly patterns
    col1, col2 = st.columns(2)
    
    with col1:
        # Day of week analysis
        attendance_df['Day_of_Week'] = attendance_df['Date'].dt.day_name()
        day_counts = attendance_df.groupby('Day_of_Week').size().reset_index(name='Count')
        
        day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        day_counts['Day_of_Week'] = pd.Categorical(day_counts['Day_of_Week'], categories=day_order, ordered=True)
        day_counts = day_counts.sort_values('Day_of_Week')
        
        fig = px.bar(day_counts, x='Day_of_Week', y='Count',
                    title="Attendance by Day of Week",
                    color='Count',
                    color_continuous_scale='viridis')
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Month analysis (if data spans multiple months)
        attendance_df['Month'] = attendance_df['Date'].dt.strftime('%Y-%m')
        month_counts = attendance_df.groupby('Month').size().reset_index(name='Count')
        
        if len(month_counts) > 1:
            fig = px.line(month_counts, x='Month', y='Count',
                         title="Monthly Attendance Trend",
                         markers=True)
            fig.update_layout(
                height=400,
                xaxis={'tickangle': 45}
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Need data spanning multiple months for monthly trend analysis")
    
    # Export trend data using universal export section
    trend_export = daily_attendance.copy()
    trend_export['Date'] = trend_export['Date'].dt.strftime('%Y-%m-%d')
    
    csv_exports = {
        "Attendance Trends": trend_export.to_csv(index=False)
    }
    
    create_universal_export_section(
        attendance_df, pd.DataFrame(), start_date, end_date, 
        "Attendance Trend Report", None, csv_exports
    )


def generate_executive_summary_report(attendance_df, members_df, start_date, end_date):
    """Generate executive summary report"""
    st.subheader(f"📊 Executive Summary ({start_date} to {end_date})")
    
    # Key Performance Indicators
    st.subheader("🎯 Key Performance Indicators")
    
    col1, col2, col3, col4 = st.columns(4)
    
    total_members = len(members_df) if not members_df.empty else 0
    total_attendance = len(attendance_df) if not attendance_df.empty else 0
    unique_attendees = attendance_df['Full Name'].nunique() if not attendance_df.empty else 0
    engagement_rate = (unique_attendees / total_members * 100) if total_members > 0 else 0
    
    with col1:
        st.metric("Total Members", total_members)
    with col2:
        st.metric("Total Attendance Records", total_attendance)
    with col3:
        st.metric("Active Members", unique_attendees)
    with col4:
        st.metric("Overall Engagement", f"{engagement_rate:.1f}%")
    
    # Growth metrics
    if not attendance_df.empty and len(attendance_df) > 14:  # Need at least 2 weeks of data
        st.subheader("📈 Growth Metrics")
        
        # Calculate period-over-period growth
        mid_point = start_date + (end_date - start_date) / 2
        first_half = attendance_df[attendance_df['Date'].dt.date < mid_point]
        second_half = attendance_df[attendance_df['Date'].dt.date >= mid_point]
        
        first_half_avg = len(first_half) / (mid_point - start_date).days if (mid_point - start_date).days > 0 else 0
        second_half_avg = len(second_half) / (end_date - mid_point).days if (end_date - mid_point).days > 0 else 0
        
        growth_rate = ((second_half_avg - first_half_avg) / first_half_avg * 100) if first_half_avg > 0 else 0
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("First Half Avg Daily", f"{first_half_avg:.1f}")
        with col2:
            st.metric("Second Half Avg Daily", f"{second_half_avg:.1f}")
        with col3:
            st.metric("Growth Rate", f"{growth_rate:+.1f}%")
    
    # Summary insights
    st.subheader("🔍 Key Insights")
    
    insights = []
    
    if not attendance_df.empty:
        # Most active day
        day_counts = attendance_df.groupby(attendance_df['Date'].dt.day_name()).size()
        most_active_day = day_counts.idxmax()
        insights.append(f"📅 Most active day: **{most_active_day}** ({day_counts.max()} total attendances)")
        
        # Best performing group
        if 'Group' in attendance_df.columns and not members_df.empty:
            group_performance = []
            for group in attendance_df['Group'].unique():
                group_members = members_df[members_df['Group'] == group] if 'Group' in members_df.columns else pd.DataFrame()
                group_attendance = attendance_df[attendance_df['Group'] == group]
                total_members = len(group_members)
                active_members = group_attendance['Full Name'].nunique()
                participation_rate = (active_members / total_members * 100) if total_members > 0 else 0
                group_performance.append((group, participation_rate))
            
            if group_performance:
                best_group, best_rate = max(group_performance, key=lambda x: x[1])
                insights.append(f"🏆 Best performing group: **{best_group}** ({best_rate:.1f}% participation rate)")
        
        # Attendance consistency
        unique_days = attendance_df['Date'].dt.date.nunique()
        if unique_days > 0:
            avg_daily = total_attendance / unique_days
            insights.append(f"📊 Average daily attendance: **{avg_daily:.1f}** people")
        
        # Member engagement levels
        if unique_attendees > 0:
            total_services = attendance_df['Date'].dt.date.nunique()
            member_attendance_counts = attendance_df.groupby('Full Name').size()
            highly_engaged = sum(member_attendance_counts >= total_services * 0.8)
            insights.append(f"⭐ Highly engaged members (80%+ attendance): **{highly_engaged}** members")
    
    for insight in insights:
        st.markdown(f"• {insight}")
    
    if not insights:
        st.info("Add more attendance data to see detailed insights.")
    
    # Recommendations
    st.subheader("💡 Recommendations")
    recommendations = []
    
    if engagement_rate < 50:
        recommendations.append("📢 Consider outreach programs to increase member engagement")
    if engagement_rate < 75:
        recommendations.append("🎯 Focus on retention strategies for existing active members")
    if not attendance_df.empty:
        # Check for declining trends
        recent_week = attendance_df[attendance_df['Date'].dt.date >= (end_date - timedelta(days=7))]
        earlier_week = attendance_df[
            (attendance_df['Date'].dt.date >= (end_date - timedelta(days=14))) &
            (attendance_df['Date'].dt.date < (end_date - timedelta(days=7)))
        ]
        if len(recent_week) < len(earlier_week) * 0.9:
            recommendations.append("⚠️ Recent attendance decline detected - investigate potential causes")
    
    if not recommendations:
        recommendations.append("✅ Attendance patterns look healthy - continue current strategies")
    
    for rec in recommendations:
        st.markdown(f"• {rec}")
    
    # Export executive summary using universal export section
    csv_exports = {
        "Executive Summary": attendance_df.to_csv(index=False) if not attendance_df.empty else pd.DataFrame().to_csv(index=False)
    }
    
    create_universal_export_section(
        attendance_df, members_df, start_date, end_date, 
        "Executive Summary Report", None, csv_exports
    )


def generate_custom_date_range_report(attendance_df, members_df, start_date, end_date, selected_groups):
    """Generate custom date range report"""
    st.subheader(f"📋 Custom Date Range Report ({start_date} to {end_date})")
    
    # Summary section
    if not attendance_df.empty:
        st.subheader("📊 Period Summary")
        
        col1, col2, col3, col4 = st.columns(4)
        
        total_attendance = len(attendance_df)
        unique_attendees = attendance_df['Full Name'].nunique()
        unique_days = attendance_df['Date'].dt.date.nunique()
        period_length = (end_date - start_date).days + 1
        
        with col1:
            st.metric("Total Attendance", total_attendance)
        with col2:
            st.metric("Unique Attendees", unique_attendees)
        with col3:
            st.metric("Active Days", unique_days)
        with col4:
            st.metric("Period Length", f"{period_length} days")
        
        # Detailed breakdown by selected groups
        if selected_groups and 'Group' in attendance_df.columns:
            st.subheader("👥 Group Breakdown")
            
            group_data = []
            for group in selected_groups:
                group_attendance = attendance_df[attendance_df['Group'] == group]
                group_data.append({
                    'Group': group,
                    'Total Attendance': len(group_attendance),
                    'Unique Members': group_attendance['Full Name'].nunique(),
                    'Avg per Day': len(group_attendance) / unique_days if unique_days > 0 else 0
                })
            
            group_df = pd.DataFrame(group_data)
            st.dataframe(group_df, use_container_width=True, hide_index=True)
        
        # Export comprehensive report using universal export section
        export_data = attendance_df.copy()
        export_data['Date'] = export_data['Date'].dt.strftime('%Y-%m-%d')
        
        csv_exports = {
            "Custom Report": export_data.to_csv(index=False),
            "Group Summary": group_df.to_csv(index=False)
        }
        
        create_universal_export_section(
            attendance_df, members_df, start_date, end_date, 
            "Custom Date Range Report", selected_groups, csv_exports
        )
    else:
        st.warning("No attendance data found for the selected period and groups.")


def show_history():
    """Display attendance history with search and filter capabilities"""
    st.title("📜 Attendance History")
    st.markdown("Search, filter, and manage historical attendance records")
    
    # Load data
    members_df = st.session_state.sheets_manager.load_members()
    attendance_df = st.session_state.sheets_manager.load_attendance()
    
    if attendance_df.empty:
        st.warning("📜 No attendance history available. Start marking attendance to build history!")
        return
    
    # Search and filter controls
    st.subheader("🔍 Search & Filter")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Text search
        search_term = st.text_input(
            "Search by name:",
            placeholder="Enter member name...",
            help="Search for specific members by name"
        )
    
    with col2:
        # Date range filter
        date_range = st.date_input(
            "Date range:",
            value=(attendance_df['Date'].min().date(), attendance_df['Date'].max().date()),
            min_value=attendance_df['Date'].min().date(),
            max_value=attendance_df['Date'].max().date(),
            help="Filter by date range"
        )
    
    with col3:
        # Group filter
        if not members_df.empty and 'Group' in attendance_df.columns:
            available_groups = sorted(attendance_df['Group'].dropna().unique())
            selected_groups = st.multiselect(
                "Filter by groups:",
                options=available_groups,
                default=available_groups,
                help="Select specific groups to view"
            )
        else:
            selected_groups = []
    
    # Additional filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Records per page
        records_per_page = st.selectbox(
            "Records per page:",
            [25, 50, 100, 200, 500],
            index=2
        )
    
    with col2:
        # Sort options
        sort_options = {
            "Date (Newest first)": ("Date", False),
            "Date (Oldest first)": ("Date", True),
            "Name (A-Z)": ("Full Name", True),
            "Name (Z-A)": ("Full Name", False),
            "Group": ("Group", True)
        }
        sort_choice = st.selectbox("Sort by:", list(sort_options.keys()))
        sort_column, sort_ascending = sort_options[sort_choice]
    
    with col3:
        # Quick date filters
        quick_filter = st.selectbox(
            "Quick date filter:",
            ["Custom Range", "Last 7 days", "Last 30 days", "Last 90 days", "This month", "Last month"]
        )
        
        if quick_filter != "Custom Range":
            today = date.today()
            if quick_filter == "Last 7 days":
                date_range = (today - timedelta(days=7), today)
            elif quick_filter == "Last 30 days":
                date_range = (today - timedelta(days=30), today)
            elif quick_filter == "Last 90 days":
                date_range = (today - timedelta(days=90), today)
            elif quick_filter == "This month":
                date_range = (today.replace(day=1), today)
            elif quick_filter == "Last month":
                first_day_this_month = today.replace(day=1)
                last_day_last_month = first_day_this_month - timedelta(days=1)
                first_day_last_month = last_day_last_month.replace(day=1)
                date_range = (first_day_last_month, last_day_last_month)
    
    # Apply filters
    filtered_df = attendance_df.copy()
    
    # Date filter
    if len(date_range) == 2:
        start_date, end_date = date_range
        filtered_df = filtered_df[
            (filtered_df['Date'].dt.date >= start_date) & 
            (filtered_df['Date'].dt.date <= end_date)
        ]
    
    # Group filter
    if selected_groups and 'Group' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['Group'].isin(selected_groups)]
    
    # Name search filter
    if search_term:
        mask = filtered_df['Full Name'].str.contains(search_term, case=False, na=False)
        filtered_df = filtered_df[mask]
    
    # Sort data
    filtered_df = filtered_df.sort_values(sort_column, ascending=sort_ascending)
    
    # Display summary
    st.subheader("📊 Filter Results")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Records", len(filtered_df))
    with col2:
        unique_members = filtered_df['Full Name'].nunique() if not filtered_df.empty else 0
        st.metric("Unique Members", unique_members)
    with col3:
        unique_dates = filtered_df['Date'].dt.date.nunique() if not filtered_df.empty else 0
        st.metric("Unique Dates", unique_dates)
    with col4:
        if not filtered_df.empty:
            date_span = (filtered_df['Date'].max().date() - filtered_df['Date'].min().date()).days + 1
            st.metric("Date Span (Days)", date_span)
        else:
            st.metric("Date Span (Days)", 0)
    
    if filtered_df.empty:
        st.warning("No records match your filter criteria.")
        return
    
    # Pagination
    total_records = len(filtered_df)
    total_pages = (total_records - 1) // records_per_page + 1
    
    if total_pages > 1:
        st.subheader("📄 Pagination")
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col1:
            if st.button("⬅️ Previous", disabled=st.session_state.get('history_page', 1) <= 1):
                st.session_state.history_page = max(1, st.session_state.get('history_page', 1) - 1)
                st.rerun()
        
        with col2:
            page_num = st.selectbox(
                f"Page (of {total_pages}):",
                range(1, total_pages + 1),
                index=st.session_state.get('history_page', 1) - 1,
                key="page_selector"
            )
            if page_num != st.session_state.get('history_page', 1):
                st.session_state.history_page = page_num
                st.rerun()
        
        with col3:
            if st.button("Next ➡️", disabled=st.session_state.get('history_page', 1) >= total_pages):
                st.session_state.history_page = min(total_pages, st.session_state.get('history_page', 1) + 1)
                st.rerun()
    
    # Get current page data
    current_page = st.session_state.get('history_page', 1)
    start_idx = (current_page - 1) * records_per_page
    end_idx = start_idx + records_per_page
    page_df = filtered_df.iloc[start_idx:end_idx].copy()
    
    # Display records
    st.subheader(f"📋 Records ({start_idx + 1}-{min(end_idx, total_records)} of {total_records})")
    
    # Prepare display dataframe
    display_df = page_df.copy()
    display_df['Date'] = display_df['Date'].dt.strftime('%Y-%m-%d')
    if 'Timestamp' in display_df.columns:
        display_df['Time'] = pd.to_datetime(display_df['Timestamp']).dt.strftime('%H:%M:%S')
    
    # Select columns to display
    display_columns = ['Date', 'Full Name', 'Group']
    if 'Membership Number' in display_df.columns:
        display_columns.insert(1, 'Membership Number')
    if 'Time' in display_df.columns:
        display_columns.append('Time')
    
    display_df = display_df[display_columns]
    
    # Display with edit capabilities
    st.dataframe(
        display_df, 
        use_container_width=True, 
        hide_index=True,
        column_config={
            "Date": st.column_config.DateColumn("Date"),
            "Full Name": st.column_config.TextColumn("Full Name"),
            "Group": st.column_config.TextColumn("Group"),
            "Time": st.column_config.TextColumn("Time") if 'Time' in display_columns else None
        }
    )
    
    # Bulk operations
    st.subheader("🔧 Bulk Operations")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📊 Export Filtered Data", use_container_width=True):
            export_df = filtered_df.copy()
            export_df['Date'] = export_df['Date'].dt.strftime('%Y-%m-%d')
            if 'Timestamp' in export_df.columns:
                export_df['Timestamp'] = pd.to_datetime(export_df['Timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
            
            csv_data = export_df.to_csv(index=False)
            st.download_button(
                label="💾 Download CSV",
                data=csv_data,
                file_name=f"attendance_history_{date.today().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
    
    with col2:
        if st.button("📈 Quick Analytics", use_container_width=True):
            st.session_state.selected_page = "📊 Analytics"
            st.rerun()
    
    with col3:
        if st.button("📋 Generate Report", use_container_width=True):
            st.session_state.selected_page = "📋 Reports"
            st.rerun()
    
    with col4:
        if st.button("🗑️ Delete Filtered Records", use_container_width=True, type="secondary"):
            st.session_state.show_bulk_delete = True
            st.rerun()
    
    # Bulk Delete Modal
    if st.session_state.get('show_bulk_delete', False):
        st.divider()
        st.error("⚠️ Bulk Delete Filtered Records")
        
        st.write(f"**You are about to delete {len(filtered_df)} records matching your current filters.**")
        
        if len(filtered_df) > 0:
            # Show a preview of what will be deleted
            preview_df = filtered_df[['Date', 'Full Name', 'Group']].head(10)
            preview_df['Date'] = preview_df['Date'].dt.strftime('%Y-%m-%d')
            
            st.write("**Preview of records to be deleted (showing first 10):**")
            st.dataframe(preview_df, use_container_width=True, hide_index=True)
            
            if len(filtered_df) > 10:
                st.write(f"... and {len(filtered_df) - 10} more records")
        
        st.error("**⚠️ WARNING: This action cannot be undone!**")
        
        # Type confirmation
        st.write("To confirm, type **DELETE** in the box below:")
        confirmation = st.text_input("Confirmation:", key="bulk_delete_confirmation")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🗑️ Delete All Filtered Records", key="confirm_bulk_delete", type="primary", disabled=(confirmation != "DELETE")):
                if confirmation == "DELETE":
                    deleted_count = 0
                    total_to_delete = len(filtered_df)
                    
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    # Delete records one by one
                    for idx, (_, record) in enumerate(filtered_df.iterrows()):
                        record_to_delete = {
                            'Date': record['Date'].strftime('%Y-%m-%d'),
                            'Full Name': record['Full Name'],
                            'Timestamp': record.get('Timestamp', '')
                        }
                        
                        if st.session_state.sheets_manager.delete_attendance_record(record_to_delete):
                            deleted_count += 1
                        
                        # Update progress
                        progress = (idx + 1) / total_to_delete
                        progress_bar.progress(progress)
                        status_text.text(f"Deleted {deleted_count}/{total_to_delete} records...")
                        time.sleep(0.1)  # Small delay to show progress
                    
                    st.success(f"✅ Successfully deleted {deleted_count} out of {total_to_delete} records!")
                    st.session_state.show_bulk_delete = False
                    time.sleep(2)
                    st.rerun()
                else:
                    st.error("Please type DELETE to confirm")
        
        with col2:
            if st.button("❌ Cancel", key="cancel_bulk_delete"):
                st.session_state.show_bulk_delete = False
                st.rerun()
    
    # Record details expander
    if not page_df.empty:
        st.subheader("🔍 Record Details")
        
        selected_record = st.selectbox(
            "Select a record to view details:",
            options=range(len(page_df)),
            format_func=lambda x: f"{page_df.iloc[x]['Date'].strftime('%Y-%m-%d')} - {page_df.iloc[x]['Full Name']} ({page_df.iloc[x]['Group']})"
        )
        
        if selected_record is not None:
            record = page_df.iloc[selected_record]
            
            with st.expander(f"📝 Details for {record['Full Name']} on {record['Date'].strftime('%Y-%m-%d')}", expanded=True):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Member Information:**")
                    st.write(f"• **Name:** {record['Full Name']}")
                    st.write(f"• **Group:** {record['Group']}")
                    if 'Membership Number' in record and pd.notna(record['Membership Number']):
                        st.write(f"• **Membership Number:** {record['Membership Number']}")
                
                with col2:
                    st.write("**Attendance Information:**")
                    st.write(f"• **Date:** {record['Date'].strftime('%Y-%m-%d')}")
                    st.write(f"• **Day of Week:** {record['Date'].strftime('%A')}")
                    if 'Timestamp' in record and pd.notna(record['Timestamp']):
                        timestamp = pd.to_datetime(record['Timestamp'])
                        st.write(f"• **Time Recorded:** {timestamp.strftime('%H:%M:%S')}")
                    st.write(f"• **Status:** Present")
                
                # Member's attendance history
                member_history = attendance_df[attendance_df['Full Name'] == record['Full Name']].copy()
                if len(member_history) > 1:
                    st.write("**Member's Attendance History:**")
                    member_history = member_history.sort_values('Date', ascending=False).head(10)
                    member_history['Date'] = member_history['Date'].dt.strftime('%Y-%m-%d')
                    st.dataframe(
                        member_history[['Date', 'Group']],
                        use_container_width=True,
                        hide_index=True
                    )
                
                # Edit/Delete options
                st.write("**Actions:**")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✏️ Edit Record", key=f"edit_{selected_record}"):
                        st.session_state[f'editing_record_{selected_record}'] = True
                        st.rerun()
                with col2:
                    if st.button("🗑️ Delete Record", key=f"delete_{selected_record}", type="secondary"):
                        st.session_state[f'deleting_record_{selected_record}'] = True
                        st.rerun()
                
                # Edit Record Modal
                if st.session_state.get(f'editing_record_{selected_record}', False):
                    st.divider()
                    st.subheader("✏️ Edit Attendance Record")
                    
                    with st.form(f"edit_form_{selected_record}"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            # Get member options for dropdown
                            members_df = st.session_state.sheets_manager.load_members()
                            member_options = sorted(members_df['Full Name'].unique()) if not members_df.empty else [record['Full Name']]
                            
                            edit_name = st.selectbox(
                                "Member Name:",
                                options=member_options,
                                index=member_options.index(record['Full Name']) if record['Full Name'] in member_options else 0
                            )
                            
                            edit_date = st.date_input(
                                "Date:",
                                value=record['Date'].date(),
                                key=f"edit_date_{selected_record}"
                            )
                        
                        with col2:
                            # Get group options
                            group_options = sorted(members_df['Group'].unique()) if not members_df.empty else [record['Group']]
                            edit_group = st.selectbox(
                                "Group:",
                                options=group_options,
                                index=group_options.index(record['Group']) if record['Group'] in group_options else 0
                            )
                            
                            edit_membership_number = st.text_input(
                                "Membership Number:",
                                value=str(record.get('Membership Number', '')),
                                key=f"edit_membership_{selected_record}"
                            )
                        
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            submitted = st.form_submit_button("💾 Save Changes", type="primary")
                        with col2:
                            if st.form_submit_button("❌ Cancel"):
                                st.session_state[f'editing_record_{selected_record}'] = False
                                st.rerun()
                        
                        if submitted:
                            # Create updated record
                            original_record = {
                                'Date': record['Date'].strftime('%Y-%m-%d'),
                                'Full Name': record['Full Name'],
                                'Timestamp': record.get('Timestamp', '')
                            }
                            
                            updated_record = {
                                'Date': edit_date.strftime('%Y-%m-%d'),
                                'Membership Number': edit_membership_number,
                                'Full Name': edit_name,
                                'Group': edit_group,
                                'Status': 'Present',
                                'Timestamp': record.get('Timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                            }
                            
                            # Update the record
                            if st.session_state.sheets_manager.update_attendance_record(original_record, updated_record):
                                st.success("✅ Record updated successfully!")
                                st.session_state[f'editing_record_{selected_record}'] = False
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error("❌ Failed to update record")
                
                # Delete Record Modal
                if st.session_state.get(f'deleting_record_{selected_record}', False):
                    st.divider()
                    st.error("⚠️ Delete Attendance Record")
                    st.write(f"Are you sure you want to delete the attendance record for **{record['Full Name']}** on **{record['Date'].strftime('%Y-%m-%d')}**?")
                    st.write("This action cannot be undone.")
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        if st.button("🗑️ Yes, Delete", key=f"confirm_delete_{selected_record}", type="primary"):
                            # Create record identifier
                            record_to_delete = {
                                'Date': record['Date'].strftime('%Y-%m-%d'),
                                'Full Name': record['Full Name'],
                                'Timestamp': record.get('Timestamp', '')
                            }
                            
                            # Delete the record
                            if st.session_state.sheets_manager.delete_attendance_record(record_to_delete):
                                st.success("✅ Record deleted successfully!")
                                st.session_state[f'deleting_record_{selected_record}'] = False
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error("❌ Failed to delete record")
                    
                    with col2:
                        if st.button("❌ Cancel", key=f"cancel_delete_{selected_record}"):
                            st.session_state[f'deleting_record_{selected_record}'] = False
                            st.rerun()


def show_admin_panel():
    """Display comprehensive admin panel with system management tools"""
    st.title("🔧 Admin Panel")
    st.markdown("System administration, data management, and maintenance tools")
    
    # System Status Section
    st.subheader("🖥️ System Status")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        status = "🟢 Connected" if st.session_state.sheets_manager.connection_status else "🔴 Disconnected"
        st.metric("Connection Status", status)
    
    with col2:
        cache_size = len(st.session_state.sheets_manager.cache)
        st.metric("Cache Entries", cache_size)
    
    with col3:
        # Calculate cache age
        if st.session_state.sheets_manager.cache:
            oldest_cache = min(time.time() - cached_time for cached_time, _ in st.session_state.sheets_manager.cache.values())
            cache_age = f"{int(oldest_cache // 60)}m {int(oldest_cache % 60)}s"
        else:
            cache_age = "No cache"
        st.metric("Oldest Cache", cache_age)
    
    with col4:
        # Memory usage approximation
        cache_memory = sum(len(str(data)) for _, data in st.session_state.sheets_manager.cache.values())
        memory_mb = cache_memory / (1024 * 1024)
        st.metric("Cache Memory", f"{memory_mb:.2f} MB")
    
    # System Actions
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 Refresh Connection", use_container_width=True):
            with st.spinner("Reconnecting to Google Sheets..."):
                # Force a fresh connection by resetting the status first
                st.session_state.sheets_manager.connection_status = False
                if st.session_state.sheets_manager.initialize_connection():
                    st.session_state.sheets_manager.setup_worksheets()
                    st.success("✅ Connection refreshed successfully!")
                else:
                    st.error("❌ Failed to refresh connection")
                st.rerun()
    
    with col2:
        if st.button("🗑️ Clear All Cache", use_container_width=True):
            st.session_state.sheets_manager.clear_cache()
            st.success("🧹 All cache cleared!")
            st.rerun()
    
    with col3:
        if st.button("📊 Force Data Refresh", use_container_width=True):
            with st.spinner("Refreshing all data..."):
                st.session_state.sheets_manager.clear_cache()
                members_df = st.session_state.sheets_manager.load_members(use_cache=False)
                attendance_df = st.session_state.sheets_manager.load_attendance(use_cache=False)
                st.success("📈 Data refreshed from Google Sheets!")
    
    st.divider()
    
    # Data Management Section
    st.subheader("📊 Data Management")
    
    # Load fresh data for accurate statistics
    members_df = st.session_state.sheets_manager.load_members(use_cache=False)
    attendance_df = st.session_state.sheets_manager.load_attendance(use_cache=False)
    
    # Data statistics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Members", len(members_df) if not members_df.empty else 0)
    
    with col2:
        st.metric("Attendance Records", len(attendance_df) if not attendance_df.empty else 0)
    
    with col3:
        if not attendance_df.empty:
            unique_attendees = attendance_df['Full Name'].nunique()
            st.metric("Active Members", unique_attendees)
        else:
            st.metric("Active Members", 0)
    
    with col4:
        if not attendance_df.empty:
            date_range = (attendance_df['Date'].max() - attendance_df['Date'].min()).days
            st.metric("Data Span (Days)", date_range)
        else:
            st.metric("Data Span (Days)", 0)
    
    # Data Quality Checks
    st.subheader("🔍 Data Quality Analysis")
    
    issues = []
    
    if not members_df.empty:
        # Check for duplicate members
        duplicate_members = members_df[members_df.duplicated(subset=['Full Name', 'Group'], keep=False)]
        if not duplicate_members.empty:
            issues.append(f"⚠️ Found {len(duplicate_members)} potential duplicate member records")
        
        # Check for missing required fields
        missing_names = members_df['Full Name'].isna().sum()
        if missing_names > 0:
            issues.append(f"⚠️ Found {missing_names} members with missing names")
        
        missing_groups = members_df['Group'].isna().sum() if 'Group' in members_df.columns else 0
        if missing_groups > 0:
            issues.append(f"⚠️ Found {missing_groups} members with missing groups")
    
    if not attendance_df.empty:
        # Check for orphaned attendance records (members not in members list)
        if not members_df.empty:
            member_names = set(members_df['Full Name'].dropna())
            attendance_names = set(attendance_df['Full Name'].dropna())
            orphaned = attendance_names - member_names
            if orphaned:
                issues.append(f"⚠️ Found {len(orphaned)} attendance records for members not in member list")
        
        # Check for invalid dates
        future_dates = attendance_df[attendance_df['Date'].dt.date > date.today()]
        if not future_dates.empty:
            issues.append(f"⚠️ Found {len(future_dates)} attendance records with future dates")
        
        # Check for duplicate attendance records
        duplicate_attendance = attendance_df[
            attendance_df.duplicated(subset=['Date', 'Full Name'], keep=False)
        ]
        if not duplicate_attendance.empty:
            issues.append(f"⚠️ Found {len(duplicate_attendance)} potential duplicate attendance records")
    
    if issues:
        st.warning("Data Quality Issues Found:")
        for issue in issues:
            st.markdown(f"• {issue}")
    else:
        st.success("✅ No data quality issues detected!")
    
    # Bulk Operations Section
    st.subheader("⚙️ Bulk Operations")
    
    tab1, tab2, tab3, tab4 = st.tabs(["Data Export", "Data Import", "Data Cleanup", "Maintenance"])
    
    with tab1:
        st.subheader("📤 Export Data")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Members Data**")
            if not members_df.empty:
                csv_members = members_df.to_csv(index=False)
                st.download_button(
                    label="📥 Download Members CSV",
                    data=csv_members,
                    file_name=f"members_export_{date.today().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
                
                # JSON export
                json_members = members_df.to_json(orient='records', indent=2)
                st.download_button(
                    label="📥 Download Members JSON",
                    data=json_members,
                    file_name=f"members_export_{date.today().strftime('%Y%m%d')}.json",
                    mime="application/json",
                    use_container_width=True
                )
            else:
                st.info("No member data to export")
        
        with col2:
            st.write("**Attendance Data**")
            if not attendance_df.empty:
                export_attendance = attendance_df.copy()
                export_attendance['Date'] = export_attendance['Date'].dt.strftime('%Y-%m-%d')
                if 'Timestamp' in export_attendance.columns:
                    export_attendance['Timestamp'] = pd.to_datetime(export_attendance['Timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
                
                csv_attendance = export_attendance.to_csv(index=False)
                st.download_button(
                    label="📥 Download Attendance CSV",
                    data=csv_attendance,
                    file_name=f"attendance_export_{date.today().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
                
                # JSON export
                json_attendance = export_attendance.to_json(orient='records', indent=2)
                st.download_button(
                    label="📥 Download Attendance JSON",
                    data=json_attendance,
                    file_name=f"attendance_export_{date.today().strftime('%Y%m%d')}.json",
                    mime="application/json",
                    use_container_width=True
                )
            else:
                st.info("No attendance data to export")
        
        # Combined export
        st.write("**Combined Export**")
        if not members_df.empty and not attendance_df.empty:
            if st.button("📦 Generate Complete Backup", use_container_width=True):
                # Create a comprehensive backup
                backup_data = {
                    "export_date": date.today().isoformat(),
                    "members": members_df.to_dict(orient='records'),
                    "attendance": export_attendance.to_dict(orient='records'),
                    "statistics": {
                        "total_members": len(members_df),
                        "total_attendance_records": len(attendance_df),
                        "date_range": {
                            "start": attendance_df['Date'].min().strftime('%Y-%m-%d') if not attendance_df.empty else None,
                            "end": attendance_df['Date'].max().strftime('%Y-%m-%d') if not attendance_df.empty else None
                        }
                    }
                }
                
                backup_json = json.dumps(backup_data, indent=2)
                st.download_button(
                    label="💾 Download Complete Backup",
                    data=backup_json,
                    file_name=f"church_attendance_backup_{date.today().strftime('%Y%m%d')}.json",
                    mime="application/json"
                )
    
    with tab2:
        st.subheader("📥 Import Data")
        
        st.warning("⚠️ Import functionality is not yet implemented for safety reasons.")
        st.markdown("""
        **Coming Soon:**
        - CSV file import with validation
        - Data mapping and transformation
        - Duplicate detection during import
        - Preview and confirm before saving
        """)
        
        # Placeholder for future import functionality
        uploaded_file = st.file_uploader(
            "Choose a CSV file",
            type="csv",
            help="Feature coming soon - files uploaded here won't be processed yet"
        )
        
        if uploaded_file is not None:
            st.info("📝 File received but import processing is not yet implemented")
    
    with tab3:
        st.subheader("🧹 Data Cleanup Tools")
        
        if st.button("🔍 Analyze Data Quality", use_container_width=True):
            st.success("Data quality analysis completed (see results above)")
        
        st.warning("⚠️ Cleanup operations are not yet implemented for safety reasons.")
        st.markdown("""
        **Planned Cleanup Features:**
        - Remove duplicate records
        - Fix data formatting issues
        - Merge similar member names
        - Archive old records
        """)
        
        # Show problematic records if any
        if not members_df.empty:
            duplicate_members = members_df[members_df.duplicated(subset=['Full Name', 'Group'], keep=False)]
            if not duplicate_members.empty:
                st.subheader("🔍 Potential Duplicate Members")
                st.dataframe(duplicate_members.sort_values(['Full Name', 'Group']), use_container_width=True)
        
        if not attendance_df.empty and not members_df.empty:
            member_names = set(members_df['Full Name'].dropna())
            attendance_names = set(attendance_df['Full Name'].dropna())
            orphaned = attendance_names - member_names
            if orphaned:
                st.subheader("⚠️ Orphaned Attendance Records")
                orphaned_records = attendance_df[attendance_df['Full Name'].isin(orphaned)]
                st.dataframe(
                    orphaned_records[['Date', 'Full Name', 'Group']].head(20),
                    use_container_width=True
                )
                if len(orphaned_records) > 20:
                    st.info(f"... and {len(orphaned_records) - 20} more records")
    
    with tab4:
        st.subheader("🔧 System Maintenance")
        
        # Cache management
        st.write("**Cache Management**")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🗑️ Clear Members Cache", use_container_width=True):
                # Clear only members-related cache
                keys_to_remove = [key for key in st.session_state.sheets_manager.cache.keys() if 'load_members' in key]
                for key in keys_to_remove:
                    del st.session_state.sheets_manager.cache[key]
                st.success("Members cache cleared!")
        
        with col2:
            if st.button("🗑️ Clear Attendance Cache", use_container_width=True):
                # Clear only attendance-related cache
                keys_to_remove = [key for key in st.session_state.sheets_manager.cache.keys() if 'load_attendance' in key]
                for key in keys_to_remove:
                    del st.session_state.sheets_manager.cache[key]
                st.success("Attendance cache cleared!")
        
        with col3:
            if st.button("🔄 Reset All Session Data", use_container_width=True):
                # Clear all session state except the sheets manager
                sheets_manager = st.session_state.sheets_manager
                st.session_state.clear()
                st.session_state.sheets_manager = sheets_manager
                st.success("Session data reset!")
                st.rerun()
        
        # Performance monitoring
        st.write("**Performance Monitoring**")
        
        # Show recent API call timing if available
        if hasattr(st.session_state.sheets_manager, '_last_call_times'):
            st.info("API call timing data would be displayed here (feature coming soon)")
        
        # System diagnostics
        st.write("**System Diagnostics**")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🩺 Run Connection Test", use_container_width=True):
                with st.spinner("Testing connection..."):
                    try:
                        test_result = st.session_state.sheets_manager.initialize_connection()
                        if test_result:
                            st.success("✅ Connection test passed!")
                        else:
                            st.error("❌ Connection test failed!")
                    except Exception as e:
                        st.error(f"❌ Connection test error: {str(e)}")
        
        with col2:
            if st.button("🔍 Check Data Integrity", use_container_width=True):
                with st.spinner("Checking data integrity..."):
                    integrity_issues = 0
                    
                    # Check if all required worksheets exist
                    try:
                        members_test = st.session_state.sheets_manager.load_members(use_cache=False)
                        attendance_test = st.session_state.sheets_manager.load_attendance(use_cache=False)
                        st.success("✅ Data integrity check passed!")
                    except Exception as e:
                        st.error(f"❌ Data integrity issues found: {str(e)}")
                        integrity_issues += 1
    
    # System Information
    st.divider()
    st.subheader("ℹ️ System Information")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Application Info**")
        st.write("• **Version:** Church Attendance System v1.0")
        st.write("• **Framework:** Streamlit")
        st.write("• **Storage:** Google Sheets")
        st.write("• **Cache Timeout:** 5 minutes")
    
    with col2:
        st.write("**Current Session**")
        st.write(f"• **Session Started:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        st.write(f"• **Cache Entries:** {len(st.session_state.sheets_manager.cache)}")
        st.write(f"• **Connection Status:** {'Active' if st.session_state.sheets_manager.connection_status else 'Inactive'}")
        st.write(f"• **Rate Limiting:** Active")


# PDF Generation Functions
def create_pdf_report(report_data: dict, report_type: str) -> bytes:
    """Create a PDF report from report data"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.darkblue,
        spaceAfter=30,
        alignment=1  # Center alignment
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.darkgreen,
        spaceAfter=12
    )
    
    # Header with church info
    story.append(Paragraph("⛪ Church Attendance Management System", title_style))
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"{report_type}", subtitle_style))
    story.append(Paragraph(f"Generated on: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", styles['Normal']))
    story.append(Spacer(1, 20))
    
    # Report period
    if 'period' in report_data:
        story.append(Paragraph(f"<b>Report Period:</b> {report_data['period']}", styles['Normal']))
        story.append(Spacer(1, 12))
    
    # Key metrics section
    if 'metrics' in report_data:
        story.append(Paragraph("📊 Key Metrics", subtitle_style))
        metrics_data = []
        for metric_name, metric_value in report_data['metrics'].items():
            metrics_data.append([metric_name, str(metric_value)])
        
        metrics_table = Table(metrics_data, colWidths=[3*inch, 2*inch])
        metrics_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(metrics_table)
        story.append(Spacer(1, 20))
    
    # Detailed data tables
    if 'tables' in report_data:
        for table_name, table_data in report_data['tables'].items():
            story.append(Paragraph(f"📋 {table_name}", subtitle_style))
            
            if isinstance(table_data, pd.DataFrame) and not table_data.empty:
                # Convert DataFrame to table data
                table_rows = [list(table_data.columns)]
                table_rows.extend(table_data.values.tolist())
                
                # Create table
                pdf_table = Table(table_rows)
                pdf_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('FONTSIZE', (0, 1), (-1, -1), 8),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
                ]))
                story.append(pdf_table)
            else:
                story.append(Paragraph("No data available for this section.", styles['Normal']))
            
            story.append(Spacer(1, 15))
    
    # Summary and insights
    if 'summary' in report_data:
        story.append(Paragraph("📝 Summary & Insights", subtitle_style))
        for insight in report_data['summary']:
            story.append(Paragraph(f"• {insight}", styles['Normal']))
        story.append(Spacer(1, 15))
    
    # Footer
    story.append(Spacer(1, 30))
    story.append(Paragraph("This report was automatically generated by the Church Attendance Management System.", 
                          styles['Italic']))
    
    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


def generate_printable_report_html(report_data: dict, report_type: str) -> str:
    """Generate HTML for printable reports with proper styling"""
    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{report_type}</title>
        <style>
            @media print {{
                .no-print {{ display: none; }}
                body {{ margin: 0.5in; }}
            }}
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
            }}
            .header {{
                text-align: center;
                border-bottom: 2px solid #4CAF50;
                padding-bottom: 20px;
                margin-bottom: 30px;
            }}
            .header h1 {{
                color: #2E7D32;
                margin: 0;
                font-size: 24px;
            }}
            .header h2 {{
                color: #666;
                margin: 5px 0;
                font-size: 18px;
            }}
            .metrics-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin: 20px 0;
            }}
            .metric-card {{
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 15px;
                text-align: center;
                background-color: #f9f9f9;
            }}
            .metric-value {{
                font-size: 24px;
                font-weight: bold;
                color: #2E7D32;
            }}
            .metric-label {{
                font-size: 14px;
                color: #666;
                margin-top: 5px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
            }}
            th, td {{
                border: 1px solid #ddd;
                padding: 8px;
                text-align: left;
            }}
            th {{
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
            }}
            tr:nth-child(even) {{
                background-color: #f2f2f2;
            }}
            .section-title {{
                color: #2E7D32;
                border-bottom: 1px solid #4CAF50;
                padding-bottom: 5px;
                margin: 25px 0 15px 0;
            }}
            .summary-list {{
                background-color: #f0f8f0;
                padding: 15px;
                border-radius: 5px;
                margin: 15px 0;
            }}
            .summary-list ul {{
                margin: 0;
                padding-left: 20px;
            }}
            .footer {{
                margin-top: 40px;
                padding-top: 20px;
                border-top: 1px solid #ddd;
                text-align: center;
                font-size: 12px;
                color: #666;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>⛪ Church Attendance Management System</h1>
            <h2>{report_type}</h2>
            <p><strong>Generated on:</strong> {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
            {'<p><strong>Report Period:</strong> ' + report_data.get('period', 'N/A') + '</p>' if 'period' in report_data else ''}
        </div>
    """
    
    # Add metrics section
    if 'metrics' in report_data:
        html_template += """
        <h3 class="section-title">📊 Key Metrics</h3>
        <div class="metrics-grid">
        """
        for metric_name, metric_value in report_data['metrics'].items():
            html_template += f"""
            <div class="metric-card">
                <div class="metric-value">{metric_value}</div>
                <div class="metric-label">{metric_name}</div>
            </div>
            """
        html_template += "</div>"
    
    # Add tables section
    if 'tables' in report_data:
        for table_name, table_data in report_data['tables'].items():
            html_template += f"""<h3 class="section-title">📋 {table_name}</h3>"""
            
            if isinstance(table_data, pd.DataFrame) and not table_data.empty:
                html_template += table_data.to_html(classes='', table_id='', escape=False, index=False)
            else:
                html_template += "<p>No data available for this section.</p>"
    
    # Add summary section
    if 'summary' in report_data:
        html_template += """
        <h3 class="section-title">📝 Summary & Insights</h3>
        <div class="summary-list">
            <ul>
        """
        for insight in report_data['summary']:
            html_template += f"<li>{insight}</li>"
        html_template += "</ul></div>"
    
    # Footer
    html_template += """
        <div class="footer">
            <p>This report was automatically generated by the Church Attendance Management System.</p>
        </div>
    </body>
    </html>
    """
    
    return html_template


def send_report_email(recipient_email: str, report_data: dict, report_type: str, 
                     attachment_type: str = 'pdf') -> bool:
    """Send report via email with PDF or HTML attachment"""
    try:
        # Email configuration - these should be set in Streamlit secrets
        smtp_server = st.secrets.get("email", {}).get("smtp_server", "smtp.gmail.com")
        smtp_port = st.secrets.get("email", {}).get("smtp_port", 587)
        sender_email = st.secrets.get("email", {}).get("sender_email", "")
        sender_password = st.secrets.get("email", {}).get("sender_password", "")
        
        if not sender_email or not sender_password:
            st.error("Email configuration not found in secrets. Please configure email settings.")
            return False
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = f"Church Attendance Report - {report_type}"
        
        # Email body
        body = f"""
Dear Team,

Please find attached the {report_type} generated from the Church Attendance Management System.

Report Details:
- Type: {report_type}
- Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}
- Period: {report_data.get('period', 'N/A')}

Best regards,
Church Attendance Management System
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Create and attach report
        if attachment_type == 'pdf':
            pdf_bytes = create_pdf_report(report_data, report_type)
            attachment = MIMEBase('application', 'octet-stream')
            attachment.set_payload(pdf_bytes)
            encoders.encode_base64(attachment)
            attachment.add_header(
                'Content-Disposition',
                f'attachment; filename="{report_type.replace(" ", "_")}.pdf"'
            )
        else:  # HTML
            html_content = generate_printable_report_html(report_data, report_type)
            attachment = MIMEText(html_content, 'html')
            attachment.add_header(
                'Content-Disposition',
                f'attachment; filename="{report_type.replace(" ", "_")}.html"'
            )
        
        msg.attach(attachment)
        
        # Send email
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, recipient_email, text)
        server.quit()
        
        return True
        
    except Exception as e:
        st.error(f"Failed to send email: {str(e)}")
        return False


def create_universal_export_section(attendance_df: pd.DataFrame, members_df: pd.DataFrame, 
                                   start_date: date, end_date: date, report_type: str,
                                   selected_groups: List[str] = None, additional_csv_data: dict = None):
    """Create a universal export section for all report types"""
    st.subheader("📤 Export & Share Report")
    
    # Create unique identifier for this export section
    section_id = hash(f"{report_type}_{start_date}_{end_date}_{str(selected_groups)}")
    
    # Enhanced export options
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # CSV export
        if additional_csv_data:
            main_csv = list(additional_csv_data.values())[0]
            main_filename = list(additional_csv_data.keys())[0]
        else:
            main_csv = attendance_df.to_csv(index=False)
            main_filename = f"{report_type.lower().replace(' ', '_')}"
        
        st.download_button(
            label="📊 Download CSV",
            data=main_csv,
            file_name=f"{main_filename}_{start_date.strftime('%Y_%m_%d')}.csv",
            mime="text/csv",
            key=f"csv_main_{section_id}"
        )
    
    with col2:
        # PDF export - generate and store in session state
        pdf_key = f"pdf_data_{section_id}"
        
        if st.button("📄 Generate PDF", key=f"pdf_btn_{section_id}", use_container_width=True):
            try:
                with st.spinner("Generating PDF..."):
                    # Extract report data
                    pdf_report_data = extract_report_data_for_pdf(
                        attendance_df, members_df, start_date, end_date, 
                        report_type, selected_groups
                    )
                    
                    # Create PDF
                    pdf_bytes = create_pdf_report(pdf_report_data, report_type)
                    
                    # Store in session state
                    st.session_state[pdf_key] = pdf_bytes
                    st.success(f"✅ PDF generated successfully! ({len(pdf_bytes)} bytes)")
                    
            except Exception as e:
                st.error(f"❌ Error generating PDF: {str(e)}")
                import traceback
                st.code(traceback.format_exc())
        
        # Show download button if PDF exists
        if pdf_key in st.session_state:
            st.download_button(
                label="📥 Download PDF Report",
                data=st.session_state[pdf_key],
                file_name=f"{report_type.replace(' ', '_')}_{start_date.strftime('%Y_%m_%d')}.pdf",
                mime="application/pdf",
                key=f"download_pdf_{section_id}",
                use_container_width=True
            )
    
    with col3:
        # HTML export - generate and store in session state
        html_key = f"html_data_{section_id}"
        
        if st.button("🖨️ Generate HTML", key=f"html_btn_{section_id}", use_container_width=True):
            try:
                with st.spinner("Generating printable HTML..."):
                    # Extract report data
                    pdf_report_data = extract_report_data_for_pdf(
                        attendance_df, members_df, start_date, end_date, 
                        report_type, selected_groups
                    )
                    
                    # Create HTML
                    html_content = generate_printable_report_html(pdf_report_data, report_type)
                    
                    # Store in session state
                    st.session_state[html_key] = html_content
                    st.success(f"✅ HTML generated successfully! ({len(html_content)} characters)")
                    
            except Exception as e:
                st.error(f"❌ Error generating HTML: {str(e)}")
                import traceback
                st.code(traceback.format_exc())
        
        # Show download button if HTML exists
        if html_key in st.session_state:
            st.download_button(
                label="📥 Download HTML (Printable)",
                data=st.session_state[html_key],
                file_name=f"{report_type.replace(' ', '_')}_{start_date.strftime('%Y_%m_%d')}_Printable.html",
                mime="text/html",
                key=f"download_html_{section_id}",
                use_container_width=True
            )
            
            # Show preview
            with st.expander("📋 Preview Printable Report"):
                st.components.v1.html(st.session_state[html_key], height=400, scrolling=True)
    
    with col4:
        # Email functionality - simple approach
        st.write("**📧 Email Report**")
        
        with st.form(f"email_form_{section_id}"):
            recipient_email = st.text_input(
                "Recipient Email",
                placeholder="pastor@church.org"
            )
            
            email_format = st.selectbox(
                "Format",
                ["PDF Attachment", "HTML Attachment"]
            )
            
            if st.form_submit_button("📧 Send Report", type="primary", use_container_width=True):
                if recipient_email:
                    try:
                        with st.spinner("Generating and sending report..."):
                            st.info("Step 1: Extracting report data...")
                            # Extract report data
                            pdf_report_data = extract_report_data_for_pdf(
                                attendance_df, members_df, start_date, end_date, 
                                report_type, selected_groups
                            )
                            
                            st.info("Step 2: Checking email configuration...")
                            # Check if email is configured
                            if not hasattr(st.secrets, "email") or not st.secrets.get("email", {}):
                                st.error("❌ Email not configured! Please add email settings to .streamlit/secrets.toml")
                                st.code("""
# Add this to .streamlit/secrets.toml:
[email]
smtp_server = "smtp.gmail.com"
smtp_port = 587
sender_email = "your-email@gmail.com" 
sender_password = "your-app-password"
                                """)
                                return
                            
                            st.info("Step 3: Sending email...")
                            # Send email
                            attachment_type = 'pdf' if email_format == "PDF Attachment" else 'html'
                            
                            if send_report_email(recipient_email, pdf_report_data, 
                                               report_type, attachment_type):
                                st.success(f"✅ Report emailed successfully to {recipient_email}!")
                            else:
                                st.error("❌ Failed to send email. Check email configuration.")
                                
                    except Exception as e:
                        st.error(f"❌ Error sending email: {str(e)}")
                        import traceback
                        st.code(traceback.format_exc())
                else:
                    st.error("❌ Please enter a recipient email address.")
    
    # Additional data exports if provided
    if additional_csv_data and len(additional_csv_data) > 1:
        st.markdown("---")
        st.subheader("📊 Additional Data Exports")
        cols = st.columns(min(len(additional_csv_data) - 1, 3))
        
        for idx, (name, csv_data) in enumerate(list(additional_csv_data.items())[1:]):
            if idx < len(cols):
                with cols[idx]:
                    st.download_button(
                        label=f"📊 {name}",
                        data=csv_data,
                        file_name=f"{name.lower().replace(' ', '_')}_{start_date.strftime('%Y_%m_%d')}.csv",
                        mime="text/csv",
                        key=f"csv_{name}_{section_id}"
                    )


def extract_report_data_for_pdf(attendance_df: pd.DataFrame, members_df: pd.DataFrame, 
                               start_date: date, end_date: date, report_type: str,
                               selected_groups: List[str] = None) -> dict:
    """Extract and structure report data for PDF generation"""
    report_data = {
        'period': f"{start_date.strftime('%B %d, %Y')} - {end_date.strftime('%B %d, %Y')}",
        'metrics': {},
        'tables': {},
        'summary': []
    }
    
    if attendance_df.empty:
        report_data['summary'] = ["No attendance data available for the selected period."]
        return report_data
    
    # Common metrics
    total_attendance = len(attendance_df)
    unique_attendees = attendance_df['Full Name'].nunique()
    unique_days = attendance_df['Date'].dt.date.nunique()
    avg_daily_attendance = total_attendance / unique_days if unique_days > 0 else 0
    
    report_data['metrics'] = {
        'Total Attendance Records': total_attendance,
        'Unique Attendees': unique_attendees,
        'Active Days': unique_days,
        'Average Daily Attendance': f"{avg_daily_attendance:.1f}"
    }
    
    # Daily breakdown
    daily_attendance = attendance_df.groupby(attendance_df['Date'].dt.date).size().reset_index(name='Count')
    daily_attendance.columns = ['Date', 'Attendance Count']
    daily_attendance['Date'] = daily_attendance['Date'].astype(str)
    report_data['tables']['Daily Attendance Breakdown'] = daily_attendance
    
    # Group performance if available
    if 'Group' in attendance_df.columns and not attendance_df['Group'].isna().all():
        group_summary = attendance_df.groupby('Group').agg({
            'Full Name': 'nunique',
            'Date': 'count'
        }).reset_index()
        group_summary.columns = ['Group', 'Unique Members', 'Total Attendance']
        report_data['tables']['Group Performance'] = group_summary
    
    # Top attendees
    top_attendees = attendance_df.groupby(['Full Name', 'Group']).size().reset_index(name='Attendance Count')
    top_attendees = top_attendees.sort_values('Attendance Count', ascending=False).head(10)
    report_data['tables']['Top 10 Attendees'] = top_attendees
    
    # Generate summary insights
    if unique_days > 0:
        participation_rate = (unique_attendees / len(members_df)) * 100 if not members_df.empty else 0
        
        summary_insights = [
            f"Total of {total_attendance} attendance records were recorded over {unique_days} active days",
            f"Average daily attendance was {avg_daily_attendance:.1f} people",
            f"Participation rate: {participation_rate:.1f}% of registered members attended during this period"
        ]
        
        if 'Group' in attendance_df.columns:
            most_active_group = attendance_df['Group'].value_counts().index[0] if len(attendance_df['Group'].value_counts()) > 0 else 'N/A'
            summary_insights.append(f"Most active group: {most_active_group}")
        
        report_data['summary'] = summary_insights
    
    return report_data


if __name__ == "__main__":
    main()