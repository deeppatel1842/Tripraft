"""
Vault Service for Group Planner
Handles file upload/download for the logistics vault.
Files are stored on disk under UPLOAD_DIR/<group_id>/.
"""

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Tuple

from app.domain.group_planner.models import (GroupActivity, TravelGroup,
                                             TripMember, VaultDocument)
from app.infrastructure.db.connection import get_db_session

logger = logging.getLogger(__name__)

ALLOWED_MIME_TYPES = {
    'application/pdf',
    'image/jpeg',
    'image/png',
    'image/webp',
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


class VaultService:

    @staticmethod
    def _upload_dir(group_id: str) -> str:
        base = os.environ.get('UPLOAD_DIR', os.path.join(os.getcwd(), 'uploads'))
        path = os.path.join(base, 'vault', str(group_id))
        os.makedirs(path, exist_ok=True)
        return path

    @staticmethod
    def upload_file(
        group_id: str,
        user_id: str,
        file_storage,
    ) -> Tuple[bool, Dict[str, Any]]:
        try:
            with get_db_session() as session:
                member = session.query(TripMember).filter(
                    TripMember.group_id == group_id,
                    TripMember.user_id == user_id,
                    TripMember.is_active == True,
                ).first()
                if not member:
                    return False, {'error': 'Not a member of this group'}

                original_name = file_storage.filename or 'untitled'
                mime = file_storage.content_type or 'application/octet-stream'

                if mime not in ALLOWED_MIME_TYPES:
                    return False, {'error': f'File type not allowed. Accepted: PDF, JPEG, PNG, WebP'}

                # Read into memory to check size
                data = file_storage.read()
                if len(data) > MAX_FILE_SIZE:
                    return False, {'error': 'File exceeds 10 MB limit'}
                if len(data) == 0:
                    return False, {'error': 'Empty file'}

                # Generate unique filename
                ext = os.path.splitext(original_name)[1] or '.bin'
                safe_name = f"{uuid.uuid4().hex}{ext}"

                dest_dir = VaultService._upload_dir(group_id)
                dest_path = os.path.join(dest_dir, safe_name)
                with open(dest_path, 'wb') as f:
                    f.write(data)

                doc = VaultDocument(
                    group_id=group_id,
                    filename=safe_name,
                    original_filename=original_name,
                    mime_type=mime,
                    file_size=len(data),
                    uploaded_by=user_id,
                )
                session.add(doc)
                session.flush()

                activity = GroupActivity(
                    group_id=group_id,
                    user_id=user_id,
                    action='vault_upload',
                    entity_type='vault',
                    entity_id=doc.id,
                    details={'filename': original_name[:80]},
                )
                session.add(activity)

                session.commit()
                session.refresh(doc)

                return True, {'document': doc.to_dict()}

        except Exception as e:
            logger.error("Vault upload error: %s", e)
            return False, {'error': 'Failed to upload file'}

    @staticmethod
    def list_files(group_id: str, user_id: str) -> Tuple[bool, Dict[str, Any]]:
        try:
            with get_db_session() as session:
                member = session.query(TripMember).filter(
                    TripMember.group_id == group_id,
                    TripMember.user_id == user_id,
                    TripMember.is_active == True,
                ).first()
                if not member:
                    return False, {'error': 'Not a member of this group'}

                docs = session.query(VaultDocument).filter(
                    VaultDocument.group_id == group_id,
                    VaultDocument.is_deleted == False,
                ).order_by(VaultDocument.created_at.desc()).all()

                return True, {'documents': [d.to_dict() for d in docs]}

        except Exception as e:
            logger.error("Vault list error: %s", e)
            return False, {'error': 'Failed to list vault documents'}

    @staticmethod
    def delete_file(group_id: str, doc_id: str, user_id: str) -> Tuple[bool, Dict[str, Any]]:
        try:
            with get_db_session() as session:
                member = session.query(TripMember).filter(
                    TripMember.group_id == group_id,
                    TripMember.user_id == user_id,
                    TripMember.is_active == True,
                ).first()
                if not member:
                    return False, {'error': 'Not a member of this group'}

                doc = session.query(VaultDocument).filter(
                    VaultDocument.id == doc_id,
                    VaultDocument.group_id == group_id,
                    VaultDocument.is_deleted == False,
                ).first()
                if not doc:
                    return False, {'error': 'Document not found'}

                doc.is_deleted = True
                session.commit()

                return True, {'message': 'Document deleted'}

        except Exception as e:
            logger.error("Vault delete error: %s", e)
            return False, {'error': 'Failed to delete document'}

    @staticmethod
    def get_file_path(group_id: str, doc_id: str, user_id: str) -> Tuple[bool, Dict[str, Any]]:
        """Return the on-disk path + metadata for streaming."""
        try:
            with get_db_session() as session:
                member = session.query(TripMember).filter(
                    TripMember.group_id == group_id,
                    TripMember.user_id == user_id,
                    TripMember.is_active == True,
                ).first()
                if not member:
                    return False, {'error': 'Not a member of this group'}

                doc = session.query(VaultDocument).filter(
                    VaultDocument.id == doc_id,
                    VaultDocument.group_id == group_id,
                    VaultDocument.is_deleted == False,
                ).first()
                if not doc:
                    return False, {'error': 'Document not found'}

                dest_dir = VaultService._upload_dir(group_id)
                path = os.path.join(dest_dir, doc.filename)
                if not os.path.isfile(path):
                    return False, {'error': 'File not found on disk'}

                return True, {
                    'path': path,
                    'filename': doc.original_filename,
                    'mime_type': doc.mime_type,
                }

        except Exception as e:
            logger.error("Vault get file error: %s", e)
            return False, {'error': 'Failed to get file'}


vault_service = VaultService()
