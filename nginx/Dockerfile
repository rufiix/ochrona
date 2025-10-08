# Use the stable alpine-based NGINX image
FROM nginx:stable-alpine

# Remove the default NGINX configuration file
RUN rm /etc/nginx/conf.d/default.conf

# Copy our custom NGINX configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Install OpenSSL, generate the self-signed certificates for development,
# and then remove OpenSSL to keep the image lean.
RUN apk add --no-cache openssl && \
    mkdir -p /etc/nginx/certs && \
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/nginx/certs/nginx-selfsigned.key \
    -out /etc/nginx/certs/nginx-selfsigned.crt \
    -subj "/C=US/ST=Development/L=DevCity/O=AstraeaDev/CN=localhost" && \
    apk del openssl

# Expose ports for HTTP and HTTPS
EXPOSE 80 443