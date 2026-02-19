"""
TripRaft Backend Migration Script
===================================
Migrates from scattered module structure to clean enterprise architecture.

This script:
1. Creates domain model files with updated imports
2. Migrates service files with updated imports
3. Migrates route files with updated imports
4. Creates schema files
5. Updates factory and entry point
6. Moves old files to unwanted/
7. Adds .llm documentation files
"""

import os
import re
import shutil
from pathlib import Path

BACKEND = Path(__file__).parent
APP = BACKEND / "app"

# ============================================================================
# IMPORT REPLACEMENT RULES
# ============================================================================

IMPORT_RULES = [
    # -- shared_db -> new locations --
    (r"from shared_db\.models import Base, User, UserSession.*",
     "from app.infrastructure.db.base import Base\nfrom app.domain.users.models import User, UserSession"),
    (r"from shared_db\.models import Base, User.*",
     "from app.infrastructure.db.base import Base\nfrom app.domain.users.models import User"),
    (r"from shared_db\.models import Base.*",
     "from app.infrastructure.db.base import Base"),
    (r"from shared_db\.models import User, UserSession",
     "from app.domain.users.models import User, UserSession"),
    (r"from shared_db\.models import User",
     "from app.domain.users.models import User"),
    (r"from shared_db\.connection import (.+)",
     r"from app.infrastructure.db.connection import \1"),
    (r"from shared_db\.auth import (.+)",
     r"from app.infrastructure.auth.decorators import \1"),
    (r"from shared_db import (.+)",
     r"from app.infrastructure.db.connection import \1"),
    (r"from shared_db\.schemas import (.+)",
     r"from app.schemas.common import \1"),

    # -- expense_engine -> new locations --
    (r"from expense_engine\.database\.models import (.+)",
     r"from app.domain.expenses.models import \1"),
    (r"from expense_engine\.database import (.+)",
     r"from app.infrastructure.db.connection import \1"),
    (r"from expense_engine\.auth\.jwt_handler import (.+)",
     r"from app.infrastructure.auth.jwt import \1"),
    (r"from expense_engine\.auth\.password import (.+)",
     r"from app.infrastructure.auth.password import \1"),
    (r"from expense_engine\.auth import (.+)",
     r"from app.infrastructure.auth.decorators import \1"),
    (r"from expense_engine\.services\.auth_service import (.+)",
     r"from app.services.auth_service import \1"),
    (r"from expense_engine\.services\.group_service_sql import (.+)",
     r"from app.services.expense_group_service import \1"),
    (r"from expense_engine\.services\.expense_service_sql import (.+)",
     r"from app.services.expense_service import \1"),
    (r"from expense_engine\.services\.settlement_service_sql import (.+)",
     r"from app.services.settlement_service import \1"),
    (r"from expense_engine\.services\.invitation_service_sql import (.+)",
     r"from app.services.expense_invite_service import \1"),
    (r"from expense_engine\.services\.email_service import (.+)",
     r"from app.services.email_service import \1"),
    (r"from expense_engine\.database import init_db",
     "from app.infrastructure.db.connection import init_db"),

    # Relative imports from expense_engine routes/services
    (r"from \.\.database\.models import (.+)",
     r"from app.domain.expenses.models import \1"),
    (r"from \.\.database import (.+)",
     r"from app.infrastructure.db.connection import \1"),
    (r"from \.\.auth\.jwt_handler import (.+)",
     r"from app.infrastructure.auth.jwt import \1"),
    (r"from \.\.auth\.password import (.+)",
     r"from app.infrastructure.auth.password import \1"),
    (r"from \.\.auth import (.+)",
     r"from app.infrastructure.auth.decorators import \1"),
    (r"from \.\.services\.auth_service import (.+)",
     r"from app.services.auth_service import \1"),
    (r"from \.\.services\.group_service_sql import (.+)",
     r"from app.services.expense_group_service import \1"),
    (r"from \.\.services\.expense_service_sql import (.+)",
     r"from app.services.expense_service import \1"),
    (r"from \.\.services\.settlement_service_sql import (.+)",
     r"from app.services.settlement_service import \1"),
    (r"from \.\.services\.invitation_service_sql import (.+)",
     r"from app.services.expense_invite_service import \1"),
    (r"from \.\.services\.email_service import (.+)",
     r"from app.services.email_service import \1"),

    # -- Group_planner -> new locations --
    (r"from Group_planner\.database\.models import (.+)",
     r"from app.domain.group_planner.models import \1"),
    (r"from Group_planner\.database\.connection import (.+)",
     r"from app.infrastructure.db.connection import \1"),
    (r"from Group_planner\.services\.group_service import (.+)",
     r"from app.services.travel_group_service import \1"),
    (r"from Group_planner\.services\.place_service import (.+)",
     r"from app.services.travel_place_service import \1"),
    (r"from Group_planner\.services\.poll_service import (.+)",
     r"from app.services.poll_service import \1"),
    (r"from Group_planner\.services\.invitation_service import (.+)",
     r"from app.services.trip_invite_service import \1"),
    (r"from Group_planner\.services\.checklist_service import (.+)",
     r"from app.services.checklist_service import \1"),
    (r"from Group_planner\.services\.events_service import (.+)",
     r"from app.services.events_service import \1"),
    (r"from Group_planner\.services\.destination_service import (.+)",
     r"from app.services.destination_service import \1"),

    # Relative imports from Group_planner
    (r"from \.\.database\.models import (.+)",
     r"from app.domain.group_planner.models import \1"),
    (r"from \.\.database\.connection import (.+)",
     r"from app.infrastructure.db.connection import \1"),
    (r"from \.\.services\.group_service import (.+)",
     r"from app.services.travel_group_service import \1"),
    (r"from \.\.services\.place_service import (.+)",
     r"from app.services.travel_place_service import \1"),
    (r"from \.\.services\.poll_service import (.+)",
     r"from app.services.poll_service import \1"),
    (r"from \.\.services\.invitation_service import (.+)",
     r"from app.services.trip_invite_service import \1"),
    (r"from \.\.services\.checklist_service import (.+)",
     r"from app.services.checklist_service import \1"),
    (r"from \.\.services\.events_service import (.+)",
     r"from app.services.events_service import \1"),
    (r"from \.\.services\.destination_service import (.+)",
     r"from app.services.destination_service import \1"),

    # -- middleware / cache --
    (r"from middleware\.rate_limiter import (.+)",
     r"from app.core.rate_limiter import \1"),
    (r"from middleware import (.+)",
     r"from app.core.rate_limiter import \1"),
    (r"from cache\.redis_client import (.+)",
     r"from app.infrastructure.cache.redis import \1"),

    # -- email_config --
    (r"from email_config import (.+)",
     r"from app.services.email_service import \1"),

    # -- place_search internal --
    (r"from place_search\.database import (.+)",
     r"from app.domain.places.repository import \1"),
    (r"from place_search\.models import (.+)",
     r"from app.domain.places.models import \1"),
    (r"from place_search\.config import (.+)",
     r"from app.core.config import \1"),
    (r"from place_search\.services import (.+)",
     r"from app.services.place_search_service import \1"),
    (r"from \.database import (.+)",
     r"from app.domain.places.repository import \1"),
    (r"from \.models import (.+)",
     r"from app.domain.places.models import \1"),
    (r"from \.config import (.+)",
     r"from app.core.config import \1"),
    (r"from \.services import (.+)",
     r"from app.services.place_search_service import \1"),
]


def transform_imports(content, source_module=None):
    """Apply import transformation rules to file content."""
    lines = content.split('\n')
    new_lines = []
    for line in lines:
        transformed = False
        for pattern, replacement in IMPORT_RULES:
            if re.match(pattern, line.strip()):
                indent = len(line) - len(line.lstrip())
                new_line = re.sub(pattern, replacement, line.strip())
                # Handle multi-line replacements
                for sub_line in new_line.split('\n'):
                    new_lines.append(' ' * indent + sub_line)
                transformed = True
                break
        if not transformed:
            new_lines.append(line)
    return '\n'.join(new_lines)


def replace_prints_with_logging(content):
    """Replace print() calls with logger calls."""
    # Add logger if not present and there are print statements
    if 'print(' in content and 'logger = logging.getLogger' not in content:
        # Find the import section end
        lines = content.split('\n')
        insert_idx = 0
        for i, line in enumerate(lines):
            if line.startswith('import ') or line.startswith('from '):
                insert_idx = i + 1
            elif line.strip() and not line.startswith('#') and not line.startswith('"""') and insert_idx > 0:
                break

        has_logging_import = any('import logging' in l for l in lines)
        if not has_logging_import:
            lines.insert(insert_idx, '')
            lines.insert(insert_idx + 1, 'import logging')
            insert_idx += 2

        has_logger = any('logger = logging.getLogger' in l for l in lines)
        if not has_logger:
            lines.insert(insert_idx, '')
            lines.insert(insert_idx + 1, 'logger = logging.getLogger(__name__)')

        content = '\n'.join(lines)

    # Replace print statements with logger.info
    content = re.sub(r'(\s*)print\(f(["\'])(.*?)\2\)', r'\1logger.info(\2\3\2)', content)
    content = re.sub(r'(\s*)print\((["\'])(.*?)\2\)', r'\1logger.info(\2\3\2)', content)
    return content


def write_file(path, content):
    """Write content to file, creating directories as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
    print(f"  Created: {path.relative_to(BACKEND)}")


def read_file(path):
    """Read file content."""
    return path.read_text(encoding='utf-8')


# ============================================================================
# PHASE 1: Create Domain Model Files
# ============================================================================

def create_expense_models():
    """Create domain/expenses/models.py from expense_engine models."""
    src = BACKEND / "expense_engine" / "database" / "models.py"
    content = read_file(src)
    content = transform_imports(content)
    # Remove the noqa comment that's no longer relevant
    content = content.replace("  # noqa: F401", "")
    write_file(APP / "domain" / "expenses" / "models.py", content)

    # __init__.py
    init_content = '''"""
Expense domain models and business entities.
"""

from .models import (
    Expense,
    ExpenseHistory,
    ExpenseSplit,
    Group,
    GroupBalance,
    GroupMember,
    Invitation,
    Settlement,
)

__all__ = [
    "Group",
    "GroupMember",
    "Expense",
    "ExpenseSplit",
    "Settlement",
    "GroupBalance",
    "Invitation",
    "ExpenseHistory",
]
'''
    write_file(APP / "domain" / "expenses" / "__init__.py", init_content)


def create_group_planner_models():
    """Create domain/group_planner/models.py from Group_planner models."""
    src = BACKEND / "Group_planner" / "database" / "models.py"
    content = read_file(src)
    content = transform_imports(content)
    content = content.replace("  # noqa: F401", "")
    write_file(APP / "domain" / "group_planner" / "models.py", content)

    init_content = '''"""
Group planner domain models for collaborative travel planning.
"""

from .models import (
    ChecklistItem,
    GroupActivity,
    ItineraryDocument,
    Place,
    PlaceVote,
    Poll,
    PollVote,
    TravelGroup,
    TripInvitation,
    TripMember,
)

__all__ = [
    "TravelGroup",
    "TripMember",
    "Place",
    "PlaceVote",
    "Poll",
    "PollVote",
    "TripInvitation",
    "ChecklistItem",
    "ItineraryDocument",
    "GroupActivity",
]
'''
    write_file(APP / "domain" / "group_planner" / "__init__.py", init_content)


def create_places_domain():
    """Create domain/places/ from place_search models and api models."""
    # Models from place_search
    src = BACKEND / "place_search" / "models.py"
    content = read_file(src)
    write_file(APP / "domain" / "places" / "models.py", content)

    # Repository from place_search database
    src = BACKEND / "place_search" / "database.py"
    content = read_file(src)
    content = transform_imports(content)
    write_file(APP / "domain" / "places" / "repository.py", content)

    init_content = '''"""
Place and location domain models for geographic data.
"""
'''
    write_file(APP / "domain" / "places" / "__init__.py", init_content)


# ============================================================================
# PHASE 2: Create Schema Files
# ============================================================================

def create_schema_files():
    """Create schema files from shared_db/schemas.py."""
    src = BACKEND / "shared_db" / "schemas.py"
    content = read_file(src)

    # Fix the duplicate return statement
    content = content.replace(
        "        return None, err.messages\n        return None, err.messages",
        "        return None, err.messages"
    )

    # Write as common schemas (contains both expense and GP schemas + validate_request)
    write_file(APP / "schemas" / "common.py", content)

    # Update schemas/__init__.py
    init_content = '''"""
Request/response validation schemas.
"""

from .common import (
    AddPlaceSchema,
    ChangePasswordSchema,
    CheckEmailSchema,
    CreateChecklistItemSchema,
    CreateExpenseGroupSchema,
    CreateExpenseSchema,
    CreatePollSchema,
    CreateSettlementSchema,
    CreateTravelGroupSchema,
    InviteMemberSchema,
    LoginSchema,
    SignupSchema,
    UpdateBudgetSchema,
    VotePollSchema,
    validate_request,
)
from .users import (
    AuthResponse,
    MessageResponse,
    PasswordChangeRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
    UserUpdateRequest,
)

__all__ = [
    # Common schemas
    "validate_request",
    "SignupSchema",
    "LoginSchema",
    "ChangePasswordSchema",
    "CheckEmailSchema",
    "CreateExpenseGroupSchema",
    "CreateExpenseSchema",
    "CreateSettlementSchema",
    "CreateTravelGroupSchema",
    "UpdateBudgetSchema",
    "InviteMemberSchema",
    "CreatePollSchema",
    "VotePollSchema",
    "CreateChecklistItemSchema",
    "AddPlaceSchema",
    # User schemas
    "UserRegisterRequest",
    "UserLoginRequest",
    "UserUpdateRequest",
    "PasswordChangeRequest",
    "RefreshTokenRequest",
    "UserResponse",
    "AuthResponse",
    "TokenResponse",
    "MessageResponse",
]
'''
    write_file(APP / "schemas" / "__init__.py", init_content)


# ============================================================================
# PHASE 3: Migrate Service Files
# ============================================================================

SERVICE_MAPPINGS = [
    # (source_path, dest_filename)
    ("expense_engine/services/auth_service.py", "auth_service.py"),
    ("expense_engine/services/group_service_sql.py", "expense_group_service.py"),
    ("expense_engine/services/expense_service_sql.py", "expense_service.py"),
    ("expense_engine/services/settlement_service_sql.py", "settlement_service.py"),
    ("expense_engine/services/invitation_service_sql.py", "expense_invite_service.py"),
    ("expense_engine/services/email_service.py", "email_service.py"),
    ("Group_planner/services/group_service.py", "travel_group_service.py"),
    ("Group_planner/services/place_service.py", "travel_place_service.py"),
    ("Group_planner/services/poll_service.py", "poll_service.py"),
    ("Group_planner/services/invitation_service.py", "trip_invite_service.py"),
    ("Group_planner/services/checklist_service.py", "checklist_service.py"),
    ("Group_planner/services/events_service.py", "events_service.py"),
    ("Group_planner/services/destination_service.py", "destination_service.py"),
    ("place_search/services.py", "place_search_service.py"),
]


def migrate_services():
    """Migrate all service files with updated imports."""
    for src_rel, dest_name in SERVICE_MAPPINGS:
        src = BACKEND / src_rel
        if not src.exists():
            print(f"  SKIP (not found): {src_rel}")
            continue
        content = read_file(src)
        content = transform_imports(content)
        content = replace_prints_with_logging(content)
        write_file(APP / "services" / dest_name, content)

    # Update services __init__.py
    init_content = '''"""
Service layer -- orchestrates domain logic and infrastructure.
"""

from .user_service import UserService, user_service

__all__ = [
    "UserService",
    "user_service",
]
'''
    write_file(APP / "services" / "__init__.py", init_content)


# ============================================================================
# PHASE 4: Migrate Route Files
# ============================================================================

ROUTE_MAPPINGS = [
    # (source_path, dest_filename)
    ("expense_engine/routes/auth_routes.py", "auth.py"),
    ("expense_engine/routes/groups_sql_routes.py", "expense_groups.py"),
    ("expense_engine/routes/expenses_sql_routes.py", "expenses.py"),
    ("expense_engine/routes/settlements_sql_routes.py", "settlements.py"),
    ("expense_engine/routes/invitations_sql_routes.py", "expense_invitations.py"),
    ("Group_planner/routes/groups_routes.py", "gp_groups.py"),
    ("Group_planner/routes/places_routes.py", "gp_places.py"),
    ("Group_planner/routes/polls_routes.py", "gp_polls.py"),
    ("Group_planner/routes/invitations_routes.py", "gp_invitations.py"),
    ("Group_planner/routes/checklist_routes.py", "gp_checklist.py"),
    ("Group_planner/routes/events_routes.py", "gp_events.py"),
    ("Group_planner/routes/optimized_routes.py", "gp_destinations.py"),
]


def migrate_routes():
    """Migrate all route files with updated imports."""
    for src_rel, dest_name in ROUTE_MAPPINGS:
        src = BACKEND / src_rel
        if not src.exists():
            print(f"  SKIP (not found): {src_rel}")
            continue
        content = read_file(src)
        content = transform_imports(content)
        content = replace_prints_with_logging(content)
        write_file(APP / "api" / "v1" / dest_name, content)

    # Migrate locations routes
    src = BACKEND / "api" / "routes" / "locations.py"
    if src.exists():
        content = read_file(src)
        # Fix imports for locations route
        content = content.replace(
            "from ..utils import ",
            "from app.api.utils import "
        )
        content = content.replace(
            "from ..utils.database import ",
            "from app.domain.places.location_repository import "
        )
        content = content.replace(
            "from ..models.places import ",
            "from app.domain.places.location_models import "
        )
        content = content.replace(
            "from ..models import ",
            "from app.domain.places.location_models import "
        )
        content = transform_imports(content)
        content = replace_prints_with_logging(content)
        write_file(APP / "api" / "v1" / "locations.py", content)

    # Migrate trip planner routes
    src = BACKEND / "api" / "routes" / "trip_planner.py"
    if src.exists():
        content = read_file(src)
        content = content.replace(
            "from ..utils import ",
            "from app.api.utils import "
        )
        content = content.replace(
            "from ..utils.database import ",
            "from app.domain.places.location_repository import "
        )
        content = content.replace(
            "from ..models.places import ",
            "from app.domain.places.location_models import "
        )
        content = content.replace(
            "from ..models import ",
            "from app.domain.places.location_models import "
        )
        content = transform_imports(content)
        content = replace_prints_with_logging(content)
        write_file(APP / "api" / "v1" / "trips.py", content)

    # Migrate place search routes
    src = BACKEND / "place_search" / "routes.py"
    if src.exists():
        content = read_file(src)
        content = transform_imports(content)
        content = replace_prints_with_logging(content)
        write_file(APP / "api" / "v1" / "places.py", content)

    # Create v1/__init__.py
    init_content = '''"""
API v1 route blueprints.
"""
'''
    write_file(APP / "api" / "v1" / "__init__.py", init_content)


# ============================================================================
# PHASE 5: Migrate Supporting Files
# ============================================================================

def migrate_supporting():
    """Migrate middleware, utils, and supporting files."""
    # Request logger (from api/middleware/request_logger.py)
    src = BACKEND / "api" / "middleware" / "request_logger.py"
    if src.exists():
        content = read_file(src)
        write_file(APP / "api" / "middleware.py", content)

    # Route viewer
    src = BACKEND / "api" / "route_viewer.py"
    if src.exists():
        content = read_file(src)
        write_file(APP / "api" / "route_viewer.py", content)

    # API utils (responses, validators)
    for name in ["responses.py", "validators.py", "database.py", "__init__.py"]:
        src = BACKEND / "api" / "utils" / name
        if src.exists():
            content = read_file(src)
            write_file(APP / "api" / "utils" / name, content)

    # Location models (from api/models/places.py)
    src = BACKEND / "api" / "models" / "places.py"
    if src.exists():
        content = read_file(src)
        # Update imports to use new database location
        content = content.replace(
            "from ..utils.database import get_db",
            "from app.api.utils.database import get_db"
        )
        content = content.replace(
            "from ..utils import ",
            "from app.api.utils import "
        )
        write_file(APP / "domain" / "places" / "location_models.py", content)

    # Location repository (from api/utils/database.py for DatabaseManager)
    src = BACKEND / "api" / "utils" / "database.py"
    if src.exists():
        content = read_file(src)
        write_file(APP / "domain" / "places" / "location_repository.py", content)

    # Email config
    src = BACKEND / "email_config.py"
    if src.exists():
        content = read_file(src)
        write_file(APP / "infrastructure" / "email" / "config.py", content)


# ============================================================================
# PHASE 6: Create/Update Factory
# ============================================================================

def create_factory():
    """Create the unified Flask application factory."""
    content = '''"""
TripRaft Application Factory
Creates and configures the Flask application with all routes and middleware.
"""

import logging
import sys
from pathlib import Path

from flask import Flask, jsonify, request
from flask_compress import Compress
from flask_cors import CORS

from app.core.config import get_config
from app.core.logging import setup_logging
from app.core.security import add_security_headers

logger = logging.getLogger(__name__)


def create_app():
    """
    Application factory pattern.

    Returns:
        Configured Flask application
    """
    app = Flask(__name__)

    # Load configuration
    config = get_config()
    app.config.from_object(config)

    # Setup structured logging
    setup_logging(app)

    # Initialize request logger
    _init_request_logger(app)

    # CORS
    cors_origins = config.CORS_ORIGINS if hasattr(config, "CORS_ORIGINS") else ["http://localhost:5173"]
    CORS(
        app,
        resources={r"/api/*": {"origins": cors_origins}},
        supports_credentials=True,
        allow_headers=["Content-Type", "Authorization", "Accept", "Origin", "X-Requested-With"],
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        max_age=86400,
    )

    # Explicit OPTIONS handler
    @app.route("/api/<path:path>", methods=["OPTIONS"])
    def handle_options(_path):
        response = app.make_default_options_response()
        origin = request.headers.get("Origin", "")
        allowed_origins = app.config.get("CORS_ORIGINS", [])
        if origin in allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, Accept, Origin, X-Requested-With"
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Max-Age"] = "86400"
        return response

    # Gzip compression
    Compress(app)
    app.config["COMPRESS_MIMETYPES"] = [
        "text/html", "text/css", "text/xml",
        "application/json", "application/javascript", "text/javascript",
    ]
    app.config["COMPRESS_LEVEL"] = 6
    app.config["COMPRESS_MIN_SIZE"] = 500

    # Initialize database
    _init_databases(app)

    # Redis cache
    _init_redis(app)

    # Rate limiter
    _init_rate_limiter(app)

    # Register all blueprints
    _register_blueprints(app)

    # Security middleware
    _register_middleware(app)

    # Error handlers
    _register_error_handlers(app)

    # Root endpoints
    _register_root_endpoints(app)

    # Log registered routes
    _log_routes(app)

    return app


# ---------------------------------------------------------------------------
# Initialisation helpers
# ---------------------------------------------------------------------------

def _init_databases(app):
    """Initialize SQLAlchemy (tripraft.db) and travel database."""
    try:
        from app.infrastructure.db.connection import init_db
        init_db(app)
        logger.info("TripRaft database initialized")
    except Exception as exc:
        logger.warning("Database initialization issue: %s", exc)

    # Initialize travel_data_complete.db (read-only geographic data)
    try:
        config = get_config()
        if hasattr(config, "DATABASE_PATH") and config.DATABASE_PATH and config.DATABASE_PATH.exists():
            from app.api.utils.database import init_database
            init_database(config.DATABASE_PATH)
    except Exception as exc:
        logger.warning("Travel database initialization skipped: %s", exc)


def _init_redis(app):
    """Initialize Redis cache with graceful fallback."""
    try:
        from app.infrastructure.cache.redis import redis_client
        redis_client.init_app(app)
        app.extensions["redis"] = redis_client if redis_client.available else None
    except Exception as exc:
        logger.warning("Redis unavailable, running without cache: %s", exc)
        app.extensions["redis"] = None


def _init_rate_limiter(app):
    """Attach rate limiter to the Flask app."""
    try:
        from app.core.rate_limiter import init_rate_limiter
        init_rate_limiter(app)
    except Exception as exc:
        logger.warning("Rate limiter not available: %s", exc)


def _init_request_logger(app):
    """Initialize colored request/response logger."""
    try:
        from app.api.middleware import init_request_logger
        init_request_logger(app)
    except Exception as exc:
        logger.debug("Request logger not available: %s", exc)


# ---------------------------------------------------------------------------
# Blueprint registration
# ---------------------------------------------------------------------------

def _register_blueprints(app):
    """Register all API route blueprints."""
    api_prefix = app.config.get("API_PREFIX", "/api/v1")

    # --- Health ---
    try:
        from app.api.health import health_bp
        app.register_blueprint(health_bp, url_prefix="/api/health")
    except Exception as exc:
        logger.warning("Health blueprint not available: %s", exc)

    # --- Users (new clean auth) ---
    try:
        from app.api.v1.users import users_bp
        app.register_blueprint(users_bp, url_prefix=f"{api_prefix}/users")
    except Exception as exc:
        logger.warning("Users blueprint not available: %s", exc)

    # --- Expense Engine auth (legacy endpoints /api/expense/*) ---
    try:
        from app.api.v1.auth import auth_bp
        app.register_blueprint(auth_bp)
    except Exception as exc:
        logger.warning("Expense auth blueprint not available: %s", exc)

    # --- Expense groups ---
    try:
        from app.api.v1.expense_groups import groups_sql_bp
        app.register_blueprint(groups_sql_bp)
    except Exception as exc:
        logger.warning("Expense groups blueprint not available: %s", exc)

    # --- Expenses ---
    try:
        from app.api.v1.expenses import expenses_sql_bp
        app.register_blueprint(expenses_sql_bp)
    except Exception as exc:
        logger.warning("Expenses blueprint not available: %s", exc)

    # --- Settlements ---
    try:
        from app.api.v1.settlements import settlements_sql_bp
        app.register_blueprint(settlements_sql_bp)
    except Exception as exc:
        logger.warning("Settlements blueprint not available: %s", exc)

    # --- Expense invitations ---
    try:
        from app.api.v1.expense_invitations import invitations_sql_bp
        app.register_blueprint(invitations_sql_bp)
    except Exception as exc:
        logger.warning("Expense invitations blueprint not available: %s", exc)

    # --- Group Planner ---
    try:
        from app.api.v1.gp_groups import groups_bp
        app.register_blueprint(groups_bp)
    except Exception as exc:
        logger.warning("GP groups blueprint not available: %s", exc)

    try:
        from app.api.v1.gp_places import places_bp
        app.register_blueprint(places_bp)
    except Exception as exc:
        logger.warning("GP places blueprint not available: %s", exc)

    try:
        from app.api.v1.gp_polls import polls_bp
        app.register_blueprint(polls_bp)
    except Exception as exc:
        logger.warning("GP polls blueprint not available: %s", exc)

    try:
        from app.api.v1.gp_invitations import invitations_bp
        app.register_blueprint(invitations_bp)
    except Exception as exc:
        logger.warning("GP invitations blueprint not available: %s", exc)

    try:
        from app.api.v1.gp_checklist import checklist_bp
        app.register_blueprint(checklist_bp)
    except Exception as exc:
        logger.warning("GP checklist blueprint not available: %s", exc)

    try:
        from app.api.v1.gp_events import events_bp
        app.register_blueprint(events_bp)
    except Exception as exc:
        logger.warning("GP events blueprint not available: %s", exc)

    try:
        from app.api.v1.gp_destinations import group_planner_v2
        app.register_blueprint(group_planner_v2)
    except Exception as exc:
        logger.warning("GP destinations blueprint not available: %s", exc)

    # --- Locations ---
    try:
        from app.api.v1.locations import locations_bp
        app.register_blueprint(locations_bp, url_prefix=f"{api_prefix}/locations")
    except Exception as exc:
        logger.warning("Locations blueprint not available: %s", exc)

    # --- Place Search ---
    try:
        from app.api.v1.places import place_search_bp
        app.register_blueprint(place_search_bp)
    except Exception as exc:
        logger.warning("Place search blueprint not available: %s", exc)

    # --- Trip Planner ---
    try:
        from app.api.v1.trips import trip_planner_bp
        app.register_blueprint(trip_planner_bp)
    except Exception as exc:
        logger.warning("Trip planner blueprint not available: %s", exc)

    # --- Route viewer ---
    try:
        from app.api.route_viewer import route_viewer_bp
        app.register_blueprint(route_viewer_bp)
    except Exception as exc:
        logger.warning("Route viewer not available: %s", exc)


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

def _register_middleware(app):
    """Register request/response middleware."""

    @app.before_request
    def before_request():
        if request.method != "OPTIONS":
            app.logger.debug("Request: %s %s", request.method, request.path)

    @app.after_request
    def after_request(response):
        add_security_headers(response)

        # CORS fallback
        origin = request.headers.get("Origin")
        allowed_origins = app.config.get("CORS_ORIGINS", [])
        if origin and origin in allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, Accept, Origin"
            response.headers["Access-Control-Expose-Headers"] = "Content-Type"
        return response


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------

def _register_error_handlers(app):
    """Register custom error handlers."""

    @app.errorhandler(404)
    def not_found(_error):
        return jsonify({"success": False, "error": "Endpoint not found"}), 404

    @app.errorhandler(405)
    def method_not_allowed(_error):
        return jsonify({"success": False, "error": "Method not allowed"}), 405

    @app.errorhandler(429)
    def rate_limited(_error):
        return jsonify({"success": False, "error": "Rate limit exceeded"}), 429

    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error("Internal server error: %s", error, exc_info=True)
        return jsonify({"success": False, "error": "Internal server error"}), 500

    @app.errorhandler(Exception)
    def handle_exception(error):
        app.logger.error("Unhandled exception: %s", error, exc_info=True)
        return jsonify({"success": False, "error": "An unexpected error occurred"}), 500


# ---------------------------------------------------------------------------
# Root endpoints
# ---------------------------------------------------------------------------

def _register_root_endpoints(app):
    """Register root and health check endpoints."""

    @app.route("/health", methods=["GET"])
    def health_check():
        return jsonify({
            "status": "healthy",
            "service": "TripRaft Backend",
            "version": "2.0.0",
        }), 200

    @app.route("/", methods=["GET"])
    def root():
        return jsonify({
            "message": "TripRaft Backend API",
            "version": "2.0.0",
            "status": "operational",
            "endpoints": {
                "health": "/health",
                "routes": "/api/routes",
                "auth": "/api/expense",
                "expenses": "/api/expense/groups",
                "group_planner": "/api/v2/group-planner",
                "locations": "/api/v1/locations",
                "place_search": "/api/v1/place-search",
                "trip_planner": "/api/trip-planner",
            },
        }), 200


# ---------------------------------------------------------------------------
# Debug route listing
# ---------------------------------------------------------------------------

def _log_routes(app):
    """Log all registered routes on startup."""
    route_count = 0
    for rule in app.url_map.iter_rules():
        if rule.endpoint != "static":
            route_count += 1
    logger.info("Registered %d API routes", route_count)
'''
    write_file(APP / "api" / "factory.py", content)

    # Update app/api/__init__.py
    init_content = '''"""
TripRaft API layer.
"""

from .factory import create_app

__all__ = ["create_app"]
'''
    write_file(APP / "api" / "__init__.py", init_content)

    # Update app/__init__.py
    init_content = '''"""
TripRaft Backend Application
Enterprise-grade Flask backend.
"""

from app.api.factory import create_app

__all__ = ["create_app"]
'''
    write_file(APP / "__init__.py", init_content)


# ============================================================================
# PHASE 7: Create New run.py
# ============================================================================

def create_run_py():
    """Create the new main entry point."""
    content = '''"""
TripRaft Backend -- Main Entry Point
Run this file to start the Flask server.
"""

import logging
import os
import sys
from pathlib import Path

# Fix Unicode encoding for Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    os.environ["PYTHONIOENCODING"] = "utf-8"

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app import create_app
from app.core.config import get_config

logger = logging.getLogger(__name__)


def main():
    """Main entry point."""
    config = get_config()
    app = create_app()

    logger.info(
        "Starting TripRaft Backend | env=%s | http://%s:%s",
        config.FLASK_ENV,
        config.HOST,
        config.PORT,
    )

    try:
        app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)
    except Exception as exc:
        logger.critical("Failed to start server: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
'''
    write_file(BACKEND / "run.py", content)


# ============================================================================
# PHASE 8: Move Old Files to unwanted/
# ============================================================================

def move_old_files():
    """Move old scattered modules to unwanted/ folder."""
    unwanted = BACKEND / "unwanted"
    unwanted.mkdir(exist_ok=True)

    old_modules = [
        "api",
        "expense_engine",
        "Group_planner",
        "place_search",
        "shared_db",
        "cache",
        "middleware",
        "email_config.py",
        "run_new.py",
    ]

    for item in old_modules:
        src = BACKEND / item
        if src.exists():
            dest = unwanted / item
            if dest.exists():
                # Remove existing dest to avoid conflicts
                if dest.is_dir():
                    shutil.rmtree(dest)
                else:
                    dest.unlink()
            shutil.move(str(src), str(dest))
            print(f"  Moved: {item} -> unwanted/{item}")
        else:
            print(f"  SKIP (not found): {item}")


# ============================================================================
# PHASE 9: LLM Documentation Files
# ============================================================================

LLM_DOCS = {
    "app": """# app/
Root application package. Contains the entire backend.

## Structure
- core/       -- Framework-agnostic config, logging, exceptions, rate limiting
- infrastructure/ -- DB, cache, auth, email, external APIs
- domain/     -- Business entities and repository patterns
- services/   -- Use-case orchestration (domain + infrastructure)
- api/        -- Flask blueprints, routes, middleware
- schemas/    -- Request/response validation
- workers/    -- Background jobs and schedulers
""",
    "app/core": """# core/
Framework-agnostic core utilities.

## Files
- config.py       -- Application settings loaded from .env
- logging.py      -- Structured JSON logging for production, colored for dev
- exceptions.py   -- Custom exception hierarchy (AppError, ValidationError, etc.)
- rate_limiter.py -- Flask-Limiter integration with per-operation limits
- security.py     -- Security headers and CORS middleware
""",
    "app/infrastructure": """# infrastructure/
External service integrations and technical concerns.

## Sub-packages
- db/       -- SQLAlchemy engine (tripraft.db) + raw sqlite3 (travel_data_complete.db)
- cache/    -- Redis client with JSON serialization and route caching
- auth/     -- JWT token generation/verification, bcrypt passwords, auth decorators
- email/    -- SMTP email service (invitations, password reset)
- external/ -- Third-party API clients (Ticketmaster, etc.)
""",
    "app/infrastructure/db": """# infrastructure/db/
Database layer -- single source of truth for all connections.

## Files
- base.py       -- Shared SQLAlchemy declarative Base
- connection.py -- Engine, SessionLocal, scoped session, init_db(), get_db()
- travel_db.py  -- Read-only sqlite3 connection for travel_data_complete.db
""",
    "app/infrastructure/cache": """# infrastructure/cache/
Redis cache with graceful fallback when unavailable.

## Files
- redis.py -- RedisClient singleton, get/set/delete JSON, cache_response decorator
""",
    "app/infrastructure/auth": """# infrastructure/auth/
Authentication and authorization infrastructure.

## Files
- jwt.py        -- JWT access/refresh token creation and verification
- password.py   -- bcrypt password hashing and verification
- decorators.py -- @require_auth, @require_refresh_token, @optional_auth decorators
""",
    "app/infrastructure/email": """# infrastructure/email/
Email notification infrastructure.

## Files
- smtp.py   -- SMTP email service (send_invitation, send_password_reset, etc.)
- config.py -- Email type enable/disable configuration
""",
    "app/infrastructure/external": """# infrastructure/external/
Third-party API clients.

## Planned
- ticketmaster.py -- Ticketmaster events API client
- amadeus.py      -- Flights and hotels API client
""",
    "app/domain": """# domain/
Business entities and repository patterns. Pure business logic, no Flask.

## Sub-packages
- users/         -- User and UserSession models + repositories
- expenses/      -- Expense engine models (Group, Expense, Settlement, etc.)
- group_planner/ -- Travel planning models (TravelGroup, Place, Poll, etc.)
- places/        -- Geographic data models and repositories
""",
    "app/domain/users": """# domain/users/
User domain -- shared across expense engine and group planner.

## Files
- models.py     -- User, UserSession SQLAlchemy models
- repository.py -- UserRepository, UserSessionRepository CRUD operations

## Database
Table: users, user_sessions (in tripraft.db)
""",
    "app/domain/expenses": """# domain/expenses/
Expense management domain -- Splitwise-style expense splitting.

## Files
- models.py -- Group, GroupMember, Expense, ExpenseSplit, Settlement,
               GroupBalance, Invitation, ExpenseHistory

## Database
Tables in tripraft.db:
- groups, group_members, expenses, expense_splits
- settlements, group_balances, invitations, expense_history
""",
    "app/domain/group_planner": """# domain/group_planner/
Collaborative travel planning domain.

## Files
- models.py -- TravelGroup, TripMember, Place, PlaceVote, Poll, PollVote,
               TripInvitation, ChecklistItem, ItineraryDocument, GroupActivity

## Database
Tables in tripraft.db (prefixed gp_):
- travel_groups, gp_group_members, gp_places, gp_place_votes
- gp_polls, gp_poll_votes, gp_invitations, gp_checklist_items
- gp_itinerary_documents, gp_group_activities
""",
    "app/domain/places": """# domain/places/
Geographic data domain -- countries, states, cities, places.

## Files
- models.py               -- Dataclass models for place search results
- repository.py            -- DatabaseConnection for place search (travel_data_complete.db)
- location_models.py       -- PlacesModel, CitiesModel, etc. for locations API
- location_repository.py   -- DatabaseManager for locations queries

## Database
Read-only: travel_data_complete.db (countries, states, cities, places, photos, tags)
""",
    "app/services": """# services/
Use-case orchestration -- coordinates domain and infrastructure.

## Files
- user_service.py           -- User registration, login, profile management
- auth_service.py           -- Legacy auth (signup/login at /api/expense)
- expense_group_service.py  -- Expense group CRUD
- expense_service.py        -- Expense creation, editing, splitting
- settlement_service.py     -- Settlement recording and balance recalculation
- expense_invite_service.py -- Expense group invitation management
- email_service.py          -- Email notification orchestration
- travel_group_service.py   -- Travel group CRUD and membership
- travel_place_service.py   -- Place suggestions and voting
- poll_service.py           -- Poll creation and voting
- trip_invite_service.py    -- Trip group invitation management
- checklist_service.py      -- Pre-trip checklist items
- events_service.py         -- Ticketmaster event search
- destination_service.py    -- Destination autocomplete and search
- place_search_service.py   -- Full-text place search and autocomplete
""",
    "app/api": """# api/
Flask REST API layer -- routes, middleware, error handling.

## Files
- factory.py      -- Application factory (create_app)
- health.py       -- Health check endpoints (/api/health/*)
- middleware.py    -- Request/response logging
- route_viewer.py -- Styled route listing at /api/routes

## Sub-packages
- v1/   -- All versioned API route blueprints
- utils/ -- Response helpers, validators, database manager
""",
    "app/api/v1": """# api/v1/
Versioned API route blueprints.

## Files
- users.py              -- /api/v1/users (clean auth)
- auth.py               -- /api/expense (legacy auth endpoints)
- expense_groups.py     -- /api/expense/groups
- expenses.py           -- /api/expense/expenses
- settlements.py        -- /api/expense/settlements
- expense_invitations.py-- /api/expense/invitations
- gp_groups.py          -- /api/v2/group-planner (groups)
- gp_places.py          -- /api/v2/group-planner (places)
- gp_polls.py           -- /api/v2/group-planner (polls)
- gp_invitations.py     -- /api/v2/group-planner (invitations)
- gp_checklist.py       -- /api/v2/group-planner (checklist)
- gp_events.py          -- /api/v2/group-planner (events)
- gp_destinations.py    -- /api/v2/group-planner (destination search)
- locations.py          -- /api/v1/locations
- places.py             -- /api/v1/place-search
- trips.py              -- /api/trip-planner
""",
    "app/schemas": """# schemas/
Request/response validation schemas.

## Files
- users.py   -- Pydantic models for user auth requests/responses
- common.py  -- Marshmallow schemas for expenses, group planner, validation helper
""",
    "app/workers": """# workers/
Background jobs and scheduled tasks.

## Planned
- scheduler.py      -- APScheduler integration
- background_jobs.py -- Cache warming, cleanup tasks
""",
}


def create_llm_files():
    """Create .llm documentation files in each folder."""
    for folder, content in LLM_DOCS.items():
        path = APP if folder == "app" else APP / folder.replace("app/", "")
        write_file(path / ".llm", content)


# ============================================================================
# PHASE 10: Update __init__.py Files
# ============================================================================

def update_init_files():
    """Create/update miscellaneous __init__.py files."""
    # domain/__init__.py
    write_file(APP / "domain" / "__init__.py", '"""Business entities and repository patterns."""\n')

    # domain/trips/__init__.py
    write_file(APP / "domain" / "trips" / "__init__.py", '"""Trip planning models and repositories."""\n')

    # infrastructure/__init__.py
    write_file(APP / "infrastructure" / "__init__.py", '"""External service integrations."""\n')

    # infrastructure/external/__init__.py
    write_file(APP / "infrastructure" / "external" / "__init__.py", '"""Third-party API clients."""\n')

    # workers/__init__.py
    write_file(APP / "workers" / "__init__.py", '"""Background jobs and scheduled tasks."""\n')

    # core/__init__.py
    core_init = '''"""
Core utilities -- config, logging, exceptions, rate limiting, security.
"""

from .config import get_config
from .exceptions import (
    AppError,
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    NotFoundError,
    RateLimitError,
    ValidationError,
)

__all__ = [
    "get_config",
    "AppError",
    "ValidationError",
    "AuthenticationError",
    "AuthorizationError",
    "NotFoundError",
    "ConflictError",
    "RateLimitError",
]
'''
    write_file(APP / "core" / "__init__.py", core_init)


# ============================================================================
# PHASE 11: Create Backend Structure Doc
# ============================================================================

def create_structure_doc():
    """Create BACKEND_STRUCTURE.md documenting the entire architecture."""
    content = '''# TripRaft Backend Architecture

## Overview
Clean, enterprise-grade Flask backend following the structure used by Stripe, Uber, and Airbnb.

## Directory Layout

```
backend/
├── .env                          # Environment variables (secrets, API keys)
├── run.py                        # Main entry point
├── requirements.txt              # Python dependencies
├── Dockerfile                    # Container build
│
├── app/                          # Application root
│   ├── __init__.py               # Re-exports create_app
│   │
│   ├── core/                     # Framework-agnostic core
│   │   ├── config.py             # Settings from .env (Config, DevelopmentConfig, ProductionConfig)
│   │   ├── logging.py            # Structured JSON logging (production) / colored (dev)
│   │   ├── exceptions.py         # AppError -> ValidationError, AuthenticationError, NotFoundError, etc.
│   │   ├── rate_limiter.py       # Flask-Limiter with per-operation limits
│   │   └── security.py           # Security headers, CORS middleware
│   │
│   ├── infrastructure/           # Technical concerns & external integrations
│   │   ├── db/
│   │   │   ├── base.py           # Shared SQLAlchemy declarative Base
│   │   │   ├── connection.py     # ONE engine for tripraft.db (SessionLocal, get_db)
│   │   │   └── travel_db.py      # Read-only sqlite3 for travel_data_complete.db
│   │   ├── cache/
│   │   │   └── redis.py          # RedisClient singleton, JSON helpers, @cache_response
│   │   ├── auth/
│   │   │   ├── jwt.py            # JWT access/refresh token helpers
│   │   │   ├── password.py       # bcrypt hash/verify
│   │   │   └── decorators.py     # @require_auth, @require_refresh_token, @optional_auth
│   │   ├── email/
│   │   │   ├── smtp.py           # SMTP email service
│   │   │   └── config.py         # Email type enable/disable
│   │   └── external/             # Third-party API clients (future)
│   │
│   ├── domain/                   # Business entities (no Flask dependency)
│   │   ├── users/
│   │   │   ├── models.py         # User, UserSession (SQLAlchemy)
│   │   │   └── repository.py     # UserRepository, UserSessionRepository
│   │   ├── expenses/
│   │   │   └── models.py         # Group, GroupMember, Expense, ExpenseSplit,
│   │   │                         # Settlement, GroupBalance, Invitation, ExpenseHistory
│   │   ├── group_planner/
│   │   │   └── models.py         # TravelGroup, TripMember, Place, PlaceVote, Poll,
│   │   │                         # PollVote, TripInvitation, ChecklistItem,
│   │   │                         # ItineraryDocument, GroupActivity
│   │   └── places/
│   │       ├── models.py         # Dataclass models (Country, City, Place, etc.)
│   │       ├── repository.py     # DatabaseConnection for place search
│   │       ├── location_models.py    # PlacesModel, CitiesModel for locations API
│   │       └── location_repository.py # DatabaseManager for location queries
│   │
│   ├── services/                 # Use-case orchestration
│   │   ├── user_service.py       # User register, login, profile, password
│   │   ├── auth_service.py       # Legacy auth (signup/login/refresh/logout)
│   │   ├── expense_group_service.py  # Expense group CRUD
│   │   ├── expense_service.py    # Expense create/edit/delete/split
│   │   ├── settlement_service.py # Settlement recording, balance recalc
│   │   ├── expense_invite_service.py # Expense group invitations
│   │   ├── email_service.py      # Email notification logic
│   │   ├── travel_group_service.py   # Travel group CRUD, membership
│   │   ├── travel_place_service.py   # Place suggestions, voting
│   │   ├── poll_service.py       # Poll creation and voting
│   │   ├── trip_invite_service.py    # Trip invitations
│   │   ├── checklist_service.py  # Pre-trip checklist
│   │   ├── events_service.py     # Ticketmaster event search
│   │   ├── destination_service.py    # Destination autocomplete
│   │   └── place_search_service.py   # Place full-text search
│   │
│   ├── api/                      # Flask REST API layer
│   │   ├── factory.py            # create_app() -- THE app factory
│   │   ├── health.py             # /api/health/* endpoints
│   │   ├── middleware.py         # Request/response logging
│   │   ├── route_viewer.py       # Styled route listing at /api/routes
│   │   ├── utils/
│   │   │   ├── responses.py      # success_response, error_response, paginated_response
│   │   │   ├── validators.py     # validate_pagination, validate_search_query
│   │   │   └── database.py       # DatabaseManager for travel_data_complete.db
│   │   └── v1/                   # Versioned route blueprints
│   │       ├── users.py          # /api/v1/users/*
│   │       ├── auth.py           # /api/expense/*
│   │       ├── expense_groups.py # /api/expense/groups/*
│   │       ├── expenses.py       # /api/expense/expenses/*
│   │       ├── settlements.py    # /api/expense/settlements/*
│   │       ├── expense_invitations.py # /api/expense/invitations/*
│   │       ├── gp_groups.py      # /api/v2/group-planner/* (groups)
│   │       ├── gp_places.py      # /api/v2/group-planner/* (places)
│   │       ├── gp_polls.py       # /api/v2/group-planner/* (polls)
│   │       ├── gp_invitations.py # /api/v2/group-planner/* (invitations)
│   │       ├── gp_checklist.py   # /api/v2/group-planner/* (checklist)
│   │       ├── gp_events.py      # /api/v2/group-planner/* (events)
│   │       ├── gp_destinations.py# /api/v2/group-planner/* (destination search)
│   │       ├── locations.py      # /api/v1/locations/*
│   │       ├── places.py         # /api/v1/place-search/*
│   │       └── trips.py          # /api/trip-planner/*
│   │
│   ├── schemas/                  # Validation
│   │   ├── users.py              # Pydantic user auth schemas
│   │   └── common.py             # Marshmallow expense/GP validation schemas
│   │
│   └── workers/                  # Background jobs (future)
│
├── database/                     # SQLite database files
│   ├── tripraft.db               # Main app DB (users, expenses, groups)
│   └── travel_data_complete.db   # Read-only geographic data
│
├── tests/                        # Test suite
├── scripts/                      # Utility scripts
└── unwanted/                     # Archived old code (pre-migration)
```

## Database Architecture

### tripraft.db (SQLAlchemy ORM)
Single unified database for all transactional data:

| Domain | Tables |
|--------|--------|
| Users | `users`, `user_sessions` |
| Expenses | `groups`, `group_members`, `expenses`, `expense_splits`, `settlements`, `group_balances`, `invitations`, `expense_history` |
| Group Planner | `travel_groups`, `gp_group_members`, `gp_places`, `gp_place_votes`, `gp_polls`, `gp_poll_votes`, `gp_invitations`, `gp_checklist_items`, `gp_itinerary_documents`, `gp_group_activities` |

### travel_data_complete.db (Read-only, raw sqlite3)
Geographic reference data:
- `countries`, `states`, `cities`, `places`, `photos`, `tags`, `opening_hours`, `place_tags`

## API Endpoints

| Prefix | Module | Description |
|--------|--------|-------------|
| `/api/expense/*` | Expense Engine | Auth, groups, expenses, settlements, invitations |
| `/api/v2/group-planner/*` | Group Planner | Travel groups, places, polls, checklist, events |
| `/api/v1/locations/*` | Locations | Countries, states, cities, places hierarchy |
| `/api/v1/place-search/*` | Place Search | Autocomplete, full-text search |
| `/api/trip-planner/*` | Trip Planner | Trip planning and itinerary |
| `/api/v1/users/*` | Users | Clean auth (register, login, profile) |
| `/api/health/*` | Health | System health checks |

## Key Principles
- **Single Base**: All SQLAlchemy models share one `Base` from `infrastructure/db/base.py`
- **Single Engine**: One `engine` in `infrastructure/db/connection.py` for `tripraft.db`
- **Single Auth**: All routes use decorators from `infrastructure/auth/decorators.py`
- **No print()**: All output goes through `logging` module
- **No hardcoded values**: Everything from `.env` via `core/config.py`
'''
    write_file(BACKEND / "BACKEND_STRUCTURE.md", content)


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 60)
    print("TripRaft Backend Migration")
    print("=" * 60)

    print("\n[Phase 1] Creating domain model files...")
    create_expense_models()
    create_group_planner_models()
    create_places_domain()

    print("\n[Phase 2] Creating schema files...")
    create_schema_files()

    print("\n[Phase 3] Migrating service files...")
    migrate_services()

    print("\n[Phase 4] Migrating route files...")
    migrate_routes()

    print("\n[Phase 5] Migrating supporting files...")
    migrate_supporting()

    print("\n[Phase 6] Creating application factory...")
    create_factory()

    print("\n[Phase 7] Creating run.py...")
    create_run_py()

    print("\n[Phase 8] Updating __init__.py files...")
    update_init_files()

    print("\n[Phase 9] Creating .llm documentation files...")
    create_llm_files()

    print("\n[Phase 10] Creating BACKEND_STRUCTURE.md...")
    create_structure_doc()

    print("\n[Phase 11] Moving old files to unwanted/...")
    move_old_files()

    print("\n" + "=" * 60)
    print("Migration complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Run: python run.py")
    print("2. Check: http://localhost:5000/health")
    print("3. Verify all endpoints work")


if __name__ == "__main__":
    main()
