from sqlalchemy.orm import Mapped

from jetio import JetioModel


def test_api_exclude_from_read_is_found_via_mro_not_just_own_class():
    """A `class API: exclude_from_read = [...]` defined on a mixin, not on
    the model class itself, should still be honored -- this is exactly how
    jetio-auth's JetioAuthMixin is meant to hide `hashed_password` from
    read responses. Previously, ModelMetaclass looked up `API` via
    `attrs.get('API')`, which only checks the class being defined's own
    namespace, silently ignoring one defined on a base/mixin."""

    class SecretMixin:
        class API:
            exclude_from_read = ["secret"]

    class SecretWidget(SecretMixin, JetioModel):
        name: Mapped[str]
        secret: Mapped[str]

    read_fields = SecretWidget.__pydantic_read_model__.model_fields
    assert "name" in read_fields
    assert "secret" not in read_fields, "mixin-defined API.exclude_from_read was ignored"


def test_api_config_on_the_model_itself_still_wins_over_a_mixins():
    """If both a mixin and the model itself define `class API`, the more
    specific one (the model's own) should be used -- normal Python
    attribute-resolution semantics, most-derived class wins."""

    class MixinWithExclude:
        class API:
            exclude_from_read = ["from_mixin"]

    class PriorityWidget(MixinWithExclude, JetioModel):
        class API:
            exclude_from_read = ["from_model"]

        from_mixin: Mapped[str]
        from_model: Mapped[str]

    read_fields = PriorityWidget.__pydantic_read_model__.model_fields
    assert "from_mixin" in read_fields, "model's own API should override the mixin's, not merge"
    assert "from_model" not in read_fields
