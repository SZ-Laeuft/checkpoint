#!/bin/bash
set -e

PROJECT_ROOT="/home/checkpoint/checkpoint"
PKG_DIR="$PROJECT_ROOT/pkg/checkpoint/opt/checkpoint"
OUTPUT_DEB="$PROJECT_ROOT/pkg/checkpoint_0.1.0_arm64.deb"

echo "🔨 Building Checkpoint Debian Package"
echo "======================================"

# Step 1: Build frontend
echo "📦 Building Svelte frontend..."
cd "$PROJECT_ROOT/web"
npm ci
npm run build

# Step 2: Prepare static files
echo "📁 Preparing static files..."
cd "$PROJECT_ROOT"
rm -rf static
mkdir -p static
cp -R web/build/* static/

# Step 3: Generate lock file (if not exists)
echo "🔒 Generating uv.lock..."
uv lock

# Step 4: Clear and prepare package directory
echo "📦 Preparing package directory..."
rm -rf "$PKG_DIR"
mkdir -p "$PKG_DIR"

# Step 5: Copy project (exclude unnecessary files)
rsync -a \
  --exclude '.git' \
  --exclude '.venv' \
  --exclude 'pkg' \
  --exclude '.pytest_cache' \
  --exclude '__pycache__' \
  --exclude '.idea' \
  --exclude 'node_modules' \
  --exclude 'web/build' \
  ./ "$PKG_DIR/"

# Step 6: Build .deb
echo "📦 Building .deb package..."
dpkg-deb --build "$PROJECT_ROOT/pkg/checkpoint"
mv "$PROJECT_ROOT/pkg/checkpoint.deb" "$OUTPUT_DEB"

echo "✅ Package built: $OUTPUT_DEB"
echo ""
echo "📥 To install on target system:"
echo "   sudo apt install -y ./pkg/checkpoint_0.1.0_arm64.deb"
echo ""
echo "🚀 Service will auto-start. Check status with:"
echo "   sudo systemctl status checkpoint.service"
