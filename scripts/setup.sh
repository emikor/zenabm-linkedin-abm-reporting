#!/usr/bin/env bash
# setup.sh — First-run setup wizard for linkedin-abm-reporter
#
# What this does:
#   1. Checks if .env already exists (asks to confirm overwrite)
#   2. Prompts for your ZenABM API token
#   3. Tests the token against the /linkedin-metrics endpoint
#   4. Writes .env on success
#   5. Prints next steps

set -euo pipefail

# Resolve plugin root (parent of the scripts/ directory)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE="${PLUGIN_ROOT}/.env"
VENV_DIR="${PLUGIN_ROOT}/.venv"
REQUIREMENTS_FILE="${PLUGIN_ROOT}/requirements.txt"
BASE_URL="${ZENABM_BASE_URL:-https://app.zenabm.com/api/v1}"

# ── Colours ────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Colour

print_header() {
  echo ""
  echo -e "${CYAN}${BOLD}╔══════════════════════════════════════════════╗${NC}"
  echo -e "${CYAN}${BOLD}║     LinkedIn ABM Reporter — Setup Wizard     ║${NC}"
  echo -e "${CYAN}${BOLD}╚══════════════════════════════════════════════╝${NC}"
  echo ""
}

# ── Create virtualenv + install deps ───────────────────────────────────────
# We always use a local .venv so we work on PEP-668-protected systems
# (Homebrew Python, Debian/Ubuntu, etc.) without needing --break-system-packages.
ensure_venv() {
  # Pick a Python interpreter
  local py=""
  for candidate in python3 python; do
    if command -v "${candidate}" >/dev/null 2>&1; then
      py="${candidate}"
      break
    fi
  done
  if [[ -z "${py}" ]]; then
    echo -e "${RED}[ERROR] No python3/python found on PATH.${NC}"
    echo "    Install Python 3.9+ from https://www.python.org/downloads/ and rerun."
    exit 1
  fi

  if [[ ! -x "${VENV_DIR}/bin/python" ]]; then
    echo -e "Creating virtualenv at ${VENV_DIR}..."
    if ! "${py}" -m venv "${VENV_DIR}" 2>/tmp/zenabm_venv_err; then
      echo -e "${RED}[ERROR] Failed to create virtualenv.${NC}"
      echo "    If you're on Debian/Ubuntu you may need: sudo apt-get install python3-venv"
      echo "    Details:"
      sed 's/^/    /' /tmp/zenabm_venv_err
      rm -f /tmp/zenabm_venv_err
      exit 1
    fi
    rm -f /tmp/zenabm_venv_err
    echo -e "${GREEN}[OK] Virtualenv created.${NC}"
  else
    echo -e "${GREEN}[OK] Existing virtualenv detected at ${VENV_DIR}.${NC}"
  fi

  # Install dependencies into the venv
  echo -e "Installing Python dependencies..."
  if ! "${VENV_DIR}/bin/python" -m pip install --disable-pip-version-check --quiet --upgrade pip; then
    echo -e "${YELLOW}[WARN] Could not upgrade pip inside the venv, continuing anyway.${NC}"
  fi
  if ! "${VENV_DIR}/bin/python" -m pip install --disable-pip-version-check --quiet -r "${REQUIREMENTS_FILE}"; then
    echo -e "${RED}[ERROR] Failed to install dependencies from ${REQUIREMENTS_FILE}.${NC}"
    echo "    Re-run with verbose output to debug:"
    echo "      ${VENV_DIR}/bin/python -m pip install -r ${REQUIREMENTS_FILE}"
    exit 1
  fi
  echo -e "${GREEN}[OK] Dependencies installed into .venv.${NC}"
}

# ── Check for existing .env ────────────────────────────────────────────────
check_existing_env() {
  if [[ -f "${ENV_FILE}" ]]; then
    echo -e "${YELLOW}[!] A .env file already exists at:${NC}"
    echo "    ${ENV_FILE}"
    echo ""
    read -rp "    Overwrite it? [y/N] " confirm
    if [[ ! "${confirm}" =~ ^[Yy]$ ]]; then
      echo ""
      echo -e "${GREEN}Setup cancelled. Existing .env kept.${NC}"
      exit 0
    fi
    echo ""
  fi
}

# ── Prompt for token ───────────────────────────────────────────────────────
prompt_token() {
  echo -e "${BOLD}Where to find your ZenABM API token:${NC}"
  echo "  Log in to ZenABM → Settings → API → copy your Bearer token"
  echo ""
  read -rsp "Enter your ZenABM API token: " TOKEN
  echo ""

  if [[ -z "${TOKEN}" ]]; then
    echo -e "${RED}[ERROR] No token entered. Aborting.${NC}"
    exit 1
  fi
}

# ── Test the token ─────────────────────────────────────────────────────────
test_token() {
  echo ""
  echo -e "Testing token against ZenABM API..."

  # Use the last 7 days as a test window
  END_DATE="$(date +%Y-%m-%d)"
  START_DATE="$(date -d '7 days ago' +%Y-%m-%d 2>/dev/null || date -v-7d +%Y-%m-%d)"

  HTTP_STATUS=$(
    curl -s -o /tmp/zenabm_test_response.json -w "%{http_code}" \
      -H "Authorization: Bearer ${TOKEN}" \
      -H "Accept: application/json" \
      "${BASE_URL}/linkedin-metrics?startDate=${START_DATE}&endDate=${END_DATE}" \
      2>/dev/null
  ) || true

  if [[ "${HTTP_STATUS}" == "200" ]]; then
    echo -e "${GREEN}[OK] Token is valid (HTTP 200).${NC}"
  elif [[ "${HTTP_STATUS}" == "401" || "${HTTP_STATUS}" == "403" ]]; then
    echo -e "${RED}[ERROR] Authentication failed (HTTP ${HTTP_STATUS}).${NC}"
    echo "    The token was rejected. Please check it and try again."
    rm -f /tmp/zenabm_test_response.json
    exit 1
  elif [[ "${HTTP_STATUS}" == "000" ]]; then
    echo -e "${YELLOW}[WARN] Could not reach ${BASE_URL}.${NC}"
    echo "    Check your internet connection or ZENABM_BASE_URL."
    read -rp "    Continue and save the token anyway? [y/N] " cont
    if [[ ! "${cont}" =~ ^[Yy]$ ]]; then
      exit 1
    fi
  else
    echo -e "${YELLOW}[WARN] Unexpected HTTP status: ${HTTP_STATUS}.${NC}"
    echo "    Response body:"
    cat /tmp/zenabm_test_response.json 2>/dev/null || true
    echo ""
    read -rp "    Continue and save the token anyway? [y/N] " cont
    if [[ ! "${cont}" =~ ^[Yy]$ ]]; then
      rm -f /tmp/zenabm_test_response.json
      exit 1
    fi
  fi

  rm -f /tmp/zenabm_test_response.json
}

# ── Write .env ─────────────────────────────────────────────────────────────
write_env() {
  cat > "${ENV_FILE}" <<EOF
# ZenABM API credentials
# Generated by setup.sh — do not commit this file to version control
ZENABM_API_TOKEN=${TOKEN}
ZENABM_BASE_URL=${BASE_URL}
EOF

  chmod 600 "${ENV_FILE}"
  echo ""
  echo -e "${GREEN}[OK] .env written to:${NC}"
  echo "    ${ENV_FILE}"
}

# ── Print next steps ───────────────────────────────────────────────────────
print_next_steps() {
  echo ""
  echo -e "${CYAN}${BOLD}Setup complete! Here's what to do next:${NC}"
  echo ""
  echo "  1. Test the CLI:"
  echo "     ${VENV_DIR}/bin/python ${PLUGIN_ROOT}/scripts/query_zenabm.py get_overview '{\"start\":\"$(date -d '7 days ago' +%Y-%m-%d 2>/dev/null || date -v-7d +%Y-%m-%d)\",\"end\":\"$(date +%Y-%m-%d)\"}'"
  echo ""
  echo "  2. Generate an ABM report in Claude Code:"
  echo "     /abm-report"
  echo "     (or ask: 'Give me last week's LinkedIn ABM report')"
  echo ""
  echo -e "${YELLOW}Note: .env is listed in .gitignore — your token will NOT be committed.${NC}"
  echo ""
}

# ── Main ───────────────────────────────────────────────────────────────────
print_header
ensure_venv
check_existing_env
prompt_token
test_token
write_env
print_next_steps
