from fastapi import FastAPI
from .database import engine
from . import models
from .api import auth, messages
from .middleware import SecurityHeadersMiddleware

# This line creates the database tables if they don't exist.
# In a production setup with Alembic, you might manage this differently.
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Astraea E2EE Messaging System",
    description="A secure, end-to-end encrypted messaging API.",
    version="0.1.0",
)

# Add Middleware
app.add_middleware(SecurityHeadersMiddleware)

# Include API routers
app.include_router(auth.router)
app.include_router(messages.router)

@app.get("/", tags=["Health Check"])
def read_root():
    """A simple health check endpoint."""
    return {"status": "ok", "message": "Welcome to the Astraea API"}