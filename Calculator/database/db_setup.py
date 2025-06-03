import sqlite3
import os

def create_database():
    """Create the usage history database and tables"""
    db_path = os.path.join(os.path.dirname(__file__), 'usage_history.db')
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Tariff calculations table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tariff_calculations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            session_id TEXT,
            calculation_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            user_email TEXT,
            order_number TEXT,
            country_of_origin TEXT,
            hs_tariff_code TEXT,
            duty REAL,
            tariff REAL,
            mode_of_delivery TEXT,
            commercial_invoice_value REAL,
            brokerage REAL,
            total_prepaid_freight REAL,
            merchandise_processing_fee REAL,
            harbour_maintenance_fee REAL,
            calculated_total REAL,
            net_value REAL,
            notes TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()
    return db_path

def get_db_connection():
    """Get database connection"""
    db_path = os.path.join(os.path.dirname(__file__), 'usage_history.db')
    return sqlite3.connect(db_path)