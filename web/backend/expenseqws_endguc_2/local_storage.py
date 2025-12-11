"""
Local Database Storage for Expenses
Saves data to JSON files in database/expense_database
STRICT PATH: Uses Path(__file__).parent.parent / 'database' / 'expense_database'
All user expenses stored in single file per user: users/{user_id}.json
"""
import json
import os
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# STRICT DATABASE PATH - DO NOT CHANGE
DATABASE_BASE_PATH = Path(__file__).parent.parent / 'database' / 'expense_database'

class LocalExpenseStorage:
    """Local JSON file storage for expenses"""
    
    def __init__(self):
        """Initialize local storage with strict path"""
        # Use the strict database path
        self.base_dir = DATABASE_BASE_PATH
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        self.users_dir = self.base_dir / 'users'
        self.groups_dir = self.base_dir / 'groups'
        self.expenses_dir = self.base_dir / 'expenses'  # ✨ NEW: Centralized expense storage
        self.participants_dir = self.base_dir / 'expense_participants'  # ✨ NEW: Track participants
        
        for directory in [self.users_dir, self.groups_dir, self.expenses_dir, self.participants_dir]:
            directory.mkdir(exist_ok=True)
    
    def _get_user_file(self, user_id):
        """Get user's expense file path"""
        return self.users_dir / f"{user_id}.json"
    
    def _load_user_data(self, user_id):
        """Load all data for a user"""
        file_path = self._get_user_file(user_id)
        if file_path.exists():
            with open(file_path, 'r') as f:
                return json.load(f)
        return {
            'user_id': user_id,
            'expenses': [],
            'profile': {},
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
    
    def _save_user_data(self, user_id, data):
        """Save all data for a user"""
        file_path = self._get_user_file(user_id)
        data['updated_at'] = datetime.utcnow().isoformat()
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    
    def save_user(self, user_data):
        """Save user profile data"""
        try:
            user_id = user_data.get('uid')
            if not user_id:
                return False
            
            data = self._load_user_data(user_id)
            data['profile'] = user_data
            self._save_user_data(user_id, data)
            return True
        except Exception as e:
            logger.error(f"Error saving user profile locally: {e}")
            return False
    
    def save_group(self, group_data):
        """Save group data to JSON file"""
        try:
            group_id = group_data.get('group_id') or group_data.get('id')
            if not group_id:
                return False
            
            file_path = self.groups_dir / f"{group_id}.json"
            
            # If file exists, preserve existing data and update
            if file_path.exists():
                with open(file_path, 'r') as f:
                    existing_data = json.load(f)
                # Update with new data
                existing_data.update(group_data)
                existing_data['updated_at'] = datetime.utcnow().isoformat()
                group_data = existing_data
            
            with open(file_path, 'w') as f:
                json.dump(group_data, f, indent=2, default=str)
            
            logger.info(f"Group {group_id} saved locally with members: {group_data.get('members', [])}")
            return True
        except Exception as e:
            logger.error(f"Error saving group locally: {e}")
            return False
    
    def save_expense(self, expense_data):
        """
        Save expense data to centralized storage (NO MORE DUPLICATION!)
        Stores expense once in expenses/{expense_id}.json
        Tracks participants in expense_participants/{expense_id}.json
        """
        try:
            expense_id = expense_data.get('expense_id') or expense_data.get('id')
            
            if not expense_id:
                logger.error("Cannot save expense: missing expense_id")
                return False
            
            # Save expense to central location (SINGLE SOURCE OF TRUTH)
            expense_file = self.expenses_dir / f"{expense_id}.json"
            with open(expense_file, 'w') as f:
                json.dump(expense_data, f, indent=2, default=str)
            
            # Track participants (who's involved in this expense)
            participants = []
            
            # Add paid_by
            paid_by = expense_data.get('paid_by')
            if paid_by:
                participants.append(paid_by)
            
            # Add all users from splits
            splits = expense_data.get('splits', [])
            for split in splits:
                user_id = split.get('user_id')
                if user_id and user_id not in participants:
                    participants.append(user_id)
            
            # Save participant mapping
            participant_file = self.participants_dir / f"{expense_id}.json"
            participant_data = {
                'expense_id': expense_id,
                'participants': participants,
                'participant_count': len(participants),
                'group_id': expense_data.get('group_id'),
                'updated_at': datetime.utcnow().isoformat()
            }
            with open(participant_file, 'w') as f:
                json.dump(participant_data, f, indent=2)
            
            logger.info(f"✅ Expense {expense_id} saved (1 file, {len(participants)} participants) - NO DUPLICATION!")
            return True
            
        except Exception as e:
            logger.error(f"Error saving expense locally: {e}")
            return False
    
    def get_user(self, user_id):
        """Get user profile data"""
        try:
            data = self._load_user_data(user_id)
            return data.get('profile') if data.get('profile') else None
        except Exception as e:
            logger.error(f"Error loading user profile locally: {e}")
            return None
    
    def get_group(self, group_id):
        """Get group data from JSON file"""
        try:
            file_path = self.groups_dir / f"{group_id}.json"
            if file_path.exists():
                with open(file_path, 'r') as f:
                    return json.load(f)
            return None
        except Exception as e:
            logger.error(f"Error loading group locally: {e}")
            return None
    
    def get_expense(self, expense_id):
        """Get expense data by ID from centralized storage"""
        try:
            expense_file = self.expenses_dir / f"{expense_id}.json"
            if expense_file.exists():
                with open(expense_file, 'r') as f:
                    return json.load(f)
            return None
        except Exception as e:
            logger.error(f"Error loading expense locally: {e}")
            return None
    
    def get_all_expenses(self, user_id=None, group_id=None):
        """
        Get all expenses, optionally filtered by user and/or group
        Uses centralized storage - NO MORE DUPLICATE WARNINGS!
        """
        try:
            all_expenses = []
            
            # Get all expenses from central storage
            for expense_file in self.expenses_dir.glob('*.json'):
                try:
                    with open(expense_file, 'r') as f:
                        expense = json.load(f)
                    
                    # Skip deleted expenses
                    if expense.get('is_deleted', False):
                        continue
                    
                    expense_id = expense.get('expense_id') or expense.get('id')
                    
                    # Check if user filter applies
                    if user_id:
                        participant_file = self.participants_dir / f"{expense_id}.json"
                        if participant_file.exists():
                            with open(participant_file, 'r') as pf:
                                participant_data = json.load(pf)
                                if user_id not in participant_data.get('participants', []):
                                    continue  # User not involved in this expense
                        else:
                            # No participant file, check expense data directly
                            participants = [expense.get('paid_by')]
                            for split in expense.get('splits', []):
                                participants.append(split.get('user_id'))
                            if user_id not in participants:
                                continue
                    
                    # Check if group filter applies
                    if group_id and expense.get('group_id') != group_id:
                        continue
                    
                    all_expenses.append(expense)
                    
                except Exception as e:
                    logger.error(f"Error loading expense from {expense_file}: {e}")
                    continue
            
            # Sort by created_at, newest first
            all_expenses.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
            logger.info(f"✅ Retrieved {len(all_expenses)} expenses (user={user_id}, group={group_id}) - NO DUPLICATES!")
            return all_expenses
            
        except Exception as e:
            logger.error(f"Error getting expenses: {e}")
            return []
    
    def update_expense(self, expense_id, updates):
        """
        Update expense in centralized storage
        
        Args:
            expense_id: The expense ID
            updates: Dictionary with fields to update (description, amount, category, date, etc.)
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            expense_file = self.expenses_dir / f"{expense_id}.json"
            
            if not expense_file.exists():
                logger.warning(f"Expense {expense_id} not found for update")
                return False
            
            # Load current expense
            with open(expense_file, 'r') as f:
                expense = json.load(f)
            
            # Update fields
            logger.info(f"✏️  Updating expense {expense_id}")
            logger.info(f"   Before: {expense.get('description')} - ${expense.get('amount')}")
            
            # Update basic fields
            if 'description' in updates:
                expense['description'] = updates['description']
            if 'amount' in updates:
                expense['amount'] = float(updates['amount'])
                # Update splits with new amount if equal split
                if expense.get('split_type') == 'EQUAL' and expense.get('splits'):
                    split_amount = expense['amount'] / len(expense['splits'])
                    for split in expense['splits']:
                        split['amount'] = round(split_amount, 2)
            if 'category' in updates:
                expense['category'] = updates['category']
            if 'date' in updates:
                expense['date'] = updates['date']
            if 'currency' in updates:
                expense['currency'] = updates['currency']
            
            # 🔧 CRITICAL FIX: Update paid_by and splits if provided
            if 'paid_by' in updates:
                expense['paid_by'] = updates['paid_by']
            if 'splits' in updates:
                expense['splits'] = updates['splits']
                # Ensure split amounts match expense amount
                if expense.get('split_type') == 'EQUAL':
                    split_amount = expense['amount'] / len(expense['splits'])
                    for split in expense['splits']:
                        split['amount'] = round(split_amount, 2)
            
            # Update timestamp
            expense['updated_at'] = datetime.utcnow().isoformat()
            
            # Save back
            with open(expense_file, 'w') as f:
                json.dump(expense, f, indent=2, default=str)
            
            logger.info(f"   After: {expense.get('description')} - ${expense.get('amount')}")
            logger.info(f"✅ Expense {expense_id} updated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error updating expense locally: {e}")
            return False
    
    def delete_expense(self, expense_id):
        """Soft delete expense from centralized storage"""
        try:
            expense_file = self.expenses_dir / f"{expense_id}.json"
            
            if not expense_file.exists():
                logger.warning(f"Expense {expense_id} not found for deletion")
                return False
            
            # Load expense and mark as deleted
            with open(expense_file, 'r') as f:
                expense = json.load(f)
            
            expense['is_deleted'] = True
            expense['deleted_at'] = datetime.utcnow().isoformat()
            
            # Save back
            with open(expense_file, 'w') as f:
                json.dump(expense, f, indent=2, default=str)
            
            logger.info(f"✅ Expense {expense_id} marked as deleted")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting expense locally: {e}")
            return False
    
# Global instance
local_storage = LocalExpenseStorage()
