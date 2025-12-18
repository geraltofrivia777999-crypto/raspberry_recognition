#!/bin/bash
# Setup script for GPIO permissions on Raspberry Pi

echo "Setting up GPIO permissions..."

# Add current user to gpio group
echo "Adding user $USER to gpio group..."
sudo usermod -a -G gpio $USER

# Make sure gpiochip devices are accessible
echo "Setting permissions for /dev/gpiochip*..."
sudo chmod 666 /dev/gpiochip* 2>/dev/null || echo "Warning: Could not chmod /dev/gpiochip*"

# Create udev rule for persistent permissions
UDEV_RULE="/etc/udev/rules.d/99-gpio.rules"
echo "Creating udev rule at $UDEV_RULE..."
echo 'SUBSYSTEM=="gpio", KERNEL=="gpiochip*", GROUP="gpio", MODE="0660"' | sudo tee $UDEV_RULE > /dev/null

# Reload udev rules
echo "Reloading udev rules..."
sudo udevadm control --reload-rules
sudo udevadm trigger

echo ""
echo "✓ GPIO setup completed!"
echo ""
echo "IMPORTANT: You need to log out and log back in for group changes to take effect."
echo "Or run: newgrp gpio"
echo ""
echo "To verify setup, run: python test_gpio.py"
