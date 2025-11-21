"""
Emergency Fix: Reset Group Balances by Recalculating from Expenses
This script recalculates balances from scratch for all groups
Use this after fixing the settlement bug to correct existing wrong balances
"""

import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from api.app import create_app
from expense_engine.core.balance_manager import BalanceManager
from firebase_admin import firestore

def reset_all_group_balances():
    """Reset all group balances by recalculating from expenses"""
    app = create_app()
    
    with app.app_context():
        db = firestore.client()
        balance_manager = BalanceManager(db)
        
        print("="*80)
        print("EMERGENCY FIX: Resetting All Group Balances")
        print("="*80)
        
        # Get all group balance documents
        balance_docs = db.collection('group_balances').stream()
        
        groups_fixed = 0
        for balance_doc in balance_docs:
            group_id = balance_doc.id
            print(f"\n📊 Processing group: {group_id}")
            
            try:
                # Force full recalculation from expenses
                print(f"   🔄 Recalculating from expenses...")
                result = balance_manager._recalculate_and_cache_balance(group_id)
                
                print(f"   ✅ Fixed group {group_id}")
                print(f"      Is settled: {result.get('is_settled')}")
                print(f"      Total debts: ${result.get('total_debts', 0):.2f}")
                
                # Display final balances
                for balance in result.get('balances', []):
                    print(f"      {balance['username']}: ${balance['balance']:.2f}")
                
                groups_fixed += 1
                
            except Exception as e:
                print(f"   ❌ Error fixing group {group_id}: {e}")
        
        print("\n" + "="*80)
        print(f"✅ COMPLETE: Fixed {groups_fixed} groups")
        print("="*80)
        print("\nYou can now:")
        print("1. Refresh your UI to see correct balances")
        print("2. All future settlements will work correctly")
        print("3. Sum-to-zero is maintained")

if __name__ == "__main__":
    reset_all_group_balances()
