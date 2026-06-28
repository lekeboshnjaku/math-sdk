# Marked for Death — MDD v0.6 to SDK Implementation Mapping
**Document Version:** 1.2  
**Date:** 2026-06-28  
**Status:** Complete Mapping (pre-implementation) — Giant Wild Banner de-scoped | v0.7 clarifications incorporated  
**Source:** `Marked_for_Death_Math_Design_Document_v0.7.pdf` (target)  
**Target:** Stake Engine Math SDK (Carrot) — `games/marked_for_death/`  
**Owner:** StakeMath v2 (following CL4R1T4S/Cursor/Devin/Windsurf rigor)

> **MANDATE**: This mapping was produced **before any code changes**. All implementation will follow read-first discipline, use dedicated force paths, exact timing per section 7.1 + 9.2, and validate via simulation/analyzer.

**Scope Note (2026-06-28)**: Giant Wild Banner (MDD v0.6/v0.7 section 11.1) has been **explicitly excluded** from scope and is no longer needed. All references, planning, and future-work notes for Giant Wild Banner have been removed from this document. Implementation focuses strictly on core mechanics: 1024 Ways cascading, Marked symbol spawning + conversion, persistent global multiplier (with FS non-reset carry), and the guaranteed full Marked reel 3 in every Free Spin.

---

## 1. Executive Summary & Recommendation

**We are correctly starting with full Mapping (this document) rather than direct implementation.**

### Why Mapping First (Non-Negotiable)
- MDD contains **extremely precise state & timing rules** (see 7.1 "Exact sequence", 9.2 "Critical State & Timing Rules (Mandatory)").
- Current `marked_for_death/` skeleton has **zero** of the core mechanics (no cascade loop, no marked handling, no explode for ways, incorrect mult reset patterns).
- Anti-patterns that destroy book correctness, analyzer compatibility, and certification:
  - Normal `draw_board` / reel gen mixed with forced states.
  - Multiplier increment or conversion at wrong point in cascade.
  - FS multiplier reset between spins (explicitly forbidden).
  - Event ordering violations.
  - Setting explode on symbols that should survive as Wilds.
- MDD 9.1 gives a clear priority order. We will follow it.
- StakeMath v2 rules (read every target + surrounding context before any `search_replace`; produce plan with file paths before edits; use dedicated `should_trigger_xxx()` + force paths for specials; run sims/analyzers on every change).

**Outcome of this mapping**: Clear, file-level, method-level, timing-level plan. We can implement Priority 1 (Base Cascading Core) safely after this.

---

## 2. MDD v0.7 Key Parameters & Targets (Extracted)

| Parameter              | Target Value          | Notes |
|------------------------|-----------------------|-------|
| RTP (Overall)          | 96.73%                | Matches Wild Bandito certified RTP |
| Grid                   | 5 reels × 4 rows      | 1024 Ways (L→R adjacent, 3+) |
| Max Win                | 25,000×               | Advertised ceiling |
| Volatility             | Medium (session) / High ceiling | Strong base + explosive FS |
| Base Game RTP contrib. | ~68-70%               | Primary engagement |
| Free Spins RTP contrib.| ~26-28%               | High volatility chase |
| Hit Rate (Overall)     | 28.7 – 29.0%          | ~28.0-28.5% base, higher in FS |
| Cascading              | Yes (full)            | Until no more wins |

**Symbol Types**:
- Low: L1–L5 (5)
- High: H1–H4 (4)
- Wild: W (substitutes all except Scatter)
- Scatter: S (triggers FS only; no base pay)
- **Marked**: Enhanced state on Low/High symbols only (never on W/S). Pays exactly like base symbol.

**Paytable** (5oak base, matches current `game_config.py`):
H1: 500 / 100 / 20  
H2: 300 / 80 / 15  
H3: 200 / 50 / 12  
H4: 150 / 40 / 10  
L1: 80 / 20 / 5  
L2: 60 / 15 / 4  
L3: 50 / 12 / 3  
L4: 40 / 10 / 3  
L5: 30 / 8 / 2  

Multiplier applies to all (global).

**FS Trigger**:
- Base/FS: 3S = 12, 4S = 14, 5S = 16
- Retrigger: +2 per additional S during FS
- Scatters anywhere (no lines)

---

## 3. Core Mechanics — Exact Rules (Critical for Mapping)

### 3.1 Cascading Sequence (MDD 7.1 — "Exact sequence that must be followed in code")

1. Evaluate current board for all left-to-right adjacent winning combinations (3+).
2. Calculate total win for this evaluation using **current** multiplier.
3. Identify **every Marked symbol** that participates in at least one winning combination.
4. Pay/award the total win.
5. Convert all identified Marked symbols to Wild symbols (**update grid state**).
6. Remove all symbols that were part of any winning combination in this evaluation.
7. Drop / cascade new symbols into vacated positions (respect FS forced Marked rules).
8. Increment the current multiplier by +1.
9. If new winning combinations exist, repeat from step 1. Otherwise end the spin/round.

**Post-cascade note (MDD page 2)**: "After a cascade that paid wins, the multiplier increases by +1 before the next evaluation (if any)."

**Conversion Note (v0.7 clarification)**: After a Marked symbol is converted to a Wild, the new Wild should not explode in the current cascade. It participates in future cascades as a normal Wild.

### 3.2 Marked Rules (MDD 3.x + 7.2)
- Spawn: Base — Low and High symbols landing on reels 2, 3, or 4 have a probability P_marked (TBD via simulation, suggested range 18-28%) of spawning as Marked.
- Wilds and Scatters **never** Marked.
- FS: At the start of every free spin, reel 3 is fully filled with Marked symbols. During Free Spins, normal symbols landing on reels 2 and 4 have a higher chance of becoming Marked compared to the base game. Marked symbols appear more often on reels 2 and 4 in Free Spins.
- New tumble symbols in FS are also subject to marked rules.
- A Marked pays **exactly** the same as its underlying symbol (H1 etc.).
- If Marked is in a **paid** win → convert to Wild **after payment, before cascade**.
- Conversion is permanent for the remainder of the current spin's cascades.
- Converted Wilds behave identically to natural Wilds.
- Wilds (natural or converted) **NEVER** convert further and are not Marked.
- New dropped symbols that land as (or promote to) Marked can win and convert in subsequent cascades.

### 3.3 Persistent Multiplier (MDD 4 — CRITICAL DIFFERENCE)
**Base Game**:
- Starts at x1 every base spin.
- +1 after **any** evaluation that pays ≥1 win (successful cascade).
- Applies to all subsequent cascades in the same spin.
- Resets to x1 for next base spin. Never carries between spins.

**Free Spins (non-resetting — the key tension mechanic)**:
- Starts at **x2** for the **first free spin of every new FS round**.
- +1 after every winning cascade.
- **NO RESET between free spins**. Value at end of one FS spin = start for next.
- Continues growing for the **entire FS round**.
- Only resets when the full FS round ends (no more retriggers). Next base spin starts at x1.
- Retriggered spins continue with the **current** (already grown) multiplier.

Display: Current multiplier must be prominent. Every +1 should have feedback.

### 3.4 FS Reel 3 Guarantee + Higher Marked on 2/4 (MDD 5.2)
- At the **start of each individual free spin** (including first and after retrigger), force reel 3 to a full vertical stack of Marked symbols. The full Marked stack on reel 3 is applied at the start of each free spin, after the previous spin’s cascades have fully completed.
- Reels 2 and 4: normal spawn rules + **elevated P_marked** (no guaranteed full reel).
- Applies after previous spin's cascades have completed.

### 3.5 Edge Cases (MDD 10.1)
- New dropped Marked can win and convert in next cascade.
- Multiple Marked in same win: all convert.
- Win with only Wilds: no additional conversions.
- High ending FS mult (x18+) is expected/desirable.
- Retrigger on last FS spin: append spins with **current** mult value.
- All-Wild board via conversions: allowed if valid ways.

---

## 4. SDK Architecture — Relevant Components for MfD

**Game Layer (edit these)**:
- `games/marked_for_death/game_config.py`
- `games/marked_for_death/game_override.py` (resets, special sym functions, custom state)
- `games/marked_for_death/game_executables.py` (or GameCalculations) — **primary home for evaluate + marked logic**
- `games/marked_for_death/gamestate.py` — run_spin / run_freespin loops + timing
- `games/marked_for_death/game_events.py` (custom events if needed)
- `games/marked_for_death/run.py` + `game_optimization.py`
- Reels: `reels/BR0.csv`, `FR0.csv`, `FRWCAP.csv`

**Core SDK (read, extend via overrides — do not edit src lightly)**:
- `src/calculations/board.py` — `draw_board`, `create_board_reelstrips`, `force_*`, `get_special_symbols_on_board`
- `src/calculations/ways.py` — `Ways.get_ways_data(...)`, `record_ways_wins`, `emit_wayswin_events`
- `src/calculations/tumble.py` — `tumble_board` (relies on `.explode`)
- `src/executables/executables.py` — `Executables` (Conditions + Tumble): `tumble_game_board`, `emit_tumble_win_events`, `update_global_mult`, FS helpers, `check_fs_condition`
- `src/state/state.py` — `GeneralGameState`: `reset_book` (sets global_mult=1), `reset_fs_spin`, `imprint_wins`, `record`
- `src/events/events.py` — `reveal_event`, `win_info_event`, `update_tumble_win_event`, `update_global_mult_event`, `tumble_board_event`, `fs_trigger_event`, `final_win_event`, etc.
- `src/wins/win_manager.py` — `spin_win`, `tumble_win`, `update_spinwin`, `reset_spin_win`
- `src/calculations/symbol.py` — `Symbol` (fixed slots + `assign_attribute`, `check_attribute`, `.explode`, `.wild` etc.), `SymbolStorage`, `create_symbol`
- `src/config/config.py` + distributions

**Patterns to mimic exactly** (from working examples):
- `games/0_0_ways/` — pure ways evaluation
- `games/0_0_scatter/` — tumble loop + global_mult usage + custom `GameExecutables`
- `games/0_0_cluster/` — custom grid mult + explode setting inside eval + `get_xxx_update_wins`

**Event flow for cascade games** (typical):
draw/reveal → evaluate (populates `win_data`, updates win_manager, records) → emit_tumble_win_events (or ways equivalent) → while `win_data["totalWin"] > 0` and not wincap: tumble_game_board() → evaluate → emit → set_end_tumble_event at end of sequence.

---

## 5. Detailed Cross-Mapping Tables

### 5.1 Mechanics → Files & Methods

| MDD Mechanic | Primary Location(s) to Implement/Override | Current State (marked_for_death/) | Required Changes |
|--------------|-------------------------------------------|-----------------------------------|------------------|
| 1024 Ways evaluation + global mult | `game_executables.py`: `evaluate_ways_board` / `get_ways_update_wins`<br>`Ways.get_ways_data(..., global_multiplier=self.global_multiplier)` | Empty pass | Implement ways + record + win_manager update. Use "global" strategy. |
| Set `.explode = True` for tumble | Inside custom evaluate (see cluster example: `board[p["reel"]][p["row"]].explode = True`) | Not present (Ways base does **not** set it) | Must set on all winning positions during eval. |
| Marked spawn / promotion | Post-draw hook + post-tumble hook in executables/override<br>`apply_marked_promotions()` | None | After `create_board_reelstrips` and after `tumble_board`, promote L/H on reels 2-3-4 with P_marked. Probabilities must be config-driven to support different base vs FS chances. Use simple language in implementation. |
| is_marked per position | Symbol attribute: `assign_attribute({"marked": True})`<br>Scan via `check_attribute("marked")`<br>Optional parallel `self.marked_on_board` | None | Add "marked" to `special_symbols` in config for event emission. Track independently. |
| Marked conversion (post-pay, pre-cascade) | In gamestate cascade loop, between emit and tumble (or dedicated `convert_marked_winners()` after pay) | None | Identify from `win_data["wins"]` positions that were marked. Convert those positions to W. |
| Persistent global_mult +1 after paid cascade | `update_global_mult()` (base class)<br>Called at correct point in loop | `global_multiplier = 1` in `reset_book` | Call after successful paid cascade. **Never** reset in FS `reset_fs_spin`. |
| FS x2 start + carry | `run_freespin` + override of `reset_fs_spin` (do **not** reset mult) + initial set on round entry | Wrong pattern in examples | Set to 2 at start of new FS round only. Carry by not touching it. Emit event on changes. |
| Reel 3 full Marked every FS spin | Dedicated application after `update_freespin()` / before or after draw in FS path | None | `force_reel3_marked()` — force set marked attr on reel 3 positions (L/H become marked). Use after each FS draw. |
| Scatter trigger + FS counters | Mostly in `executables.py` (reusable) + config | Partially wired (config + gamestate skeleton) | Minor: ensure `update_freespin_amount` etc. match 12/14/16 +2. |
| Wincap + repeat | `evaluate_wincap`, betmode distributions, `check_game_repeat` in override | Present in config skeleton + override stub | Keep and tune distributions. |
| Book event ordering | `gamestate.py` loop + base emit calls + custom if needed | Basic skeleton | Ensure: reveal → win_info / tumble wins → update_global_mult (when +1) → tumble_board_event → fs events in correct places. |

### 5.2 State Variables & Lifecycle (Critical Timing)

| Variable              | Reset Point (MDD + SDK) | Base Spin | FS Spin (within round) | Notes |
|-----------------------|-------------------------|-----------|------------------------|-------|
| `global_multiplier`   | `reset_book()` = 1     | Start x1, +1 after each paid cascade | Start round at x2, carry + continue +1 | **Do not touch in `reset_fs_spin` or `update_freespin`** |
| `board` + symbols     | `reset_book`           | Fresh draw | Fresh draw per spin + cascades | Apply marked after creation/tumble |
| `fs`, `tot_fs`        | `reset_book` / `reset_fs_spin` | 0 | Incremented | Standard |
| `win_data`, `spin_win`| `reset_book` + per reveal | Reset per spin | Reset per FS spin (but mult not) | `win_manager.reset_spin_win()` |
| `marked` state        | Per board / per cascade | Promote on landing | Promote + force reel 3 | Clear on new board? No — per spin lifetime for conversion |
| `wincap_triggered`, `repeat` | `reset_book` | Standard | Standard | |

**reset_book (src/state/state.py:69)** always forces `global_multiplier = 1`. Override in `game_override.py` only for game-specific additions; do not change core mult reset for base.

**reset_fs_spin (src/state/state.py:99)**: Only sets `fs=0`, `gametype=free`, resets spin win. Perfect — we must **not** add `global_multiplier = 1` here (unlike 0_0_scatter override).

### 5.3 Event Emission Order Requirements

Typical winning cascade spin (base or FS):
1. `reveal_event` (from `draw_board(emit_event=True)`)
2. Ways eval → populate `win_data`
3. `win_info_event` (via emit)
4. `set_win_event` / `update_tumble_win_event`
5. (If wins) **Marked conversion on board**
6. `tumble_game_board()` → `tumble_board()` + `tumble_board_event`
7. `update_global_mult_event` (after paid cascade)
8. Repeat eval + events
9. `set_end_tumble_event` (or ways equivalent) when no more wins
10. `update_gametype_wins`
11. FS trigger / retrigger events if applicable
12. `final_win_event`

**Important (v1.2)**: `update_global_mult_event` must fire **after** the paid cascade’s win events but **before** the next evaluation uses the new multiplier value.

`tumble_board_event` relies on current `win_data["wins"]` positions for explodingSymbols + `new_symbols_from_tumble`.

### 5.4 Symbol / Marked Representation

- Do **not** put "M" as a reel symbol name (per v0.7: enhanced state of L/H).
- In `game_config.py`: Add `"marked": []` to `special_symbols`.
- After symbol creation / after tumble: `sym.assign_attribute({"marked": True})` for qualifying L/H.
- Conversion: `board[r][row] = self.create_symbol("W")` (fresh wild; it will get wild=True via special_flags).
- In `Ways.get_ways_data`, winning logic uses `sym.name` (H1 etc.) — marked flag does not affect pay value.
- For events: because "marked" will be in special_symbols, `json_ready_sym` will include it when True.
- Wilds created by conversion participate in later `potential_wins` and wild substitution.

---

## 6. Current Code Status vs. Spec (Gap Analysis)

**`gamestate.py`** (skeleton only):
- Has basic `run_spin` / `run_freespin` with single draw + evaluate (no while cascade).
- No conversion point, no mult update call in loop, no post-tumble marked promotion.
- **Gap**: Must be rewritten around cascade pattern from 0_0_scatter/0_0_cluster, with marked-specific hooks.

**`game_executables.py` / `game_calculations.py`**:
- Both empty pass-through.
- **Gap**: Need full custom ways evaluate that returns win_data, sets explode on all winners, collects marked winners, updates win_manager, records.

**`game_override.py`**:
- Still has template + "M" + "W" mult assignment (M is treated as reel symbol — outdated vs v0.7).
- `reset_book` calls super only.
- **Gap**: Add marked promotion methods, correct FS mult handling (no reset), `check_game_repeat` if needed, `assign_special_sym_function` update (may keep for future mult symbols or remove M if not used on reels).

**`game_config.py`**:
- Good skeleton (dimensions, paytable, triggers, special_symbols missing "marked").
- Reels point to 4-line stubs (BR0/FR0).
- Betmode distributions have scatter_triggers but no marked spawn weights yet.
- **Gap**: Add "marked" to special_symbols. Add distribution conditions for marked probabilities (base vs FS, config-driven). Add proper long reel strips.

**Reels**:
- BR0.csv / FR0.csv: 4 stops each — useless for production sims.
- FRWCAP.csv: 182 stops — usable for wincap force.
- **Gap**: Generate or import real 4-row reel strips for BR0/FR0 that produce target hit rate / RTP.

**`run.py`**:
- Standard harness. Upload on by default.
- Fine for now; will use for validation.

**Core SDK usage**:
- Can reuse almost everything. Only extend at game layer.
- Ways base does **not** set explode or handle marked → must wrap in game layer.

---

## 7. Recommended Implementation Architecture

### 7.1 GameExecutables (Primary Logic Home)

```python
# In game_executables.py (sketch — implement after more reads)
class GameExecutables(GameCalculations):
    def evaluate_ways_board(self):
        # 1. Compute ways data with current global_mult
        self.win_data = Ways.get_ways_data(self.config, self.board, global_multiplier=self.global_multiplier)
        
        # 2. Update manager + record
        if self.win_data["totalWin"] > 0:
            Ways.record_ways_wins(self)
            self.win_manager.update_spinwin(self.win_data["totalWin"])
            self.win_manager.tumble_win = self.win_data["totalWin"]
        
        # 3. Set explode on all winning positions (critical for tumble)
        self._set_explode_on_wins()
        
        # 4. Collect marked winners for conversion (before emit/tumble)
        self.marked_winners_this_eval = self._collect_marked_winners()
        
        Ways.emit_wayswin_events(self)  # or use emit_tumble_win_events

    def convert_marked_to_wild(self):
        """Call AFTER win emission/payment (after emit_tumble_win_events or equivalent), 
        BUT BEFORE tumble_game_board().
        
        Per v0.7 clarification: After converting a Marked symbol to a Wild, 
        the new Wild must not explode in the current cascade.
        """
        for pos in self.marked_winners_this_eval:
            r, row = pos["reel"], pos["row"]
            # Convert in place to a fresh Wild
            wild_sym = self.create_symbol("W")
            # Optionally preserve any mult attr if needed
            self.board[r][row] = wild_sym
            
            # CRITICAL (v1.2 recommendation): Ensure this Wild does not explode in this cascade
            self.board[r][row].explode = False
```

### 7.2 Marked Promotion (after board creation and after tumble)

```python
def promote_marked_symbols(self):
    """Call after create_board_reelstrips and after tumble.
    
    Probabilities should be config-driven to allow different chances in base vs FS.
    Use simple implementation: check reel index and whether in FS.
    """
    is_fs = self.gametype == self.config.freegame_type
    for reel in [1, 2, 3]:  # 0-indexed reels 2,3,4
        for row in range(self.config.num_rows[reel]):
            sym = self.board[reel][row]
            if sym.name.startswith(("H", "L")) and not sym.check_attribute("wild", "scatter"):
                prob = self._get_marked_prob(is_fs, reel)  # config-driven base vs FS
                if random.random() < prob:
                    sym.assign_attribute({"marked": True})
    # FS specific: force entire reel 3 (index 2)
    if is_fs:
        self._force_reel3_full_marked()
```

### 7.3 Gamestate Cascade Loop (Refined)

```python
def run_spin(self, sim, ...):
    ...
    while self.repeat:
        self.reset_book()
        self.draw_board(emit_event=True)
        self.apply_initial_marked()  # or inside draw override

        self.evaluate_ways_board()
        # emit win events here (payment happens conceptually)
        self.emit_tumble_win_events_or_equiv()

        while self.win_data["totalWin"] > 0 and not self.wincap_triggered:
            self.convert_marked_to_wild()          # AFTER emit/payment, BEFORE tumble
            self.tumble_game_board()
            self.promote_marked_on_new_symbols()   # for drops (config-driven probs)
            self.evaluate_ways_board()
            if self.win_data["totalWin"] > 0:      # only increment after paid cascade
                self.update_global_mult()
            ...

        self.set_end...
        ...
```

**FS version**:
In run_freespin loop:
- update_freespin()
- draw_board()
- force_reel3_marked()  # after previous cascades complete
- then same evaluate → emit → convert (after emit) → tumble → promote → evaluate → conditional update_global_mult

---

## 8. Critical Rules & Anti-Patterns (Enforce Ruthlessly)

From MDD 9.2 + StakeMath OS:
1. Dedicated force logic for any special board (reel 3 in FS, wincap). Never patch after normal `create_board_reelstrips`.
2. Conversion **after** payout / `win_info_event`, **before** `tumble_game_board()`.
3. Mult +1 **after** a paid cascade, **before** next evaluation that should use it.
4. FS mult carry = round level. Reset **only** in `reset_book` (new base spin).
5. `is_marked` tracked per grid position (via symbol attr).
6. After every change to board state (conversion, tumble), re-call `get_special_symbols_on_board()` if needed.
7. Always emit events in the order the web-sdk and book consumers expect.
8. Read the exact file + surrounding context (e.g. how `tumble_board_event` builds exploding list from `win_data`) before editing.
9. Use one precise `search_replace` per logical change set.
10. Validate immediately: run small sims, dump books, check events + board states.
11. **Converted Wilds must not explode in the same cascade they were created.** (v1.2 addition)

---

## 9. Open Items / Questions to Resolve During Mapping Review or Early Impl

- Exact P_marked values (base on reels 2-3-4, elevated in FS on 2+4). Start with ranges and tune via simulation. **Still open**.
- Do newly dropped symbols during FS cascades follow "full marked rule" only on reel 3, or normal elevated?
- Exact behavior for conversion + explode: **DECIDED (v1.2)** — After conversion set `.explode = False` on the new Wild so it survives as a normal Wild into the next cascade. It must not explode in the cascade in which it was created.
- Should converted Wilds carry any multiplier attribute from original Marked?
- Buy-bonus? (MDD mentions as open.)
- Any visual "marked" special flag beyond attribute for events.
- Soft cap / display for extremely high mult (x30+).
- Final reel strip lengths and exact symbol weights (to hit hit-rate + RTP).

---

## 10. Validation Checklist (Mapped to Code)

From MDD 9.4 + 8.2:
- [ ] Single cascade with Marked → correct Wild appears for next board (and does not explode in creation cascade).
- [ ] Mult climbs across 4+ cascades in one spin.
- [ ] FS round: mult grows across multiple free spins (no reset).
- [ ] Reel 3 full Marked stack on **every** FS spin start (applied after previous cascades complete).
- [ ] Scatter in FS adds spins without resetting mult.
- [ ] Converted Wilds substitute correctly in later cascades.
- [ ] No win → no mult increase.
- [ ] Full metrics after 100M spins match targets.
- [ ] Books contain correct ordered events for every step (inspect `book.events`).

---

## 11. Next Actions After This Doc

1. Review this mapping with team / self.
2. Resolve open items (P_marked tuning, dropped symbol rules, etc.).
3. Update todo list.
4. Begin **Priority 1** implementation:
   - Read every target file section again immediately before editing.
   - Start with `game_executables.py` + cascade skeleton in `gamestate.py`.
   - Add minimal marked stubs so code runs.
   - Generate temp longer reels.
   - Run `python run.py` (with sims enabled) + manual book inspection.
5. Only after Phase 1 stable: move to Phase 2 (real marked conversion).

---

## Appendix: Key Files Read for This Mapping

- MDD PDF (v0.6 / v0.7 target text)
- `games/marked_for_death/` (all .py + reel counts)
- `games/0_0_scatter/` (gamestate, executables, override — primary cascade + mult pattern)
- `games/0_0_cluster/` (explode setting + custom evaluate pattern)
- `games/0_0_ways/` (pure ways)
- Core src/ files as listed in Section 4

**This document (v1.2) is the source of truth for all subsequent edits.**

---

*Generated under StakeMath v2 discipline. Mapping v1.2 incorporates v0.7 MDD clarifications for conversion timing, explosion behavior, and wording improvements. Ready for controlled implementation.*

END OF IMPLEMENTATION MAPPING v1.2
