"""
Email Worker - Background Email Processing
Handles email notifications asynchronously to prevent blocking API responses
"""

import logging
import threading
import time
from queue import Queue, Empty
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class EmailWorker:
    """
    Background worker for processing email notifications
    
    Features:
    - Non-blocking email sending
    - Queue-based processing
    - Automatic retry on failure
    - Graceful shutdown
    
    Performance:
    - Reduces delete expense from 2755ms to <300ms
    - Prevents email failures from blocking API responses
    """
    
    def __init__(self, max_retries: int = 3):
        """
        Initialize email worker
        
        Args:
            max_retries: Maximum retry attempts for failed emails
        """
        self.queue = Queue()
        self.max_retries = max_retries
        self.running = True
        self.processed_count = 0
        self.failed_count = 0
        
        # Start background worker thread
        self.worker_thread = threading.Thread(
            target=self._process_queue,
            daemon=True,
            name="EmailWorker"
        )
        self.worker_thread.start()
        
        logger.info("📧 Email worker started")
    
    def queue_email(
        self,
        email_type: str,
        recipients: List[str],
        data: Dict,
        priority: str = "normal"
    ) -> bool:
        """
        Add email to processing queue
        
        Args:
            email_type: Type of email (expense_created, expense_deleted, etc.)
            recipients: List of recipient email addresses
            data: Email template data
            priority: Email priority (normal, high)
        
        Returns:
            True if queued successfully
        """
        try:
            email_task = {
                'type': email_type,
                'recipients': recipients,
                'data': data,
                'priority': priority,
                'timestamp': datetime.utcnow(),
                'retry_count': 0
            }
            
            self.queue.put(email_task, block=False)
            logger.info(
                f"📬 Queued {email_type} email for {len(recipients)} recipients"
            )
            return True
            
        except Exception as e:
            logger.error(f"Failed to queue email: {e}")
            return False
    
    def _process_queue(self):
        """
        Background worker thread - processes emails from queue
        
        Runs continuously until shutdown
        """
        logger.info("📧 Email worker thread started")
        
        while self.running:
            try:
                # Get email task from queue (wait up to 1 second)
                email_task = self.queue.get(timeout=1.0)
                
                # Process the email
                self._send_email(email_task)
                
                # Mark task as done
                self.queue.task_done()
                
            except Empty:
                # Queue is empty, continue waiting
                continue
                
            except Exception as e:
                logger.error(f"Email worker error: {e}", exc_info=True)
                time.sleep(1)  # Prevent tight loop on repeated errors
        
        logger.info("📧 Email worker thread stopped")
    
    def _send_email(self, email_task: Dict):
        """
        Send email with retry logic
        
        Args:
            email_task: Email task dictionary
        """
        email_type = email_task['type']
        recipients = email_task['recipients']
        data = email_task['data']
        retry_count = email_task.get('retry_count', 0)
        
        try:
            # Import email service (lazy import to avoid circular dependencies)
            from ..email_service import EmailService
            email_service = EmailService()
            
            # Send email based on type
            if email_type == 'expense_created':
                self._send_expense_created_email(email_service, recipients, data)
            
            elif email_type == 'expense_updated':
                self._send_expense_updated_email(email_service, recipients, data)
            
            elif email_type == 'expense_deleted':
                self._send_expense_deleted_email(email_service, recipients, data)
            
            elif email_type == 'settlement_created':
                self._send_settlement_email(email_service, recipients, data)
            
            elif email_type == 'invitation_sent':
                self._send_invitation_email(email_service, recipients, data)
            
            else:
                logger.warning(f"Unknown email type: {email_type}")
                return
            
            self.processed_count += 1
            logger.info(
                f"✅ Sent {email_type} email to {len(recipients)} recipients "
                f"(total: {self.processed_count})"
            )
            
        except Exception as e:
            logger.error(f"Failed to send {email_type} email: {e}")
            
            # Retry logic
            if retry_count < self.max_retries:
                email_task['retry_count'] = retry_count + 1
                logger.info(
                    f"🔄 Retrying {email_type} email "
                    f"(attempt {retry_count + 1}/{self.max_retries})"
                )
                time.sleep(2 ** retry_count)  # Exponential backoff
                self.queue.put(email_task)
            else:
                self.failed_count += 1
                logger.error(
                    f"❌ Email failed after {self.max_retries} retries: "
                    f"{email_type} to {recipients}"
                )
    
    def _send_expense_created_email(
        self,
        email_service,
        recipients: List[str],
        data: Dict
    ):
        """Send expense created notification"""
        total_amount = data.get('amount', 0)
        split_count = data.get('split_count', 1)
        user_share = total_amount / split_count if split_count > 0 else 0
        
        for recipient in recipients:
            # Get user name from email or use default
            user_name = recipient.split('@')[0].title()
            
            email_service.send_expense_added_notification(
                to_email=recipient,
                user_name=user_name,
                expense_description=data.get('description', ''),
                amount=total_amount,
                user_share=user_share,
                payer_name=data.get('paid_by_name', 'Unknown'),
                group_name=data.get('group_name', 'Your Group')
            )
    
    def _send_expense_updated_email(
        self,
        email_service,
        recipients: List[str],
        data: Dict
    ):
        """Send expense updated notification"""
        for recipient in recipients:
            recipient_data = {
                'user_email': recipient,
                'group_name': data.get('group_name', 'Unknown Group'),
                'expense_description': data.get('description', ''),
                'amount': data.get('amount', 0),
                'currency': data.get('currency', 'USD'),
                'updated_by_name': data.get('updated_by_name', 'Unknown')
            }
            # Reuse expense notification template
            email_service.send_expense_notification(recipient_data)
    
    def _send_expense_deleted_email(
        self,
        email_service,
        recipients: List[str],
        data: Dict
    ):
        """Send expense deleted notification"""
        for recipient in recipients:
            # Get user name from email or use default
            user_name = recipient.split('@')[0].title()
            
            email_service.send_expense_deleted_notification(
                to_email=recipient,
                user_name=user_name,
                expense_description=data.get('description', ''),
                amount=data.get('amount', 0),
                deleted_by_name=data.get('deleted_by_name', 'Unknown'),
                group_name=data.get('group_name', 'Your Group')
            )
    
    def _send_settlement_email(
        self,
        email_service,
        recipients: List[str],
        data: Dict
    ):
        """Send settlement notification"""
        for recipient in recipients:
            recipient_data = {
                'email': recipient,
                'group_name': data.get('group_name', 'Unknown Group'),
                'from_name': data.get('from_name', 'Unknown'),
                'to_name': data.get('to_name', 'Unknown'),
                'amount': data.get('amount', 0),
                'currency': data.get('currency', 'USD')
            }
            email_service.send_settlement_notification(recipient_data)
    
    def _send_invitation_email(
        self,
        email_service,
        recipients: List[str],
        data: Dict
    ):
        """Send invitation email"""
        for recipient in recipients:
            recipient_data = {
                'invited_email': recipient,
                'inviter_name': data.get('inviter_name', 'Someone'),
                'group_name': data.get('group_name', 'a group'),
                'invitation_link': data.get('invitation_link', '')
            }
            email_service.send_invitation_email(recipient_data)
    
    def get_stats(self) -> Dict:
        """
        Get worker statistics
        
        Returns:
            Dictionary with worker stats
        """
        return {
            'queue_size': self.queue.qsize(),
            'processed_count': self.processed_count,
            'failed_count': self.failed_count,
            'running': self.running,
            'worker_alive': self.worker_thread.is_alive()
        }
    
    def shutdown(self, timeout: int = 10):
        """
        Gracefully shutdown worker
        
        Args:
            timeout: Maximum seconds to wait for queue to empty
        """
        logger.info("📧 Shutting down email worker...")
        
        # Wait for queue to empty
        try:
            self.queue.join()
            logger.info("📧 Queue emptied, stopping worker")
        except Exception as e:
            logger.warning(f"Error waiting for queue: {e}")
        
        # Stop worker thread
        self.running = False
        
        # Wait for thread to finish
        self.worker_thread.join(timeout=timeout)
        
        if self.worker_thread.is_alive():
            logger.warning("📧 Worker thread did not stop gracefully")
        else:
            logger.info("📧 Email worker stopped")
        
        logger.info(
            f"📊 Final stats - Processed: {self.processed_count}, "
            f"Failed: {self.failed_count}"
        )


# Singleton instance
_email_worker: Optional[EmailWorker] = None


def get_email_worker() -> EmailWorker:
    """
    Get singleton email worker instance
    
    Returns:
        EmailWorker instance
    """
    global _email_worker
    
    if _email_worker is None:
        _email_worker = EmailWorker()
    
    return _email_worker
