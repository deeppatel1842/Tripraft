"""
Admin Places API
=================
CRUD and bulk ingestion endpoints for travel data management.
All endpoints require authentication + admin role.
"""

import logging

from app.api.utils.responses import (created_response, error_response,
                                     success_response)
from app.core.rate_limiter import limit_api
from app.infrastructure.auth.decorators import require_admin, require_auth
from app.infrastructure.db.travel_db import travel_db
from app.services.data_ingestion_service import data_ingestion_service
from flask import Blueprint, g, request

logger = logging.getLogger(__name__)

admin_places_bp = Blueprint("admin_places", __name__, url_prefix="/api/v1/admin")


# ------------------------------------------------------------------
# Single place CRUD
# ------------------------------------------------------------------

@admin_places_bp.route("/places", methods=["POST"])
@require_auth
@require_admin
@limit_api("30 per minute")
def create_place():
    data = request.get_json(silent=True)
    if not data:
        return error_response("JSON body required")
    try:
        place_id = data_ingestion_service.ingest_place(
            data, source="api", ingested_by=g.user_email
        )
        return created_response(data={"id": place_id})
    except ValueError as exc:
        return error_response(str(exc))


@admin_places_bp.route("/places/<int:place_id>", methods=["PUT"])
@require_auth
@require_admin
@limit_api("30 per minute")
def update_place(place_id: int):
    data = request.get_json(silent=True)
    if not data:
        return error_response("JSON body required")
    try:
        changed = data_ingestion_service.update_place(
            place_id, data, source="api", ingested_by=g.user_email
        )
        if not changed:
            return error_response("Place not found or no changes", 404)
        return success_response(data={"id": place_id})
    except ValueError as exc:
        return error_response(str(exc))


@admin_places_bp.route("/places/<int:place_id>", methods=["DELETE"])
@require_auth
@require_admin
@limit_api("10 per minute")
def delete_place(place_id: int):
    deleted = data_ingestion_service.delete_place(
        place_id, source="api", ingested_by=g.user_email
    )
    if not deleted:
        return error_response("Place not found", 404)
    return success_response(data={"deleted": place_id})


# ------------------------------------------------------------------
# Bulk operations
# ------------------------------------------------------------------

@admin_places_bp.route("/places/bulk", methods=["POST"])
@require_auth
@require_admin
@limit_api("5 per minute")
def bulk_ingest_places():
    body = request.get_json(silent=True)
    if not body or "places" not in body:
        return error_response("JSON body with 'places' array required")
    result = data_ingestion_service.ingest_places_bulk(
        body["places"],
        source="bulk",
        ingested_by=g.user_email,
        skip_geo_check=body.get("skip_geo_check", False),
    )
    return success_response(data=result.model_dump())


@admin_places_bp.route("/places/import", methods=["POST"])
@require_auth
@require_admin
@limit_api("5 per minute")
def import_places():
    uploaded = request.files.get("file")
    if not uploaded or not uploaded.filename:
        return error_response("File upload required")
    entity_type = request.form.get("entity_type", "place")
    content = uploaded.read().decode("utf-8")
    filename = uploaded.filename.lower()
    try:
        if filename.endswith(".csv"):
            result = data_ingestion_service.import_from_csv(
                content, entity_type, source="bulk", ingested_by=g.user_email
            )
        elif filename.endswith(".json"):
            result = data_ingestion_service.import_from_json(
                content, entity_type, source="bulk", ingested_by=g.user_email
            )
        else:
            return error_response("Only .csv and .json files accepted")
    except (ValueError, UnicodeDecodeError) as exc:
        return error_response(str(exc))

    return success_response(data=result.model_dump())


@admin_places_bp.route("/places/validate", methods=["POST"])
@require_auth
@require_admin
@limit_api("20 per minute")
def validate_places():
    body = request.get_json(silent=True)
    if not body or "places" not in body:
        return error_response("JSON body with 'places' array required")
    result = data_ingestion_service.validate_only(
        body["places"], skip_geo_check=body.get("skip_geo_check", False)
    )
    return success_response(data=result.model_dump())


# ------------------------------------------------------------------
# Hierarchy management (countries / states / cities)
# ------------------------------------------------------------------

@admin_places_bp.route("/countries", methods=["POST"])
@require_auth
@require_admin
@limit_api("30 per minute")
def create_country():
    data = request.get_json(silent=True)
    if not data:
        return error_response("JSON body required")
    try:
        row_id = data_ingestion_service.ingest_country(data, source="api", ingested_by=g.user_email)
        return created_response(data={"id": row_id})
    except ValueError as exc:
        return error_response(str(exc))


@admin_places_bp.route("/states", methods=["POST"])
@require_auth
@require_admin
@limit_api("30 per minute")
def create_state():
    data = request.get_json(silent=True)
    if not data:
        return error_response("JSON body required")
    try:
        row_id = data_ingestion_service.ingest_state(data, source="api", ingested_by=g.user_email)
        return created_response(data={"id": row_id})
    except ValueError as exc:
        return error_response(str(exc))


@admin_places_bp.route("/cities", methods=["POST"])
@require_auth
@require_admin
@limit_api("30 per minute")
def create_city():
    data = request.get_json(silent=True)
    if not data:
        return error_response("JSON body required")
    try:
        row_id = data_ingestion_service.ingest_city(data, source="api", ingested_by=g.user_email)
        return created_response(data={"id": row_id})
    except ValueError as exc:
        return error_response(str(exc))


# ------------------------------------------------------------------
# Photos & Tags
# ------------------------------------------------------------------

@admin_places_bp.route("/photos", methods=["POST"])
@require_auth
@require_admin
@limit_api("30 per minute")
def create_photo():
    data = request.get_json(silent=True)
    if not data:
        return error_response("JSON body required")
    try:
        row_id = data_ingestion_service.ingest_photo(data, source="api", ingested_by=g.user_email)
        return created_response(data={"id": row_id})
    except ValueError as exc:
        return error_response(str(exc))


@admin_places_bp.route("/tags", methods=["POST"])
@require_auth
@require_admin
@limit_api("30 per minute")
def create_tag():
    data = request.get_json(silent=True)
    if not data:
        return error_response("JSON body required")
    try:
        row_id = data_ingestion_service.ingest_tag(data, source="api", ingested_by=g.user_email)
        return created_response(data={"id": row_id})
    except ValueError as exc:
        return error_response(str(exc))


# ------------------------------------------------------------------
# Audit log viewer
# ------------------------------------------------------------------

@admin_places_bp.route("/audit", methods=["GET"])
@require_auth
@require_admin
@limit_api("60 per minute")
def get_audit_log():
    limit = min(int(request.args.get("limit", 50)), 200)
    offset = int(request.args.get("offset", 0))
    entity_type = request.args.get("entity_type")
    action = request.args.get("action")

    where_clauses = []
    params = []
    if entity_type:
        where_clauses.append("entity_type = ?")
        params.append(entity_type)
    if action:
        where_clauses.append("action = ?")
        params.append(action)

    where = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    rows = travel_db.execute_query(
        f"SELECT * FROM ingestion_log {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (*params, limit, offset),
    )
    total = travel_db.execute_count(
        f"SELECT COUNT(*) FROM ingestion_log {where}", tuple(params)
    )
    return success_response(data={"total": total, "logs": rows})
