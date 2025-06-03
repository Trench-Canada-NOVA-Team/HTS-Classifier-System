import sqlite3
import streamlit as st
import uuid
from datetime import datetime
import sys
from pathlib import Path

# Add parent directory to path for database imports
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

try:
    from database.db_setup import get_db_connection, create_database
except:
    # If import fails, create dummy functions
    def get_db_connection():
        return None
    def create_database():
        return None

class SimpleLogger:
    def __init__(self):
        try:
            create_database()
            if 'session_id' not in st.session_state:
                st.session_state.session_id = str(uuid.uuid4())
            if 'user_id' not in st.session_state:
                st.session_state.user_id = None
        except:
            pass
    
    def start_user_session(self, email):
        """Start tracking user session"""
        try:
            if not email or "@" not in email:
                return
            
            conn = get_db_connection()
            if not conn:
                return
                
            cursor = conn.cursor()
            
            # Get or create user
            cursor.execute('SELECT id FROM users WHERE email = ?', (email,))
            result = cursor.fetchone()
            
            if result:
                user_id = result[0]
                cursor.execute('UPDATE users SET last_active = CURRENT_TIMESTAMP WHERE id = ?', (user_id,))
            else:
                cursor.execute('INSERT INTO users (email, name) VALUES (?, ?)', (email, email.split('@')[0]))
                user_id = cursor.lastrowid
            
            st.session_state.user_id = user_id
            conn.commit()
            conn.close()
        except:
            pass
    
    def log_calculation(self, data):
        """Log calculation data"""
        try:
            if not st.session_state.get('user_id'):
                return
            
            conn = get_db_connection()
            if not conn:
                return
                
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO tariff_calculations (
                    user_id, session_id, user_email, order_number, country_of_origin,
                    hs_tariff_code, duty, tariff, mode_of_delivery,
                    commercial_invoice_value, brokerage, total_prepaid_freight,
                    merchandise_processing_fee, harbour_maintenance_fee,
                    calculated_total, net_value, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                st.session_state.user_id,
                st.session_state.session_id,
                data.get('user_email', ''),
                data.get('order_number', ''),
                data.get('country_of_origin', ''),
                data.get('hs_tariff_code', ''),
                data.get('duty', 0),
                data.get('tariff', 0),
                data.get('mode_of_delivery', ''),
                data.get('commercial_invoice_value', 0),
                data.get('brokerage', 0),
                data.get('total_prepaid_freight', 0),
                data.get('merchandise_processing_fee', 0),
                data.get('harbour_maintenance_fee', 0),
                data.get('calculated_total', 0),
                data.get('net_value', 0),
                data.get('notes', '')
            ))
            
            conn.commit()
            conn.close()
        except:
            pass