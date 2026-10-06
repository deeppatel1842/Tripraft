# Purpose: Vault Routes for Group Planner File upload / download / list / delete for the logistics vault.
"""
Vault Routes for Group Planner
File upload / download / list / delete for the logistics vault.
"""

import logging

from app.core.apiutils.responses import (created_response, error_response,
                                     not_found_response, success_response)
from app.core.config import Config
from app.core.rate_limiter import limit_api
from app.auth.security.decorators import require_auth, require_group_role
from flask import Blueprint, g, request, send_file

logger = logging.getLogger(__name__)

vault_bp = Blueprint(
    'gp_vault',
    __name__,
    url_prefix='/api/v1/group-planner',
)


@vault_bp.route('/groups/<group_id>/vault', methods=['POST'])
@limit_api(Config.RATE_LIMITS['create'])
@require_auth
@require_group_role('member')
def upload_vault_file(group_id):
    """Upload a file to the group vault."""
    try:
        from app.trips.services.vault_service import vault_service

        uploaded = request.files.get('file')
        if not uploaded or not uploaded.filename:
            return error_response('File is required')

        ok, result = vault_service.upload_file(
            group_id=group_id,
            user_id=g.user_id,
            file_storage=uploaded,
        )
        if ok:
            return created_response(data=result['document'])
        return error_response(result.get('error'), 400)

    except Exception as e:
        logger.error("Vault upload route error: %s", e)
        return error_response('Upload failed', 500)


@vault_bp.route('/groups/<group_id>/vault', methods=['GET'])
@limit_api(Config.RATE_LIMITS['read_light'])
@require_auth
def list_vault_files(group_id):
    """List all vault files for a group."""
    try:
        from app.trips.services.vault_service import vault_service

        ok, result = vault_service.list_files(group_id=group_id, user_id=g.user_id)
        if ok:
            return success_response(data=result['documents'])
        return error_response(result.get('error'), 403)

    except Exception as e:
        logger.error("Vault list route error: %s", e)
        return error_response('Failed to list vault', 500)


@vault_bp.route('/groups/<group_id>/vault/<doc_id>', methods=['GET'])
@limit_api(Config.RATE_LIMITS['read_light'])
@require_auth
def download_vault_file(group_id, doc_id):
    """Download a vault file."""
    try:
        from app.trips.services.vault_service import vault_service

        ok, result = vault_service.get_file_path(
            group_id=group_id, doc_id=doc_id, user_id=g.user_id,
        )
        if not ok:
            return error_response(result.get('error'), 404)

        return send_file(
            result['path'],
            mimetype=result['mime_type'],
            as_attachment=True,
            download_name=result['filename'],
        )

    except Exception as e:
        logger.error("Vault download route error: %s", e)
        return error_response('Download failed', 500)


@vault_bp.route('/groups/<group_id>/vault/<doc_id>', methods=['DELETE'])
@limit_api(Config.RATE_LIMITS['delete'])
@require_auth
@require_group_role('member')
def delete_vault_file(group_id, doc_id):
    """Soft-delete a vault file."""
    try:
        from app.trips.services.vault_service import vault_service

        ok, result = vault_service.delete_file(
            group_id=group_id, doc_id=doc_id, user_id=g.user_id,
        )
        if ok:
            return success_response(message=result['message'])
        return error_response(result.get('error'), result.get('status_code', 404))

    except Exception as e:
        logger.error("Vault delete route error: %s", e)
        return error_response('Delete failed', 500)
