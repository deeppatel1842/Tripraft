"""
Email Configuration System
Centralized control for all email notifications across the application
Toggle individual email types without code changes
"""

import os
from typing import Dict


class EmailConfig:
    """
    Email notification configuration
    Enable/disable specific email types independently
    
    QUICK TOGGLE: Set email type to False to disable
    Example: 'invitation': False  # Disables all invitation emails
    """
    
    # Master switch - disables ALL emails if False
    MASTER_ENABLED: bool = True
    
    # Individual email type controls - EASY ON/OFF SWITCHES
    EMAIL_TYPES: Dict[str, bool] = {
        # Invitation emails (Group Planner + Expense Engine)
        'invitation': True,                    # ✉️ Group/expense invitations
        
        # Expense notifications
        'expense_added': True,                 # 💰 New expense created
        'expense_deleted': True,               # 🗑️ Expense deleted
        'expense_updated': False,              # 📝 Future: expense modifications
        
        # Settlement notifications
        'settlement': True,                    # 💳 Payment/settlement marked
        
        # Group notifications
        'group_created': False,                # 🎉 Future: new group created
        'member_added': False,                 # 👥 Future: member added to group
        'member_removed': False,               # ❌ Future: member removed
        
        # Reminder emails (future)
        'payment_reminder': False,             # ⏰ Payment due reminders
        'balance_summary': False,              # 📊 Weekly/monthly balance summaries
    }
    
    @classmethod
    def is_enabled(cls, email_type: str) -> bool:
        """
        Check if a specific email type is enabled
        
        Args:
            email_type: Type of email to check (e.g., 'invitation', 'expense_added')
            
        Returns:
            True if email should be sent, False otherwise
        """
        # Check master switch first
        if not cls.MASTER_ENABLED:
            return False
        
        # Check specific email type
        return cls.EMAIL_TYPES.get(email_type, False)
    
    @classmethod
    def disable_all(cls):
        """Disable all email notifications"""
        cls.MASTER_ENABLED = False
    
    @classmethod
    def enable_all(cls):
        """Enable all email notifications (respects individual type settings)"""
        cls.MASTER_ENABLED = True
    
    @classmethod
    def set_email_type(cls, email_type: str, enabled: bool):
        """
        Enable or disable a specific email type
        
        Args:
            email_type: Type of email (e.g., 'invitation')
            enabled: True to enable, False to disable
        """
        if email_type in cls.EMAIL_TYPES:
            cls.EMAIL_TYPES[email_type] = enabled
    
    @classmethod
    def get_enabled_types(cls) -> list:
        """Get list of all enabled email types"""
        if not cls.MASTER_ENABLED:
            return []
        return [email_type for email_type, enabled in cls.EMAIL_TYPES.items() if enabled]


# Global configuration instance
email_config = EmailConfig()
