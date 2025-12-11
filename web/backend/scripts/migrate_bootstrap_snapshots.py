"""
Phase 20: Bootstrap Snapshots Migration Script

Backfills the expense_bootstrap_snapshots collection for existing groups.
This creates pre-computed view documents that reduce mega-bootstrap reads
from ~10-12R to 1R per group.

Usage:
    python scripts/migrate_bootstrap_snapshots.py [--dry-run] [--user USER_ID] [--group GROUP_ID]
    
Options:
    --dry-run     Don't write to Firestore, just print what would be created
    --user        Only migrate snapshots for a specific user
    --group       Only migrate snapshots for a specific group
"""

import sys
import os
import argparse
import logging
from datetime import datetime
from typing import Dict, List, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from expense_engine.repositories import (
    GroupRepository,
    ExpenseRepository,
    BalanceRepository,
    InvitationRepository,
    UserRepository,
    SnapshotRepository
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SnapshotMigrator:
    """Migrates existing data to bootstrap snapshots"""
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.group_repo = GroupRepository()
        self.expense_repo = ExpenseRepository()
        self.balance_repo = BalanceRepository()
        self.invitation_repo = InvitationRepository()
        self.user_repo = UserRepository()
        self.snapshot_repo = SnapshotRepository()
        
        self.stats = {
            'groups_processed': 0,
            'snapshots_created': 0,
            'snapshots_skipped': 0,
            'errors': 0
        }
    
    def migrate_all(self, user_id: Optional[str] = None, group_id: Optional[str] = None):
        """
        Migrate all groups or filtered subset
        
        Args:
            user_id: If provided, only migrate groups for this user
            group_id: If provided, only migrate this specific group
        """
        logger.info("Starting bootstrap snapshot migration (dry_run=%s)", self.dry_run)
        
        if group_id:
            # Migrate specific group
            groups = [self.group_repo.get_by_id(group_id)]
            groups = [g for g in groups if g]  # Filter None
        elif user_id:
            # Migrate groups for specific user
            groups = self.group_repo.get_user_groups(user_id)
        else:
            # Migrate all groups
            groups = self._get_all_groups()
        
        logger.info("Found %d groups to process", len(groups))
        
        for group in groups:
            self._migrate_group(group)
        
        self._print_summary()
    
    def _get_all_groups(self) -> List[Dict]:
        """Get all groups from Firestore"""
        try:
            # Query all groups - this could be expensive for large datasets
            docs = self.group_repo.collection.stream()
            groups = []
            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id
                groups.append(data)
            return groups
        except Exception as exc:
            logger.error("Failed to get all groups: %s", exc)
            return []
    
    def _migrate_group(self, group: Dict):
        """Create snapshots for all members of a group"""
        group_id = group.get('id') or group.get('group_id')
        if not group_id:
            logger.warning("Group has no ID, skipping")
            return
        
        self.stats['groups_processed'] += 1
        
        members = group.get('members', [])
        if not members:
            logger.warning("Group %s has no members, skipping", group_id)
            return
        
        logger.info("Processing group: %s (%s) with %d members", 
                   group.get('name', 'Unknown'), group_id, len(members))
        
        # Get shared data for all members
        group_info = self._build_group_info(group)
        member_details = self._get_member_details(members)
        balances = self._get_group_balances(group_id)
        recent_expenses = self._get_recent_expenses(group_id)
        expense_stats = self._get_expense_stats(group_id)
        
        # Create snapshot for each member
        for member_id in members:
            self._create_member_snapshot(
                user_id=member_id,
                group_id=group_id,
                group_info=group_info,
                member_details=member_details,
                balances=balances,
                recent_expenses=recent_expenses,
                expense_stats=expense_stats
            )
    
    def _build_group_info(self, group: Dict) -> Dict:
        """Build group info object"""
        return {
            'name': group.get('name', 'Unknown Group'),
            'currency': group.get('currency', 'USD'),
            'createdAt': group.get('created_at'),
            'memberCount': len(group.get('members', []))
        }
    
    def _get_member_details(self, member_ids: List[str]) -> List[Dict]:
        """Get user details for all members"""
        details = []
        for uid in member_ids:
            try:
                user = self.user_repo.get_by_id(uid)
                if user:
                    details.append({
                        'userId': uid,
                        'displayName': user.get('display_name', 'Unknown'),
                        'email': user.get('email', ''),
                        'photoURL': user.get('photo_url', '')
                    })
                else:
                    details.append({
                        'userId': uid,
                        'displayName': 'Unknown User',
                        'email': '',
                        'photoURL': ''
                    })
            except Exception as exc:
                logger.warning("Failed to get user %s: %s", uid, exc)
                details.append({
                    'userId': uid,
                    'displayName': 'Unknown User',
                    'email': '',
                    'photoURL': ''
                })
        return details
    
    def _get_group_balances(self, group_id: str) -> Dict[str, float]:
        """Get current balances for group"""
        try:
            balance_doc = self.balance_repo.get_group_balances(group_id)
            if balance_doc:
                return balance_doc.get('balances', {})
            return {}
        except Exception as exc:
            logger.warning("Failed to get balances for group %s: %s", group_id, exc)
            return {}
    
    def _get_recent_expenses(self, group_id: str, limit: int = 5) -> List[Dict]:
        """Get recent expenses for group"""
        try:
            expenses = self.expense_repo.get_group_expenses(group_id, limit=limit)
            return [
                {
                    'id': exp.get('expense_id') or exp.get('id'),
                    'description': exp.get('description', ''),
                    'amount': exp.get('amount', 0),
                    'currency': exp.get('currency', 'USD'),
                    'paidBy': exp.get('paid_by', ''),
                    'date': exp.get('expense_date')
                }
                for exp in expenses
            ]
        except Exception as exc:
            logger.warning("Failed to get expenses for group %s: %s", group_id, exc)
            return []
    
    def _get_expense_stats(self, group_id: str) -> Dict:
        """Get expense statistics for group"""
        try:
            # This is expensive but only done once during migration
            expenses = self.expense_repo.get_group_expenses(group_id, limit=1000)
            total = sum(exp.get('amount', 0) for exp in expenses)
            
            last_activity = None
            if expenses:
                dates = [exp.get('expense_date') or exp.get('created_at') for exp in expenses]
                dates = [d for d in dates if d]
                if dates:
                    last_activity = max(dates)
            
            return {
                'totalExpenses': total,
                'expenseCount': len(expenses),
                'lastActivity': last_activity
            }
        except Exception as exc:
            logger.warning("Failed to get expense stats for group %s: %s", group_id, exc)
            return {'totalExpenses': 0, 'expenseCount': 0, 'lastActivity': None}
    
    def _create_member_snapshot(
        self,
        user_id: str,
        group_id: str,
        group_info: Dict,
        member_details: List[Dict],
        balances: Dict[str, float],
        recent_expenses: List[Dict],
        expense_stats: Dict
    ):
        """Create snapshot for a specific user/group combination"""
        doc_id = self.snapshot_repo.make_doc_id(user_id, group_id)
        
        # Check if snapshot already exists
        existing = self.snapshot_repo.get_by_id(doc_id)
        if existing:
            logger.debug("Snapshot already exists: %s, skipping", doc_id)
            self.stats['snapshots_skipped'] += 1
            return
        
        now = datetime.utcnow().isoformat()
        
        snapshot_data = {
            'userId': user_id,
            'groupId': group_id,
            'groupInfo': group_info,
            'members': member_details,
            'balances': balances,
            'yourBalance': balances.get(user_id, 0.0),
            'recentExpenses': recent_expenses,
            'pendingInvitationsCount': 0,  # Can be updated later
            'totalExpenses': expense_stats.get('totalExpenses', 0),
            'expenseCount': expense_stats.get('expenseCount', 0),
            'lastActivity': expense_stats.get('lastActivity') or now,
            'lastUpdated': now,
            'version': 1
        }
        
        if self.dry_run:
            logger.info("[DRY RUN] Would create snapshot: %s", doc_id)
            logger.debug("  Data: %s", snapshot_data)
        else:
            try:
                self.snapshot_repo.create(doc_id, snapshot_data)
                logger.info("Created snapshot: %s", doc_id)
                self.stats['snapshots_created'] += 1
            except Exception as exc:
                logger.error("Failed to create snapshot %s: %s", doc_id, exc)
                self.stats['errors'] += 1
    
    def _print_summary(self):
        """Print migration summary"""
        logger.info("=" * 50)
        logger.info("Migration Summary")
        logger.info("=" * 50)
        logger.info("Groups processed: %d", self.stats['groups_processed'])
        logger.info("Snapshots created: %d", self.stats['snapshots_created'])
        logger.info("Snapshots skipped (already exist): %d", self.stats['snapshots_skipped'])
        logger.info("Errors: %d", self.stats['errors'])
        
        if self.dry_run:
            logger.info("")
            logger.info("This was a DRY RUN - no data was written")


def main():
    parser = argparse.ArgumentParser(
        description='Migrate existing data to bootstrap snapshots (Phase 20)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Print what would be done without making changes'
    )
    parser.add_argument(
        '--user',
        type=str,
        help='Only migrate snapshots for a specific user ID'
    )
    parser.add_argument(
        '--group',
        type=str,
        help='Only migrate snapshots for a specific group ID'
    )
    
    args = parser.parse_args()
    
    migrator = SnapshotMigrator(dry_run=args.dry_run)
    migrator.migrate_all(user_id=args.user, group_id=args.group)


if __name__ == '__main__':
    main()
