"""
User-Facing Messages
All error messages, success messages, and email templates centralized.
Makes internationalization (i18n) easier in the future.
"""

from typing import Dict


# =============================================================================
# SUCCESS MESSAGES
# =============================================================================

class SuccessMessages:
    """Success response messages"""
    
    # User messages
    USER_CREATED = "User account created successfully"
    USER_UPDATED = "User profile updated successfully"
    USER_DELETED = "User account deleted successfully"
    
    # Group messages
    GROUP_CREATED = "Group created successfully"
    GROUP_UPDATED = "Group updated successfully"
    GROUP_DELETED = "Group deleted successfully"
    MEMBER_ADDED = "Member added to group successfully"
    MEMBER_REMOVED = "Member removed from group successfully"
    
    # Expense messages
    EXPENSE_CREATED = "Expense added successfully"
    EXPENSE_UPDATED = "Expense updated successfully"
    EXPENSE_DELETED = "Expense deleted successfully"
    
    # Invitation messages
    INVITATION_SENT = "Invitation sent successfully"
    INVITATION_ACCEPTED = "Invitation accepted successfully"
    INVITATION_REJECTED = "Invitation rejected"
    
    # Settlement messages
    SETTLEMENT_CREATED = "Settlement recorded successfully"
    SETTLEMENT_COMPLETED = "Payment marked as completed"
    SETTLEMENT_CANCELLED = "Settlement cancelled"
    
    # Balance messages
    BALANCE_RETRIEVED = "Balance retrieved successfully"
    BALANCES_CALCULATED = "Balances calculated successfully"


# =============================================================================
# ERROR MESSAGES
# =============================================================================

class ErrorMessages:
    """Error response messages"""
    
    # Generic errors
    INTERNAL_ERROR = "An internal error occurred. Please try again."
    VALIDATION_ERROR = "Validation error in request data"
    UNAUTHORIZED = "Authentication required"
    FORBIDDEN = "You don't have permission to perform this action"
    NOT_FOUND = "Resource not found"
    CONFLICT = "Resource already exists"
    RATE_LIMIT_EXCEEDED = "Rate limit exceeded. Please try again later."
    
    # User errors
    USER_NOT_FOUND = "User not found"
    USER_ALREADY_EXISTS = "User already exists with this email or username"
    INVALID_CREDENTIALS = "Invalid email or password"
    USERNAME_TAKEN = "Username is already taken"
    EMAIL_TAKEN = "Email is already registered"
    WEAK_PASSWORD = "Password does not meet security requirements"
    
    # Group errors
    GROUP_NOT_FOUND = "Group not found"
    NOT_GROUP_MEMBER = "You are not a member of this group"
    ALREADY_GROUP_MEMBER = "User is already a member of this group"
    INSUFFICIENT_PERMISSIONS = "You don't have permission to perform this action in this group"
    GROUP_NAME_REQUIRED = "Group name is required"
    MIN_MEMBERS_REQUIRED = "Group must have at least 2 members"
    MAX_MEMBERS_EXCEEDED = "Group has reached maximum member limit"
    
    # Expense errors
    EXPENSE_NOT_FOUND = "Expense not found"
    INVALID_AMOUNT = "Invalid expense amount"
    AMOUNT_TOO_SMALL = "Expense amount must be at least $0.01"
    AMOUNT_TOO_LARGE = "Expense amount exceeds maximum limit"
    INVALID_SPLIT_TYPE = "Invalid split type"
    INVALID_SPLIT_AMOUNTS = "Split amounts are invalid"
    SPLIT_SUM_MISMATCH = "Split amounts don't sum to total expense amount"
    INVALID_CATEGORY = "Invalid expense category"
    DESCRIPTION_REQUIRED = "Expense description is required"
    NO_SPLITS_PROVIDED = "At least one split is required"
    
    # Invitation errors
    INVITATION_NOT_FOUND = "Invitation not found"
    INVITATION_EXPIRED = "This invitation has expired"
    INVITATION_ALREADY_ACCEPTED = "This invitation has already been accepted"
    INVITATION_ALREADY_REJECTED = "This invitation has already been rejected"
    CANNOT_INVITE_SELF = "You cannot invite yourself to a group"
    USER_ALREADY_INVITED = "This user has already been invited"
    
    # Settlement errors
    SETTLEMENT_NOT_FOUND = "Settlement not found"
    INVALID_SETTLEMENT = "Invalid settlement data"
    SETTLEMENT_ALREADY_COMPLETED = "This settlement is already completed"
    SETTLEMENT_ALREADY_CANCELLED = "This settlement is already cancelled"
    CANNOT_SETTLE_WITH_SELF = "You cannot create a settlement with yourself"
    NOTHING_TO_SETTLE = "No outstanding balance to settle"
    
    # Validation errors
    MISSING_REQUIRED_FIELD = "Required field is missing: {field}"
    INVALID_FIELD_FORMAT = "Invalid format for field: {field}"
    FIELD_TOO_SHORT = "Field '{field}' is too short. Minimum length: {min_length}"
    FIELD_TOO_LONG = "Field '{field}' is too long. Maximum length: {max_length}"
    INVALID_EMAIL_FORMAT = "Invalid email format"
    INVALID_CURRENCY = "Invalid or unsupported currency code"
    INVALID_DATE_FORMAT = "Invalid date format. Use ISO 8601 format"
    
    # Database errors
    DATABASE_ERROR = "Database operation failed"
    CACHE_ERROR = "Cache operation failed"
    FIRESTORE_TIMEOUT = "Database operation timed out"
    
    # External service errors
    EMAIL_SEND_FAILED = "Failed to send email notification"
    EXTERNAL_SERVICE_ERROR = "External service temporarily unavailable"
    
    # Authentication errors
    TOKEN_EXPIRED = "Authentication token has expired"
    TOKEN_INVALID = "Invalid authentication token"
    TOKEN_MISSING = "Authentication token is missing"


# =============================================================================
# EMAIL TEMPLATES
# =============================================================================

class EmailTemplates:
    """Email message templates"""
    
    @staticmethod
    def group_invitation(inviter_name: str, group_name: str, invitation_link: str) -> Dict[str, str]:
        """Group invitation email template"""
        subject = f"{inviter_name} invited you to join '{group_name}' on TripRaft"
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="color: white; margin: 0;">TripRaft</h1>
            </div>
            
            <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px;">
                <h2 style="color: #333; margin-top: 0;">You're Invited!</h2>
                
                <p style="font-size: 16px;">
                    <strong>{inviter_name}</strong> has invited you to join the group 
                    <strong>{group_name}</strong> on TripRaft.
                </p>
                
                <p>
                    TripRaft helps you track shared expenses and settle up with friends easily.
                </p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{invitation_link}" 
                       style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                              color: white; 
                              padding: 15px 40px; 
                              text-decoration: none; 
                              border-radius: 5px; 
                              display: inline-block;
                              font-weight: bold;">
                        Accept Invitation
                    </a>
                </div>
                
                <p style="font-size: 14px; color: #666; margin-top: 30px;">
                    This invitation will expire in 7 days.
                </p>
                
                <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
                
                <p style="font-size: 12px; color: #999;">
                    If you didn't expect this invitation, you can safely ignore this email.
                </p>
            </div>
        </body>
        </html>
        """
        
        text_body = f"""
        You're invited to TripRaft!
        
        {inviter_name} has invited you to join the group "{group_name}" on TripRaft.
        
        TripRaft helps you track shared expenses and settle up with friends easily.
        
        Accept this invitation by clicking the link below:
        {invitation_link}
        
        This invitation will expire in 7 days.
        
        If you didn't expect this invitation, you can safely ignore this email.
        """
        
        return {
            'subject': subject,
            'html': html_body,
            'text': text_body
        }
    
    @staticmethod
    def expense_added(user_name: str, expense_description: str, amount: float, 
                     currency: str, user_share: float, payer_name: str, 
                     group_name: str) -> Dict[str, str]:
        """Expense added notification email"""
        subject = f"New expense in {group_name}: {expense_description}"
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="color: white; margin: 0;">TripRaft</h1>
            </div>
            
            <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px;">
                <h2 style="color: #333; margin-top: 0;">New Expense Added</h2>
                
                <p>Hi {user_name},</p>
                
                <p>
                    <strong>{payer_name}</strong> added a new expense in 
                    <strong>{group_name}</strong>:
                </p>
                
                <div style="background: white; padding: 20px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #667eea;">
                    <p style="margin: 0; font-size: 18px; font-weight: bold;">
                        {expense_description}
                    </p>
                    <p style="margin: 10px 0 0 0; font-size: 24px; color: #667eea;">
                        {currency}{amount:.2f}
                    </p>
                    <p style="margin: 10px 0 0 0; color: #666;">
                        Your share: <strong>{currency}{user_share:.2f}</strong>
                    </p>
                </div>
                
                <p>
                    You owe <strong>{currency}{user_share:.2f}</strong> to {payer_name}.
                </p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="https://tripraft.com/groups/{group_name}" 
                       style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                              color: white; 
                              padding: 15px 40px; 
                              text-decoration: none; 
                              border-radius: 5px; 
                              display: inline-block;
                              font-weight: bold;">
                        View Group
                    </a>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_body = f"""
        Hi {user_name},
        
        {payer_name} added a new expense in {group_name}:
        
        {expense_description}
        Total: {currency}{amount:.2f}
        Your share: {currency}{user_share:.2f}
        
        You owe {currency}{user_share:.2f} to {payer_name}.
        
        View group: https://tripraft.com/groups/{group_name}
        """
        
        return {
            'subject': subject,
            'html': html_body,
            'text': text_body
        }
    
    @staticmethod
    def settlement_reminder(user_name: str, creditor_name: str, amount: float, 
                          currency: str, group_name: str) -> Dict[str, str]:
        """Settlement reminder email"""
        subject = f"Reminder: You owe {currency}{amount:.2f} to {creditor_name}"
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="color: white; margin: 0;">TripRaft</h1>
            </div>
            
            <div style="background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px;">
                <h2 style="color: #333; margin-top: 0;">Payment Reminder</h2>
                
                <p>Hi {user_name},</p>
                
                <p>
                    This is a friendly reminder that you have an outstanding balance in 
                    <strong>{group_name}</strong>.
                </p>
                
                <div style="background: white; padding: 20px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #f39c12;">
                    <p style="margin: 0;">You owe:</p>
                    <p style="margin: 10px 0; font-size: 32px; color: #f39c12; font-weight: bold;">
                        {currency}{amount:.2f}
                    </p>
                    <p style="margin: 0; color: #666;">
                        to {creditor_name}
                    </p>
                </div>
                
                <p>
                    Please settle up when convenient.
                </p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="https://tripraft.com/groups/{group_name}" 
                       style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                              color: white; 
                              padding: 15px 40px; 
                              text-decoration: none; 
                              border-radius: 5px; 
                              display: inline-block;
                              font-weight: bold;">
                        Settle Up
                    </a>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_body = f"""
        Hi {user_name},
        
        This is a friendly reminder that you have an outstanding balance in {group_name}.
        
        You owe {currency}{amount:.2f} to {creditor_name}.
        
        Please settle up when convenient.
        
        View group: https://tripraft.com/groups/{group_name}
        """
        
        return {
            'subject': subject,
            'html': html_body,
            'text': text_body
        }


# =============================================================================
# VALIDATION MESSAGES
# =============================================================================

class ValidationMessages:
    """Field validation error messages"""
    
    @staticmethod
    def required_field(field_name: str) -> str:
        return f"{field_name} is required"
    
    @staticmethod
    def invalid_format(field_name: str) -> str:
        return f"Invalid format for {field_name}"
    
    @staticmethod
    def min_length(field_name: str, min_length: int) -> str:
        return f"{field_name} must be at least {min_length} characters"
    
    @staticmethod
    def max_length(field_name: str, max_length: int) -> str:
        return f"{field_name} must not exceed {max_length} characters"
    
    @staticmethod
    def min_value(field_name: str, min_value: float) -> str:
        return f"{field_name} must be at least {min_value}"
    
    @staticmethod
    def max_value(field_name: str, max_value: float) -> str:
        return f"{field_name} must not exceed {max_value}"
    
    @staticmethod
    def invalid_choice(field_name: str, valid_choices: list) -> str:
        choices_str = ", ".join(map(str, valid_choices))
        return f"{field_name} must be one of: {choices_str}"


# Export all message classes
__all__ = [
    'SuccessMessages',
    'ErrorMessages',
    'EmailTemplates',
    'ValidationMessages',
]
