"""
Data Ingestion Service
=======================
Validates, inserts, updates and bulk-imports travel entities
(countries, states, cities, places, photos, tags, opening_hours).

Every write passes through Pydantic validation, FK/duplicate checks,
audit logging (via TravelDatabase helpers), FTS rebuild, and cache
invalidation.
"""

import csv
import json
import logging
from io import StringIO
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from app.infrastructure.cache.redis import redis_client
from app.infrastructure.db.travel_db import travel_db
from app.schemas.places import (BulkResult, CityCreate, CountryCreate,
                                GeoWarning, OpeningHoursCreate, PhotoCreate,
                                PlaceCreate, PlaceUpdate, RowError,
                                StateCreate, TagCreate, ValidationResult,
                                haversine_km)
from pydantic import ValidationError as PydanticValidationError

logger = logging.getLogger(__name__)

# Maximum acceptable distance (km) between a place and its parent city
_GEO_WARN_THRESHOLD_KM = 150.0


class DataIngestionService:
    """Orchestrates validated writes into travel_data_complete.db."""

    # ------------------------------------------------------------------
    # Single-entity writes
    # ------------------------------------------------------------------

    def ingest_country(
        self, data: Dict[str, Any], *, source: str = "api", ingested_by: Optional[str] = None
    ) -> int:
        validated = CountryCreate(**data)
        self._check_duplicate("countries", {"country_name": validated.country_name})
        row_id = travel_db.insert_one(
            "countries",
            validated.model_dump(),
            source=source,
            ingested_by=ingested_by,
        )
        return row_id

    def ingest_state(
        self, data: Dict[str, Any], *, source: str = "api", ingested_by: Optional[str] = None
    ) -> int:
        validated = StateCreate(**data)
        self._verify_foreign_key("countries", validated.country_id)
        self._check_duplicate("states", {"state_name": validated.state_name, "country_id": validated.country_id})
        row_id = travel_db.insert_one(
            "states",
            validated.model_dump(),
            source=source,
            ingested_by=ingested_by,
        )
        return row_id

    def ingest_city(
        self, data: Dict[str, Any], *, source: str = "api", ingested_by: Optional[str] = None
    ) -> int:
        validated = CityCreate(**data)
        self._verify_foreign_key("states", validated.state_id)
        self._check_duplicate("cities", {"city_name": validated.city_name, "state_id": validated.state_id})
        row_id = travel_db.insert_one(
            "cities",
            validated.model_dump(),
            source=source,
            ingested_by=ingested_by,
        )
        return row_id

    def ingest_place(
        self, data: Dict[str, Any], *, source: str = "api", ingested_by: Optional[str] = None
    ) -> int:
        validated = PlaceCreate(**data)
        self._verify_foreign_key("cities", validated.city_id)
        self._check_duplicate("places", {"place_name": validated.place_name, "city_id": validated.city_id})
        row_id = travel_db.insert_one(
            "places",
            validated.model_dump(exclude_none=True),
            source=source,
            ingested_by=ingested_by,
        )
        travel_db.rebuild_fts()
        self._invalidate_related_cache()
        return row_id

    def ingest_photo(
        self, data: Dict[str, Any], *, source: str = "api", ingested_by: Optional[str] = None
    ) -> int:
        validated = PhotoCreate(**data)
        self._verify_foreign_key("places", validated.place_id)
        row_id = travel_db.insert_one(
            "photos",
            validated.model_dump(exclude_none=True),
            source=source,
            ingested_by=ingested_by,
        )
        self._invalidate_related_cache()
        return row_id

    def ingest_opening_hours(
        self, data: Dict[str, Any], *, source: str = "api", ingested_by: Optional[str] = None
    ) -> int:
        validated = OpeningHoursCreate(**data)
        self._verify_foreign_key("places", validated.place_id)
        row_id = travel_db.insert_one(
            "opening_hours",
            validated.model_dump(exclude_none=True),
            source=source,
            ingested_by=ingested_by,
        )
        return row_id

    def ingest_tag(
        self, data: Dict[str, Any], *, source: str = "api", ingested_by: Optional[str] = None
    ) -> int:
        validated = TagCreate(**data)
        existing = travel_db.execute_one(
            "SELECT id FROM tags WHERE tag_name = ?", (validated.tag_name,)
        )
        if existing:
            return existing["id"]
        row_id = travel_db.insert_one(
            "tags",
            validated.model_dump(),
            source=source,
            ingested_by=ingested_by,
        )
        return row_id

    # ------------------------------------------------------------------
    # Update / Delete
    # ------------------------------------------------------------------

    def update_place(
        self,
        place_id: int,
        data: Dict[str, Any],
        *,
        source: str = "api",
        ingested_by: Optional[str] = None,
    ) -> bool:
        validated = PlaceUpdate(**data)
        changes = validated.model_dump(exclude_none=True)
        if not changes:
            return False
        changed = travel_db.update_one("places", place_id, changes, source=source, ingested_by=ingested_by)
        if changed:
            travel_db.rebuild_fts()
            self._invalidate_related_cache()
        return changed

    def delete_place(
        self, place_id: int, *, source: str = "api", ingested_by: Optional[str] = None
    ) -> bool:
        deleted = travel_db.delete_one("places", place_id, source=source, ingested_by=ingested_by)
        if deleted:
            travel_db.rebuild_fts()
            self._invalidate_related_cache()
        return deleted

    # ------------------------------------------------------------------
    # Bulk operations
    # ------------------------------------------------------------------

    def ingest_places_bulk(
        self,
        rows: List[Dict[str, Any]],
        *,
        source: str = "bulk",
        ingested_by: Optional[str] = None,
        skip_geo_check: bool = False,
    ) -> BulkResult:
        result = BulkResult()
        valid_rows: List[Dict[str, Any]] = []

        for idx, row in enumerate(rows):
            try:
                validated = PlaceCreate(**row)
                self._verify_foreign_key("cities", validated.city_id)
                dup = self._find_duplicate("places", {"place_name": validated.place_name, "city_id": validated.city_id})
                if dup is not None:
                    result.skipped += 1
                    result.errors.append(RowError(row=idx, message=f"Duplicate of id={dup}"))
                    continue

                # Geo-distance warning
                if not skip_geo_check and validated.latitude is not None:
                    warn = self._geo_distance_check(validated.latitude, validated.longitude, validated.city_id)
                    if warn:
                        result.warnings.append(GeoWarning(row=idx, place_name=validated.place_name, **warn))

                valid_rows.append(validated.model_dump(exclude_none=True))
            except PydanticValidationError as exc:
                result.errors.append(RowError(row=idx, message=str(exc)))
            except ValueError as exc:
                result.errors.append(RowError(row=idx, message=str(exc)))

        if valid_rows:
            ids = travel_db.insert_many("places", valid_rows, source=source, ingested_by=ingested_by)
            result.inserted = len(ids)
            travel_db.rebuild_fts()
            self._invalidate_related_cache()

        return result

    def validate_only(
        self, rows: List[Dict[str, Any]], *, skip_geo_check: bool = False
    ) -> ValidationResult:
        vr = ValidationResult(total=len(rows))

        for idx, row in enumerate(rows):
            try:
                validated = PlaceCreate(**row)
                self._verify_foreign_key("cities", validated.city_id)
                dup = self._find_duplicate("places", {"place_name": validated.place_name, "city_id": validated.city_id})
                if dup is not None:
                    vr.errors.append(RowError(row=idx, message=f"Duplicate of id={dup}"))
                    continue
                if not skip_geo_check and validated.latitude is not None:
                    warn = self._geo_distance_check(validated.latitude, validated.longitude, validated.city_id)
                    if warn:
                        vr.warnings.append(GeoWarning(row=idx, place_name=validated.place_name, **warn))
                vr.valid += 1
            except PydanticValidationError as exc:
                vr.errors.append(RowError(row=idx, message=str(exc)))
            except ValueError as exc:
                vr.errors.append(RowError(row=idx, message=str(exc)))

        return vr

    # ------------------------------------------------------------------
    # CSV / JSON import
    # ------------------------------------------------------------------

    def import_from_csv(
        self,
        file_content: Union[str, Path],
        entity_type: str = "place",
        *,
        source: str = "bulk",
        ingested_by: Optional[str] = None,
    ) -> BulkResult:
        text = self._read_content(file_content)
        reader = csv.DictReader(StringIO(text))
        rows = [self._coerce_csv_row(r) for r in reader]
        return self._import_rows(rows, entity_type, source=source, ingested_by=ingested_by)

    def import_from_json(
        self,
        file_content: Union[str, Path],
        entity_type: str = "place",
        *,
        source: str = "bulk",
        ingested_by: Optional[str] = None,
    ) -> BulkResult:
        text = self._read_content(file_content)
        data = json.loads(text)
        rows = data if isinstance(data, list) else data.get("places", data.get("items", []))
        return self._import_rows(rows, entity_type, source=source, ingested_by=ingested_by)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _read_content(src: Union[str, Path]) -> str:
        if isinstance(src, Path):
            return src.read_text(encoding="utf-8")
        return src

    def _import_rows(
        self,
        rows: List[Dict[str, Any]],
        entity_type: str,
        *,
        source: str = "bulk",
        ingested_by: Optional[str] = None,
    ) -> BulkResult:
        dispatch = {
            "place": self.ingest_places_bulk,
        }
        handler = dispatch.get(entity_type)
        if not handler:
            single_dispatch = {
                "country": self.ingest_country,
                "state": self.ingest_state,
                "city": self.ingest_city,
                "photo": self.ingest_photo,
                "tag": self.ingest_tag,
                "opening_hours": self.ingest_opening_hours,
            }
            single = single_dispatch.get(entity_type)
            if not single:
                raise ValueError(f"Unknown entity_type: {entity_type}")
            result = BulkResult()
            for idx, row in enumerate(rows):
                try:
                    single(row, source=source, ingested_by=ingested_by)
                    result.inserted += 1
                except (PydanticValidationError, ValueError) as exc:
                    result.errors.append(RowError(row=idx, message=str(exc)))
            return result

        return handler(rows, source=source, ingested_by=ingested_by)

    def _verify_foreign_key(self, table: str, fk_id: int) -> None:
        row = travel_db.execute_one(f"SELECT id FROM {table} WHERE id = ?", (fk_id,))
        if not row:
            raise ValueError(f"{table} id={fk_id} does not exist")

    def _find_duplicate(self, table: str, fields: Dict[str, Any]) -> Optional[int]:
        where = " AND ".join(f"{k} = ?" for k in fields)
        row = travel_db.execute_one(
            f"SELECT id FROM {table} WHERE {where}", tuple(fields.values())
        )
        return row["id"] if row else None

    def _check_duplicate(self, table: str, fields: Dict[str, Any]) -> None:
        dup_id = self._find_duplicate(table, fields)
        if dup_id is not None:
            label = " / ".join(f"{k}={v}" for k, v in fields.items())
            raise ValueError(f"Duplicate entry in {table}: {label} (existing id={dup_id})")

    def _geo_distance_check(
        self, lat: float, lng: float, city_id: int
    ) -> Optional[Dict[str, Any]]:
        city = travel_db.execute_one(
            "SELECT city_name, latitude, longitude FROM cities WHERE id = ?", (city_id,)
        )
        if not city or city["latitude"] is None:
            return None
        dist = haversine_km(lat, lng, city["latitude"], city["longitude"])
        if dist > _GEO_WARN_THRESHOLD_KM:
            return {"distance_km": round(dist, 2), "city_name": city["city_name"]}
        return None

    @staticmethod
    def _invalidate_related_cache() -> None:
        if redis_client.available:
            redis_client.delete_pattern("place_search:*")

    @staticmethod
    def _coerce_csv_row(row: Dict[str, str]) -> Dict[str, Any]:
        """Convert CSV string values to appropriate Python types."""
        coerced: Dict[str, Any] = {}
        int_fields = {"city_id", "place_id", "state_id", "country_id", "rating_tourist_priority", "rating_traveler_experience", "thumbnail_width", "thumbnail_height"}
        float_fields = {"latitude", "longitude", "rank_score"}
        bool_fields = {"sunrise_view", "sunset_view"}

        for key, val in row.items():
            if val == "" or val is None:
                coerced[key] = None
            elif key in int_fields:
                coerced[key] = int(val)
            elif key in float_fields:
                coerced[key] = float(val)
            elif key in bool_fields:
                coerced[key] = val.lower() in ("true", "1", "yes")
            else:
                coerced[key] = val
        return coerced


# Singleton
data_ingestion_service = DataIngestionService()
