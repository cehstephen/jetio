# ---------------------------------------------------------------------------
# Jetio Framework
# Website: https://jetio.org
#
# Copyright (c) 2025 Stephen Burabari Tete. All Rights Reserved.
#
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#
# Author:   Stephen Burabari Tete
# Contact:  cehtete [at] gmail.com
# LinkedIn: https://www.linkedin.com/in/tete-stephen/
# ---------------------------------------------------------------------------

"""
Security utilities for the Jetio framework.

This module centralizes ownership/audit-field discovery logic so that:
- CrudRouter can auto-populate ownership fields consistently on CREATE.
- Authorization dependencies (e.g. owner_or_admin) can identify the same
  ownership fields consistently on UPDATE/DELETE.

The intent is to keep ownership behavior predictable and to prevent
security regressions when models use different conventional field names.
"""

from typing import List, Optional, Type, Any


# NOTE:
# Order matters. The first field found on a model is treated as the
# authoritative "ownership" field for auto-assignment and owner checks.
DEFAULT_AUDIT_FIELDS: List[str] = [
    # Standard Ownership
    "creator_id", "author_id", "owner_id", "user_id",
    # Business / Commerce
    "customer_id", "client_id", "merchant_id", "seller_id",
    # Multi-tenancy & SaaS
    "tenant_id", "account_id", "organization_id", "company_id",
    # Workflow / Governance
    "requester_id", "approver_id", "sender_id", "uploader_id",
    # Miscellaneous
    "assigned_by_id",
]


def normalize_methods(methods: Any) -> List[str]:
    """
    Normalizes HTTP method inputs into a clean list of uppercase strings.

    Accepts:
        - None
        - a string ("get", "POST")
        - a list/tuple/set of strings

    Returns:
        List[str]: uppercase methods (e.g. ["GET", "POST"])
    """
    if methods is None:
        return []
    if isinstance(methods, str):
        return [methods.upper()]
    if isinstance(methods, (list, tuple, set)):
        return [str(m).upper() for m in methods]
    return [str(methods).upper()]


def resolve_audit_field(model: Type[Any], audit_fields: Optional[List[str]] = None) -> Optional[str]:
    """
    Resolves the authoritative audit/ownership field for a given model.

    The first field in `audit_fields` that exists as an attribute on the model
    is returned. This mirrors how CrudRouter auto-assigns ownership and how
    authorization checks should determine ownership.

    Args:
        model: A Jetio/SQLAlchemy model class.
        audit_fields: Optional prioritized list of candidate field names.
                      If None, DEFAULT_AUDIT_FIELDS is used.

    Returns:
        Optional[str]: The resolved field name (e.g. "author_id"), or None if no match.
    """
    fields = audit_fields if audit_fields is not None else DEFAULT_AUDIT_FIELDS

    for field in fields:
        # For SQLAlchemy declarative models, mapped columns appear as class attributes.
        if hasattr(model, field):
            return field

    return None


def require_audit_field(model: Type[Any], audit_fields: Optional[List[str]] = None) -> str:
    """
    Like resolve_audit_field(), but raises a clear error if no ownership field is found.
    Useful for fail-closed security behavior.

    Args:
        model: A model class.
        audit_fields: Optional prioritized list of candidate fields.

    Returns:
        str: The resolved field name.

    Raises:
        RuntimeError: If no candidate field exists on the model.
    """
    field = resolve_audit_field(model, audit_fields=audit_fields)
    if not field:
        fields = audit_fields if audit_fields is not None else DEFAULT_AUDIT_FIELDS
        raise RuntimeError(
            "No audit/ownership field found on model %s. Expected one of: %s"
            % (getattr(model, "__name__", str(model)), ", ".join(fields))
        )
    return field
