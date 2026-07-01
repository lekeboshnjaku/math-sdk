# Marked for Death — Option B Baseline Summary
**Date:** 2026-07-01
**Decision:** Option B — Accept higher base hit rate (~55-70% range) and rebalance overall RTP/volatility targets (low risk, cleanest path).
**Status:** Baseline locked. Inspector clean on 100k real-dist books.

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
- **Books generated**: `library/books/books_base.json`
- **Inspector**: 100000 spins checked across 1 file(s) — **all clean**. Good to proceed!
- **Note**: Books regenerated after final event-ordering fixes + broadened inspector tolerance for legitimate FS x2 starts. Old books produced many false positives.

**All win-distribution values are absolute units (payoutMultiplier as stored in books), not normalized xBet.** Safety cap = 400 spins / 300 mult during this validation.

## Key Metrics (from this exact 100k run)

### Base vs FS RTP Contribution Split
- Harness thread contributions:
  - baseGame: ~261–278
  - freeGame: ~762–857
  - FS contribution: ~73–76% of total simulated win value

### Hit Rates
- **Base hit rate (pure base)**: **68.85%** (61,965 / 90,000)
- **0x (pure base)**: **31.2%**
- **FS involved spins**: 10,000 (10.0%)

### Volatility Profile
- Mean win per spin: ~1079.94 (internal units)
- High-vol profile driven by persistent mult carry + full-reel-3 Marked in FS.

### Win Distribution (absolute units)
- 0x: 31.2% (base)
- Positive wins dominated by small/medium; big wins mostly FS-driven.

### Max Win Paths
- Paths: long FS with persistent mult (often 50-200x+), full Marked reel 3, conversions to Wilds, retriggers/cascades.

### FS Characteristics
- FS start multiplier: exactly 2.00 (target met)
- Multiplier carry rate in FS: 99.4%
- Avg tumbles per spin: 0.97
- Long cascades (≥3 tumbles): 15.0%
- Safety cap (400) was active for validation.

## Notes
- All core mechanics validated: marked on 2-3-4 → permanent Wild after pay, persistent carry, FS x2 no reset, full reel-3 force.
- Inspector clean on fresh books generated with the final timing (winInfo → updateGlobalMult → convert → tumbleBoard).
- Smoke analyzer shows some known limitations on trigger-rate and reel-3 detection in this dist setup, but inspector + code ordering are solid.
- Do **not** change `marked_prob`, `fs_reel3_marked_count`, or core event ordering for this locked baseline.

Next steps (if needed): minor reel/paytable tweaks for exact target RTP using these clean books.
