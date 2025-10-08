# PROJECT_PLAN.md: Astraea Secure E2EE Messaging System

## 1. Introduction

This document outlines the architectural and cryptographic design for Astraea, a secure end-to-end encrypted (E2EE) messaging system. The primary design goal is "zero-knowledge," meaning the server infrastructure has no knowledge of the content of the messages being transmitted or stored.

## 2. Architecture

The system will be composed of three core, containerized services, following a classic service-oriented architecture.

*   **NGINX Proxy (`proxy`)**: This is the public-facing entry point to the system. Its responsibilities include:
    *   **TLS Termination**: Decrypting incoming HTTPS traffic. For development, this will use self-signed certificates.
    *   **Reverse Proxy**: Forwarding legitimate API requests to the FastAPI backend.
    *   **Security Hardening**: Implementing critical security headers (CSP, HSTS, X-Content-Type-Options), rate limiting to prevent abuse and brute-force attacks, and logging access patterns.
    *   **Load Balancing**: While not required for a single-node setup, this architecture allows for future load balancing across multiple backend instances.

*   **FastAPI Backend (`api`)**: The core application logic resides here. It is a stateless Python application. Its responsibilities include:
    *   **API Endpoints**: Providing a secure RESTful API for all client-server interactions.
    *   **User Management**: Handling user registration, authentication (including 2FA), and profile management.
    *   **Data Brokerage**: Interacting with the database to store and retrieve user data, public keys, and encrypted message blobs. It **never** has access to plaintext message content or users' private keys.
    *   **Authorization**: Enforcing access control rules, ensuring that only authenticated and authorized users can access specific resources.

*   **PostgreSQL Database (`db`)**: The persistent data store for the application.
    *   **Data Storage**: It will store user account information, user public keys, encrypted message payloads, and associated metadata.
    *   **Data Integrity**: Utilizes relational constraints (foreign keys, unique constraints) to maintain the integrity of the data.
    *   **Persistence**: Data will be stored in a Docker volume to ensure it persists across container restarts.

## 3. Database Schema

The schema is designed to separate user information from encrypted message content and to handle multi-recipient messages efficiently.

**Table: `users`**
Stores core user account information.

| Column            | Type           | Constraints                               | Description                                      |
| ----------------- | -------------- | ----------------------------------------- | ------------------------------------------------ |
| `id`              | UUID           | PRIMARY KEY, DEFAULT gen_random_uuid()    | Unique identifier for the user.                  |
| `username`        | VARCHAR(255)   | UNIQUE, NOT NULL                          | User's chosen username.                          |
| `hashed_password` | VARCHAR(255)   | NOT NULL                                  | Bcrypt hash of the user's password.              |
| `two_fa_secret`   | VARCHAR(255)   | NULL                                      | Encrypted TOTP secret for 2FA.                   |
| `created_at`      | TIMESTAMPTZ    | NOT NULL, DEFAULT now()                   | Timestamp of account creation.                   |
| `updated_at`      | TIMESTAMPTZ    | NOT NULL, DEFAULT now()                   | Timestamp of the last account update.            |

---

**Table: `user_keys`**
Stores user cryptographic keys. The server can never access the decrypted private key.

| Column                  | Type        | Constraints                             | Description                                                                 |
| ----------------------- | ----------- | --------------------------------------- | --------------------------------------------------------------------------- |
| `id`                    | BIGSERIAL   | PRIMARY KEY                             | Unique identifier for the key pair.                                         |
| `user_id`               | UUID        | FOREIGN KEY (users.id), NOT NULL        | The user who owns this key pair.                                            |
| `public_key`            | TEXT        | NOT NULL                                | The user's public key (e.g., RSA-4096), stored in PEM format.               |
| `encrypted_private_key` | TEXT        | NOT NULL                                | The user's private key, encrypted with their password-derived master key.   |
| `key_fingerprint`       | VARCHAR(64) | UNIQUE, NOT NULL                        | A unique hash (e.g., SHA-256) of the public key for easy identification.    |
| `is_active`             | BOOLEAN     | NOT NULL, DEFAULT true                  | Allows for key rotation. Only one key can be active at a time per user.     |
| `created_at`            | TIMESTAMPTZ | NOT NULL, DEFAULT now()                 | Timestamp of key pair creation.                                             |

---

**Table: `messages`**
A central table to represent a single message event.

| Column       | Type        | Constraints                               | Description                               |
| ------------ | ----------- | ----------------------------------------- | ----------------------------------------- |
| `id`         | UUID        | PRIMARY KEY, DEFAULT gen_random_uuid()    | Unique identifier for the message.        |
| `sender_id`  | UUID        | FOREIGN KEY (users.id), NOT NULL        | The user who sent the message.            |
| `signature`  | TEXT        | NOT NULL                                  | Digital signature of the `encrypted_payload`. |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT now()                   | Timestamp of when the message was sent.   |

---

**Table: `message_content`**
Stores the actual encrypted payload, decoupled from metadata.

| Column            | Type | Constraints                             | Description                                                                   |
| ----------------- | ---- | --------------------------------------- | ----------------------------------------------------------------------------- |
| `message_id`      | UUID | PRIMARY KEY, FOREIGN KEY (messages.id)  | Links to the message metadata.                                                |
| `encrypted_payload` | TEXT | NOT NULL                                | The full message body and attachments, encrypted with a symmetric session key. |

---

**Table: `message_recipients`**
A join table mapping messages to their recipients and storing the per-recipient encrypted session key.

| Column                  | Type        | Constraints                             | Description                                                                     |
| ----------------------- | ----------- | --------------------------------------- | ------------------------------------------------------------------------------- |
| `id`                    | BIGSERIAL   | PRIMARY KEY                             | Unique identifier for this recipient entry.                                     |
| `message_id`            | UUID        | FOREIGN KEY (messages.id), NOT NULL     | The message being sent.                                                         |
| `recipient_id`          | UUID        | FOREIGN KEY (users.id), NOT NULL        | The user receiving the message.                                                 |
| `encrypted_session_key` | TEXT        | NOT NULL                                | The message session key, asymmetrically encrypted with the recipient's public key. |
| `read_status`           | BOOLEAN     | NOT NULL, DEFAULT false                 | `true` if the recipient has marked the message as read.                         |

## 4. Cryptographic Design

Security is based on a hybrid encryption model (a combination of symmetric and asymmetric cryptography), ensuring E2EE and message authenticity.

*   **Key Derivation (User Master Key)**:
    *   A user's password will **never** be stored directly.
    *   At the client, the user's password and a salt (derived from their username or a server-provided salt) will be fed into a strong Key Derivation Function (KDF), **PBKDF2-HMAC-SHA256**, with a high iteration count.
    *   This produces a strong symmetric key (`master_key`), which is used exclusively to encrypt and decrypt the user's private key on the client-side.

*   **End-to-End Encryption (E2EE) Flow**:
    1.  **Message Composition (Client-Side)**: A user composes a message, possibly with attachments. The message and attachment data are serialized into a single plaintext payload.
    2.  **Symmetric Encryption**: The client generates a cryptographically secure, random, single-use **AES-256-GCM session key**. The plaintext payload is encrypted with this key to produce `encrypted_payload`. GCM mode is chosen because it provides both confidentiality and integrity (authentication).
    3.  **Asymmetric Encryption (Key Exchange)**: For each recipient, the client:
        a. Fetches the recipient's `public_key` from the server.
        b. Encrypts the AES `session_key` using the recipient's `public_key` with **RSA-OAEP** (using SHA-256). This results in a unique `encrypted_session_key` for each recipient.
    4.  **Transmission**: The client sends the single `encrypted_payload`, its signature (see below), and the list of `(recipient_id, encrypted_session_key)` tuples to the server.
    5.  **Decryption (Client-Side)**: A recipient's client fetches the message. It uses its `private_key` (after decrypting it with its `master_key`) to decrypt its specific `encrypted_session_key`, revealing the AES `session_key`. It then uses this key to decrypt the `encrypted_payload` with AES-256-GCM.

*   **Authenticity and Integrity**:
    *   To prove a message was sent by the claimed sender and was not tampered with, the sender's client will sign the `encrypted_payload` (the ciphertext) using its `private_key`.
    *   The signature algorithm will be **RSA-PSS** with SHA-256. PSS is chosen for its provable security properties.
    *   The recipient's client will verify this `signature` against the `encrypted_payload` using the sender's public key after receiving the message.

## 5. Authentication Flow

Authentication is based on JSON Web Tokens (JWT) and supports Time-based One-Time Passwords (TOTP) for two-factor authentication (2FA).

*   **Initial Login**:
    1.  User submits `username` and `password`.
    2.  Server validates credentials using `bcrypt`. Generic error messages are used to prevent user enumeration. The process is designed to be timing-attack resistant.
    3.  If the password is valid and 2FA is enabled, the server responds with a `2FA_required` status.
    4.  User submits their 6-digit TOTP code.
    5.  Server verifies the TOTP code.

*   **JWT Issuance**:
    *   Upon successful authentication (password + optional 2FA), the server generates two tokens:
        *   **Access Token**: A short-lived (e.g., 15 minutes) JWT signed with a strong secret key (HS256). It contains claims like `sub` (user_id), `exp` (expiration), and `iat` (issued at). This token is sent to the client and included in the `Authorization: Bearer` header of subsequent API requests.
        *   **Refresh Token**: A long-lived (e.g., 7 days) opaque token. It is stored in a secure, `HttpOnly` cookie to prevent XSS attacks from accessing it. It is associated with the user account in the database and can be revoked.

*   **Session Management**:
    *   When the Access Token expires, the client can use the Refresh Token at a `/auth/refresh` endpoint to obtain a new Access Token without requiring the user to log in again.
    *   Logging out will invalidate the Refresh Token on the server-side.

*   **Two-Factor Authentication (2FA)**:
    *   **Setup**: Users can enable 2FA in their settings. The server generates a TOTP secret using `pyotp`, stores it encrypted in the `users` table, and presents it to the user as a QR code.
    *   **Verification**: At login, the server validates the user-provided TOTP code against the stored secret.