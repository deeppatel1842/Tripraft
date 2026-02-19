"""
Email Configuration Module
Controls which email notifications are enabled/disabled
"""
import os


class EmailConfig:
    """Email notification configuration"""
    
    def __init__(self):
        # Email types that can be enabled/disabled
        self._enabled = {
            'invitation': os.getenv('EMAIL_INVITATION_ENABLED', 'true').lower() == 'true',
            'expense_added': os.getenv('EMAIL_EXPENSE_ADDED_ENABLED', 'false').lower() == 'true',
            'expense_deleted': os.getenv('EMAIL_EXPENSE_DELETED_ENABLED', 'false').lower() == 'true',
            'settlement': os.getenv('EMAIL_SETTLEMENT_ENABLED', 'false').lower() == 'true',
            'group_planner_invitation': os.getenv('EMAIL_GROUP_PLANNER_INVITATION_ENABLED', 'true').lower() == 'true',
        }
    
    def is_enabled(self, email_type: str) -> bool:
        """
        Check if a specific email type is enabled.
        
        Args:
            email_type: Type of email ('invitation', 'expense_added', etc.)
            
        Returns:
            True if enabled, False otherwise
        """
        return self._enabled.get(email_type, False)
    
    def enable(self, email_type: str) -> None:
        """Enable a specific email type"""
        self._enabled[email_type] = True
    
    def disable(self, email_type: str) -> None:
        """Disable a specific email type"""
        self._enabled[email_type] = False


# Singleton instance
email_config = EmailConfig()
