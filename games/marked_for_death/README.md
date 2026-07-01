# marked-for-death

## Reels (Improved for Testing - 2026-06-30)

**Current reel files (as of this update):**

- `reels/BR0.csv`: Base game reels — **300 stops** per reel
- `reels/FR0.csv`: Free spin reels — **300 stops** per reel
- `reels/FRWCAP.csv`: (present, ~182 stops, **NOT YET INTEGRATED** into `game_config.py` distributions; contains H5 symbols which are invalid for current paytable/specials)

**Key improvements (Option A + Option 1):**
- Lengthened from stub 150 stops → 300 stops (good granularity, still practical)
- **Scatter (S) frequency dramatically reduced**:
  - BR0: ~2.3–2.7% per position (was 12%) → realistic natural FS trigger ~1/80 spins (binomial estimate on 20 positions)
  - FR0: ~4.7–5.3% (was 8.7%) → allows retriggers without being spammy
- Varied symbol weights per reel (previously every reel was an identical copy)
- Proportioned H1–H4 / L1–L5 / W / S to support:
  - Accepted base hit rate ~55-60% (Option B: rebalance RTP/volatility targets rather than force ~28%)
  - Marked promotion (L/H symbols abundant on reels 2/3-4) to feel impactful at the configured `marked_prob` rates
- Deterministic generation via `reels/generate_improved_reels.py` (seed-based, reproducible)
- **These are testing reels, not final production.** They will be further balanced using the optimization program + analyzer once cascades, marked promotion, persistent multiplier, and forced reel-3 mechanics are complete.

**Generation:**
```powershell
cd games/marked_for_death/reels
python generate_improved_reels.py
```

See also:
- `game_config.py` (reel loading + marked_prob + fs_triggers)
- `IMPLEMENTATION_MAPPING_v1.2.md`
- `Marked_for_Death_Math_Design_Document_v0.7.pdf`

**Symbols in use:** H1–H4 (high), L1–L5 (low), W (wild), S (scatter). No other symbols on these reels.
