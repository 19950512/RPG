#!/bin/bash

# Script to generate self-signed certificates for development
# For production, use proper CA-signed certificates

set -e

CERT_DIR="./certs"
DAYS=365
COUNTRY="US"
STATE="CA"
CITY="San Francisco"
ORG="Game Server"
UNIT="Development"
COMMON_NAME="gameserver"

# Create certs directory if it doesn't exist
mkdir -p "$CERT_DIR"

echo "Generating self-signed certificates for development..."

# Generate private key
openssl genrsa -out "$CERT_DIR/gameserver.key" 2048

# Generate certificate signing request
openssl req -new -key "$CERT_DIR/gameserver.key" -out "$CERT_DIR/gameserver.csr" -subj "/C=$COUNTRY/ST=$STATE/L=$CITY/O=$ORG/OU=$UNIT/CN=$COMMON_NAME"

# Generate self-signed certificate
openssl x509 -req -in "$CERT_DIR/gameserver.csr" -signkey "$CERT_DIR/gameserver.key" -out "$CERT_DIR/gameserver.crt" -days $DAYS

# Generate PFX file for .NET (with password)
openssl pkcs12 -export -out "$CERT_DIR/gameserver.pfx" -inkey "$CERT_DIR/gameserver.key" -in "$CERT_DIR/gameserver.crt" -password pass:password

# Set proper permissions
chmod 600 "$CERT_DIR"/*

echo "Certificates generated successfully in $CERT_DIR/"
echo "Certificate files:"
echo "  - gameserver.key (private key)"
echo "  - gameserver.crt (certificate)"
echo "  - gameserver.pfx (PKCS#12 format for .NET, password: password)"
echo ""
echo "Note: These are self-signed certificates for development only."
echo "For production, use certificates from a trusted CA."
