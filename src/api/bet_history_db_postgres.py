"""
Database models and setup for bet history tracking - PostgreSQL Version
Use this for Railway deployment with PostgreSQL
"""
import os
from datetime import datetime
from typing import Optional, List
import psycopg2
from psycopg2.extras import RealDictCursor

class BetHistoryDB:
    def __init__(self, database_url: str = None):
        """
        Initialize with PostgreSQL connection
        If no URL provided, uses environment variable DATABASE_URL (Railway auto-sets this)
        """
        self.database_url = database_url or os.environ.get('DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable not set")
        
        # Railway uses postgres:// but psycopg2 needs postgresql://
        if self.database_url.startswith('postgres://'):
            self.database_url = self.database_url.replace('postgres://', 'postgresql://', 1)
        
        self.init_db()
    
    def get_connection(self):
        """Get database connection"""
        return psycopg2.connect(self.database_url, cursor_factory=RealDictCursor)
    
    def init_db(self):
        """Initialize database with bet_history table"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bet_history (
                id SERIAL PRIMARY KEY,
                player_name VARCHAR(255) NOT NULL,
                stat_type VARCHAR(50) NOT NULL,
                line DECIMAL(10, 2) NOT NULL,
                probability DECIMAL(5, 2) NOT NULL,
                recommendation TEXT NOT NULL,
                result VARCHAR(20) DEFAULT 'pending',
                stake DECIMAL(10, 2) DEFAULT 100.0,
                odds DECIMAL(10, 2) DEFAULT 1.9,
                timestamp TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        cursor.close()
        conn.close()
        print("✅ PostgreSQL database initialized successfully")
    
    def create_bet(self, player_name: str, stat_type: str, line: float, 
                   probability: float, recommendation: str, 
                   stake: float = 100.0, odds: float = 1.9) -> int:
        """Create a new bet record"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        timestamp = datetime.now()
        
        cursor.execute("""
            INSERT INTO bet_history 
            (player_name, stat_type, line, probability, recommendation, stake, odds, timestamp)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """, (player_name, stat_type, line, probability, recommendation, stake, odds, timestamp))
        
        bet_id = cursor.fetchone()['id']
        conn.commit()
        cursor.close()
        conn.close()
        
        return bet_id
    
    def get_all_bets(self) -> List[dict]:
        """Get all bets ordered by most recent first"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM bet_history 
            ORDER BY created_at DESC
        """)
        
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        bets = []
        for row in rows:
            bets.append({
                'id': row['id'],
                'playerName': row['player_name'],
                'statType': row['stat_type'],
                'line': float(row['line']),
                'probability': float(row['probability']),
                'recommendation': row['recommendation'],
                'result': row['result'],
                'stake': float(row['stake']) if row['stake'] else 0,
                'odds': float(row['odds']) if row['odds'] else 0,
                'timestamp': row['timestamp'].isoformat()
            })
        
        return bets
    
    def update_bet_result(self, bet_id: int, result: str) -> bool:
        """Update bet result (won/lost)"""
        if result not in ['won', 'lost', 'pending']:
            raise ValueError("Result must be 'won', 'lost', or 'pending'")
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE bet_history 
            SET result = %s 
            WHERE id = %s
        """, (result, bet_id))
        
        affected = cursor.rowcount
        conn.commit()
        cursor.close()
        conn.close()
        
        return affected > 0
    
    def delete_bet(self, bet_id: int) -> bool:
        """Delete a bet (optional - for admin purposes)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM bet_history WHERE id = %s", (bet_id,))
        
        affected = cursor.rowcount
        conn.commit()
        cursor.close()
        conn.close()
        
        return affected > 0
    
    def get_stats(self) -> dict:
        """Calculate betting statistics"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) as count FROM bet_history")
        total_bets = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM bet_history WHERE result = 'won'")
        won_bets = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM bet_history WHERE result = 'lost'")
        lost_bets = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM bet_history WHERE result = 'pending'")
        pending_bets = cursor.fetchone()['count']
        
        cursor.execute("SELECT COALESCE(SUM(stake), 0) as total FROM bet_history")
        total_staked = float(cursor.fetchone()['total'])
        
        cursor.execute("SELECT COALESCE(SUM(stake * odds), 0) as total FROM bet_history WHERE result = 'won'")
        total_return = float(cursor.fetchone()['total'])
        
        cursor.close()
        conn.close()
        
        win_rate = (won_bets / total_bets * 100) if total_bets > 0 else 0
        roi = ((total_return - total_staked) / total_staked * 100) if total_staked > 0 else 0
        
        return {
            'totalBets': total_bets,
            'wonBets': won_bets,
            'lostBets': lost_bets,
            'pendingBets': pending_bets,
            'winRate': round(win_rate, 1),
            'totalStaked': round(total_staked, 2),
            'totalReturn': round(total_return, 2),
            'roi': round(roi, 1)
        }


# Example usage
if __name__ == "__main__":
    # Test connection
    try:
        db = BetHistoryDB()
        print("✅ Database connection successful!")
        
        # Test: Create a bet
        bet_id = db.create_bet(
            player_name="Stephen Curry",
            stat_type="3PM",
            line=4.5,
            probability=67.3,
            recommendation="STRONG BET",
            stake=100.0,
            odds=1.9
        )
        print(f"✅ Created bet with ID: {bet_id}")
        
        # Test: Get all bets
        bets = db.get_all_bets()
        print(f"✅ Retrieved {len(bets)} bets")
        
        # Test: Get stats
        stats = db.get_stats()
        print(f"✅ Stats: {stats}")
        
    except Exception as e:
        print(f"❌ Error: {e}")