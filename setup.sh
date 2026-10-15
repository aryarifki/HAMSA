#!/usr/bin/env bash
# ==============================================================================
# HAMSA OSINT ENTERPRISE PLATFORM - AUTOMATED ENVIRONMENT BOOTSTRAP
# Targeted Platform: Debian 11/12+ & Ubuntu 20.04/22.04/24.04 LTS
# ==============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}==================================================================${NC}"
echo -e "${CYAN}   🪬 HAMSA ENTERPRISE OSINT PLATFORM - DEBIAN / UBUNTU SETUP    ${NC}"
echo -e "${CYAN}==================================================================${NC}"

# 1. Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS_NAME=$NAME
    OS_ID=$ID
    echo -e "[*] Detected Operating System: ${GREEN}${OS_NAME} (${OS_ID})${NC}"
    if [[ "$OS_ID" != "ubuntu" && "$OS_ID" != "debian" && "$ID_LIKE" != *"debian"* && "$ID_LIKE" != *"ubuntu"* ]]; then
        echo -e "${YELLOW}[!] Notice: This system is not Debian/Ubuntu. Proceeding with generic Linux setup...${NC}"
    fi
else
    echo -e "${YELLOW}[!] Warning: /etc/os-release not detected. Continuing...${NC}"
fi

# 2. Check & Initialize .env
if [ ! -f .env ]; then
    echo -e "[*] Creating local ${YELLOW}.env${NC} file from .env.example..."
    cp .env.example .env
    echo -e "${GREEN}[+] Local environment configuration created: .env${NC}"
    echo -e "    Customize your PostgreSQL password & host in .env before starting."
else
    echo -e "${GREEN}[+] Existing .env file found.${NC}"
fi

# 3. Check for Apt Package Manager (Debian/Ubuntu)
if command -v apt-get >/dev/null 2>&1; then
    echo -e "[*] Verifying Debian/Ubuntu system packages (python3-venv, libpq-dev)..."
    MISSING_PKGS=()
    dpkg -s python3-venv >/dev/null 2>&1 || MISSING_PKGS+=("python3-venv")
    dpkg -s libpq-dev >/dev/null 2>&1 || MISSING_PKGS+=("libpq-dev")
    dpkg -s gcc >/dev/null 2>&1 || MISSING_PKGS+=("gcc")

    if [ ${#MISSING_PKGS[@]} -gt 0 ]; then
        echo -e "${YELLOW}[!] Installing required build dependencies: ${MISSING_PKGS[*]}${NC}"
        if [ "$EUID" -eq 0 ]; then
            apt-get update -y && apt-get install -y "${MISSING_PKGS[@]}"
        elif command -v sudo >/dev/null 2>&1; then
            sudo apt-get update -y && sudo apt-get install -y "${MISSING_PKGS[@]}"
        else
            echo -e "${RED}[!] Please install missing packages manually as root: apt-get install ${MISSING_PKGS[*]}${NC}"
        fi
    else
        echo -e "${GREEN}[+] All Debian/Ubuntu build packages are satisfied.${NC}"
    fi
fi

# 4. Setup Python Virtual Environment
echo -e "[*] Configuring Python 3 Virtual Environment (venv)..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "${GREEN}[+] Virtual environment created at ./venv${NC}"
fi

echo -e "[*] Installing & upgrading enterprise Python packages..."
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

# 5. Frontend Node Modules Check
if [ -d "frontend" ]; then
    if command -v npm >/dev/null 2>&1; then
        echo -e "[*] Setting up Next.js frontend dependencies..."
        cd frontend
        if [ ! -d "node_modules" ]; then
            npm install
        else
            echo -e "${GREEN}[+] Frontend node_modules already installed.${NC}"
        fi
        cd ..
    else
        echo -e "${YELLOW}[!] Notice: npm not found in PATH. Install Node.js 18+ to run the Next.js frontend locally.${NC}"
    fi
fi

echo -e ""
echo -e "${GREEN}==================================================================${NC}"
echo -e "${GREEN}  ✓ SETUP COMPLETED SUCCESSFULLY!                                 ${NC}"
echo -e "${GREEN}==================================================================${NC}"
echo -e "You can now run HAMSA using either of the following methods:"
echo -e ""
echo -e "  ${CYAN}Method 1 (Docker Compose - Recommended):${NC}"
echo -e "    ${YELLOW}docker compose up -d${NC}"
echo -e "    • Starts PostgreSQL, Redis, Enterprise Backend, and Frontend."
echo -e ""
echo -e "  ${CYAN}Method 2 (Native Local Server):${NC}"
echo -e "    ${YELLOW}./start.sh${NC}"
echo -e "    • Starts the Enterprise ASGI Backend on port 8888."
echo -e "=================================================================="
