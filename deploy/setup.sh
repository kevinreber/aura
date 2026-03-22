#!/bin/bash
set -euo pipefail

# Aura - DigitalOcean Droplet Setup Script
# Run this on a fresh Ubuntu 22.04+ Droplet
# Usage: ssh root@your-droplet-ip 'bash -s' < deploy/setup.sh

echo "==> Installing Docker..."
curl -fsSL https://get.docker.com | sh

echo "==> Installing Docker Compose plugin..."
apt-get install -y docker-compose-plugin

echo "==> Creating app user..."
useradd -m -s /bin/bash -G docker aura || true

echo "==> Creating app directory..."
mkdir -p /opt/aura
chown aura:aura /opt/aura

echo "==> Setting up firewall..."
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

echo "==> Enabling Docker on boot..."
systemctl enable docker

echo "==> Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Copy your project:  scp -r . aura@your-droplet-ip:/opt/aura/"
echo "  2. SSH in:             ssh aura@your-droplet-ip"
echo "  3. Set up env:         cd /opt/aura && cp .env.example .env && nano .env"
echo "  4. Set your domain:    export DOMAIN=yourdomain.com"
echo "  5. Deploy:             make deploy"
