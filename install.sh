#!/bin/bash

echo "[+] Installing Python dependencies..."
pip3 install -r requirements.txt

chmod +x vercelstrike.py

echo "[✓] Installation complete."
