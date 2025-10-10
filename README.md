# Astraea: Secure E2EE Messaging System

Astraea is a secure, containerized web application for exchanging end-to-end encrypted (E2EE) messages. The architecture is inspired by zero-knowledge systems like ProtonMail, where the server has no ability to decrypt the content of user messages.

This project prioritizes security best practices at every layer, from the application code and cryptographic design to the containerization and deployment configuration.

## Key Features

-   **End-to-End Encryption (E2EE)**: Uses a hybrid encryption model (AES-256-GCM for message content + RSA-4096 for session key exchange) to ensure only the sender and intended recipients can read messages.
-   **Zero-Knowledge Architecture**: The server only stores encrypted data blobs and has no access to user private keys or unencrypted message content.
-   **Strong Authentication**: Secure password hashing with Bcrypt, JWT-based session management, and mandatory Two-Factor Authentication (2FA) using TOTP.
-   **Robust Security Practices**: Implements critical HTTP security headers (HSTS, CSP), rate limiting at the proxy layer, non-root containers, and strict input validation.
-   **Containerized with Docker**: The entire application stack (FastAPI Backend, PostgreSQL DB, NGINX Proxy) is orchestrated with Docker Compose for easy, reproducible deployments.
-   **Modern Python Backend**: Built with FastAPI, Pydantic, and SQLAlchemy for a high-performance, type-safe, and maintainable codebase.

## Architecture

The system consists of three main services orchestrated by Docker Compose:

1.  **`proxy` (NGINX)**: The public-facing gateway. It terminates TLS (HTTPS), serves security headers, rate-limits sensitive endpoints, and reverse-proxies requests to the backend API.
2.  **`api` (FastAPI)**: The core application backend. It handles user authentication, authorization, and the storage/retrieval of encrypted message data and user public keys.
3.  **`db` (PostgreSQL)**: A robust relational database for persistently storing user accounts, public keys, and encrypted message payloads.

## Prerequisites

Before you begin, ensure you have the following installed on your system:
-   **Docker**: [Get Docker](https://docs.docker.com/get-docker/)
-   **Docker Compose**: [Install Docker Compose](https://docs.docker.com/compose/install/)

## Getting Started

Follow these steps to get the Astraea system running on your local machine.

### 1. Clone the Repository

```sh
git clone <repository_url>
cd astraea-project
```

### 2. Configure Environment Variables

The application uses environment variables for configuration. Create a `.env` file by copying the example template:

```sh
cp .env.example .env
```

Review the `.env` file. For local development with Docker Compose, the default values should work correctly. You must provide a strong, unique `SECRET_KEY` for signing JWTs. You can generate one with the following command:

```sh
openssl rand -hex 32
```

### 3. Build and Run the Application

The entire application stack can be built and started with a single command from the project root directory:

```sh
docker-compose up --build
```

This command will:
-   Build the `api` and `proxy` Docker images from their respective Dockerfiles.
-   For the `proxy` service, it will generate a self-signed SSL certificate for local HTTPS.
-   Pull the official `postgres` image for the database.
-   Create the containers, set up the network, and start all three services.

### 4. Accessing the API

Once all services are running, the API will be accessible at **`https://localhost`**.

The interactive API documentation (powered by Swagger UI) is available at **`https://localhost/docs`**.

**Note on Self-Signed Certificate:** Your browser will display a security warning because the SSL certificate is self-signed (i.e., not trusted by a Certificate Authority). This is expected and safe for local development. You can proceed past the warning to access the API docs.

## API Endpoints Summary

All endpoints require a valid JWT Bearer token in the `Authorization` header, unless otherwise noted.

### Authentication (`/auth`)

-   `POST /auth/register`: (Public) Create a new user account.
-   `POST /auth/login`: (Public) Authenticate with username/password. Returns a final token or a pre-auth token if 2FA is enabled.
-   `POST /auth/login/verify-2fa`: (Requires Pre-Auth Token) Verify a TOTP code to complete a 2FA login.
-   `POST /auth/2fa/setup`: (Requires Auth) Generate a secret and QR code URI to enable 2FA.

### Messaging (`/messages`)

-   `POST /messages/send`: Send an encrypted message to one or more recipients.
-   `GET /messages/`: Get metadata for all messages in the user's inbox.
-   `GET /messages/{message_id}`: Get the full encrypted content of a specific message.
-   `POST /messages/{message_id}/read`: Mark a message as read.
-   `DELETE /messages/{message_id}`: Delete a message from the user's inbox.

## Security Model

The security of Astraea is founded on the principle of **zero-knowledge**. The server is designed to be an untrusted party that cannot access user data.

### End-to-End Encryption Flow

1.  **Key Generation**: On the client-side, each user generates a master RSA-4096 key pair. The public key is uploaded to the server. The private key is encrypted with a key derived from the user's password and stored by the client (or uploaded to the server as an encrypted blob for convenience). **The server never sees the unencrypted private key.**
2.  **Sending a Message**:
    - The sender's client generates a random, single-use AES-256 session key.
    - The message content is encrypted with this AES key.
    - For each recipient, the sender's client fetches their public RSA key from the server.
    - The AES session key is then encrypted separately for each recipient using their respective public key.
    - The sender's client uploads the encrypted message payload, the sender's signature of the payload, and the list of recipients with their individually encrypted session keys.
3.  **Receiving a Message**:
    - A recipient's client fetches the message payload.
    - It finds the encrypted session key that was created specifically for them.
    - The client uses the recipient's private RSA key (after decrypting it with their password) to decrypt the AES session key.
    - The client uses the decrypted session key to decrypt the message content.
    - The client verifies the sender's signature on the content using the sender's public key.

This ensures that only the intended recipients can decrypt the message content. The server only sees opaque, encrypted data.

## Project Structure

```
.
├── app/                  # FastAPI application source code
│   ├── api/              # API endpoint routers (auth.py, messages.py)
│   ├── models/           # SQLAlchemy database models (models.py)
│   ├── services/         # Business logic services (auth_service.py)
│   ├── __init__.py
│   ├── database.py       # Database session management and engine configuration.
│   ├── main.py           # Main FastAPI application entry point and middleware setup.
│   ├── middleware.py     # Custom security headers middleware.
│   └── schemas.py        # Pydantic schemas for data validation and serialization.
├── nginx/                # NGINX configuration and Dockerfile
│   ├── Dockerfile
│   └── nginx.conf
├── .env.example          # Example environment variables.
├── Dockerfile            # Dockerfile for the FastAPI `api` service.
├── docker-compose.yml    # Docker Compose orchestration file.
├── requirements.txt      # Python package dependencies.
└── README.md             # This file.
```

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