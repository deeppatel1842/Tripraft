"""
Clear ALL data from Firebase, Redis, and local storage
Complete database reset - removes groups, expenses, settlements, invitations, balances, users, and all caches
WARNING: This is a DESTRUCTIVE operation that cannot be undone!
"""

import os
import sys
from constants import FirebaseCollections
from datetime import datetime
from dotenv import load_dotenv

# Add backend directory to path
backend_path = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, backend_path)

# Load environment variables from backend .env file
env_path = os.path.join(backend_path, '.env')
load_dotenv(env_path)

# Initialize Firebase using environment variables (same as Flask app)
import firebase_admin
from firebase_admin import credentials, firestore

if not firebase_admin._apps:
    service_account_info = {
        "type": os.getenv("FIREBASE_TYPE"),
        "project_id": os.getenv("FIREBASE_PROJECT_ID"),
        "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
        "private_key": os.getenv("FIREBASE_PRIVATE_KEY", "").replace('\\n', '\n'),
        "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
        "client_id": os.getenv("FIREBASE_CLIENT_ID"),
        "auth_uri": os.getenv("FIREBASE_AUTH_URI"),
        "token_uri": os.getenv("FIREBASE_TOKEN_URI"),
        "auth_provider_x509_cert_url": os.getenv("FIREBASE_AUTH_PROVIDER_X509_CERT_URL"),
        "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_X509_CERT_URL")
    }
    
    cred = credentials.Certificate(service_account_info)
    firebase_admin.initialize_app(cred)
    print("✅ Firebase initialized successfully")

db = firestore.client()

def clear_all_data():
    """Clear ALL data from Firebase, Redis, and local storage - COMPLETE RESET"""
    
    print("\n" + "="*80)
    print("⚠️  WARNING: COMPLETE DATABASE RESET")
    print("="*80)
    print("This will DELETE ALL data:")
    print("  • All groups")
    print("  • All expenses") 
    print("  • All settlements")
    print("  • All invitations")
    print("  • All group members")
    print("  • All group balances")
    print("  • All expense splits")
    print("  • All users (optional)")
    print("  • All Redis cache")
    print("  • All local storage")
    print("="*80)
    
    # Safety confirmation
    confirm = input("\n⚠️  Type 'DELETE ALL DATA' to confirm: ")
    if confirm != "DELETE ALL DATA":
        print("❌ Confirmation failed. Aborting.")
        return
    
    print("\n🔥 Starting complete data wipe...")
    print("="*80)
    
    # Counters for summary
    stats = {
        'groups': 0,
        'expenses': 0,
        'settlements': 0,
        'invitations': 0,
        'group_members': 0,
        'group_balances': 0,
        'expense_splits': 0,
        'users': 0,
        'redis_keys': 0
    }
    
    # 1. Delete ALL GROUPS
    print("\n🗑️  Step 1: Deleting ALL groups...")
    try:
        groups_ref = db.collection(FirebaseCollections.GROUPS)
        groups = groups_ref.stream()
        
        for group_doc in groups:
            try:
                group_data = group_doc.to_dict()
                print(f"   Deleting group: {group_data.get('name', 'Unknown')} ({group_doc.id})")
                groups_ref.document(group_doc.id).delete()
                stats['groups'] += 1
            except Exception as e:
                print(f"   ❌ Failed to delete group {group_doc.id}: {e}")
        
        print(f"   ✅ Deleted {stats['groups']} groups")
    except Exception as e:
        print(f"   ⚠️  Error deleting groups: {e}")
    
    # 2. Delete ALL EXPENSES
    print(f"\n🗑️  Step 2: Deleting ALL expenses...")
    try:
        expenses_ref = db.collection(FirebaseCollections.EXPENSES)
        expenses = expenses_ref.stream()
        
        for expense_doc in expenses:
            try:
                expense_data = expense_doc.to_dict()
                description = expense_data.get('description', 'Unknown')
                print(f"   Deleting expense: {description} ({expense_doc.id})")
                expenses_ref.document(expense_doc.id).delete()
                stats['expenses'] += 1
            except Exception as e:
                print(f"   ❌ Failed to delete expense {expense_doc.id}: {e}")
        
        print(f"   ✅ Deleted {stats['expenses']} expenses")
    except Exception as e:
        print(f"   ⚠️  Error deleting expenses: {e}")
    
    # 3. Delete ALL SETTLEMENTS
    print(f"\n🗑️  Step 3: Deleting ALL settlements...")
    try:
        settlements_ref = db.collection(FirebaseCollections.SETTLEMENTS)
        settlements = settlements_ref.stream()
        
        for settlement_doc in settlements:
            try:
                settlement_data = settlement_doc.to_dict()
                amount = settlement_data.get('amount', 0)
                print(f"   Deleting settlement: ${amount} ({settlement_doc.id})")
                settlements_ref.document(settlement_doc.id).delete()
                stats['settlements'] += 1
            except Exception as e:
                print(f"   ❌ Failed to delete settlement {settlement_doc.id}: {e}")
        
        print(f"   ✅ Deleted {stats['settlements']} settlements")
    except Exception as e:
        print(f"   ⚠️  Error deleting settlements: {e}")
    
    # 4. Delete ALL INVITATIONS
    print(f"\n🗑️  Step 4: Deleting ALL invitations...")
    try:
        invitations_ref = db.collection(FirebaseCollections.GROUP_INVITATIONS)
        invitations = invitations_ref.stream()
        
        for invitation_doc in invitations:
            try:
                invitation_data = invitation_doc.to_dict()
                inviter = invitation_data.get('inviter_id', 'Unknown')
                print(f"   Deleting invitation from {inviter} ({invitation_doc.id})")
                invitations_ref.document(invitation_doc.id).delete()
                stats['invitations'] += 1
            except Exception as e:
                print(f"   ❌ Failed to delete invitation {invitation_doc.id}: {e}")
        
        print(f"   ✅ Deleted {stats['invitations']} invitations")
    except Exception as e:
        print(f"   ⚠️  Error deleting invitations: {e}")
    
    # 5. Delete ALL GROUP MEMBERS
    print(f"\n🗑️  Step 5: Deleting ALL group members...")
    try:
        members_ref = db.collection(FirebaseCollections.GROUP_MEMBERS)
        members = members_ref.stream()
        
        for member_doc in members:
            try:
                member_data = member_doc.to_dict()
                user_id = member_data.get('user_id', 'Unknown')
                print(f"   Deleting member: {user_id} ({member_doc.id})")
                members_ref.document(member_doc.id).delete()
                stats['group_members'] += 1
            except Exception as e:
                print(f"   ❌ Failed to delete member {member_doc.id}: {e}")
        
        print(f"   ✅ Deleted {stats['group_members']} group members")
    except Exception as e:
        print(f"   ⚠️  Error deleting group members: {e}")
    
    # 6. Delete ALL GROUP BALANCES
    print(f"\n🗑️  Step 6: Deleting ALL group balances...")
    try:
        balances_ref = db.collection(FirebaseCollections.GROUP_BALANCES)
        balances = balances_ref.stream()
        
        for balance_doc in balances:
            try:
                balance_data = balance_doc.to_dict()
                group_id = balance_data.get('group_id', 'Unknown')
                print(f"   Deleting balance for group: {group_id} ({balance_doc.id})")
                balances_ref.document(balance_doc.id).delete()
                stats['group_balances'] += 1
            except Exception as e:
                print(f"   ❌ Failed to delete balance {balance_doc.id}: {e}")
        
        print(f"   ✅ Deleted {stats['group_balances']} group balances")
    except Exception as e:
        print(f"   ⚠️  Error deleting group balances: {e}")
    
    # 7. Delete ALL EXPENSE SPLITS
    print(f"\n🗑️  Step 7: Deleting ALL expense splits...")
    try:
        splits_ref = db.collection('expense_splits')
        splits = splits_ref.stream()
        
        for split_doc in splits:
            try:
                split_data = split_doc.to_dict()
                expense_id = split_data.get('expense_id', 'Unknown')
                print(f"   Deleting split for expense: {expense_id} ({split_doc.id})")
                splits_ref.document(split_doc.id).delete()
                stats['expense_splits'] += 1
            except Exception as e:
                print(f"   ❌ Failed to delete split {split_doc.id}: {e}")
        
        print(f"   ✅ Deleted {stats['expense_splits']} expense splits")
    except Exception as e:
        print(f"   ⚠️  Error deleting expense splits: {e}")
    
    # 8. Delete ALL USERS (optional - ask for confirmation)
    print(f"\n🗑️  Step 8: Deleting ALL users...")
    delete_users = input("   ⚠️  Delete ALL users? (yes/no): ").lower()
    if delete_users == 'yes':
        try:
            users_ref = db.collection('users')
            users = users_ref.stream()
            
            for user_doc in users:
                try:
                    user_data = user_doc.to_dict()
                    username = user_data.get('username', 'Unknown')
                    print(f"   Deleting user: {username} ({user_doc.id})")
                    users_ref.document(user_doc.id).delete()
                    stats['users'] += 1
                except Exception as e:
                    print(f"   ❌ Failed to delete user {user_doc.id}: {e}")
            
            print(f"   ✅ Deleted {stats['users']} users")
        except Exception as e:
            print(f"   ⚠️  Error deleting users: {e}")
    else:
        print(f"   ℹ️  Skipped user deletion (users preserved)")
    
    # 9. Clear ALL Redis cache
    print(f"\n🔄 Step 9: Clearing ALL Redis cache...")
    try:
        import redis
        redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        
        # Get all keys
        all_keys = redis_client.keys("*")
        if all_keys:
            # Delete all keys
            deleted = redis_client.delete(*all_keys)
            stats['redis_keys'] = deleted
            print(f"   ✅ Cleared {deleted} Redis cache keys")
        else:
            print(f"   ℹ️  No Redis keys found")
        
        print(f"   ✅ Redis completely cleared")
    except Exception as e:
        print(f"   ⚠️  Error clearing Redis: {e}")
    
    # 10. Clear local storage
    print(f"\n🗑️  Step 10: Clearing local storage...")
    try:
        import json
        # Local storage file path
        local_storage_path = os.path.join(backend_path, 'expense_engine', 'local_expenses.json')
        if os.path.exists(local_storage_path):
            # Write empty expenses
            with open(local_storage_path, 'w') as f:
                json.dump({'expenses': {}}, f)
            print(f"   ✅ Local storage file cleared")
        else:
            print(f"   ℹ️  No local storage file found")
    except Exception as e:
        print(f"   ⚠️  Error clearing local storage: {e}")
    
    # Summary
    print("\n" + "="*80)
    print("✅ COMPLETE DATABASE WIPE FINISHED")
    print("="*80)
    print(f"   Groups deleted:         {stats['groups']}")
    print(f"   Expenses deleted:       {stats['expenses']}")
    print(f"   Settlements deleted:    {stats['settlements']}")
    print(f"   Invitations deleted:    {stats['invitations']}")
    print(f"   Group members deleted:  {stats['group_members']}")
    print(f"   Group balances deleted: {stats['group_balances']}")
    print(f"   Expense splits deleted: {stats['expense_splits']}")
    print(f"   Users deleted:          {stats['users']}")
    print(f"   Redis keys cleared:     {stats['redis_keys']}")
    print(f"   Local storage:          Cleared")
    print("\n🔥 Database is now COMPLETELY EMPTY")
    print("="*80 + "\n")


if __name__ == '__main__':
    try:
        clear_all_data()
    except KeyboardInterrupt:
        print("\n\n⚠️  Database wipe interrupted by user")
    except Exception as e:
        print(f"\n❌ Error during database wipe: {e}")
        import traceback
        traceback.print_exc()
