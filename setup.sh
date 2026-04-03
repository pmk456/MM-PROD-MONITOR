#!/bin/bash

set -e

echo -e "\033[0;32m[+] Updating system..."
sudo apt update -y

install_if_missing() {
    if ! dpkg -s "$1" >/dev/null 2>&1; then
        echo -e "\033[0;32m[+] Installing $1..."
        sudo apt install -y "$1"
    else
        echo -e "\033[0;33m[=] $1 already installed"
    fi
}

# Packages
install_if_missing python3
install_if_missing python3-pip
install_if_missing python3-venv

# Move into src
cd src

echo -e "\033[0;32m[+] Setting up virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "\033[0;32m[+] Virtual environment created in src/"
else
    echo -e "\033[0;33m[=] venv already exists"
fi

echo -e "[+] Activating venv..."
source venv/bin/activate

echo -e "[+] Installing dependencies..."
if [ -f "../requirements.txt" ]; then
    pip install -r ../requirements.txt
elif [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    echo -e "\033[0;31m[-] No requirements.txt found"
fi

CRON_JOB="* * * * * /home/$(whoami)/mm-prod-monitor/src/venv/bin/python /home/$(whoami)/mm-prod-monitor/src/monitor.py >> /home/$(whoami)/mm-prod-monitor/monitor.log 2>&1"

# Check if already exists
(crontab -l 2>/dev/null | grep -F "$CRON_JOB") >/dev/null 2>&1

if [ $? -eq 0 ]; then
    echo -e "\033[0;33m[=] Cron job already exists"
else
    echo -e "\033[0;32m[+] Adding cron job..."
    (crontab -l 2>/dev/null; echo -e "$CRON_JOB") | crontab -
    echo -e "\033[0;32m[+] Cron job added"
fi

echo -e "\033[0;32m[+] Setup complete - Pmk"
