#!/bin/bash
# run_until_minted.sh — keep the Hashcats farm running in back-to-back windows until the
# wallet can no longer pay a mint, or TARGET_MINTS cats have been minted.
set -u
cd "$(dirname "$0")"
export PATH="$HOME/.local/bin:$PATH"
PY="$HOME/.local/share/uv/tools/modal/bin/python"
KEY="$HOME/.hermes/secrets/hashcats_miner_key"
TARGET_MINTS="${TARGET_MINTS:-2}"
SHARDS="${SHARDS:-16}"
WINDOW_MIN="${WINDOW_MIN:-20}"
MAX_MINUTES="${MAX_MINUTES:-90}"
LOG="supervisor.log"
DEADLINE=$(( $(date +%s) + MAX_MINUTES*60 ))

log(){ echo "[$(date '+%H:%M:%S')] $*" | tee -a "$LOG"; }

mints_done(){ n=$(grep -c '"tx"' solutions.json 2>/dev/null); echo "${n:-0}" | head -1; }

# prints: "<verdict> <balance_eth> <price_eth>"
funds_state() {
  $PY - <<'PYEOF'
import hashcats as hc
W = "0x4444444444444444444444444444444444444444"
bal = int(hc.rpc("eth_getBalance", [W, "latest"]), 16)
pri = int(hc.rpc("eth_call", [{"to": hc.COLLECTION, "data": hc.sel("mintPrice()") + hc.enc()}, "latest"]), 16)
print(("OK" if bal > pri * 1.02 else "STOP"), f"{bal/1e18:.6f}", f"{pri/1e18:.6f}")
PYEOF
}

log "supervisor start | target mints $TARGET_MINTS | shards $SHARDS | window ${WINDOW_MIN}m"
while :; do
  if [ "$(date +%s)" -ge "$DEADLINE" ]; then log "time budget (${MAX_MINUTES}m) reached — stopping"; break; fi
  done_now=$(mints_done)
  if [ "$done_now" -ge "$TARGET_MINTS" ]; then log "target reached ($done_now mints) — stopping"; break; fi
  state=$(funds_state)
  verdict=$(echo "$state" | awk '{print $1}')
  if [ "$verdict" != "OK" ]; then log "funds exhausted ($state) — stopping"; break; fi
  log "window start | mints so far $done_now | balance $(echo "$state" | awk '{print $2}') RH-ETH | price $(echo "$state" | awk '{print $3}')"
  $PY farm.py --shards "$SHARDS" --minutes "$WINDOW_MIN" --max-mints "$TARGET_MINTS" --slice 13 --key "$KEY" >> "$LOG" 2>&1
  # Modal workspace cap: stop cleanly instead of spinning (needs a budget raise on modal.com)
  if tail -40 "$LOG" | grep -q "exceeded its spend limit"; then
    log "Modal workspace spend limit hit — GPU unavailable. Raise the budget at modal.com or stop here."
    break
  fi
  sleep 4
done
log "supervisor exit"
