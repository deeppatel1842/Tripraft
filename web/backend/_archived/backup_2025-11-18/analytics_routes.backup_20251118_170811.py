"""
Route Handlers for Analytics & Subscription Management
======================================================
API endpoints for analytics, plan management, and settlement reports.

Endpoints:
- GET  /api/analytics/user/{user_id} - Get user analytics
- GET  /api/analytics/dashboard - Get business dashboard metrics
- GET  /api/plan/limits - Get current user plan limits
- POST /api/plan/upgrade - Upgrade to paid plan
- POST /api/settlements/archive - Manually trigger archiving
- GET  /api/settlements/report/{group_id} - Generate settlement PDF

Author: Production Team
Date: November 18, 2025
"""

from flask import Blueprint, request, jsonify, g, send_file
from datetime import datetime, timedelta
from functools import wraps
from typing import Optional

from analytics.analytics_engine import AnalyticsEngine, EventType, get_analytics_summary
from analytics.plan_manager import PlanManager, check_and_track_expense_creation
from analytics.settlement_archiver import SettlementArchiver, generate_and_send_monthly_report

# Create blueprint
analytics_bp = Blueprint('analytics', __name__, url_prefix='/api')


def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(g, 'user_id'):
            return jsonify({"error": "Authentication required"}), 401
        return f(*args, **kwargs)
    return decorated_function


def require_admin(f):
    """Decorator to require admin privileges"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not hasattr(g, 'user_role') or g.user_role != 'admin':
            return jsonify({"error": "Admin privileges required"}), 403
        return f(*args, **kwargs)
    return decorated_function


# ==================== ANALYTICS ENDPOINTS ====================

@analytics_bp.route('/analytics/user/<user_id>', methods=['GET'])
@require_auth
def get_user_analytics(user_id: str):
    """
    Get analytics for a specific user
    
    Returns:
        JSON with user analytics data
    """
    try:
        # Check if user is requesting their own data or is admin
        if g.user_id != user_id and g.get('user_role') != 'admin':
            return jsonify({"error": "Unauthorized"}), 403
        
        from firebase_admin import firestore
        db = firestore.client()
        
        summary = get_analytics_summary(db, user_id)
        
        return jsonify({
            "success": True,
            "data": summary
        }), 200
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@analytics_bp.route('/analytics/dashboard', methods=['GET'])
@require_auth
@require_admin
def get_dashboard_metrics():
    """
    Get business dashboard metrics
    (Admin only)
    
    Query params:
        - days: Number of days to include (default: 30)
    
    Returns:
        JSON with business metrics
    """
    try:
        days = int(request.args.get('days', 30))
        
        from firebase_admin import firestore
        db = firestore.client()
        
        analytics = AnalyticsEngine(db)
        
        # Calculate current metrics
        current_metrics = analytics.calculate_daily_metrics()
        
        # Get historical metrics
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        historical_metrics = analytics.get_metrics_range(start_date, end_date)
        
        return jsonify({
            "success": True,
            "data": {
                "current": current_metrics.to_dict(),
                "historical": historical_metrics,
                "period_days": days
            }
        }), 200
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@analytics_bp.route('/analytics/track', methods=['POST'])
@require_auth
def track_custom_event():
    """
    Track a custom analytics event
    
    Request body:
        {
            "event_type": "custom_event_name",
            "properties": {...}
        }
    
    Returns:
        JSON with success status
    """
    try:
        data = request.get_json()
        event_type_str = data.get('event_type')
        properties = data.get('properties', {})
        
        if not event_type_str:
            return jsonify({"error": "event_type is required"}), 400
        
        from firebase_admin import firestore
        db = firestore.client()
        
        analytics = AnalyticsEngine(db)
        
        # Try to match to EventType enum, otherwise track as custom
        try:
            event_type = EventType[event_type_str.upper()]
        except KeyError:
            # Custom event - store directly
            event_type_value = event_type_str
        else:
            event_type_value = event_type
        
        success = analytics.track_event(
            event_type_value,
            g.user_id,
            properties=properties
        )
        
        return jsonify({
            "success": success
        }), 200 if success else 500
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ==================== PLAN MANAGEMENT ENDPOINTS ====================

@analytics_bp.route('/plan/limits', methods=['GET'])
@require_auth
def get_plan_limits():
    """
    Get current user's plan limits and usage
    
    Returns:
        JSON with plan information
    """
    try:
        from firebase_admin import firestore
        db = firestore.client()
        
        manager = PlanManager(db)
        limit_info = manager.get_limit_info(g.user_id)
        
        return jsonify({
            "success": True,
            "data": limit_info
        }), 200
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@analytics_bp.route('/plan/usage', methods=['GET'])
@require_auth
def get_usage_summary():
    """
    Get usage summary for current user
    
    Query params:
        - days: Number of days to analyze (default: 30)
    
    Returns:
        JSON with usage statistics
    """
    try:
        days = int(request.args.get('days', 30))
        
        from firebase_admin import firestore
        db = firestore.client()
        
        manager = PlanManager(db)
        usage = manager.get_usage_summary(g.user_id, days)
        
        return jsonify({
            "success": True,
            "data": usage
        }), 200
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@analytics_bp.route('/plan/upgrade', methods=['POST'])
@require_auth
def upgrade_to_paid():
    """
    Upgrade user to paid plan
    
    Request body:
        {
            "payment_method": "stripe_token_id"  (for future implementation)
        }
    
    Returns:
        JSON with success status
    """
    try:
        from firebase_admin import firestore
        db = firestore.client()
        
        manager = PlanManager(db)
        
        # TODO: Add payment processing here
        # For now, just upgrade the user
        
        success = manager.upgrade_user_to_paid(g.user_id)
        
        if success:
            return jsonify({
                "success": True,
                "message": "Successfully upgraded to paid plan"
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": "Failed to upgrade plan"
            }), 500
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@analytics_bp.route('/plan/check-limit/<limit_type>', methods=['GET'])
@require_auth
def check_limit(limit_type: str):
    """
    Check if user can perform an action
    
    Limit types:
        - expense: Can create expense
        - group: Can create group
        - pdf: Can export PDF
    
    Returns:
        JSON with limit check result
    """
    try:
        from firebase_admin import firestore
        db = firestore.client()
        
        manager = PlanManager(db)
        
        if limit_type == 'expense':
            can_do, error = manager.can_create_expense(g.user_id)
        elif limit_type == 'group':
            can_do, error = manager.can_create_group(g.user_id)
        elif limit_type == 'pdf':
            can_do, error = manager.can_export_pdf(g.user_id)
        else:
            return jsonify({"error": "Invalid limit type"}), 400
        
        return jsonify({
            "success": True,
            "allowed": can_do,
            "message": error if not can_do else None
        }), 200
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ==================== SETTLEMENT ARCHIVING ENDPOINTS ====================

@analytics_bp.route('/settlements/archive', methods=['POST'])
@require_auth
@require_admin
def trigger_archiving():
    """
    Manually trigger settlement archiving
    (Admin only)
    
    Returns:
        JSON with archiving results
    """
    try:
        from firebase_admin import firestore
        db = firestore.client()
        
        archiver = SettlementArchiver(db)
        archived_count = archiver.archive_all_old_settlements()
        
        return jsonify({
            "success": True,
            "archived_count": archived_count
        }), 200
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@analytics_bp.route('/settlements/report/<group_id>', methods=['GET'])
@require_auth
def generate_settlement_report(group_id: str):
    """
    Generate settlement PDF report for a group
    
    Query params:
        - start_date: Start date (YYYY-MM-DD)
        - end_date: End date (YYYY-MM-DD)
        - send_email: Whether to send via email (true/false)
    
    Returns:
        PDF file or JSON with download URL
    """
    try:
        from firebase_admin import firestore, storage
        db = firestore.client()
        bucket = storage.bucket()
        
        # Check if user has access to this group
        group_ref = db.collection('groups').document(group_id)
        group_doc = group_ref.get()
        
        if not group_doc.exists:
            return jsonify({"error": "Group not found"}), 404
        
        group_data = group_doc.to_dict()
        member_ids = group_data.get('member_ids', [])
        
        if g.user_id not in member_ids:
            return jsonify({"error": "Unauthorized"}), 403
        
        # Check if user can export PDF
        manager = PlanManager(db)
        can_export, error = manager.can_export_pdf(g.user_id)
        
        if not can_export:
            return jsonify({
                "success": False,
                "error": error,
                "upgrade_required": True
            }), 403
        
        # Parse dates
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        send_email = request.args.get('send_email', 'false').lower() == 'true'
        
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        else:
            start_date = datetime.utcnow() - timedelta(days=30)
        
        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        else:
            end_date = datetime.utcnow()
        
        # Generate PDF
        archiver = SettlementArchiver(db, bucket)
        pdf_buffer = archiver.generate_settlement_pdf(group_id, start_date, end_date)
        
        if not pdf_buffer:
            return jsonify({
                "success": False,
                "error": "No settlements found for this period"
            }), 404
        
        # Track analytics
        analytics = AnalyticsEngine(db)
        analytics.track_event(
            EventType.PDF_GENERATED,
            g.user_id,
            properties={"group_id": group_id}
        )
        
        if send_email:
            # Save to storage and send email
            filename = f"settlement_report_{start_date.strftime('%Y_%m')}.pdf"
            pdf_url = archiver.save_pdf_to_storage(pdf_buffer, group_id, filename)
            
            # Get member emails
            member_emails = []
            for member_id in member_ids:
                user_doc = db.collection('users').document(member_id).get()
                if user_doc.exists:
                    user_data = user_doc.to_dict()
                    email = user_data.get('email')
                    if email:
                        member_emails.append(email)
            
            archiver.send_settlement_report_email(group_id, pdf_url, member_emails)
            
            return jsonify({
                "success": True,
                "message": "Report sent to all group members",
                "download_url": pdf_url
            }), 200
        else:
            # Return PDF file directly
            return send_file(
                pdf_buffer,
                mimetype='application/pdf',
                as_attachment=True,
                download_name=f'settlement_report_{group_id}.pdf'
            )
    
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ==================== HELPER FUNCTION ====================

def init_analytics_routes(app, db):
    """
    Initialize analytics routes
    
    Args:
        app: Flask app instance
        db: Firestore database
    """
    from expense_engine.logging_utils import get_logger
    
    logger = get_logger(__name__)
    app.register_blueprint(analytics_bp)
    
    # Store db reference for use in routes
    app.config['ANALYTICS_DB'] = db
    
    # logger.info("Analytics routes initialized")
