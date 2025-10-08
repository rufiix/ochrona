# Presentation Outline: Astraea Secure Messaging System

This document outlines a presentation for the Astraea E2EE Messaging System, focusing on its architecture, core security principles, and technology choices.

---

### **Slide 1: Title Slide**

*   **Title**: Astraea: A Modern Architecture for Secure, Zero-Knowledge Messaging
*   **Subtitle**: Inspired by ProtonMail, Built with a Security-First Mindset
*   **Presenter**: Jules, Senior Secure Software Engineer
*   **Date**: October 2025

---

### **Slide 2: The Problem - Why Zero-Knowledge?**

*   **The Challenge**: Standard messaging platforms are high-value targets. A server breach can expose the private communications of all users.
*   **The Solution**: A "Zero-Knowledge" architecture. The server has no ability to read user messages, rendering a server-side data breach ineffective for compromising message content.
*   **Project Goal**: To design and build a simple, robust, and highly secure E2EE messaging system where the server is merely a synchronized, encrypted vault.

---

### **Slide 3: System Architecture - A 3-Tier Model**

*   A diagram showing the three containerized services.
*   **1. NGINX Reverse Proxy (The Gatekeeper)**
    *   Public entry point, terminates TLS (HTTPS).
    *   Hardens security with headers and rate limiting.
    *   Routes traffic to the backend.
*   **2. FastAPI Backend API (The Broker)**
    *   Stateless application logic (Python).
    *   Manages users, authentication, and authorization.
    *   Stores and retrieves **only encrypted data**. It cannot read messages.
*   **3. PostgreSQL Database (The Vault)**
    *   The persistent data store for all user accounts and encrypted message blobs.
    *   Ensures data integrity through relational constraints.

---

### **Slide 4: The Core of Security - Cryptographic Design**

*   **Hybrid Encryption**: The best of both worlds.
    *   **Symmetric (AES-256-GCM)**: A unique, random "session key" is used to encrypt the message content. Fast and secure.
    *   **Asymmetric (RSA-4096)**: The session key itself is then encrypted with each recipient's public key.
*   **End-to-End Encryption Flow (Diagram)**:
    1.  Client generates a random AES session key.
    2.  Client encrypts the message with this key.
    3.  Client encrypts the session key for each recipient using their public keys.
    4.  Server stores the encrypted message and the encrypted session keys.
*   **Authenticity**: Messages are digitally signed with the sender's private key (RSA-PSS) to prevent tampering and spoofing.

---

### **Slide 5: Authentication - Securing Access**

*   **Multi-Layered Approach**:
    *   **Password Hashing**: Using `Bcrypt` with a high cost factor to protect user credentials even if the database is compromised.
    *   **JWT Sessions**: Short-lived access tokens for API requests and long-lived (secure cookie) refresh tokens for session persistence.
    *   **Mandatory 2FA**: Time-based One-Time Passwords (TOTP) are required after password validation, providing a critical second layer of security against credential theft.

---

### **Slide 6: Technology Stack**

*   **Backend**: **FastAPI (Python)** - Chosen for its high performance, modern async capabilities, and automatic data validation with Pydantic, which is a security feature in itself.
*   **Database**: **PostgreSQL** - For its robustness, reliability, and strong support for relational data integrity.
*   **Proxy**: **NGINX** - The industry standard for high-performance reverse proxying, load balancing, and security.
*   **Cryptography**: **`cryptography` & `passlib`** libraries - Well-vetted, industry-standard libraries for cryptographic operations and password hashing.
*   **Containerization**: **Docker & Docker Compose** - For creating a portable, reproducible, and isolated deployment environment.

---

### **Slide 7: Security Best Practices in Action**

*   **Defense in Depth**:
    *   **Application Level**: Strict input validation, security headers (CSP, HSTS), non-root user execution.
    *   **Infrastructure Level**: Multi-stage Docker builds for minimal attack surface, rate limiting at the proxy layer, container isolation.
    *   **Architectural Level**: The zero-knowledge design itself is the primary security control.

---

### **Slide 8: Conclusion & Next Steps**

*   **Summary**: Astraea successfully implements a secure, zero-knowledge messaging architecture using modern, robust technologies.
*   **Future Work**:
    *   Secure password recovery flow.
    *   Implementation of key rotation.
    *   Security audit and penetration testing.
    *   Building a client-side application to interact with the API.
*   **Q&A**