# Astraea: Secure E2EE Messaging System

Astraea is a secure, containerized web application for exchanging end-to-end encrypted (E2EE) messages. The architecture is inspired by zero-knowledge systems like ProtonMail, where the server has no ability to decrypt the content of user messages.

This document serves as a comprehensive guide for developers, providing a deep dive into the system's architecture, security model, API, and setup procedures.

## Key Features

-   **End-to-End Encryption (E2EE)**: Uses a hybrid encryption model (AES-256-GCM for message content + RSA-4096 for session key exchange) to ensure only the sender and intended recipients can read messages.
-   **Zero-Knowledge Architecture**: The server only stores encrypted data blobs and has no access to user private keys or unencrypted message content.
-   **Strong Authentication**: Secure password hashing with Bcrypt, JWT-based session management, and optional Two-Factor Authentication (2FA) using TOTP.
-   **Robust Security Practices**: Implements critical HTTP security headers (HSTS, CSP), rate limiting at the proxy layer, non-root containers, and strict input validation.
-   **Containerized with Docker**: The entire application stack (FastAPI Backend, PostgreSQL DB, NGINX Proxy) is orchestrated with Docker Compose for easy, reproducible deployments.
-   **Modern Python Backend**: Built with FastAPI, Pydantic, and SQLAlchemy for a high-performance, type-safe, and maintainable codebase.

## Architecture

The system consists of three main services orchestrated by Docker Compose:

1.  **`proxy` (NGINX)**: The public-facing gateway. It terminates TLS (HTTPS), serves security headers, rate-limits sensitive endpoints, and reverse-proxies requests to the backend API.
2.  **`api` (FastAPI)**: The core application backend. It handles user authentication, authorization, and the storage/retrieval of encrypted message data and user public keys.
3.  **`db` (PostgreSQL)**: A robust relational database for persistently storing user accounts, public keys, and encrypted message payloads.

## Getting Started

### Prerequisites

-   **Docker**: [Get Docker](https://docs.docker.com/get-docker/)
-   **Docker Compose**: [Install Docker Compose](https://docs.docker.com/compose/install/)

### 1. Clone the Repository

```sh
git clone <repository_url>
cd astraea
```

### 2. Configure Environment Variables

The application uses environment variables for configuration. Create a `.env` file by copying the example template:

```sh
cp .env.example .env
```

Review the `.env` file. For local development with Docker Compose, the default values should work correctly. You **must** provide a strong, unique `SECRET_KEY` for signing JWTs. You can generate one with the following command:

```sh
openssl rand -hex 32
```
Update the `SECRET_KEY` in your `.env` file with the generated value.

### 3. Build and Run the Application

The entire application stack can be built and started with a single command from the project root directory:

```sh
docker-compose up --build
```

### 4. Accessing the API

Once all services are running, the API will be accessible at **`https://localhost`**.

The interactive API documentation (powered by Swagger UI) is available at **`https://localhost/docs`**.

**Note on Self-Signed Certificate:** Your browser will display a security warning because the SSL certificate is self-signed. This is expected and safe for local development. You can proceed past the warning to access the API docs.

## Security Model

The security of Astraea is founded on the principle of **zero-knowledge**. The server is designed to be an untrusted party that cannot access user data.

### Client-Side Cryptographic Responsibilities

A compliant client **must** perform the following cryptographic operations:

1.  **Key Generation**:
    - Upon registration, the client generates a master **RSA-4096** key pair.
    - The **public key** is uploaded to the server.
    - The **private key** must be encrypted with a key derived from the user's password (e.g., using PBKDF2). The resulting encrypted private key blob should be stored by the client or can be uploaded to the server for convenience (as `encrypted_private_key`).
    - **The unencrypted private key must never be transmitted to the server.**

2.  **Sending a Message**:
    - Generate a random, single-use **AES-256** session key.
    - Encrypt the message content (plaintext) using the AES key with GCM mode to get the `encrypted_payload`.
    - Create a digital signature of the `encrypted_payload` using the sender's private RSA key.
    - For each recipient:
        - Fetch the recipient's public RSA key from the server.
        - Encrypt the AES session key with the recipient's public key.
    - Send the `encrypted_payload`, `signature`, and a dictionary mapping each recipient's username to their `encrypted_session_key` to the `/messages/send` endpoint.

3.  **Receiving a Message**:
    - Fetch the full message data from the `GET /messages/{message_id}` endpoint.
    - Decrypt the `encrypted_session_key` using the recipient's private RSA key (this requires the user's password to decrypt the private key first). This yields the original AES session key.
    - Decrypt the `encrypted_payload` using the recovered AES session key.
    - Verify the `signature` against the `encrypted_payload` using the sender's public key.

## Database Schema

The database consists of five main tables:

-   **`users`**: Stores user account information.
    - `id` (UUID, PK): Unique user identifier.
    - `username` (String): Unique, indexed username.
    - `hashed_password` (String): Bcrypt-hashed password.
    - `two_fa_secret` (String, nullable): Encrypted TOTP secret for 2FA.
-   **`user_keys`**: Stores user cryptographic keys.
    - `id` (UUID, PK): Unique key identifier.
    - `user_id` (UUID, FK -> users.id): The user who owns the key.
    - `public_key` (Text): The user's public RSA key in PEM format.
    - `encrypted_private_key` (Text): The user's private key, encrypted client-side.
    - `key_fingerprint` (String): A unique hash of the public key for easy lookup.
-   **`messages`**: Acts as a container for a message, linking the sender and metadata.
    - `id` (UUID, PK): Unique message identifier.
    - `sender_id` (UUID, FK -> users.id): The user who sent the message.
    - `signature` (Text): The sender's digital signature of the message payload.
-   **`message_content`**: Stores the actual encrypted message payload.
    - `message_id` (UUID, PK, FK -> messages.id): Links to the parent message.
    - `encrypted_payload` (Text): The message content, encrypted with a session key.
-   **`message_recipients`**: Links messages to their recipients and stores the key needed to decrypt them.
    - `id` (UUID, PK): Unique identifier for this recipient entry.
    - `message_id` (UUID, FK -> messages.id): The message being received.
    - `recipient_id` (UUID, FK -> users.id): The user receiving the message.
    - `encrypted_session_key` (Text): The session key, encrypted with this recipient's public key.
    - `read_status` (Boolean): `true` if the user has marked the message as read.

## API Reference

The base URL for the API is `https://localhost`. All endpoints requiring authentication must include a JWT in the `Authorization` header as a Bearer token.

### Authentication (`/auth`)

#### `POST /auth/register`
(Public) Creates a new user account.

-   **Request Body** (`application/json`):
    ```json
    {
      "username": "newuser",
      "password": "a_very_strong_password_123"
    }
    ```
-   **Success Response** (`201 Created`):
    ```json
    {
      "username": "newuser",
      "id": "a-uuid-string",
      "created_at": "timestamp"
    }
    ```
-   **Error Responses**:
    - `400 Bad Request`: If username is already registered.
    - `422 Unprocessable Entity`: If `username` or `password` do not meet validation criteria (e.g., too short).

#### `POST /auth/login`
(Public) Authenticates a user.

-   **Request Body** (`application/x-www-form-urlencoded`):
    - `username`: The user's username.
    - `password`: The user's password.
-   **Example with `curl`**:
    ```sh
    curl -X POST -d "username=newuser&password=a_very_strong_password_123" https://localhost/auth/login --insecure
    ```
-   **Success Response (2FA Disabled)** (`200 OK`):
    ```json
    {
      "access_token": "jwt_access_token",
      "token_type": "bearer"
    }
    ```
-   **Success Response (2FA Enabled)** (`200 OK`):
    ```json
    {
      "pre_auth_token": "jwt_pre_auth_token",
      "token_type": "bearer",
      "2fa_required": true
    }
    ```
-   **Error Responses**:
    - `401 Unauthorized`: If credentials are incorrect.

#### `POST /auth/login/verify-2fa`
Verifies a TOTP code to complete a 2FA login. Requires the `pre_auth_token` as the Bearer token.

-   **Request Body** (`application/json`):
    ```json
    {
      "totp_code": "123456"
    }
    ```
-   **Success Response** (`200 OK`):
    ```json
    {
      "access_token": "final_jwt_access_token",
      "token_type": "bearer"
    }
    ```
-   **Error Responses**:
    - `400 Bad Request`: If the TOTP code is invalid.
    - `401 Unauthorized`: If the `pre_auth_token` is invalid or expired.

#### `POST /auth/2fa/setup`
Generates a secret and QR code URI to enable 2FA. Requires authentication.

-   **Success Response** (`200 OK`):
    ```json
    {
      "secret": "BASE32_ENCODED_SECRET",
      "qr_code_uri": "otpauth://totp/Astraea:username?secret=...&issuer=Astraea"
    }
    ```
-   **Error Responses**:
    - `400 Bad Request`: If 2FA is already enabled.

### Messaging (`/messages`)

#### `POST /messages/send`
Sends an encrypted message. Requires authentication.

-   **Request Body** (`application/json`):
    ```json
    {
      "recipients": ["user2", "user3"],
      "encrypted_payload": "base64_encoded_encrypted_content",
      "signature": "base64_encoded_signature",
      "recipient_session_keys": {
        "user2": "base64_encoded_encrypted_key_for_user2",
        "user3": "base64_encoded_encrypted_key_for_user3"
      }
    }
    ```
-   **Success Response** (`201 Created`):
    ```json
    {
        "id": "message-uuid",
        "sender_id": "sender-uuid",
        "sender_username": "sender_username",
        "created_at": "timestamp",
        "read_status": false
    }
    ```
-   **Error Responses**:
    - `404 Not Found`: If one or more recipient usernames do not exist.
    - `400 Bad Request`: If the list of recipients is empty or a key is missing.

#### `GET /messages/`
Gets metadata for all messages in the user's inbox. Requires authentication.

-   **Success Response** (`200 OK`):
    ```json
    [
      {
        "id": "message-uuid",
        "sender_id": "sender-uuid",
        "sender_username": "some_sender",
        "created_at": "timestamp",
        "read_status": true
      }
    ]
    ```

#### `GET /messages/{message_id}`
Gets the full encrypted content of a specific message. Requires authentication.

-   **Success Response** (`200 OK`):
    ```json
    {
        "id": "message-uuid",
        "sender_id": "sender-uuid",
        "signature": "base64_encoded_signature",
        "encrypted_payload": "base64_encoded_encrypted_content",
        "encrypted_session_key": "base64_encoded_session_key_for_current_user",
        "created_at": "timestamp"
    }
    ```
-   **Error Responses**:
    - `404 Not Found`: If the message does not exist or the user is not a recipient.

#### `POST /messages/{message_id}/read`
Marks a message as read. Requires authentication.

-   **Success Response** (`204 No Content`)

#### `DELETE /messages/{message_id}`
Deletes a message from the user's inbox. Requires authentication.

-   **Success Response** (`204 No Content`)

## Application Management

### Running in the Background

To run the services in detached mode (in the background), use the `-d` flag:

```sh
docker-compose up --build -d
```

### Stopping the Application

To stop the running services:
```sh
docker-compose down
```

To stop the services and **delete all data** (including the database volume), use the `-v` flag:
```sh
docker-compose down -v
```