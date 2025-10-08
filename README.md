# Astraea: Secure E2EE Messaging System

Astraea is a secure, containerized web application for exchanging end-to-end encrypted (E2EE) messages. The architecture is inspired by zero-knowledge systems like ProtonMail, where the server has no ability to decrypt the content of the messages it stores and transmits.

This project prioritizes security best practices at every layer, from the application code and cryptographic design to the containerization and deployment configuration.

## Key Features

-   **End-to-End Encryption (E2EE)**: Uses a hybrid encryption model (AES-256-GCM + RSA-4096) to ensure only the sender and intended recipients can read messages.
-   **Zero-Knowledge Architecture**: The server only stores encrypted data blobs and has no access to user private keys or message content.
-   **Strong Authentication**: Secure password hashing with Bcrypt, JWT-based session management, and mandatory Two-Factor Authentication (2FA) using TOTP.
-   **Robust Security Practices**: Implements critical HTTP security headers (HSTS, CSP), rate limiting, non-root containers, and strict input validation.
-   **Containerized with Docker**: The entire application stack (FastAPI Backend, PostgreSQL DB, NGINX Proxy) is orchestrated with Docker Compose for easy, reproducible deployments.
-   **Service-Oriented Architecture**: A clean separation of concerns between the reverse proxy, the backend API, and the database.

## Architecture

The system consists of three main services orchestrated by Docker Compose:

1.  **`proxy` (NGINX)**: The public-facing gateway. It terminates TLS (HTTPS), provides security hardening, rate-limits sensitive endpoints, and reverse-proxies requests to the backend API.
2.  **`api` (FastAPI)**: The core application backend written in Python. It handles user authentication, authorization, and the storage/retrieval of encrypted message data.
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

### 2. Build and Run the Application

The entire application stack can be built and started with a single command from the project root directory:

```sh
docker-compose up --build
```

This command will:
-   Build the `api` and `proxy` Docker images from their respective Dockerfiles.
-   For the `proxy` service, it will generate a self-signed SSL certificate for local HTTPS.
-   Pull the official `postgres` image for the database.
-   Create the containers, set up the network, and start all three services.

### 3. Accessing the API

Once all services are running, the API will be accessible at **`https://localhost`**.

**Note on Self-Signed Certificate:** Your browser will display a security warning because the SSL certificate is self-signed (i.e., not trusted by a Certificate Authority). This is expected and safe for local development. You can proceed past the warning to access the API.

## Running the Application in the Background

To run the services in detached mode (in the background), use the `-d` flag:

```sh
docker-compose up --build -d
```

To stop the services, run:

```sh
docker-compose down
```

To stop the services and remove the persistent database volume (deleting all data), run:

```sh
docker-compose down -v
```

## Project Structure

```
.
├── app/                  # FastAPI application source code
│   ├── api/              # API endpoint routers (auth, messages)
│   ├── core/             # Core application logic (empty in this version)
│   ├── models/           # SQLAlchemy database models
│   ├── services/         # Business logic services (auth)
│   ├── __init__.py
│   ├── database.py       # Database session management
│   ├── main.py           # Main FastAPI application entry point
│   ├── middleware.py     # Custom security middleware
│   └── schemas.py        # Pydantic data schemas
├── nginx/                # NGINX configuration and Dockerfile
│   ├── Dockerfile
│   └── nginx.conf
├── .env                  # Environment variables for the API
├── Dockerfile            # Dockerfile for the FastAPI application
├── docker-compose.yml    # Docker Compose orchestration file
├── PROJECT_PLAN.md       # The initial project architecture plan
└── README.md             # This file
```