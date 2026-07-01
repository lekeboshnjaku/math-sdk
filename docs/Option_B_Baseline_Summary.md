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
- **Mode**: Real distributions (use_validation_distributions = False), fs_safety_cap = True
- **Books generated**: library/books/books_base.json
- **Inspector**: Clean (0 issues across 100k spins). Marked conversion windows OK.
- **Cascade activity** (smoke): Avg tumbles ~0.98/spin, long cascades ~15.1%. FS carry ~99.4%.

**Note on win distribution buckets**: Values are in absolute units (payoutMultiplier as stored in books), **not normalized xBet**. Wincap = 2,500,000 units.

## Key Metrics

### Base vs FS RTP Contribution Split
- From harness thread contributions (100k run):
  - Average baseGame: ~267.7
  - Average freeGame: ~812.2
  - **Base ~24.8%**, **FS ~75.2%** of simulated win value.
- From book win sums (proportional):
  - Base ~22-25% of total win value
  - FS ~75-78% of total win value
- **Note**: FS remains the dominant RTP/volatility driver.

### Hit Rates
- Pure basegame-only spins: ~96,000 (scaled)
- **Base hit rate (pure base)**: **~67-68%** (consistent with detailed 25k analysis at 67.8%)
- FS involved spins: ~4.0-4.2% (low/controlled)

### Volatility Profile
- Mean win per spin: ~107,635 units
- Std dev: ~430,560
- Coeff of variation: ~4.0 (high)
- Profile: Hitty base + explosive FS via Marked conversions, reel-3 force, and mult carry.

### Win Distribution (payoutMultiplier buckets)
- 0x: ~31%
- Small (<10k units): ~24%
- Medium (10k–99k units): ~35%
- Big (≥100k units): ~10%

**Base win quality distribution**: Among positive base-only wins, ~37% small, ~54% medium, ~9% big (majority satisfying small/medium in base; big wins predominantly FS-driven).

**Note**: Buckets in absolute units (not normalized xBet).

### Max Win Paths
- Max seen: **2,500,000** (wincap)
- Paths: Long FS with persistent mult (often 50-200x+), full Marked reel 3, conversions to Wilds, retriggers/cascades.

### FS Characteristics
- Avg executed length: ~90-100
- Median: ~90-94
- Max: 400 (**safety cap**)
- Safety cap hits: low percentage (in 25k samples small % hit 400; 100k full count similar based on FS trigger rate)
