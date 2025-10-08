# ==============================================================================
# Stage 1: Builder
#
# This stage installs all dependencies, including build-time dependencies,
# into a virtual environment. The goal is to create a self-contained package
# directory that can be copied to the final, lean production image.
# ==============================================================================
FROM python:3.11-slim as builder

WORKDIR /app

# Set environment variables for the build
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install pip-tools for dependency management and system dependencies
# required for building some Python packages.
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc build-essential && \
    pip install --no-cache-dir --upgrade pip

# Copy the requirements file and install dependencies into a target directory
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir=/app/wheels -r requirements.txt


# ==============================================================================
# Stage 2: Production
#
# This is the final, lean image. It starts from a fresh Python slim base,
# creates a non-root user for security, and copies only the necessary
# application code and pre-built dependencies from the builder stage.
# ==============================================================================
FROM python:3.11-slim

WORKDIR /home/astraea/app

# Create a non-root user 'astraea' to run the application.
# This is a critical security best practice.
RUN groupadd -r astraea && useradd --no-log-init -r -g astraea astraea
RUN chown -R astraea:astraea /home/astraea

# Copy the pre-built wheels from the builder stage
COPY --from=builder /app/wheels /wheels

# Install the Python dependencies from the wheels
RUN pip install --no-cache-dir /wheels/*

# Copy the application source code
COPY ./app ./app

# Switch to the non-root user
USER astraea

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application using Uvicorn.
# --host 0.0.0.0 makes it accessible from outside the container.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]