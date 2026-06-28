#!/usr/bin/env python3
"""
analyze_smoke.py

Lightweight analyzer for smoke test books of Marked for Death.
Verifies core mechanics implemented in Slices 1-4.

Usage:
    python analyze_smoke.py games/marked_for_death/library/books

    (or any folder containing books_base.jsonl, books_base.json, or compressed variants)

It performs fast checks on:
- FS trigger rate
- FS multiplier start at x2 and carry/growth
- Reel 3 full Marked forcing at start of every FS spin
- Marked -> Wild conversion rate (via survival in tumbles)
- Cascade activity (avg tumbles, long cascades)
- Basic sanity (event counts, win range)

Keeps loading and checks simple and modular.
"""

import argparse
import json
import os
import glob
from collections import defaultdict
import sys

def load_books(folder_path: str):
    """Load all books from a folder. Handles .jsonl, .json, and optional .zst."""
    books = []
    patterns = ["*books*.jsonl", "*books*.json", "*books*.jsonl.zst", "*books*.jsonl.zstd"]
    found_files = []
    for pat in patterns:
        found_files.extend(glob.glob(os.path.join(folder_path, pat)))

    if not found_files:
        print(f"No books files found in {folder_path}")
        return books

    for f in sorted(set(found_files)):
        if not os.path.isfile(f):
            continue
        try:
            if f.endswith(('.zst', '.zstd')):
                try:
                    import zstandard as zstd
                    import io
                    with open(f, "rb") as fh:
                        dctx = zstd.ZstdDecompressor()
                        with dctx.stream_reader(fh) as reader:
                            txt = io.TextIOWrapper(reader, encoding="utf-8")
                            for line in txt:
                                line = line.strip()
                                if line:
                                    obj = json.loads(line)
                                    if isinstance(obj, dict) and "events" in obj:
                                        books.append(obj)
                except ImportError:
                    print(f"Skipping compressed {f} (zstandard not installed)")
                    continue
                except Exception as e:
                    print(f"Error decompressing {f}: {e}")
                    continue
            else:
                with open(f, "r", encoding="utf-8") as fh:
                    content = fh.read().strip()
                    if not content:
                        continue
                    if content.startswith("["):
                        # JSON array format
                        data = json.loads(content)
                        if isinstance(data, list):
                            for item in data:
                                if isinstance(item, dict) and "events" in item:
                                    books.append(item)
                        elif isinstance(data, dict) and "events" in data:
                            books.append(data)
                    else:
                        # Assume JSONL (one book per line)
                        for line in content.splitlines():
                            line = line.strip()
                            if line:
                                obj = json.loads(line)
                                if isinstance(obj, dict) and "events" in obj:
                                    books.append(obj)
        except Exception as e:
            print(f"Warning: failed to load {f}: {e}")
            continue

    return books

def is_fs_criteria(criteria: str) -> bool:
    c = str(criteria).lower()
    return "free" in c or c == "freegame"

def extract_reel3_marked_fraction(board):
    """Given a board from REVEAL, return (is_full_marked, marked_count, total) for reel 3.
    Handles padding by taking the inner 4 rows.
    """
    if not board or len(board) <= 2:
        return False, 0, 0
    reel = board[2]  # reel 3 (0-based)
    if len(reel) > 4:
        # padding: top + 4 rows + bottom
        inner = reel[1:5]
    else:
        inner = reel
    if not inner:
        return False, 0, 0
    marked_count = sum(1 for sym in inner if isinstance(sym, dict) and sym.get("marked"))
    total = len(inner)
    is_full = (marked_count == total and total >= 4)
    return is_full, marked_count, total

def analyze_books(books):
    if not books:
        print("No valid books to analyze.")
        return

    print(f"Loaded {len(books)} books for analysis.\n")

    # === Sanity checks ===
    broken = [b for b in books if not b.get("events") or not isinstance(b["events"], list)]
    print(f"Sanity: {len(broken)} books with missing/invalid events")
    if len(broken) > len(books) * 0.05:
        print("WARNING: >5% broken books detected!")

    # Basic win stats
    wins = []
    for b in books:
        w = b.get("baseGameWins", 0) + b.get("freeGameWins", 0)
        wins.append(w)
    if wins:
        print(f"Win distribution (per spin): min={min(wins):.1f} max={max(wins):.1f} avg={sum(wins)/len(wins):.2f}")
    if any(w < 0 for w in wins):
        print("WARNING: Negative wins detected!")

    # === FS trigger rate ===
    base_books = [b for b in books if not is_fs_criteria(b.get("criteria", ""))]
    fs_books = [b for b in books if is_fs_criteria(b.get("criteria", ""))]
    fs_triggers = sum(
        1 for b in books
        for e in b.get("events", [])
        if e.get("type") in ("freeSpinTrigger", "freeSpinRetrigger")
    )
    trigger_rate = (fs_triggers / len(base_books) * 100) if base_books else 0
    print(f"\nFS Trigger rate: {trigger_rate:.2f}% ({fs_triggers} triggers from {len(base_books)} base spins)")
    if trigger_rate < 0.5 or trigger_rate > 30:
        print("  WARNING: FS trigger rate looks off for smoke test (typical 5-15% range expected depending on config).")

    # === Multiplier behavior in FS ===
    fs_start_mults = []
    carry_count = 0
    total_mult_transitions = 0
    for b in fs_books:
        mults = []
        for e in b.get("events", []):
            if e.get("type") == "updateGlobalMult":
                m = e.get("globalMult")
                if isinstance(m, (int, float)):
                    mults.append(int(m))
        if mults:
            fs_start_mults.append(mults[0])
            for i in range(1, len(mults)):
                total_mult_transitions += 1
                if mults[i] >= mults[i-1]:
                    carry_count += 1

    if fs_start_mults:
        avg_start = sum(fs_start_mults) / len(fs_start_mults)
        print(f"FS starting multiplier (avg): {avg_start:.2f} (target: 2.0)")
        if abs(avg_start - 2.0) > 0.5:
            print("  WARNING: FS rounds not consistently starting at x2!")
        if total_mult_transitions > 0:
            carry_pct = (carry_count / total_mult_transitions) * 100
            print(f"Multiplier carry rate in FS: {carry_pct:.1f}% ({carry_count}/{total_mult_transitions})")
            if carry_pct < 95:
                print("  WARNING: Multiplier not carrying/growing reliably in FS.")

    # === Reel 3 forcing in FS ===
    fs_reveals_checked = 0
    reel3_full_forces = 0
    for b in fs_books:
        events = b.get("events", [])
        saw_fs_start = False
        for e in events:
            typ = e.get("type")
            if typ in ("freeSpinTrigger", "freeSpinRetrigger", "updateFreeSpin"):
                saw_fs_start = True
            if typ == "reveal" and saw_fs_start:
                fs_reveals_checked += 1
                is_full, _, _ = extract_reel3_marked_fraction(e.get("board", []))
                if is_full:
                    reel3_full_forces += 1
                saw_fs_start = False  # check only the reveal right after spin start

    if fs_reveals_checked > 0:
        force_pct = (reel3_full_forces / fs_reveals_checked) * 100
        print(f"\nReel 3 full Marked at FS spin starts: {force_pct:.1f}% ({reel3_full_forces}/{fs_reveals_checked})")
        if force_pct < 90:
            print("  WARNING: Reel 3 forcing not reliable in FS spins.")

    # === Marked symbol conversion ===
    # Count marked wins + how often they survived (proxy for successful conversion + explode=False)
    marked_win_count = 0
    survived_count = 0
    for b in books:
        board_state = None
        pending_marked_positions = []
        for e in b.get("events", []):
            if e.get("type") == "reveal":
                board = e.get("board", [])
                board_state = []
                for col in board:
                    if len(col) > 4:
                        col = col[1:5]  # strip padding
                    board_state.append([
                        {"name": s.get("name", ""), "marked": bool(s.get("marked"))}
                        for s in col
                    ])
                pending_marked_positions = []
            elif e.get("type") in ("winInfo",) and board_state:
                for win in e.get("wins", []):
                    for p in win.get("positions", []):
                        r = p["reel"]
                        rw = p["row"]
                        if 0 <= r < len(board_state) and 0 <= rw < len(board_state[r]):
                            if board_state[r][rw].get("marked"):
                                marked_win_count += 1
                                pending_marked_positions.append((r, rw))
            elif e.get("type") == "tumbleBoard" and pending_marked_positions:
                exploding = set((p["reel"], p.get("row", 0)) for p in e.get("explodingSymbols", []))
                for pos in pending_marked_positions:
                    if pos not in exploding:
                        survived_count += 1
                pending_marked_positions = []

    if marked_win_count > 0:
        conv_pct = (survived_count / marked_win_count) * 100
        print(f"\nMarked wins that survived tumble (converted): {conv_pct:.1f}% ({survived_count}/{marked_win_count})")
        if conv_pct < 70:
            print("  WARNING: Low marked-to-wild conversion survival rate.")

    # === Cascade activity ===
    total_tumbles = 0
    total_reveals = 0
    long_cascade_count = 0
    current_tumbles = 0
    for b in books:
        for e in b.get("events", []):
            if e.get("type") == "reveal":
                total_reveals += 1
                if current_tumbles >= 3:
                    long_cascade_count += 1
                current_tumbles = 0
            elif e.get("type") == "tumbleBoard":
                total_tumbles += 1
                current_tumbles += 1
    if total_reveals > 0:
        avg_tumbles = total_tumbles / total_reveals
        long_rate = (long_cascade_count / total_reveals) * 100
        print(f"\nCascade activity:")
        print(f"  Avg tumbles per spin: {avg_tumbles:.2f}")
        print(f"  Long cascades (>=3 tumbles): {long_rate:.1f}%")
        if avg_tumbles < 0.1:
            print("  WARNING: Almost no cascades detected.")

    print("\n=== Slice 1-4 Smoke Test Summary ===")
    print("Checks completed. Review warnings above if any metrics look suspicious.")
    print("This is a lightweight sanity check only — not a full validation or RTP report.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Smoke test analyzer for Marked for Death (Slices 1-4)")
    parser.add_argument(
        "books_folder",
        help="Path to the folder containing generated books (e.g. games/marked_for_death/library/books or publish_files)"
    )
    args = parser.parse_args()

    if not os.path.isdir(args.books_folder):
        print(f"Error: {args.books_folder} is not a directory.")
        sys.exit(1)

    books = load_books(args.books_folder)
    analyze_books(books)
