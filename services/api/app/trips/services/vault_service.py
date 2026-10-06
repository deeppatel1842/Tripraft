# Purpose: Vault Service for Group Planner Handles file upload/download for the logistics vault.
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

from app.trips.models import (GroupActivity, TravelGroup,
                                             TripMember, VaultDocument)
from app.core.db.connection import get_db_session

logger = logging.getLogger(__name__)

ALLOWED_MIME_TYPES = {
    'application/pdf',
    'image/jpeg',
    'image/png',
    'image/webp',
}
_EXTENSION_BY_MIME = {
    'application/pdf': '.pdf',
    'image/jpeg': '.jpg',
    'image/png': '.png',
    'image/webp': '.webp',
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
    def _document_path(group_id: str, filename: str) -> str:
        """Build a vault path without allowing legacy names to traverse it."""
        directory = os.path.abspath(VaultService._upload_dir(group_id))
        basename = os.path.basename(filename)
        path = os.path.abspath(os.path.join(directory, basename))
        if os.path.commonpath((directory, path)) != directory:
            raise ValueError('Invalid vault file path')
        return path

    @staticmethod
    def _detect_mime(data: bytes) -> str | None:
        """Identify supported files from their signatures, never HTTP metadata."""
        if data.startswith(b'%PDF-'):
            return 'application/pdf'
        if data.startswith(b'\xff\xd8\xff'):
            return 'image/jpeg'
        if data.startswith(b'\x89PNG\r\n\x1a\n'):
            return 'image/png'
        if data.startswith(b'RIFF') and data[8:12] == b'WEBP':
            return 'image/webp'
        return None

    @staticmethod
    def upload_file(
        group_id: str,
        user_id: str,
        file_storage,
    ) -> Tuple[bool, Dict[str, Any]]:
        temporary_path = None
        try:
            with get_db_session() as session:
                member = session.query(TripMember).filter(
                    TripMember.group_id == group_id,
                    TripMember.user_id == user_id,
                    TripMember.is_active == True,
                ).first()
                if not member:
                    return False, {'error': 'Not a member of this group'}

                # Read into memory to check size
                data = file_storage.read()
                if len(data) > MAX_FILE_SIZE:
                    return False, {'error': 'File exceeds 10 MB limit'}
                if len(data) == 0:
                    return False, {'error': 'Empty file'}

                # Content-Type and filename extensions come from the client;
                # use a compact signature allowlist and a server-assigned
                # extension instead.
                mime = VaultService._detect_mime(data)
                if mime not in ALLOWED_MIME_TYPES:
                    return False, {'error': 'File type not allowed. Accepted: PDF, JPEG, PNG, WebP'}
                original_name = os.path.basename(file_storage.filename or 'untitled')[:255]

                # Generate unique filename
                ext = _EXTENSION_BY_MIME[mime]
                safe_name = f"{uuid.uuid4().hex}{ext}"

                dest_path = VaultService._document_path(group_id, safe_name)
                # Hold bytes in a uniquely named temporary file.  It becomes
                # visible at its final name only after the database commit;
                # failures before then are cleaned up below.
                temporary_path = f'{dest_path}.{uuid.uuid4().hex}.uploading'
                with open(temporary_path, 'xb') as f:
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

                try:
                    os.replace(temporary_path, dest_path)
                    temporary_path = None
                except OSError as exc:
                    # Compensate the committed metadata if publication of the
                    # file failed, leaving no downloadable orphan record.
                    logger.error('Vault file publication failed: %s', exc)
                    doc.is_deleted = True
                    session.commit()
                    return False, {'error': 'Failed to store upload'}

                return True, {'document': doc.to_dict()}

        except Exception as e:
            logger.error("Vault upload error: %s", e)
            return False, {'error': 'Failed to upload file'}
        finally:
            if temporary_path:
                try:
                    os.remove(temporary_path)
                except FileNotFoundError:
                    pass
                except OSError as exc:
                    logger.error('Could not clean up failed vault upload: %s', exc)

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

                is_group_admin = member.role in {'creator', 'admin'}
                if str(doc.uploaded_by) != str(user_id) and not is_group_admin:
                    return False, {
                        'error': 'Only the uploader or a group admin may delete this document',
                        'status_code': 403,
                    }

                doc.is_deleted = True
                session.commit()

                path = VaultService._document_path(group_id, doc.filename)

            # The database commit makes the document inaccessible.  Remove
            # its private bytes immediately rather than retaining a growing
            # collection of soft-deleted files on disk.
            try:
                os.remove(path)
            except FileNotFoundError:
                pass
            except OSError as exc:
                # Do not claim deletion while private bytes remain on disk.
                # Restore the metadata so the caller can retry, instead of
                # creating an unreachable file with no cleanup queue.
                logger.error('Vault disk cleanup failed for %s: %s', doc_id, exc)
                with get_db_session() as recovery_session:
                    failed_delete = recovery_session.get(VaultDocument, doc_id)
                    if failed_delete:
                        failed_delete.is_deleted = False
                        recovery_session.commit()
                return False, {'error': 'Failed to remove document from storage'}

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

                path = VaultService._document_path(group_id, doc.filename)
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
