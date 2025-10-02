"""
Database operations for user management
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv
from typing import Optional, Dict
from datetime import datetime

load_dotenv()


def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(
        dbname=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD', ''),
        host=os.getenv('DB_HOST'),
        port=os.getenv('DB_PORT', '5432')
    )


class UserDB:
    """Database operations for users"""
    
    @staticmethod
    def create_user(email: str, hashed_password: str) -> Optional[Dict]:
        """Create new user, return user dict or None if email exists"""
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            cursor.execute("""
                INSERT INTO users (email, hashed_password)
                VALUES (%s, %s)
                RETURNING id, email, created_at
            """, (email, hashed_password))
            
            user = cursor.fetchone()
            conn.commit()
            return dict(user) if user else None
            
        except psycopg2.IntegrityError:
            conn.rollback()
            return None
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def get_user_by_email(email: str) -> Optional[Dict]:
        """Get user by email"""
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            cursor.execute("""
                SELECT id, email, hashed_password, is_active, created_at
                FROM users WHERE email = %s
            """, (email,))
            
            user = cursor.fetchone()
            return dict(user) if user else None
            
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def log_api_usage(user_id: int, endpoint: str, ip_address: str = None):
        """Log API usage"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO api_usage (user_id, endpoint, ip_address)
                VALUES (%s, %s, %s)
            """, (user_id, endpoint, ip_address))
            
            conn.commit()
        finally:
            cursor.close()
            conn.close()