#!/usr/bin/env bash
# The code never names a club (TR-40). Anything club-specific belongs in config/club.yaml or an
# overlay. Documentation, config/, and the pre-application holding page in web/ are exempt.
set -uo pipefail
cd "$(dirname "$0")/.."
hits=$(grep -rniE 'w3usr|scranton' apps templates static 2>/dev/null | grep -v '^Binary')
if [ -n "$hits" ]; then
  echo "Club-specific strings in code (TR-40):"; echo "$hits"; exit 1
fi
echo "club-neutral: ok"
