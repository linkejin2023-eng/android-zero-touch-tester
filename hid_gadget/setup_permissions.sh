#!/bin/bash

# Configuration for Trimble T70 and Android Accessory Mode
RULES_FILE="/etc/udev/rules.d/51-android-aoa.rules"

echo "Creating udev rules for AOAv2 at $RULES_FILE..."

cat <<EOF | sudo tee $RULES_FILE
# Trimble T70 (Standard & OOBE)
SUBSYSTEM=="usb", ATTR{idVendor}=="099e", ATTR{idProduct}=="02b1", MODE="0666", GROUP="plugdev"
# Trimble T70 (ADB Enabled)
SUBSYSTEM=="usb", ATTR{idVendor}=="099e", ATTR{idProduct}=="02b5", MODE="0666", GROUP="plugdev"
# Fastboot Mode
SUBSYSTEM=="usb", ATTR{idVendor}=="18d1", ATTR{idProduct}=="d00d", MODE="0666", GROUP="plugdev"
# Android Accessory Mode (AOA)
SUBSYSTEM=="usb", ATTR{idVendor}=="18d1", ATTR{idProduct}=="2d00", MODE="0666", GROUP="plugdev"
SUBSYSTEM=="usb", ATTR{idVendor}=="18d1", ATTR{idProduct}=="2d01", MODE="0666", GROUP="plugdev"
EOF

echo "Reloading udev rules..."
sudo udevadm control --reload-rules
sudo udevadm trigger

echo "Setup complete. Please unplug and replug your Trimble T70."
echo "You should now be able to run the OOBE bypass without sudo."
