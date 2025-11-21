"""
Clear all group trip planner data from Firebase
Completely removes all groups, invitations, and related data for fresh start
"""

import os
import sys
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

def clear_all_group_planner_data():
    """Clear all group trip planner data from Firebase"""
    
    print("\n" + "="*80)
    print("🧹 CLEARING ALL GROUP TRIP PLANNER DATA")
    print("="*80)
    
    # 1. Delete all group invitations first (to avoid foreign key issues)
    print("\n📧 Step 1: Deleting all group invitations...")
    invitations_ref = db.collection('group_invitations')
    invitations = invitations_ref.stream()
    invitation_count = 0
    
    for inv_doc in invitations:
        try:
            inv_data = inv_doc.to_dict()
            email = inv_data.get('invited_email', 'Unknown')
            group_name = inv_data.get('group_name', 'Unknown')
            
            invitations_ref.document(inv_doc.id).delete()
            invitation_count += 1
            print(f"   ✅ Deleted invitation: {email} for {group_name} ({inv_doc.id})")
        except Exception as e:
            print(f"   ❌ Failed to delete invitation {inv_doc.id}: {e}")
    
    print(f"   Total invitations deleted: {invitation_count}")
    
    # 2. Delete all groups from users' subcollections
    print("\n🗑️  Step 2: Deleting groups from user collections...")
    users_ref = db.collection('users')
    users = users_ref.stream()
    user_group_count = 0
    
    for user_doc in users:
        try:
            user_id = user_doc.id
            # Get all groups for this user
            user_groups_ref = users_ref.document(user_id).collection('groups')
            user_groups = user_groups_ref.stream()
            
            for group_doc in user_groups:
                try:
                    group_data = group_doc.to_dict()
                    group_name = group_data.get('name', 'Unknown')
                    
                    user_groups_ref.document(group_doc.id).delete()
                    user_group_count += 1
                    print(f"   ✅ Deleted user group: {group_name} for user {user_id}")
                except Exception as e:
                    print(f"   ❌ Failed to delete user group {group_doc.id}: {e}")
        except Exception as e:
            print(f"   ⚠️  Error processing user {user_doc.id}: {e}")
    
    print(f"   Total user groups deleted: {user_group_count}")
    
    # 3. Delete all places
    print("\n🗺️  Step 3: Deleting all places...")
    places_ref = db.collection('places')
    places = places_ref.stream()
    places_count = 0
    
    for place_doc in places:
        try:
            place_data = place_doc.to_dict()
            place_name = place_data.get('name', 'Unknown')
            
            places_ref.document(place_doc.id).delete()
            places_count += 1
            print(f"   ✅ Deleted place: {place_name} ({place_doc.id})")
        except Exception as e:
            print(f"   ❌ Failed to delete place {place_doc.id}: {e}")
    
    print(f"   Total places deleted: {places_count}")
    
    # 4. Delete all polls
    print("\n📊 Step 4: Deleting all polls...")
    polls_ref = db.collection('polls')
    polls = polls_ref.stream()
    polls_count = 0
    
    for poll_doc in polls:
        try:
            poll_data = poll_doc.to_dict()
            poll_question = poll_data.get('question', 'Unknown')
            
            polls_ref.document(poll_doc.id).delete()
            polls_count += 1
            print(f"   ✅ Deleted poll: {poll_question} ({poll_doc.id})")
        except Exception as e:
            print(f"   ❌ Failed to delete poll {poll_doc.id}: {e}")
    
    print(f"   Total polls deleted: {polls_count}")
    
    # 5. Clear Redis cache for group planner
    print(f"\n🔄 Step 5: Clearing Redis cache...")
    try:
        import redis
        redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        
        # Clear all group planner related caches
        groupplanner_keys = redis_client.keys("groupplanner:*")
        group_planner_keys = redis_client.keys("group_planner:*")
        
        all_keys = groupplanner_keys + group_planner_keys
        if all_keys:
            redis_client.delete(*all_keys)
            print(f"   ✅ Cleared {len(all_keys)} cache entries")
            for key in all_keys[:10]:  # Show first 10
                print(f"      - {key}")
            if len(all_keys) > 10:
                print(f"      ... and {len(all_keys) - 10} more")
        else:
            print(f"   ℹ️  No cache entries found")
        
        print(f"   ✅ Redis cache cleared")
    except Exception as e:
        print(f"   ⚠️  Error clearing Redis: {e}")
        print(f"      (Redis may not be running - this is optional)")
    
    # Summary
    print("\n" + "="*80)
    print("✅ CLEANUP COMPLETE")
    print("="*80)
    print(f"   Invitations deleted: {invitation_count}")
    print(f"   User groups deleted: {user_group_count}")
    print(f"   Places deleted: {places_count}")
    print(f"   Polls deleted: {polls_count}")
    print(f"   Redis cache: Cleared")
    print("\n💡 Group Planner has been completely reset")
    print("   All users will start with empty group lists")
    print("   All invitations have been removed")
    print("="*80 + "\n")


if __name__ == '__main__':
    # Confirmation prompt
    print("\n⚠️  WARNING: This will DELETE ALL group trip planner data!")
    print("   - All trip groups")
    print("   - All pending invitations")
    print("   - All cached data")
    print("\n   This action CANNOT be undone!\n")
    
    response = input("Are you sure you want to continue? (type 'yes' to confirm): ")
    
    if response.lower() == 'yes':
        try:
            clear_all_group_planner_data()
        except KeyboardInterrupt:
            print("\n\n⚠️  Cleanup interrupted by user")
        except Exception as e:
            print(f"\n❌ Error during cleanup: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("\n❌ Cleanup cancelled. No data was deleted.")
