"""
Background Workers for Expense Engine
Handles asynchronous tasks like email notifications, cleanup, etc.
"""

__all__ = ['EmailWorker', 'get_email_worker']

from .email_worker import EmailWorker, get_email_worker
