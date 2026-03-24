#!/bin/bash
cd /home/checkpoint/nfc-reader/web/
npm ci
npm run build
cd /home/checkpoint/nfc-reader/
rm -rf static
mkdir -p static
cp -R web/build/* static/
rsync -a   --exclude '.git'   --exclude '.venv'   --exclude 'pkg'   ./ pkg/checkpoint/opt/checkpoint/
dpkg-deb --build pkg/checkpoint
mv pkg/checkpoint.deb pkg/checkpoint_0.1.0_arm64.deb
sudo apt install -y ./pkg/checkpoint_0.1.0_arm64.deb
sudo systemctl status checkpoint.service --no-pager
