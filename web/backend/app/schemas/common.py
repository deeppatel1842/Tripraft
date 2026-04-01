"""
Input Validation Schemas — backward-compatibility re-exports.

All schemas have been split into per-domain modules.  This file re-exports
them so that existing ``from app.schemas.common import …`` statements
continue to work without modification.
"""
from marshmallow import ValidationError

# ---------------------------------------------------------------------------
# Re-exports from per-domain modules
# ---------------------------------------------------------------------------
from .auth import (ChangePasswordSchema, CheckEmailSchema, LoginSchema,
                   SignupSchema, UpdateProfileSchema)
from .expense_groups import (CreateExpenseGroupSchema, JoinGroupSchema,
                             UpdateExpenseGroupSchema)
from .expenses import CreateExpenseSchema, UpdateExpenseSchema
from .gp_checklist import (AssignChecklistItemSchema,
                           CreateChecklistItemSchema,
                           UpdateChecklistItemSchema)
from .gp_places import (AddPlaceSchema, GeocodeSchema,
                        UpdatePlaceRemarksSchema, UpdatePlaceSchema)
from .gp_polls import CreatePollSchema, VotePollSchema
from .group_planner import (CreateTravelGroupSchema, UpdateBudgetSchema,
                            UpdateItineraryDocumentSchema,
                            UpdateTravelGroupSchema)
from .invitations import (CreateExpenseInvitationSchema,
                          CreateGPInvitationSchema, InviteMemberSchema)
from .settlements import CreateSettlementSchema
from .trips import TripGenerateSchema

# ---------------------------------------------------------------------------
# HELPER: Validate request data (kept for routes still using inline pattern)
# ---------------------------------------------------------------------------

def validate_request(schema_class, data):
    """
    Validate request data against a marshmallow schema.

    Args:
        schema_class: A marshmallow Schema class (not an instance).
        data: The raw dict to validate.

    Returns:
        (validated_data, None) on success.
        (None, error_dict) on failure.
    """
    schema = schema_class()
    try:
        result = schema.load(data)
        return result, None
    except ValidationError as err:
        return None, err.messages
