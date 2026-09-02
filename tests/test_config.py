"""SECRET_KEY has no hardcoded default -- a fixed value shipped in this
package's own published source would be public, not secret, letting
anyone forge a valid JWT for any user. See GH issue #9.

It's Optional at the Settings level (not a required field) rather than
enforced at import time, since jetio.config is imported unconditionally
by the whole package -- most of the framework (CRUD-only apps, anything
not using JWT auth) never needs it set at all. The enforcement itself is
in jetio.auth's create_access_token()/decode_access_token(), tested in
test_auth.py.
"""

from jetio.config import Settings


def test_settings_has_no_secret_key_by_default(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    settings = Settings(_env_file=None)
    assert settings.SECRET_KEY is None


def test_settings_accepts_an_explicit_secret_key(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "a-real-secret-for-this-test-only")
    settings = Settings(_env_file=None)
    assert settings.SECRET_KEY == "a-real-secret-for-this-test-only"
