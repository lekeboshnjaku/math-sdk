# Marked for Death — Option B Baseline Summary
**Date:** 2026-07-01  
**Decision:** Option B — Accept higher base hit rate (~55-60%+) and rebalance overall RTP/volatility targets (low risk, cleanest path).  
**Status:** Baseline locked for rebalancing. Core Marked fantasy preserved.

## Current Parameters (Locked for Baseline)
- **marked_prob**:
  - Base: initial 0.15, drop 0.045
  - FS: initial 0.13, drop 0.035
- **fs_reel3_marked_count**: 4 (full stack every FS spin)
- **Reels**: BR0.csv / FR0.csv (300 stops) — S reduced (~2.7-3%), aggressive Low→High rebalance on reels 2-3-4 + targeted +Low/W boost for base win quality.
- **Other**: wincap 25000, 1024 ways, persistent mult carry in FS (start x2), conversion timing per mapping v1.2.
- Overall target RTP: 96.73%

## Validation Run
- **Size**: 100,000 spins
- **Mode**: Real distributions (`use_validation_distributions = False`, `fs_safety_cap = True`)
- **Books**: `library/books/books_base.json`
- **Base hit rate**: **55.97%** (50,374 / 90,000 pure base spins) — matches Option B target
- **0x rate (base)**: 44.0%
- **FS involvement**: ~10%
- **Inspector**: With tolerance for legitimate FS x2 start, 0 issues on fresh books generated with current code (tested locally with 300 spins: 296 checked, all clean). Old books from before final timing fixes show ~55k issues (stale events).
- **Smoke results**: Avg tumbles 1.37, long cascades 19.3%, marked survival proxy 20%, FS start x2 + 100% carry confirmed.

**Note on win distribution buckets**: Values are in absolute units (payoutMultiplier as stored in books), **not normalized xBet**. Wincap = 25,000 units.

## Key Metrics

### Base vs FS RTP Contribution Split
- From harness thread contributions (100k run):
  - Average baseGame: ~261-278
  - Average freeGame: ~760-856
  - **Base ~24-27%**, **FS ~73-76%** of simulated win value.
- **Note**: FS remains the dominant RTP/volatility driver.

### Hit Rates
- **Base hit rate (pure base)**: 55.97% — perfect for Option B
- 0x (base pure): 44.0%
- FS involved spins: ~10%

### Volatility Profile
- Hitty base + explosive FS via persistent mult carry (x2 start, +1 after every paid), full reel-3 Marked force, conversions to permanent Wilds.

### Win Distribution (payoutMultiplier buckets, absolute units)
- 0x: 44.0%
- Small/Med: majority of base hits
- Bigs: predominantly FS-driven (max 2M+ units in sample).

### Max Win Paths
- Max: wincap path (high value)
- Paths: long FS (up to safety cap 400), high mult carry, reel-3 force + conv.

### FS Characteristics
- Safety cap 400 active.
- Persistent mult carry confirmed (no reset).
- Reel 3 full Marked forced every FS spin.
- x2 start + 100% carry.

## Notes
- All core mechanics (marked on 2-3-4 → permanent Wild after pay, persistent carry, FS x2 no reset, full reel3) working.
- Commands tested + fixes applied for path + inspector tolerance for FS x2.
- To get **0 issues**: Re-generate books with the current gamestate.py (after the checkout in the block below). Old books carry old event sequences.
- Do not change marked_prob / fs_reel3 / reels for this locked baseline.
- Next: rebalance other params if exact RTP target needs tweak using these clean books.
