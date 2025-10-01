"""
Usage Limiter - Responsible Gambling Protection
Limits daily analyses to prevent compulsive checking
"""

import time
from datetime import datetime, timedelta
from typing import Dict, Optional
import json
import os
from pathlib import Path


class UsageLimiter:
    """
    Track and limit daily usage with responsible gambling features.
    
    Design principles:
    - Prevent compulsive checking (time + count limits)
    - Transparent about limits
    - No dark patterns or manipulation
    """
    
    ANONYMOUS_DAILY_LIMIT = 5
    AUTHENTICATED_DAILY_LIMIT = 7
    MINIMUM_INTERVAL_SECONDS = 300  # 5 minutes between checks
    
    def __init__(self, storage_dir: str = 'data/usage'):
        """
        Initialize usage limiter.
        
        Args:
            storage_dir: Directory to store usage data
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
    
    def check_can_analyze(self, user_id: str, is_authenticated: bool = False) -> Dict:
        """
        Check if user can perform an analysis.
        
        Args:
            user_id: User identifier (session ID or email)
            is_authenticated: Whether user has an account
            
        Returns:
            Dict with allowed status and details
        """
        usage_data = self._load_usage(user_id)
        
        # Reset if new day
        if self._is_new_day(usage_data.get('last_reset')):
            usage_data = self._reset_daily_usage(user_id)
        
        # Check daily limit
        daily_limit = (self.AUTHENTICATED_DAILY_LIMIT if is_authenticated 
                      else self.ANONYMOUS_DAILY_LIMIT)
        count_today = usage_data.get('count_today', 0)
        
        if count_today >= daily_limit:
            return {
                'allowed': False,
                'reason': 'daily_limit_reached',
                'message': f"Daily limit of {daily_limit} analyses reached. Resets at midnight.",
                'remaining': 0,
                'reset_time': self._get_next_reset_time(),
                'wellness_note': "Taking breaks from betting analysis is healthy. Consider reviewing past analyses instead of creating new ones."
            }
        
        # Check time interval (prevent rapid checking)
        last_use = usage_data.get('last_use_timestamp', 0)
        time_since_last = time.time() - last_use
        
        if time_since_last < self.MINIMUM_INTERVAL_SECONDS:
            wait_seconds = int(self.MINIMUM_INTERVAL_SECONDS - time_since_last)
            return {
                'allowed': False,
                'reason': 'cooldown_active',
                'message': f"Please wait {wait_seconds // 60} minutes between analyses.",
                'remaining': daily_limit - count_today,
                'cooldown_seconds': wait_seconds,
                'wellness_note': "Rapid checking can indicate compulsive behavior. Take a break."
            }
        
        # Allowed - return remaining count
        return {
            'allowed': True,
            'remaining': daily_limit - count_today - 1,  # After this use
            'total_limit': daily_limit,
            'analyses_today': count_today
        }
    
    def record_usage(self, user_id: str):
        """
        Record that user performed an analysis.
        
        Args:
            user_id: User identifier
        """
        usage_data = self._load_usage(user_id)
        
        # Reset if new day
        if self._is_new_day(usage_data.get('last_reset')):
            usage_data = self._reset_daily_usage(user_id)
        
        # Increment count
        usage_data['count_today'] = usage_data.get('count_today', 0) + 1
        usage_data['last_use_timestamp'] = time.time()
        usage_data['total_lifetime_uses'] = usage_data.get('total_lifetime_uses', 0) + 1
        
        self._save_usage(user_id, usage_data)
    
    def get_usage_stats(self, user_id: str) -> Dict:
        """Get user's usage statistics."""
        usage_data = self._load_usage(user_id)
        
        if self._is_new_day(usage_data.get('last_reset')):
            usage_data = self._reset_daily_usage(user_id)
        
        return {
            'count_today': usage_data.get('count_today', 0),
            'total_lifetime': usage_data.get('total_lifetime_uses', 0),
            'last_use': datetime.fromtimestamp(
                usage_data.get('last_use_timestamp', 0)
            ).isoformat() if usage_data.get('last_use_timestamp') else None,
            'next_reset': self._get_next_reset_time()
        }
    
    def _load_usage(self, user_id: str) -> Dict:
        """Load usage data from file."""
        file_path = self.storage_dir / f"{self._sanitize_id(user_id)}.json"
        
        if file_path.exists():
            with open(file_path, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_usage(self, user_id: str, data: Dict):
        """Save usage data to file."""
        file_path = self.storage_dir / f"{self._sanitize_id(user_id)}.json"
        
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _reset_daily_usage(self, user_id: str) -> Dict:
        """Reset daily usage counter."""
        return {
            'count_today': 0,
            'last_reset': datetime.now().date().isoformat(),
            'total_lifetime_uses': self._load_usage(user_id).get('total_lifetime_uses', 0)
        }
    
    def _is_new_day(self, last_reset: Optional[str]) -> bool:
        """Check if it's a new day since last reset."""
        if not last_reset:
            return True
        
        last_date = datetime.fromisoformat(last_reset).date()
        today = datetime.now().date()
        return today > last_date
    
    def _get_next_reset_time(self) -> str:
        """Get next midnight reset time."""
        tomorrow = datetime.now() + timedelta(days=1)
        midnight = datetime.combine(tomorrow.date(), datetime.min.time())
        return midnight.isoformat()
    
    def _sanitize_id(self, user_id: str) -> str:
        """Sanitize user ID for filename."""
        return user_id.replace('@', '_').replace('.', '_')


# Test the limiter
if __name__ == "__main__":
    limiter = UsageLimiter()
    
    print("Usage Limiter Test")
    print("="*60)
    
    test_user = "test_session_12345"
    
    # Test 1: Check initial state
    print("\nTest 1: Initial check")
    result = limiter.check_can_analyze(test_user)
    print(f"  Allowed: {result['allowed']}")
    print(f"  Remaining: {result['remaining']}")
    
    # Test 2: Use all daily limit
    print("\nTest 2: Using daily limit")
    for i in range(5):
        result = limiter.check_can_analyze(test_user)
        if result['allowed']:
            limiter.record_usage(test_user)
            print(f"  Analysis {i+1}: ✓ (Remaining: {result['remaining']})")
        else:
            print(f"  Analysis {i+1}: ✗ ({result['reason']})")
    
    # Test 3: Try after limit reached
    print("\nTest 3: After limit reached")
    result = limiter.check_can_analyze(test_user)
    print(f"  Allowed: {result['allowed']}")
    print(f"  Message: {result['message']}")
    print(f"  Wellness note: {result['wellness_note']}")
    
    # Test 4: Check stats
    print("\nTest 4: Usage statistics")
    stats = limiter.get_usage_stats(test_user)
    print(f"  Today: {stats['count_today']}")
    print(f"  Lifetime: {stats['total_lifetime']}")
    
    print("\n" + "="*60)
    print("Test complete!")