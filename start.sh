#!/usr/bin/env bash
# ==============================================================================
# HAMSA OSINT ENTERPRISE PLATFORM - START SCRIPT
# Starts the Enterprise ASGI Server (FastAPI + Uvicorn) with strict port checks
# ==============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Ensure .env exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}[!] .env not found. Copying .env.example -> .env...${NC}"
    cp .env.example .env
fi

# Load .env
export $(grep -v '^#' .env | xargs -d '\n')

# Verify Python Virtual Environment
PYTHON_BIN="./venv/bin/python3"
if [ ! -f "$PYTHON_BIN" ]; then
    echo -e "${YELLOW}[!] Virtual environment not detected. Running ./setup.sh first...${NC}"
    chmod +x ./setup.sh
    ./setup.sh
fi

WEB_PORT="${HAMSA_WEB_PORT:-8888}"
WEB_HOST="${HAMSA_WEB_HOST:-0.0.0.0}"

# CRITICAL PORT ISOLATION: Prevent port 8080 from ever being used
if [ "$WEB_PORT" -eq 8080 ]; then
    echo -e "${RED}[!] CRITICAL ERROR: Port 8080 is reserved for external crawlers. Reverting to port 8888.${NC}"
    WEB_PORT=8888
fi

echo -e "${CYAN}==================================================================${NC}"
echo -e "${CYAN}   🪬 LAUNCHING HAMSA ENTERPRISE INTELLIGENCE BACKEND SERVICE     ${NC}"
echo -e "${CYAN}==================================================================${NC}"
echo -e "[*] Database Engine:  ${GREEN}${HAMSA_DB_ENGINE:-postgres}${NC}"
echo -e "[*] Listening Host:   ${GREEN}${WEB_HOST}${NC}"
echo -e "[*] Listening Port:   ${GREEN}${WEB_PORT}${NC}"
echo -e "[*] Swagger Docs:     ${CYAN}http://localhost:${WEB_PORT}/docs${NC}"
echo -e "[*] Next.js Frontend: ${CYAN}http://localhost:3000${NC}"
echo -e "${CYAN}==================================================================${NC}"

# Execute backend
exec "$PYTHON_BIN" -m hamsa.web.server --serve --port "$WEB_PORT"
