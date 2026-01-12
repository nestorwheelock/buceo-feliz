#!/bin/bash
# Initialize Let's Encrypt SSL certificates for happydiving.mx

set -e

DOMAIN="happydiving.mx"
EMAIL="${CERTBOT_EMAIL:-admin@happydiving.mx}"

cd /opt/diveops

# Check if certificates already exist
if [ -f "/opt/diveops/certs/live/${DOMAIN}/fullchain.pem" ]; then
    echo "SSL certificates already exist for ${DOMAIN}"
    exit 0
fi

echo "Setting up SSL certificates for ${DOMAIN}..."

# Create temporary nginx config for ACME challenge only
cat > /opt/diveops/nginx-temp.conf << 'NGINX_TEMP'
worker_processes 1;
events { worker_connections 512; }
http {
    server {
        listen 80;
        server_name happydiving.mx www.happydiving.mx;

        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }

        location / {
            return 200 'SSL setup in progress...';
            add_header Content-Type text/plain;
        }
    }
}
NGINX_TEMP

# Stop nginx if running
docker compose -f docker-compose.prod.yml stop nginx 2>/dev/null || true

# Start nginx with temporary config
docker run -d --name nginx-temp \
    -p 80:80 \
    -v /opt/diveops/nginx-temp.conf:/etc/nginx/nginx.conf:ro \
    -v diveops_certbot_www:/var/www/certbot \
    nginx:alpine

# Wait for nginx to start
sleep 3

# Run certbot to get certificates
docker run --rm \
    -v diveops_certs_data:/etc/letsencrypt \
    -v diveops_certbot_www:/var/www/certbot \
    certbot/certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email "${EMAIL}" \
    --agree-tos \
    --no-eff-email \
    -d "${DOMAIN}" \
    -d "www.${DOMAIN}"

# Stop and remove temporary nginx
docker stop nginx-temp
docker rm nginx-temp

# Remove temporary config
rm /opt/diveops/nginx-temp.conf

# Copy certificates to local volume
docker run --rm \
    -v diveops_certs_data:/certs:ro \
    -v /opt/diveops/certs:/local \
    alpine sh -c 'cp -rL /certs/* /local/ 2>/dev/null || true'

echo "SSL certificates obtained successfully!"
echo "Now restart the main stack with: docker compose -f docker-compose.prod.yml up -d"
