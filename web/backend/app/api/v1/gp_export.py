"""
Export & Integration Routes for Group Planner
GET  /groups/<id>/export/pdf   — download trip PDF
GET  /groups/<id>/calendar.ics — download iCal
POST /groups/<id>/clone        — clone a group as template
POST /groups/join              — join group by code
"""

import logging

from app.api.utils.responses import error_response, success_response
from app.core.config import Config
from app.core.rate_limiter import limit_api
from app.infrastructure.auth.decorators import require_auth
from flask import Blueprint, Response, g, request

logger = logging.getLogger(__name__)

export_bp = Blueprint(
    'gp_export',
    __name__,
    url_prefix='/api/v1/group-planner'
)


@export_bp.route('/groups/<group_id>/export/pdf', methods=['GET'])
@limit_api(Config.RATE_LIMITS['read_heavy'])
@require_auth
def export_pdf(group_id):
    """Download trip plan as PDF."""
    from app.services.export_service import export_service

    ok, result = export_service.generate_pdf(group_id, g.user_id)
    if not ok:
        code = 404 if 'not found' in result.get('error', '').lower() else 500
        return error_response(result.get('error', 'Export failed'), code)

    return Response(
        result,
        mimetype='application/pdf',
        headers={'Content-Disposition': f'attachment; filename=trip-{group_id}.pdf'},
    )


@export_bp.route('/groups/<group_id>/calendar.ics', methods=['GET'])
@limit_api(Config.RATE_LIMITS['read_heavy'])
@require_auth
def export_ical(group_id):
    """Download trip plan as iCal file."""
    from app.services.export_service import export_service

    ok, result = export_service.generate_ical(group_id, g.user_id)
    if not ok:
        code = 404 if 'not found' in result.get('error', '').lower() else 500
        return error_response(result.get('error', 'Export failed'), code)

    return Response(
        result,
        mimetype='text/calendar',
        headers={'Content-Disposition': f'attachment; filename=trip-{group_id}.ics'},
    )


@export_bp.route('/groups/<group_id>/clone', methods=['POST'])
@limit_api(Config.RATE_LIMITS['create'])
@require_auth
def clone_group(group_id):
    """Clone a group as a new template trip."""
    from app.services.travel_group_service import group_service

    ok, result = group_service.clone_group(group_id, g.user_id)
    if not ok:
        code = 404 if 'not found' in result.get('error', '').lower() else 400
        return error_response(result.get('error', 'Clone failed'), code)

    return success_response('Group cloned', result, 201)


@export_bp.route('/groups/join', methods=['POST'])
@limit_api(Config.RATE_LIMITS['create'])
@require_auth
def join_by_code():
    """Join a group using a group code."""
    from app.services.travel_group_service import group_service

    data = request.get_json(silent=True) or {}
    code = (data.get('code') or '').strip()
    if not code:
        return error_response('Group code is required', 400)

    ok, result = group_service.join_by_code(code, g.user_id)
    if not ok:
        code_status = 409 if 'Already' in result.get('error', '') else 404
        return error_response(result.get('error', 'Join failed'), code_status)

    return success_response('Joined group', result)
