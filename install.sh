#!/usr/bin/env bash
set -euo pipefail

URL="https://github.com/SZ-Laeuft/checkpoint/raw/refs/heads/master/pkg/checkpoint_0.1.0_arm64.deb"
TMP_DEB="/tmp/checkpoint_0.1.0_arm64.deb"
BASE_DIR="/home/checkpoint"

echo "Removing app folder..."
sudo rm -rf "$BASE_DIR/app"
sudo apt remove -y checkpoint || true

echo "Removing folders containing 'checkpoint' in their name..."
find "$BASE_DIR" -maxdepth 1 -type d -name '*checkpoint*' ! -path "$BASE_DIR" -exec rm -rf {} +

echo "Cleaning up..."
rm -f "$TMP_DEB"
sudo rm -rf /opt/checkpoint/app || true

echo "Downloading package..."
curl -L "$URL" -o "$TMP_DEB"

echo "Installing package..."
sudo apt-get update
sudo apt-get install -y "$TMP_DEB"


echo "Done."