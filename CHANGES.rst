=========
Changelog
=========

All notable changes to this project will be documented in this file.

The format is based on `Keep a Changelog <https://keepachangelog.com/en/1.0.0/>`_,
and this project adheres to `Semantic Versioning <https://semver.org/spec/v2.0.0.html>`_.

---

Version 2.0.0
========================

Security / Breaking Changes
----------------------------

*   **`SECRET_KEY` no longer has a hardcoded default**:
    `Settings.SECRET_KEY` previously defaulted to a fixed value hardcoded in this package's own published source. Left unoverridden, that's not a weak secret, it's a *known* one -- anyone reading jetio's source could sign a fully valid JWT for any user, including an admin, with zero credentials. Verified exploitable end-to-end against a real app before this fix.

    `SECRET_KEY` is now `Optional[str] = None` at the `Settings` level rather than a required field, since `jetio.config` is imported unconditionally by the whole package -- making it required broke even the bare `Jetio()` quickstart, which never touches auth. Enforcement moved to where the actual risk lives: `create_access_token()`/`decode_access_token()` (`jetio/auth.py`) now raise a clear `RuntimeError` the first time either is called without a real secret configured.

    **Breaking**: any app that never explicitly set `SECRET_KEY` and uses JWT auth (directly, or via `jetio-auth`) will start raising `RuntimeError` on login/token calls after upgrading, instead of silently working with the old public default. Set a real `SECRET_KEY` environment variable (e.g. `openssl rand -hex 32`) before upgrading if your app uses JWT auth. Apps that don't use JWT auth at all are unaffected.

---

Version 1.2.3
========================

Bug Fixes
---------

*   **`HTTPException` headers are no longer dropped**:
    Raising `starlette.exceptions.HTTPException(status_code, detail, headers={...})` previously lost the `headers` on the way to the response -- only `.detail`/`.status_code` were used. Any code relying on custom headers on an error response (e.g. `Retry-After` on a 429 from a rate limiter) now gets them.

*   **`Request.client` is now public**:
    `Request` previously exposed no supported way to read the connecting client's address. `Request.client` is now a documented public attribute -- a `(host, port)` tuple, or `None` if the ASGI server didn't provide one.

*   **`run()` no longer crashes on terminals that can't encode its startup message**:
    The default Windows console (which decodes stdout as `cp1252` unless `PYTHONIOENCODING=utf-8` is set) previously crashed with `UnicodeEncodeError` on the emoji in the startup banner, before the server ever started listening. It now falls back to a plain-text message.

*   **`class API` configuration is now found on parent classes, not just the model itself**:
    `class API: exclude_from_read = [...]` defined on a mixin (rather than the model class directly) was previously silently ignored, since the lookup only checked the model's own class body. This is security-relevant: it's the mechanism `jetio-auth`'s `JetioAuthMixin` uses to keep `hashed_password` out of API responses, and it wasn't working for that exact case. The lookup now walks the MRO, so a mixin-defined `API` is respected -- while a model's own `class API` still takes priority if both are present.

---

Version 1.1.0
========================

Improvements
------------

*   **Improved Default Hashing and Installation**:
    The default password hashing scheme is now `pbkdf2_sha256`. This provides excellent security out-of-the-box while being pure Python, which resolves common installation issues on systems without a C compiler (like Windows).

*   **Backward Compatibility for `bcrypt`**:
    The framework now seamlessly verifies both new `pbkdf2_sha256` hashes and existing `bcrypt` hashes, ensuring a smooth upgrade path for existing applications. No code changes are needed for existing projects to upgrade.

*   **Optional `bcrypt` Support**:
    For users who prefer `bcrypt` and have the necessary build tools, it can be installed as an optional extra. To use `bcrypt` for hashing new passwords, install Jetio with the `[bcrypt]` extra and configure the `CryptContext` in your application:

    .. code-block:: bash

        pip install "jetio[bcrypt]"

    .. code-block:: python

        # In your application's auth configuration
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt", "pbkdf2_sha256"], deprecated="auto")

---

Version 1.0.6
=============

*   Initial public release of the Jetio framework.
*   Features include automatic CRUD generation from SQLAlchemy models, decorator-based routing, and built-in Swagger UI.
