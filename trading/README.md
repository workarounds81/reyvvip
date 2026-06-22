# RCP1 BTC Battlefield — Automated Routine

## How it works

1. **GitHub Actions** triggers `btc_routine.py` every 4 hours (cron: `0 */4 * * *`)
2. The script fetches live BTC price + Fear & Greed Index
3. It checks Hyperliquid directly to detect any open position on the Battlefield wallet
4. **If position open** → monitors vs TP/SL levels → fires close signal if hit
5. **If flat** → sends the 6-point checklist to Claude AI → if all pass → fires entry signal to SIGNUM → logs state

## Required GitHub Secrets

Set these in **Settings → Secrets and variables → Actions**:

| Secret | Value |
|--------|-------|
| `SIGNUM_API_KEY` | Your SIGNUM API key (from SIGNUM dashboard) |
| `ANTHROPIC_API_KEY` | Your Anthropic API key |

## Changing the schedule

Edit `.github/workflows/btc-trading-routine.yml`, line with `cron:`:
- Every 4 hours: `0 */4 * * *`
- Every hour: `0 * * * *`

## Manual trigger

GitHub → Actions → "BTC Trading Routine" → **Run workflow**
Select mode: `auto` / `checklist-only` / `monitor-only`

## State file

`trading/position_state.json` — committed back to `main` after each run.
Tracks: direction, entry price, TP/SL levels, strategy code, open timestamp.

## Trade log

`trading/trade_log.md` — append-only log of every routine run, signal fired, and outcome.

## Strategy codes

| Code | Style | Order Size | SL | Notes |
|------|-------|-----------|-----|-------|
| SS | Set & Sleep (swing) | 20% | 1.5–2% | 3x leverage |
| AM | Ambush (trap play) | 30% | Beyond liq cluster | 5x, liq pocket setup |
| AGG | Aggressive (momentum) | 15% | 0.5–0.8% | 5x, breakout |
| AS | Asymmetric Scalp | 10% | 0.2–0.3% max | 5x-8x, sniper entry |

## Risk rules (hardcoded)
- Max 2% of Battlefield balance per trade (~$5 on $249.8)
- Never open second position while one is active
- Red folder (high-impact macro event within 4h) = hard gate, no entry
- Never widen stop, never average down
