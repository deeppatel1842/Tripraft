"""
Phase 21 Migration Script: Build Extreme Dashboard Documents
=============================================================

This script migrates existing users to the new extreme dashboard pattern.
For each user, it:
1. Fetches all their groups, expenses, settlements, invitations
2. Builds a single dashboard document
3. Saves to expense_user_dashboards collection

Usage:
    python -m expense_engine.scripts.migrate_to_extreme_dashboard [--dry-run] [--user USER_ID]

Options:
    --dry-run    Show what would be done without making changes
    --user       Migrate a specific user only
    --limit      Maximum number of users to migrate (default: all)
"""

import argparse
import logging
import sys
from datetime import datetime
from typing import Dict, List, Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_firestore_client():
    """Get Firestore client with Firebase initialization"""
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore
        
        # Check if already initialized
        try:
            firebase_admin.get_app()
        except ValueError:
            # Initialize with default credentials
            import os
            cred_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
            if cred_path:
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
            else:
                firebase_admin.initialize_app()
        
        return firestore.client()
    except Exception as e:
        logger.error("Failed to initialize Firebase: %s", e)
        sys.exit(1)


def get_all_users(db) -> List[Dict]:
    """Get all users who have expense group memberships"""
    from google.cloud.firestore_v1.base_query import FieldFilter
    
    # Get unique user IDs from group members
    members_ref = db.collection('expense_group_members')
    docs = members_ref.where(filter=FieldFilter('is_active', '==', True)).stream()
    
    user_ids = set()
    user_emails = {}
    
    for doc in docs:
        data = doc.to_dict()
        uid = data.get('user_id')
        if uid:
            user_ids.add(uid)
    
    # Get user details
    users = []
    for uid in user_ids:
        user_doc = db.collection('users').document(uid).get()
        if user_doc.exists:
            user_data = user_doc.to_dict()
            users.append({
                'user_id': uid,
                'email': user_data.get('email', ''),
                'display_name': user_data.get('display_name', '')
            })
    
    logger.info("Found %d users with expense group memberships", len(users))
    return users


def build_dashboard_for_user(db, user_id: str, user_email: str) -> Dict:
    """Build complete dashboard document for a user"""
    from google.cloud.firestore_v1.base_query import FieldFilter
    from firebase_admin import firestore as fs
    
    dashboard = {
        'user_id': user_id,
        'updated_at': datetime.utcnow().isoformat(),
        'groups': {},
        'pending_invitations': [],
        'summary': {
            'total_owed_to_you': 0.0,
            'total_you_owe': 0.0,
            'net_balance': 0.0,
            'group_count': 0,
            'active_group_count': 0
        }
    }
    
    try:
        # Get user's group memberships
        members_ref = db.collection('expense_group_members')
        member_query = (members_ref
            .where(filter=FieldFilter('user_id', '==', user_id))
            .where(filter=FieldFilter('is_active', '==', True)))
        
        member_docs = list(member_query.stream())
        group_ids = [doc.to_dict().get('group_id') for doc in member_docs]
        
        if not group_ids:
            logger.info("User %s has no active group memberships", user_id)
            return dashboard
        
        # Batch fetch groups
        group_refs = [db.collection('expense_groups').document(gid) for gid in group_ids]
        group_docs = db.get_all(group_refs)
        
        # Batch fetch balances
        balance_refs = [db.collection('expense_group_balances').document(gid) for gid in group_ids]
        balance_docs = db.get_all(balance_refs)
        
        # Build maps
        balance_map = {doc.id: doc.to_dict() for doc in balance_docs if doc.exists}
        
        total_owed = 0.0
        total_owes = 0.0
        
        for group_doc in group_docs:
            if not group_doc.exists:
                continue
            
            group_data = group_doc.to_dict()
            group_id = group_doc.id
            
            # Skip deleted groups
            if group_data.get('is_deleted'):
                continue
            
            # Get balances
            balance_data = balance_map.get(group_id, {})
            balances = balance_data.get('balances', {})
            user_balance = float(balances.get(user_id, 0))
            
            if user_balance > 0:
                total_owed += user_balance
            else:
                total_owes += abs(user_balance)
            
            # Get all members for this group
            group_members_query = (members_ref
                .where(filter=FieldFilter('group_id', '==', group_id))
                .where(filter=FieldFilter('is_active', '==', True)))
            
            group_member_docs = list(group_members_query.stream())
            members = []
            for m_doc in group_member_docs:
                m_data = m_doc.to_dict()
                members.append({
                    'user_id': m_data.get('user_id'),
                    'display_name': m_data.get('display_name', 'Unknown'),
                    'role': m_data.get('role', 'member')
                })
            
            # Fetch recent expenses (last 20)
            expenses_ref = db.collection('expense_expenses')
            expenses_query = (expenses_ref
                .where(filter=FieldFilter('group_id', '==', group_id))
                .where(filter=FieldFilter('is_deleted', '==', False))
                .order_by('created_at', direction=fs.Query.DESCENDING)
                .limit(20))
            
            expense_docs = list(expenses_query.stream())
            recent_expenses = []
            for e_doc in expense_docs:
                e_data = e_doc.to_dict()
                recent_expenses.append({
                    'expense_id': e_data.get('expense_id'),
                    'description': e_data.get('description'),
                    'amount': float(e_data.get('amount', 0)),
                    'currency': e_data.get('currency', 'USD'),
                    'paid_by': e_data.get('paid_by'),
                    'paid_by_name': e_data.get('paid_by_name'),
                    'split_type': e_data.get('split_type'),
                    'category': e_data.get('category'),
                    'expense_date': e_data.get('expense_date'),
                    'created_at': e_data.get('created_at'),
                    'is_edited': e_data.get('is_edited', False)
                })
            
            # Fetch recent settlements (last 10)
            settlements_ref = db.collection('expense_settlements')
            settlements_query = (settlements_ref
                .where(filter=FieldFilter('group_id', '==', group_id))
                .order_by('created_at', direction=fs.Query.DESCENDING)
                .limit(10))
            
            settlement_docs = list(settlements_query.stream())
            recent_settlements = []
            for s_doc in settlement_docs:
                s_data = s_doc.to_dict()
                recent_settlements.append({
                    'settlement_id': s_data.get('settlement_id'),
                    'from_user_id': s_data.get('from_user_id'),
                    'to_user_id': s_data.get('to_user_id'),
                    'amount': float(s_data.get('amount', 0)),
                    'currency': s_data.get('currency', 'USD'),
                    'status': s_data.get('status'),
                    'created_at': s_data.get('created_at')
                })
            
            # Add group to dashboard
            dashboard['groups'][group_id] = {
                'group_id': group_id,
                'name': group_data.get('name', 'Unknown Group'),
                'currency': group_data.get('currency', 'USD'),
                'created_by': group_data.get('created_by'),
                'created_at': group_data.get('created_at'),
                'member_count': len(members),
                'your_balance': user_balance,
                'total_spent': group_data.get('total_spent', 0),
                'expense_count': group_data.get('expense_count', len(recent_expenses)),
                'is_settled': abs(user_balance) < 0.01,
                'members': members,
                'balances': balances,
                'recent_expenses': recent_expenses,
                'recent_settlements': recent_settlements
            }
        
        # Fetch pending invitations
        if user_email:
            invitations_ref = db.collection('expense_invitations')
            inv_query = (invitations_ref
                .where(filter=FieldFilter('invitee_email', '==', user_email.lower()))
                .where(filter=FieldFilter('status', '==', 'pending')))
            
            inv_docs = list(inv_query.stream())
            for inv_doc in inv_docs:
                inv_data = inv_doc.to_dict()
                dashboard['pending_invitations'].append({
                    'invitation_id': inv_data.get('invitation_id'),
                    'group_id': inv_data.get('group_id'),
                    'group_name': inv_data.get('group_name'),
                    'invited_by': inv_data.get('invited_by'),
                    'inviter_name': inv_data.get('inviter_name'),
                    'inviter_email': inv_data.get('inviter_email'),
                    'token': inv_data.get('token'),
                    'created_at': inv_data.get('created_at'),
                    'expires_at': inv_data.get('expires_at')
                })
        
        # Update summary
        dashboard['summary']['total_owed_to_you'] = total_owed
        dashboard['summary']['total_you_owe'] = total_owes
        dashboard['summary']['net_balance'] = total_owed - total_owes
        dashboard['summary']['group_count'] = len(dashboard['groups'])
        dashboard['summary']['active_group_count'] = len([
            g for g in dashboard['groups'].values() 
            if not g['is_settled']
        ])
        
    except Exception as e:
        logger.error("Error building dashboard for user %s: %s", user_id, e)
        import traceback
        traceback.print_exc()
    
    return dashboard


def migrate_user(db, user: Dict, dry_run: bool = False) -> bool:
    """Migrate a single user to extreme dashboard"""
    user_id = user['user_id']
    user_email = user.get('email', '')
    
    logger.info("Processing user: %s (%s)", user_id, user_email or 'no email')
    
    # Build dashboard
    dashboard = build_dashboard_for_user(db, user_id, user_email)
    
    # Calculate size
    import json
    size_bytes = len(json.dumps(dashboard).encode('utf-8'))
    size_kb = size_bytes / 1024
    
    logger.info(
        "  Groups: %d, Invitations: %d, Size: %.1f KB",
        len(dashboard['groups']),
        len(dashboard['pending_invitations']),
        size_kb
    )
    
    if size_bytes > 900000:  # 90% of 1MB limit
        logger.warning("  WARNING: Dashboard size approaching 1MB limit!")
    
    if dry_run:
        logger.info("  [DRY-RUN] Would save dashboard for user %s", user_id)
        return True
    
    try:
        # Save dashboard
        dashboard_ref = db.collection('expense_user_dashboards').document(user_id)
        dashboard_ref.set(dashboard)
        logger.info("  Saved dashboard for user %s", user_id)
        return True
    except Exception as e:
        logger.error("  Failed to save dashboard for user %s: %s", user_id, e)
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Migrate users to extreme dashboard pattern'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without making changes'
    )
    parser.add_argument(
        '--user',
        type=str,
        help='Migrate a specific user only'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=0,
        help='Maximum number of users to migrate (0 = all)'
    )
    
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("Phase 21 Migration: Extreme Dashboard Documents")
    logger.info("=" * 60)
    
    if args.dry_run:
        logger.info("DRY-RUN MODE - No changes will be made")
    
    # Initialize Firestore
    db = get_firestore_client()
    
    if args.user:
        # Migrate single user
        user_doc = db.collection('users').document(args.user).get()
        if user_doc.exists:
            user_data = user_doc.to_dict()
            users = [{
                'user_id': args.user,
                'email': user_data.get('email', ''),
                'display_name': user_data.get('display_name', '')
            }]
        else:
            logger.error("User not found: %s", args.user)
            sys.exit(1)
    else:
        # Get all users
        users = get_all_users(db)
    
    if args.limit > 0:
        users = users[:args.limit]
        logger.info("Limited to %d users", args.limit)
    
    # Migrate users
    success_count = 0
    fail_count = 0
    
    for i, user in enumerate(users, 1):
        logger.info("[%d/%d] Processing user...", i, len(users))
        if migrate_user(db, user, dry_run=args.dry_run):
            success_count += 1
        else:
            fail_count += 1
    
    logger.info("=" * 60)
    logger.info("Migration complete!")
    logger.info("  Success: %d", success_count)
    logger.info("  Failed: %d", fail_count)
    logger.info("=" * 60)


if __name__ == '__main__':
    main()
