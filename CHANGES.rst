=========
Changelog
=========

All notable changes to this project will be documented in this file.

The format is based on `Keep a Changelog <https://keepachangelog.com/en/1.0.0/>`_,
and this project adheres to `Semantic Versioning <https://semver.org/spec/v2.0.0.html>`_.

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
