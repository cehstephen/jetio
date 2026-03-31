import pytest

from jetio.security import (
    DEFAULT_AUDIT_FIELDS,
    normalize_methods,
    require_audit_field,
    resolve_audit_field,
)


class ModelWithOwner:
    owner_id = 1


class ModelWithoutOwner:
    pass


def test_normalize_methods_all_supported_input_shapes():
    assert normalize_methods(None) == []
    assert normalize_methods("get") == ["GET"]
    assert normalize_methods(["get", "POST"]) == ["GET", "POST"]
    assert normalize_methods(("put", "delete")) == ["PUT", "DELETE"]
    assert set(normalize_methods({"patch", "head"})) == {"PATCH", "HEAD"}
    assert normalize_methods(123) == ["123"]


def test_resolve_audit_field_uses_defaults_and_custom_priority():
    assert resolve_audit_field(ModelWithOwner) == "owner_id"
    assert resolve_audit_field(ModelWithOwner, ["creator_id", "owner_id"]) == "owner_id"
    assert resolve_audit_field(ModelWithoutOwner) is None


def test_require_audit_field_success_and_failure_message():
    assert require_audit_field(ModelWithOwner, ["owner_id"]) == "owner_id"

    with pytest.raises(RuntimeError) as exc:
        require_audit_field(ModelWithoutOwner)

    message = str(exc.value)
    assert "No audit/ownership field found" in message
    assert ", ".join(DEFAULT_AUDIT_FIELDS[:3]) in message
