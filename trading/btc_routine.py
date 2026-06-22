"""
RCP1 BTC Battlefield — Automated Trading Routine
Bot: kuETUfIT | Exchange: Hyperliquid Perpetuals | Pair: BTC/USDC

Runs every 4 hours via GitHub Actions.
Reads/writes trading/position_state.json for state persistence.
Fires signals via SIGNUM REST API (mirrors the SIGNUM MCP signal format).
"""

import json
import os
import sys
import datetime
import requests
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

BOT_PUBLIC_CODE   = "kuETUfIT"
BOT_NUMERIC_ID    = 26085
TICKER            = "BTCUSDC"
SIGNUM_WEBHOOK    = "https://signals.signum.money/trading"
SIGNUM_API_KEY    = os.environ.get("SIGNUM_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
RUN_MODE          = os.environ.get("RUN_MODE", "auto")   # auto | checklist-only | monitor-only

BATTLEFIELD_BALANCE = 249.8   # USDC — update if balance changes
MAX_RISK_PCT        = 0.02    # 2% max risk per trade

STATE_FILE = Path(__file__).parent / "position_state.json"
LOG_FILE   = Path(__file__).parent / "trade_log.md"

# ── Utility ───────────────────────────────────────────────────────────────────

def now_utc() -> str:
    return datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

def log(msg: str, also_print: bool = True):
    entry = f"[{now_utc()}] {msg}"
    if also_print:
        print(entry)
    with open(LOG_FILE, "a") as f:
        f.write(entry + "\n")

def load_state() -> dict:
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"open": False}

def save_state(state: dict):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

# ── SIGNUM Signal ─────────────────────────────────────────────────────────────

def fire_signal(action: str, order_size: str, position_size: str, reason: str = ""):
    payload = {
        "action":        action,
        "ticker":        TICKER,
        "order_size":    order_size,
        "position_size": position_size,
        "schema":        "2",
        "bot_id":        BOT_PUBLIC_CODE,
    }
    log(f"SIGNAL → action={action} size={order_size} pos={position_size} | {reason}")
    if not SIGNUM_API_KEY:
        log("WARNING: SIGNUM_API_KEY not set — signal NOT sent (dry run)")
        return False
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {SIGNUM_API_KEY}"}
    try:
        r = requests.post(SIGNUM_WEBHOOK, json=payload, headers=headers, timeout=10)
        log(f"SIGNUM response: {r.status_code} {r.text[:200]}")
        return r.status_code in (200, 201, 202)
    except Exception as e:
        log(f"SIGNUM request failed: {e}")
        return False

def close_position(state: dict, reason: str):
    direction = state.get("direction", "long")
    action    = "sell" if direction == "long" else "buy"
    ok = fire_signal(action, "100%", "0", reason)
    if ok:
        entry  = state.get("entry_price", "?")
        strategy = state.get("strategy", "?")
        log(f"CLOSED {direction.upper()} | strategy={strategy} | entry={entry} | reason={reason}")
        save_state({"open": False, "last_close": now_utc(), "last_close_reason": reason})
    return ok

# ── Data Fetchers ─────────────────────────────────────────────────────────────

def fetch_btc_price() -> float | None:
    """CoinGecko simple price (no key needed)."""
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": "bitcoin", "vs_currencies": "usd"},
            timeout=8,
        )
        return float(r.json()["bitcoin"]["usd"])
    except Exception as e:
        log(f"BTC price fetch failed: {e}")
        return None

def fetch_fear_greed() -> dict | None:
    try:
        r = requests.get("https://api.alternative.me/fng/", timeout=8)
        d = r.json()["data"][0]
        return {"value": int(d["value"]), "classification": d["value_classification"]}
    except Exception as e:
        log(f"Fear & Greed fetch failed: {e}")
        return None

def fetch_hyperliquid_position() -> dict | None:
    """
    Check Hyperliquid for open position on the Battlefield wallet.
    Uses the public Hyperliquid info endpoint (no auth needed for read).
    """
    wallet = "0xb20802c133FEE911FB6Efc3bd60555Cb12B7Dcf0"
    try:
        r = requests.post(
            "https://api.hyperliquid.xyz/info",
            json={"type": "clearinghouseState", "user": wallet},
            timeout=10,
        )
        data = r.json()
        positions = data.get("assetPositions", [])
        for pos in positions:
            p = pos.get("position", {})
            if p.get("coin") == "BTC" and float(p.get("szi", 0)) != 0:
                return {
                    "coin":        p["coin"],
                    "size":        float(p["szi"]),
                    "entry_price": float(p.get("entryPx", 0)),
                    "direction":   "long" if float(p["szi"]) > 0 else "short",
                    "unrealised_pnl": float(p.get("unrealizedPnl", 0)),
                }
        return None   # no open BTC position
    except Exception as e:
        log(f"Hyperliquid position check failed: {e}")
        return None

# ── Claude AI Analysis (6-point checklist) ────────────────────────────────────

CHECKLIST_PROMPT = """You are the trading analyst for RCP1 BTC Battlefield, a BTC/USDC perpetual futures bot on Hyperliquid (5x leverage, 249.8 USDC collateral).

Today is {date}. Current BTC price: ${btc_price:,.0f}. Fear & Greed Index: {fg_value} ({fg_class}).

Run the full 6-point entry checklist below. For each point, use your knowledge and available data to make a judgment call. Be concise but rigorous.

## CHECKLIST

### Point 1 — TA
Assess BTC/USDC price structure on 4H and Daily timeframes. Identify trend direction, key S/R levels, price action signals (HH/HL or LH/LL). Is price in clear trend territory or no-man's land?

### Point 2 — SENTIMENT
Fear & Greed = {fg_value} ({fg_class}). Assess BTC dominance direction, DXY posture (risk-on vs risk-off), whether BTC is leading or lagging alts.

### Point 3 — NEWS
What are the major BTC/macro headlines right now? Any exchange issues, regulatory actions, ETF flow data, or Fed-related events that could cause sudden volatility?

### Point 4 — CALENDAR (HARD GATE)
Are there any HIGH-IMPACT economic events (FOMC, CPI, NFP, PPI, GDP, Fed speeches) in the next 4 hours? If YES → automatic FAIL, no exceptions.

### Point 5 — HEATMAP
Based on current price ${btc_price:,.0f}, where are the likely major liquidation clusters? Is there a large liq pocket in or against the intended trade direction?

### Point 6 — PSYCHOLOGY
Is funding rate positive (market long-heavy) or negative (short-heavy)? Is OI rising or falling? Is the crowd positioned with or against the likely trade direction?

---

## OUTPUT FORMAT

Respond ONLY with valid JSON, no commentary outside the JSON block:

```json
{{
  "point1_ta":          {{"pass": true/false, "direction": "long"/"short"/"none", "reason": "..."}},
  "point2_sentiment":   {{"pass": true/false, "reason": "..."}},
  "point3_news":        {{"pass": true/false, "reason": "..."}},
  "point4_calendar":    {{"pass": true/false, "reason": "..."}},
  "point5_heatmap":     {{"pass": true/false, "liq_above": "...", "liq_below": "...", "reason": "..."}},
  "point6_psychology":  {{"pass": true/false, "funding_bias": "long-heavy"/"short-heavy"/"neutral", "reason": "..."}},
  "all_pass":           true/false,
  "trade_direction":    "long"/"short"/"none",
  "strategy_code":      "SS"/"AM"/"AGG"/"AS"/"none",
  "strategy_reason":    "...",
  "entry_notes":        "...",
  "tp_level":           null or number,
  "sl_level":           null or number
}}
```
"""

def run_claude_checklist(btc_price: float, fg: dict) -> dict | None:
    if not ANTHROPIC_API_KEY:
        log("WARNING: ANTHROPIC_API_KEY not set — cannot run Claude checklist")
        return None

    prompt = CHECKLIST_PROMPT.format(
        date=now_utc(),
        btc_price=btc_price,
        fg_value=fg["value"],
        fg_class=fg["classification"],
    )

    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key":         ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type":      "application/json",
            },
            json={
                "model":      "claude-opus-4-8",
                "max_tokens": 1500,
                "messages":   [{"role": "user", "content": prompt}],
            },
            timeout=60,
        )
        text = r.json()["content"][0]["text"]
        # Extract JSON block
        start = text.find("{")
        end   = text.rfind("}") + 1
        if start == -1:
            log(f"Claude returned no JSON: {text[:300]}")
            return None
        return json.loads(text[start:end])
    except Exception as e:
        log(f"Claude checklist failed: {e}")
        return None

# ── Strategy → Signal Parameters ─────────────────────────────────────────────

STRATEGY_PARAMS = {
    #            order_size  leverage_note
    "SS":  dict(order_size="20%",  note="Swing — 3x override, wide SL"),
    "AM":  dict(order_size="30%",  note="Ambush — 5x, liq cluster target"),
    "AGG": dict(order_size="15%",  note="Momentum scalp — 5x, tight SL"),
    "AS":  dict(order_size="10%",  note="Sniper — 5x-8x, 0.2-0.3% SL"),
}

# ── Main Flows ────────────────────────────────────────────────────────────────

def run_monitoring(state: dict, btc_price: float):
    direction  = state.get("direction", "long")
    tp         = state.get("tp_level")
    sl         = state.get("sl_level")
    entry      = state.get("entry_price", 0)

    log(f"MONITORING | {direction.upper()} | entry={entry} | tp={tp} | sl={sl} | now={btc_price:,.2f}")

    if tp and ((direction == "long" and btc_price >= tp) or
               (direction == "short" and btc_price <= tp)):
        close_position(state, f"TP HIT @ {btc_price:,.2f} (target was {tp})")
        return

    if sl and ((direction == "long" and btc_price <= sl) or
               (direction == "short" and btc_price >= sl)):
        close_position(state, f"SL HIT @ {btc_price:,.2f} (stop was {sl})")
        return

    log(f"Position open — no TP/SL trigger — continuing to monitor")

def run_checklist_and_entry(btc_price: float, fg: dict):
    log(f"CHECKLIST START | BTC={btc_price:,.2f} | F&G={fg['value']} ({fg['classification']})")

    result = run_claude_checklist(btc_price, fg)
    if result is None:
        log("NO TRADE — checklist could not complete (Claude unavailable)")
        return

    # Log each point
    points = ["point1_ta","point2_sentiment","point3_news","point4_calendar","point5_heatmap","point6_psychology"]
    for p in points:
        d = result.get(p, {})
        status = "✓ PASS" if d.get("pass") else "✗ FAIL"
        log(f"  {p}: {status} — {d.get('reason','')}")

    if not result.get("all_pass"):
        failed = [p for p in points if not result.get(p, {}).get("pass")]
        log(f"NO TRADE — failed points: {', '.join(failed)}")
        return

    direction = result.get("trade_direction", "none")
    strategy  = result.get("strategy_code", "none")

    if direction == "none" or strategy == "none":
        log("NO TRADE — all points passed but no clear direction or strategy assigned")
        return

    params     = STRATEGY_PARAMS.get(strategy, STRATEGY_PARAMS["SS"])
    order_size = params["order_size"]
    pos_size   = "1" if direction == "long" else "-1"
    action     = "buy"  if direction == "long" else "sell"
    tp         = result.get("tp_level")
    sl         = result.get("sl_level")

    log(f"ENTRY | {direction.upper()} | strategy={strategy} | size={order_size} | TP={tp} | SL={sl} | {params['note']}")
    log(f"  Notes: {result.get('entry_notes','')}")

    ok = fire_signal(action, order_size, pos_size, f"{strategy} {direction}")
    if ok:
        save_state({
            "open":        True,
            "direction":   direction,
            "entry_price": btc_price,
            "strategy":    strategy,
            "order_size":  order_size,
            "tp_level":    tp,
            "sl_level":    sl,
            "opened_at":   now_utc(),
        })
        log(f"POSITION OPENED ✓ | {strategy} {direction.upper()} @ {btc_price:,.2f}")
    else:
        log("ENTRY SIGNAL FAILED — state not updated")

# ── Entry Point ───────────────────────────────────────────────────────────────

def main():
    log("=" * 60)
    log(f"RCP1 BTC BATTLEFIELD ROUTINE | mode={RUN_MODE}")

    # ── Fetch live data ──
    btc_price = fetch_btc_price()
    if btc_price is None:
        log("ABORT — could not fetch BTC price")
        sys.exit(1)
    log(f"BTC price: ${btc_price:,.2f}")

    fg = fetch_fear_greed()
    if fg is None:
        fg = {"value": 50, "classification": "Neutral (fetch failed)"}
    log(f"Fear & Greed: {fg['value']} — {fg['classification']}")

    # ── Check actual Hyperliquid position ──
    hl_pos = fetch_hyperliquid_position()
    state  = load_state()

    if hl_pos:
        log(f"HYPERLIQUID: open {hl_pos['direction'].upper()} {hl_pos['size']} BTC @ entry {hl_pos['entry_price']:.2f} | uPnL {hl_pos['unrealised_pnl']:.2f}")
        # Sync state if we detect a live position not recorded locally
        if not state.get("open"):
            log("State mismatch: HL has open position but local state says closed — syncing")
            state = {
                "open":        True,
                "direction":   hl_pos["direction"],
                "entry_price": hl_pos["entry_price"],
                "strategy":    state.get("strategy", "unknown"),
                "tp_level":    state.get("tp_level"),
                "sl_level":    state.get("sl_level"),
                "opened_at":   state.get("opened_at", now_utc()),
            }
            save_state(state)

    if RUN_MODE == "checklist-only":
        btc_price_val = btc_price
        fg_val = fg
        run_checklist_and_entry(btc_price_val, fg_val)
        return

    if RUN_MODE == "monitor-only":
        if state.get("open") or hl_pos:
            run_monitoring(state if state.get("open") else {
                "direction":   hl_pos["direction"],
                "entry_price": hl_pos["entry_price"],
                "tp_level":    state.get("tp_level"),
                "sl_level":    state.get("sl_level"),
            }, btc_price)
        else:
            log("No open position to monitor")
        return

    # ── AUTO mode: monitor first, else checklist ──
    if state.get("open") or hl_pos:
        effective_state = state if state.get("open") else {
            "direction":   hl_pos["direction"],
            "entry_price": hl_pos["entry_price"],
            "tp_level":    state.get("tp_level"),
            "sl_level":    state.get("sl_level"),
        }
        run_monitoring(effective_state, btc_price)
    else:
        run_checklist_and_entry(btc_price, fg)

    log("ROUTINE COMPLETE")
    log("=" * 60)

if __name__ == "__main__":
    main()
