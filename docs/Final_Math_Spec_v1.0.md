# Marked for Death — Final Math Specification v1.0

**Document status:** Official reference (Option B locked baseline)  
**Date:** 2026-07-01  
**Game ID:** `marked_for_death`  
**Validation basis:** 1,000,000-spin real-distribution simulation (`use_validation_distributions = False`, `fs_safety_cap = True`)

---

## 1. Game Overview

### Grid & Pay System

| Property | Value |
|----------|-------|
| Grid | 5 reels × 4 rows (with padding) |
| Pay system | 1,024 ways (left-to-right) |
| Symbols | H1–H4 (high), L1–L5 (low), W (wild), S (scatter) |
| Bet mode | `base` (cost = 1.0) |

### Targets & Limits

| Property | Value |
|----------|-------|
| **Target RTP** | **96.73%** |
| **Max win (wincap)** | **25,000× bet** |
| Volatility profile | **High** — hitty base with extreme FS ceiling |

### Design Philosophy

Marked for Death is built around a **bimodal payout identity**:

- **Base game:** Frequent positive outcomes (~69% base-win involvement) delivering small-to-large wins without requiring a feature. Designed to feel *hitty* and self-sufficient.
- **Free Spins:** Rare entry (~4% of spins) but dominant value delivery (~75% of total win mass). FS provides the **multiplier fantasy** — persistent global mult starting at ×2, marked-to-wild cascades, full reel-3 force, and retriggers driving ×100–×25,000 outcomes.

The Option B path explicitly accepts a **higher base hit rate (~55–70%)** rather than forcing a low ~28% hit, rebalancing RTP and volatility through FS contribution instead.

---

## 2. Locked Parameters

> **Do not change** `marked_prob`, `fs_reel3_marked_count`, or core event-ordering rules for this baseline without a versioned spec update.

### Marked Promotion Probabilities

| Context | Initial (reels 2–4 landing) | Drop (post-tumble) |
|---------|------------------------------|---------------------|
| **Base** | 0.15 | 0.045 |
| **Free Spins** | 0.13 | 0.035 |

Applied on reels 2, 3, and 4 on initial board landing and after each tumble drop.

### Free Spins Constants

| Parameter | Value |
|-----------|-------|
| `fs_reel3_marked_count` | **4** (full vertical Marked stack on reel 3 every FS spin) |
| FS round start multiplier | **×2** (emitted after first paid FS win level) |
| Multiplier growth | **+1** after every paid cascade (carries across FS spins; never resets mid-round) |

### Wincap & Safety (Validation)

| Parameter | Value |
|-----------|-------|
| Wincap | 25,000× bet |
| FS safety cap (validation only) | 400 FS spins / ×300 global multiplier |
| Safety cap status | **Active** during 1M validation (`fs_safety_cap = True`) |

### Reel Strip Summary

| Strip | File | Stops/reel | Notes |
|-------|------|------------|-------|
| Base | `reels/BR0.csv` | 300 | Scatter ~2.5–3% per position; varied weights reels 2–4 |
| Free Spins | `reels/FR0.csv` | 300 | Scatter ~4.5–5.3%; supports controlled retriggers |
| Wincap (unused) | `reels/FRWCAP.csv` | ~182 | Present; **not integrated** into distributions |

Reels are **testing-grade** (generated via `reels/generate_improved_reels.py`). Production strips expected after optimization pass.

### Betmode Distribution Quotas (Real)

| Criteria | Quota | Purpose |
|----------|-------|---------|
| `wincap` | 0.1% | Force max-win path sampling |
| `freegame` | 10% | Force FS entry paths |
| `0` | 40% | Zero-win fence |
| `basegame` | 50% | Natural base play |

---

## 3. Core Mechanics

### 3.1 Marked Promotion & Conversion

1. **Promotion:** On initial landing and after each tumble, eligible positions on reels 2–4 may receive the Marked attribute per `marked_prob`.
2. **Conversion:** After win events are emitted for a paid cascade level, marked symbols convert to **Wild** *before* the corresponding `tumbleBoard` event.
3. **Timing (book event order):**  
   `reveal` → `winInfo` / `updateTumbleWin` → `updateGlobalMult` → *(internal convert)* → `tumbleBoard` → …

Marked conversion is **silent in books** (no dedicated event type); validated via inspector cascade-timing checks.

### 3.2 Persistent Global Multiplier

| Phase | Rule |
|-------|------|
| **Base game** | Starts at ×1; +1 after each paid cascade within the spin |
| **FS round entry** | Resets to ×2 for the new round (value set at entry; `updateGlobalMult(2)` deferred until first FS paid win) |
| **Within FS round** | +1 after each paid cascade; **never resets** between FS spins |
| **Retrigger** | Adds spins only; multiplier unchanged |

### 3.3 Free Spins — Trigger, Retrigger, Reel 3 Force

**Triggers (base game scatter count → spins awarded):**

| Scatters | Base spins | FS retriggers |
|----------|------------|---------------|
| 3 | 12 | 8 |
| 4 | 14 | 10 |
| 5 | 16 | 12 |
| 6+ | +2 per additional scatter | +2 per additional scatter |

**Reel 3 force:** At the start of **every** FS spin (including after retriggers), reel 3 is fully populated with Marked symbols (`fs_reel3_marked_count = 4`), then normal promotion rules apply on reels 2 and 4.

**Anticipation:** Base = 2 scatters visible; FS = 1 scatter visible.

### 3.4 Cascades / Tumbles

- Wins evaluated on ways; winning symbols removed; gravity refill; repeat while wins exist.
- Scatters typically persist through tumbles (not removed), enabling retrigger chains in long FS.
- Each paid cascade level: evaluate → emit wins → update global mult → convert marked → tumble.

---

## 4. Validation Status

### 1M Real-Distribution Run

| Item | Result |
|------|--------|
| **Spin count** | 1,000,000 |
| **Mode** | Real distributions, `fs_safety_cap = True` |
| **Books output** | `library/publish_files/books_base.jsonl.zst` (1,000,000 entries, ~908 MB compressed) |
| **Lookup table** | `library/lookup_tables/lookUpTable_base.csv` (1,000,000 rows) |
| **Runtime** | ~397 seconds (8 threads, compressed batching) |
| **Harness thread RTP (avg)** | ~1,060% total (~267% base + ~793% FS components) |

### Inspector Status

| Check | Result |
|-------|--------|
| `inspect_books.py` (1M streamed) | **0 issues** across 1,000,000 spins |
| Marked conversion windows | 4,709,031 / 4,709,031 OK |
| Event ordering | All clean (Priority 1 rules) |

### Validation Configuration Notes

- Safety cap (400 spins / ×300 mult) was **enabled** — truncates pathological FS monsters; 3 rounds (0.007%) hit ≥400 FS reveals in 1M sample.
- Published book boards expose symbol `name` only; reel-3 Marked state is **not observable** in book JSON (server-side force confirmed in code).

---

## 5. Key Performance Metrics (1M Run)

*All payout figures in **× bet** unless noted. Source: `lookUpTableSegmented_base.csv` + streamed book analysis.*

### 5.1 Base Game Performance

| Metric | Value |
|--------|-------|
| **0× rate (all spins)** | **31.36%** |
| **Base win involvement** (`baseGameWins > 0`) | **68.64%** |
| **Positive pure-base spins** | 64.63% of all spins |
| **Base ≥50× without FS** | **48.60%** of all spins |
| **Base ≥200× without FS** | 30.48% of all spins |

**Base satisfaction (positive pure-base only, n = 646,269):**

| Category | % of positive base |
|----------|-------------------|
| Small (<50×) | 24.81% |
| Medium (50–200×) | 28.02% |
| Big (200×+) | 47.17% |

### 5.2 Free Spins Performance

| Metric | Value |
|--------|-------|
| **FS-involved spins** | **40,106 (4.01%)** |
| **Mean FS round length** | **94.9** freegame reveals |
| **Median FS round length** | **92.0** reveals |
| **P90 FS round length** | 182 reveals |
| Safety cap hits (≥400 reveals) | 0.007% (3 rounds) |

**FS length distribution:**

| Band | % of FS rounds |
|------|----------------|
| ≤20 reveals | 18.3% |
| 21–60 | 16.9% |
| 61–120 | 31.5% |
| 120+ | 33.2% |

### 5.3 RTP / Win Mass Split

| Source | % of total win mass |
|--------|---------------------|
| **Base game wins** | **25.22%** |
| **Free Spins wins** | **74.78%** |
| Wins ≥100× (mass) | 99.17% |
| Wins ≥500× (mass) | 93.00% |

| Segment | Mean payout | Median payout |
|---------|-------------|---------------|
| Overall | 1,060.21× | 63.00× |
| Pure base | 253.10× | 53.00× |
| FS-involved | 20,377.49× | 25,166.00× |

> **Note:** Observed mean return (~1,060× bet/spin aggregate) exceeds the 96.73% design target. RTP calibration via optimization/reel balancing is flagged as future work (see §7).

### 5.4 FS Multiplier Distribution

| Threshold (max mult in FS) | % of FS rounds |
|----------------------------|----------------|
| ×5+ | 100.00% |
| ×10+ | 99.64% |
| ×20+ | 93.44% |
| ×50+ | 76.05% |
| **×100+** | **59.91%** |

**Final multiplier buckets (FS round end):**

| Bucket | % of FS rounds |
|--------|----------------|
| ×2–5 | 0.01% |
| ×6–10 | 0.57% |
| ×11–20 | 6.95% |
| ×21–50 | 16.78% |
| ×51–100 | 16.32% |
| **×100+** | **59.37%** |

| Growth metric | Value |
|---------------|-------|
| Mean final mult | ×110.33 |
| Median final mult | ×117.0 |
| Mean growth from ×2 start | **+108.33** |
| Mean paid-cascade +1 steps | 108.3 |

Cascade count correlates strongly with mult growth (r = 0.905); FS round length r = 0.963.

### 5.5 Payout Distribution Shape

**Overall win buckets (count %):**

| Bucket | % spins | % win mass |
|--------|---------|------------|
| 0× | 31.36% | 0.00% |
| <10× | 4.64% | 0.02% |
| 10–50× | 11.39% | 0.28% |
| 50–100× | 7.69% | 0.52% |
| 100–500× | 25.94% | 6.18% |
| **500×+** | **18.98%** | **93.00%** |

**Bimodality indicators:**

| Indicator | Value |
|-----------|-------|
| Zero-win spike | 31.36% at 0× |
| High-win spike | 18.98% at 500×+ |
| FS rounds landing 500×+ | 99.98% |
| Low-band mass (<50×) | 0.30% of win value |
| High-band mass (500×+) | 93.00% of win value |
| Mean / median gap (overall) | 16.8× (extreme right skew) |

---

## 6. Game Identity & Design Notes

### Payout Curve Shape

The game exhibits a **strongly bimodal** distribution:

1. **Low mode (~31%):** Zero-win dead spins.
2. **Base-positive mode (~65%):** Mostly 10×–500× outcomes; median pure-base payout ≈ 53×.
3. **FS mega-win mode (~4% of spins, ~93% of mass):** Almost exclusively 500×+ totals, clustering near wincap.

The “middle” (50–100× count band) is thin relative to the tails.

### Role of Base vs Free Spins

| Role | Base Game | Free Spins |
|------|-----------|------------|
| **Frequency** | Every spin | ~4% of spins |
| **Player feel** | Hitty, self-rewarding | Chase / jackpot fantasy |
| **Win mass** | ~25% | ~75% |
| **Big-win driver** | Can deliver 200×–25,000× alone (30% of spins ≥200× base-only) | Delivers ×100+ mult in 60% of rounds |
| **Mechanical identity** | Marked spawn + convert + modest mult growth | ×2 start, persistent carry, reel-3 force, retrigger chains |

### Multiplier Fantasy Delivery

FS is the primary vehicle for the **×100+ multiplier fantasy**:

- Persistent ×2 start → +1 per paid cascade → long rounds accumulate 100+ steps routinely.
- Full reel-3 Marked force ensures wild-capable center reel every FS spin.
- Marked conversions (silent, cascade-driven) sustain tumble chains that feed mult growth.
- Retriggers extend round length without resetting mult, enabling wincap-adjacent outcomes.

---

## 7. Open Items / Future Work

| Item | Priority | Notes |
|------|----------|-------|
| **RTP calibration to 96.73%** | High | 1M run mean return ~1,060× bet/spin — significant overshoot vs target; requires optimization / reel or paytable tuning |
| **Disable safety cap for production sims** | High | Re-run 1M+ with `fs_safety_cap = False` before certifying max-win and tail frequencies |
| **RTP convergence testing** | High | Confirm stability at 10M+ spins with cap off |
| **Max-win frequency study** | Medium | Characterize 25,000× hit rate and path distribution with cap disabled |
| **Production reel strips** | Medium | Replace BR0/FR0 testing reels; integrate reviewed FRWCAP if needed |
| **Optimization program pass** | Medium | Use locked mechanics + fence targets from `game_optimization.py` |
| **Book observability** | Low | Consider exposing Marked attribute in published boards for QA (currently name-only) |
| **Stat sheet / PAR integration** | Low | Fix analytics pipeline for automated PAR generation post-sim |

---

## Appendix: Paytable Reference

| Symbol | 5-way | 4-way | 3-way |
|--------|-------|-------|-------|
| H1 | 500 | 100 | 20 |
| H2 | 300 | 80 | 15 |
| H3 | 200 | 50 | 12 |
| H4 | 150 | 40 | 10 |
| L1 | 80 | 20 | 5 |
| L2 | 60 | 15 | 4 |
| L3 | 50 | 12 | 3 |
| L4 | 40 | 10 | 3 |
| L5 | 30 | 8 | 2 |

---

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-07-01 | Math SDK / Option B baseline | Initial locked spec from 1M validation |

**Related files:**
- `games/marked_for_death/game_config.py`
- `games/marked_for_death/gamestate.py`
- `docs/Option_B_Baseline_Summary.md`
- `games/marked_for_death/library/publish_files/books_base.jsonl.zst`
- `games/marked_for_death/library/lookup_tables/lookUpTableSegmented_base.csv`