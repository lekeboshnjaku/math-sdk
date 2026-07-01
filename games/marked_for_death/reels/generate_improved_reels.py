#!/usr/bin/env python3
"""
generate_improved_reels.py

Option A implementation for Marked for Death reel improvement (Option 1).

Generates longer, weighted BR0.csv and FR0.csv with:
- 300 stops per reel
- Increased S frequency for natural FS hit rate of ~5-8% (P(>=3S) on 20 positions)
- Varied per reel
- Good mix for marked promotion
- Deterministic via seeds

These are TESTING REELS (not final production).

Usage:
  python reels/generate_improved_reels.py
  (overwrites BR0.csv and FR0.csv in this dir with new content)

Symbols kept: H1-H4, L1-L5, W, S  (exact match to game_config paytable + specials)
"""

import random
import os
from collections import Counter

LENGTH = 300
SYMBOLS = ["H1", "H2", "H3", "H4", "L1", "L2", "L3", "L4", "L5", "W", "S"]

def make_counts_balanced(reel_idx: int, is_base: bool) -> dict:
    """Return exact counts summing to LENGTH for the reel.
    Aggressive Phase 2 reel tuning (real distributions validation):
    - Clear reductions to Low symbols (esp L4/L5) on reels 2-3-4 to cut easy 3-symbol Low hits.
    - Noticeable Low -> High rebalance on middle reels.
    - S kept at reduced levels.
    Reels only - marked_prob and fs_reel3_marked_count untouched.
    """
    if is_base:
        # Base: aggressive Phase 2 reel tuning to drive base hit rate toward 28-28.5%
        # - S reduced
        # - Reels 2-3-4: previous Low->High + now targeted +Low/W for better small/medium win frequency in base
        #   (address bimodal: more consistent small/medium base wins vs 0x or FS big)
        base_s = [8, 9, 8, 9, 8][reel_idx]
        base_w = [22, 21, 23, 20, 22][reel_idx]
        base_h1 = [13, 12, 13, 12, 12][reel_idx]
        base_h2 = [17, 18, 17, 18, 17][reel_idx]
        base_h3 = [22, 21, 22, 21, 21][reel_idx]
        base_h4 = [28, 27, 28, 27, 28][reel_idx]
        base_l1 = [30, 31, 30, 31, 30][reel_idx]
        base_l2 = [34, 33, 34, 33, 34][reel_idx]
        base_l3 = [36, 37, 36, 37, 36][reel_idx]
        base_l4 = [38, 39, 38, 39, 38][reel_idx]
        base_l5 = [42, 41, 42, 41, 42][reel_idx]
        if reel_idx in (1, 2, 3):
            # Targeted tweak for Option A: boost Low + W on middle reels for more frequent small/medium base wins
            # (more 3L/4L small hits + wild-assisted wins), while keeping overall hit rate high but improving quality
            base_l5 += 6
            base_l4 += 4
            base_l2 += 3
            base_w += 3
            base_h4 -= 8
            base_h3 -= 8
        counts = {
            "S": base_s, "W": base_w,
            "H1": base_h1, "H2": base_h2, "H3": base_h3, "H4": base_h4,
            "L1": base_l1, "L2": base_l2, "L3": base_l3, "L4": base_l4, "L5": base_l5,
        }
    else:
        # Free Spins: keep S at current reduced level (slightly lower than previous)
        # Apply similar noticeable Low -> High rebalance on reels 2-3-4 for consistency
        fs_s = [13, 14, 13, 14, 13][reel_idx]
        fs_w = [26, 27, 25, 28, 27][reel_idx]
        fs_h1 = [15, 14, 15, 14, 15][reel_idx]
        fs_h2 = [21, 20, 21, 20, 21][reel_idx]
        fs_h3 = [25, 26, 25, 26, 25][reel_idx]
        fs_h4 = [30, 29, 30, 29, 30][reel_idx]
        fs_l1 = [26, 27, 26, 27, 26][reel_idx]
        fs_l2 = [30, 29, 30, 29, 30][reel_idx]
        fs_l3 = [32, 33, 32, 33, 32][reel_idx]
        fs_l4 = [33, 34, 33, 34, 33][reel_idx]
        fs_l5 = [40, 39, 40, 39, 40][reel_idx]
        if reel_idx in (1, 2, 3):
            # Larger visible shift on middle reels
            fs_l5 -= 5
            fs_l4 -= 4
            fs_h4 += 5
            fs_h3 += 4
        counts = {
            "S": fs_s, "W": fs_w,
            "H1": fs_h1, "H2": fs_h2, "H3": fs_h3, "H4": fs_h4,
            "L1": fs_l1, "L2": fs_l2, "L3": fs_l3, "L4": fs_l4, "L5": fs_l5,
        }

    # Enforce sum == LENGTH (fix rounding drift)
    s = sum(counts.values())
    if s != LENGTH:
        # Adjust most common low symbol
        diff = LENGTH - s
        counts["L5"] += diff
    assert sum(counts.values()) == LENGTH, f"Counts must sum to {LENGTH}"
    return counts


def generate_strip(counts: dict, seed: int) -> list[str]:
    """Build a strip list of exact length by creating pool + shuffle + light declump."""
    pool = []
    for sym, cnt in counts.items():
        pool.extend([sym] * cnt)
    assert len(pool) == LENGTH

    rng = random.Random(seed)
    rng.shuffle(pool)

    # Light declump pass: break runs of 4+ identical (esp for S/W/H)
    for _ in range(2):  # 2 passes
        i = 0
        while i < len(pool) - 3:
            if pool[i] == pool[i+1] == pool[i+2] == pool[i+3]:
                # swap the 4th with something different later
                for j in range(i+4, min(i+12, len(pool))):
                    if pool[j] != pool[i]:
                        pool[i+3], pool[j] = pool[j], pool[i+3]
                        break
            i += 1
    return pool


def write_csv(reel_strips: list[list[str]], out_path: str, name: str):
    """Write the 5-column transposed CSV (standard SDK format)."""
    num_stops = len(reel_strips[0])
    lines = []
    for pos in range(num_stops):
        row = ",".join(reel_strips[r][pos] for r in range(5))
        lines.append(row)
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    print(f"Wrote {name} -> {out_path} ({num_stops} stops x 5 reels)")


def analyze_strip(reel_strips: list[list[str]], label: str):
    print(f"\n=== {label} (improved) ===")
    print(f"Stops per reel: {[len(r) for r in reel_strips]}")
    total_s = 0
    for i, reel in enumerate(reel_strips):
        cnt = Counter(reel)
        tot = len(reel)
        s = cnt.get("S", 0)
        total_s += s
        pct_s = s / tot * 100
        print(f"  Reel {i}: S={s} ({pct_s:.1f}%)  W={cnt.get('W',0)}  "
              f"H1={cnt.get('H1',0)} H2={cnt.get('H2',0)} H3={cnt.get('H3',0)} H4={cnt.get('H4',0)}")
    print(f"Total S across reels: {total_s} (avg per reel {total_s/5:.1f})")
    # Quick expected trigger estimate
    p = (total_s / 5) / LENGTH
    # approx using binomial for 20 positions
    from math import comb
    def p_ge3(n=20, pp=p):
        return sum(comb(n,k) * (pp**k) * ((1-pp)**(n-k)) for k in range(3, n+1))
    print(f"Approx base draw P(>=3S) ~ {p_ge3()*100:.1f}% (every ~{1/p_ge3():.0f} spins)  [p_sym={p*100:.2f}%]")


def main():
    print("Marked for Death - Improved Reel Generator (for testing)")
    print("=" * 60)
    print("NOTE: These reels are for more realistic testing (Option 1).")
    print("      NOT production final. Tune further after mechanics + sims.\n")

    reels_dir = os.path.dirname(os.path.abspath(__file__))

    # Generate BR0
    br_strips = []
    for r in range(5):
        counts = make_counts_balanced(r, is_base=True)
        strip = generate_strip(counts, seed=42 + r * 1000)
        br_strips.append(strip)
    write_csv(br_strips, os.path.join(reels_dir, "BR0.csv"), "BR0.csv")
    analyze_strip(br_strips, "BR0 (base)")

    # Generate FR0
    fr_strips = []
    for r in range(5):
        counts = make_counts_balanced(r, is_base=False)
        strip = generate_strip(counts, seed=123 + r * 1000)
        fr_strips.append(strip)
    write_csv(fr_strips, os.path.join(reels_dir, "FR0.csv"), "FR0.csv")
    analyze_strip(fr_strips, "FR0 (freespin)")

    print("\nDone. Reels updated for better FS frequency and variety.")
    print("Next: verify in game_config, then run sims/books for hit rate / FS freq.")
    print("Remember to commit the generator script + new reels.")


if __name__ == "__main__":
    main()
