# Bibliography and Resources

This document lists the key libraries, standards, and resources that were instrumental in the design and implementation of the Astraea Secure E2EE Messaging System.

## Core Technology Stack

-   **FastAPI**: A modern, high-performance web framework for building APIs with Python 3.8+ based on standard Python type hints.
    -   *Website*: [https://fastapi.tiangolo.com/](https://fastapi.tiangolo.com/)

-   **PostgreSQL**: A powerful, open-source object-relational database system with over 30 years of active development that has earned it a strong reputation for reliability, feature robustness, and performance.
    -   *Website*: [https://www.postgresql.org/](https://www.postgresql.org/)

-   **NGINX**: An open-source web server that can also be used as a reverse proxy, load balancer, mail proxy, and HTTP cache.
    -   *Website*: [https://www.nginx.com/](https://www.nginx.com/)

-   **Docker & Docker Compose**: A platform for developing, shipping, and running applications in containers, providing OS-level virtualization.
    -   *Website*: [https://www.docker.com/](https://www.docker.com/)

## Python Libraries

-   **Pydantic**: Data validation and settings management using Python type annotations. Essential for enforcing strict, type-safe data models at the API boundary.
    -   *Repository*: [https://github.com/pydantic/pydantic](https://github.com/pydantic/pydantic)

-   **SQLAlchemy**: The Python SQL Toolkit and Object Relational Mapper that gives application developers the full power and flexibility of SQL.
    -   *Website*: [https://www.sqlalchemy.org/](https://www.sqlalchemy.org/)

-   **Passlib**: A comprehensive password hashing library for Python that provides a wide range of secure hashing algorithms. We used the `bcrypt` scheme.
    -   *Website*: [https://passlib.readthedocs.io/](https://passlib.readthedocs.io/)

-   **python-jose**: A JavaScript Object Signing and Encryption (JOSE) implementation in Python, used for handling JSON Web Tokens (JWT).
    -   *Repository*: [https://github.com/mpdavis/python-jose](https://github.com/mpdavis/python-jose)

-   **pyotp**: A Python library for generating and verifying one-time passwords (HOTP/TOTP). Used for our Two-Factor Authentication implementation.
    -   *Repository*: [https://github.com/pyauth/pyotp](https://github.com/pyauth/pyotp)

-   **cryptography**: A package which provides cryptographic recipes and primitives to Python developers. Used for core cryptographic operations.
    -   *Website*: [https://cryptography.io/](https://cryptography.io/)

## Standards and Specifications (RFCs)

-   **RFC 7519: JSON Web Token (JWT)**: The standard that defines a compact and self-contained way for securely transmitting information between parties as a JSON object.
    -   *Link*: [https://tools.ietf.org/html/rfc7519](https://tools.ietf.org/html/rfc7519)

-   **RFC 4880: OpenPGP Message Format**: While not directly implemented, the hybrid encryption model (symmetric encryption of content with a key that is then asymmetrically encrypted) is a core concept of OpenPGP.
    -   *Link*: [https://tools.ietf.org/html/rfc4880](https://tools.ietf.org/html/rfc4880)

-   **RFC 6238: TOTP: Time-Based One-Time Password Algorithm**: The standard that defines the TOTP algorithm, a cornerstone of our 2FA implementation.
    -   *Link*: [https://tools.ietf.org/html/rfc6238](https://tools.ietf.org/html/rfc6238)

-   **NIST FIPS 197: Advanced Encryption Standard (AES)**: The specification for the AES algorithm, used for symmetric encryption of message payloads.
    -   *Link*: [https://csrc.nist.gov/publications/detail/fips/197/final](https://csrc.nist.gov/publications/detail/fips/197/final)

-   **PKCS #1 v2.2: RSA Cryptography Standard**: Defines the recommended practices for implementing RSA-based public-key cryptography, including the OAEP and PSS padding schemes.
    -   *Link*: [https://www.rfc-editor.org/rfc/rfc8017](https://www.rfc-editor.org/rfc/rfc8017)

## Security Resources

-   **OWASP Top 10**: The Open Web Application Security Project's list of the 10 most critical web application security risks. A guiding resource for security-conscious development.
    -   *Website*: [https://owasp.org/www-project-top-ten/](https://owasp.org/www-project-top-ten/)

-   **MDN Web Docs - Security**: An excellent resource for understanding and correctly implementing web security headers like `Strict-Transport-Security` and `Content-Security-Policy`.
    -   *Link*: [https://developer.mozilla.org/en-US/docs/Web/Security](https://developer.mozilla.org/en-US/docs/Web/Security)