!#/usr/bin/bash
sudo apt remove checkpoint -y
./build.sh
sudo apt install -y ./pkg/checkpoint_0.1.0_arm64.deb