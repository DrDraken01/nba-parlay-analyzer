"""
Results Tracker - Transparent Win/Loss History
Shows users the reality of their betting performance
"""

from datetime import datetime
from typing import Dict, List, Optional
import json
from pathlib import Path
import pandas as pd


class ResultsTracker:
    """
    Track actual parlay results to show users reality.
    
    Design principle: Radical transparency about losses.
    No sugar-coating, no hiding negative trends.
    """
    
    def __init__(self, storage_dir: str = 'data/results'):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
    
    def log_parlay(self, user_id: str, parlay_data: Dict):
        """
        Log a parlay prediction for later verification.
        
        Args:
            user_id: User identifier
            parlay_data: Parlay details with predictions
        """
        history = self._load_history(user_id)
        
        entry = {
            'parlay_id': f"parlay_{len(history) + 1}",
            'timestamp': datetime.now().isoformat(),
            'legs': parlay_data['legs'],
            'predicted_probability': parlay_data.get('combined_probability', 0),
            'wager_amount': None,  # User can add later
            'result': 'pending',
            'actual_outcome': None
        }
        
        history.append(entry)
        self._save_history(user_id, history)
        
        return entry['parlay_id']
    
    def update_result(self, user_id: str, parlay_id: str, 
                     won: bool, wager_amount: float = 0, 
                     payout: float = 0):
        """
        Update parlay with actual result.
        
        Args:
            user_id: User identifier
            parlay_id: Parlay ID to update
            won: Whether the parlay won
            wager_amount: Amount wagered
            payout: Amount won (if won)
        """
        history = self._load_history(user_id)
        
        for entry in history:
            if entry['parlay_id'] == parlay_id:
                entry['result'] = 'won' if won else 'lost'
                entry['wager_amount'] = wager_amount
                entry['payout'] = payout if won else 0
                entry['net_profit'] = (payout - wager_amount) if won else -wager_amount
                entry['updated_at'] = datetime.now().isoformat()
                break
        
        self._save_history(user_id, history)
    
    def get_performance_summary(self, user_id: str) -> Dict:
        """
        Get brutally honest performance summary.
        
        Returns the truth about their betting performance.
        """
        history = self._load_history(user_id)
        
        if not history:
            return {
                'total_parlays': 0,
                'message': 'No betting history yet.'
            }
        
        completed = [p for p in history if p['result'] in ['won', 'lost']]
        
        if not completed:
            return {
                'total_parlays': len(history),
                'pending': len(history),
                'message': 'All parlays still pending results.'
            }
        
        wins = [p for p in completed if p['result'] == 'won']
        losses = [p for p in completed if p['result'] == 'lost']
        
        total_wagered = sum(p.get('wager_amount', 0) for p in completed if p.get('wager_amount'))
        total_returned = sum(p.get('payout', 0) for p in wins)
        net_profit = total_returned - total_wagered
        
        roi = (net_profit / total_wagered * 100) if total_wagered > 0 else 0
        win_rate = (len(wins) / len(completed) * 100) if completed else 0
        
        # Calculate expected vs actual
        avg_predicted_prob = sum(p.get('predicted_probability', 0) for p in completed) / len(completed) if completed else 0
        expected_wins = avg_predicted_prob * len(completed)
        actual_wins = len(wins)
        
        # Determine message tone based on results
        if net_profit < 0:
            reality_check = f"You've lost ${abs(net_profit):.2f}. The model predicted better, but variance is real."
        elif net_profit > 0:
            reality_check = f"You're up ${net_profit:.2f}. This is unusual - don't expect it to continue."
        else:
            reality_check = "Break even. You're beating most bettors already."
        
        return {
            'total_parlays': len(completed),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': round(win_rate, 1),
            'predicted_win_rate': round(avg_predicted_prob * 100, 1),
            'total_wagered': round(total_wagered, 2),
            'total_returned': round(total_returned, 2),
            'net_profit': round(net_profit, 2),
            'roi': round(roi, 1),
            'reality_check': reality_check,
            'warning': self._generate_warning(net_profit, len(completed))
        }
    
    def get_recent_results(self, user_id: str, limit: int = 10) -> List[Dict]:
        """Get recent betting results."""
        history = self._load_history(user_id)
        completed = [p for p in history if p['result'] in ['won', 'lost']]
        
        # Sort by timestamp, most recent first
        completed.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        return completed[:limit]
    
    def _generate_warning(self, net_profit: float, num_parlays: int) -> Optional[str]:
        """Generate warnings for concerning patterns."""
        
        # Large losses
        if net_profit < -500:
            return "SIGNIFICANT LOSSES. Consider taking a break. Visit ncpgambling.org for help."
        
        # High volume
        if num_parlays > 50:
            return "High betting volume detected. This pattern can indicate problem gambling."
        
        # Moderate losses
        if net_profit < -100:
            return "Losing trend detected. Remember: no model eliminates the house edge."
        
        return None
    
    def export_to_csv(self, user_id: str) -> str:
        """Export betting history to CSV for external analysis."""
        history = self._load_history(user_id)
        
        if not history:
            return None
        
        # Flatten for CSV
        rows = []
        for entry in history:
            rows.append({
                'parlay_id': entry['parlay_id'],
                'date': entry['timestamp'],
                'predicted_probability': entry.get('predicted_probability'),
                'result': entry.get('result'),
                'wager': entry.get('wager_amount'),
                'payout': entry.get('payout'),
                'profit': entry.get('net_profit')
            })
        
        df = pd.DataFrame(rows)
        filepath = self.storage_dir / f"{user_id}_history.csv"
        df.to_csv(filepath, index=False)
        
        return str(filepath)
    
    def _load_history(self, user_id: str) -> List[Dict]:
        """Load betting history from file."""
        filepath = self.storage_dir / f"{self._sanitize_id(user_id)}.json"
        
        if filepath.exists():
            with open(filepath, 'r') as f:
                return json.load(f)
        return []
    
    def _save_history(self, user_id: str, history: List[Dict]):
        """Save betting history to file."""
        filepath = self.storage_dir / f"{self._sanitize_id(user_id)}.json"
        
        with open(filepath, 'w') as f:
            json.dump(history, f, indent=2)
    
    def _sanitize_id(self, user_id: str) -> str:
        """Sanitize user ID for filename."""
        return user_id.replace('@', '_').replace('.', '_')


# Test the tracker
if __name__ == "__main__":
    tracker = ResultsTracker()
    test_user = "test_user_123"
    
    print("Results Tracker Test - Realistic Scenario")
    print("="*60)
    
    # Simulate a user making predictions and mostly losing (realistic)
    print("\nSimulating 10 parlays (typical results - mostly losses):")
    
    test_parlays = [
        {'combined_probability': 0.15, 'won': False, 'wager': 50, 'payout': 0},
        {'combined_probability': 0.20, 'won': False, 'wager': 50, 'payout': 0},
        {'combined_probability': 0.18, 'won': True, 'wager': 50, 'payout': 300},  # One win
        {'combined_probability': 0.22, 'won': False, 'wager': 50, 'payout': 0},
        {'combined_probability': 0.16, 'won': False, 'wager': 50, 'payout': 0},
        {'combined_probability': 0.19, 'won': False, 'wager': 50, 'payout': 0},
        {'combined_probability': 0.25, 'won': False, 'wager': 50, 'payout': 0},
        {'combined_probability': 0.21, 'won': False, 'wager': 50, 'payout': 0},
        {'combined_probability': 0.17, 'won': False, 'wager': 50, 'payout': 0},
        {'combined_probability': 0.23, 'won': False, 'wager': 50, 'payout': 0},
    ]
    
    for i, parlay in enumerate(test_parlays, 1):
        parlay_id = tracker.log_parlay(test_user, {
            'legs': [],
            'combined_probability': parlay['combined_probability']
        })
        
        tracker.update_result(
            test_user, 
            parlay_id, 
            won=parlay['won'],
            wager_amount=parlay['wager'],
            payout=parlay['payout']
        )
        
        result = "WON" if parlay['won'] else "LOST"
        print(f"  Parlay {i}: {result} (predicted {parlay['combined_probability']:.0%} chance)")
    
    # Show the brutal reality
    print("\n" + "="*60)
    print("PERFORMANCE SUMMARY")
    print("="*60)
    
    summary = tracker.get_performance_summary(test_user)
    
    print(f"\nRecord: {summary['wins']} wins, {summary['losses']} losses")
    print(f"Win Rate: {summary['win_rate']}% (Predicted: {summary['predicted_win_rate']}%)")
    print(f"\nTotal Wagered: ${summary['total_wagered']}")
    print(f"Total Returned: ${summary['total_returned']}")
    print(f"Net Profit/Loss: ${summary['net_profit']}")
    print(f"ROI: {summary['roi']}%")
    print(f"\n{summary['reality_check']}")
    
    if summary.get('warning'):
        print(f"\nWARNING: {summary['warning']}")
    
    print("\n" + "="*60)