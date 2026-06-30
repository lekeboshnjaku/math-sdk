from game_calculations import GameCalculations
from src.calculations.ways import Ways


class GameExecutables(GameCalculations):
    """Game-specific cascade logic for Marked for Death (Priority 1).

    Implements:
    - 1024 Ways evaluation with global multiplier
    - Explode flags for tumble
    - Marked symbol promotion and conversion to Wild
    - Reel-3 forced Marked in Free Spins

    See IMPLEMENTATION_MAPPING_v1.2.md sections 7.1 (sequence), 7.2 (marked rules),
    and 9.2 (critical timing).
    """

    def evaluate_ways_board(self):
        """Calculate 1024 Ways wins using the current global_multiplier.

        This is called after every board reveal (initial and post-tumble).

        Responsibilities:
        - Compute win_data via Ways.get_ways_data (includes per-win global_mult).
        - If there is a win: record it, update win_manager for payout tracking.
        - Set .explode = True on every winning symbol position so that
          tumble_game_board() (from base Tumble) will remove them.
          (Ways base implementation does NOT set explode — this is required
          for cascade/tumble mechanics per mapping 7.1.)
        - Collect positions of any Marked symbols that participated in a win
          into self.marked_winners_this_eval. These will be converted to Wilds
          by convert_marked_to_wild() in the next cascade step (see 7.2).

        References:
        - IMPLEMENTATION_MAPPING_v1.2.md 7.1 (Exact sequence, evaluate step)
        - 7.2 (Marked rules and conversion identification)
        """
        self.win_data = Ways.get_ways_data(
            self.config, self.board, global_multiplier=self.global_multiplier
        )

        if self.win_data.get("totalWin", 0) > 0:
            Ways.record_ways_wins(self)
            self.win_manager.update_spinwin(self.win_data["totalWin"])
            self.win_manager.tumble_win = self.win_data["totalWin"]

        # Set .explode = True on all winning positions.
        # This tells the tumble logic which symbols to remove/replace.
        # Critical because the base Ways class does not set this flag.
        for win in self.win_data.get("wins", []):
            for pos in win.get("positions", []):
                self.board[pos["reel"]][pos["row"]].explode = True

        # Collect positions of Marked symbols that contributed to a win.
        # These are the ones that must be converted to Wild *after* payment
        # but *before* the tumble for this cascade.
        self.marked_winners_this_eval = []
        for win in self.win_data.get("wins", []):
            for pos in win.get("positions", []):
                if self.board[pos["reel"]][pos["row"]].check_attribute("marked"):
                    self.marked_winners_this_eval.append(pos)

    def promote_marked_symbols(self, is_drop: bool = False):
        """Promote Low/High symbols on reels 2, 3, and 4 to Marked.

        Called:
        - After draw_board (initial board reveal, is_drop=False)
        - After tumble_game_board (for newly dropped symbols, is_drop=True)

        Per IMPLEMENTATION_MAPPING_v1.2.md 7.2 and MDD 7.2:
        promotion happens after board creation / after tumble.

        Probabilities come from config.marked_prob (different for base vs FS,
        and initial vs drop). Only applied to L/H symbols; Wilds and Scatters
        are never marked.
        """
        import random
        is_fs = self.gametype == self.config.freegame_type
        base_rates = self.config.marked_prob.get("base", {"initial": 0.20, "drop": 0.05})
        fs_rates = self.config.marked_prob.get("fs", {"initial": 0.25, "drop": 0.045})
        base_prob = base_rates.get("drop" if is_drop else "initial", 0.20 if not is_drop else 0.05)
        fs_prob = fs_rates.get("drop" if is_drop else "initial", 0.25 if not is_drop else 0.045)
        prob = fs_prob if is_fs else base_prob

        # Reels 2,3,4 (0-indexed: 1,2,3)
        for reel in [1, 2, 3]:
            for row in range(self.config.num_rows[reel]):
                sym = self.board[reel][row]
                if sym.name.startswith(("H", "L")) and not sym.check_attribute("wild", "scatter"):
                    if random.random() < prob:
                        sym.assign_attribute({"marked": True})

    def force_reel3_marked(self):
        """Force N Low/High symbols on reel 3 to Marked (N = config.fs_reel3_marked_count).

        Called on the *initial* board of every Free Spin (including retriggered spins),
        after any previous cascades from the prior spin have completed.

        Per MDD 3.4 / 5.1 and IMPLEMENTATION_MAPPING_v1.2.md 5.1/7.2:
        every FS spin starts with (at least) the configured number of Marked symbols
        on reel 3. Only Low/High symbols are eligible; Wild/Scatter are skipped.
        """
        if self.gametype != self.config.freegame_type:
            return

        reel = 2
        count = self.config.fs_reel3_marked_count
        rows = list(range(self.config.num_rows[reel]))

        import random
        selected = random.sample(rows, min(count, len(rows)))

        for row in selected:
            sym = self.board[reel][row]
            if sym.name[0] in ("H", "L") and not sym.check_attribute("wild", "scatter"):
                sym.assign_attribute({"marked": True})

    def convert_marked_to_wild(self):
        """Convert Marked symbols that won into Wilds (W), preparing the board for tumble.

        Must be called:
        - AFTER win emission / payment (after emit_tumble_win_events or equivalent)
        - BEFORE tumble_game_board() in the cascade loop.

        This matches the exact sequence in IMPLEMENTATION_MAPPING_v1.2.md 3.1 / 7.1
        and MDD v0.7 Section 7.1 (Marked Conversion Flow).

        For each previously collected marked winner:
        - Create a fresh Wild symbol.
        - Replace the Marked symbol with it.
        - Explicitly set .explode = False on the new Wild.

        Why .explode = False?
        Per MDD v0.7 clarification and mapping 9.2: the newly created Wild must
        NOT explode (and therefore must not be tumbled) in the *current* cascade.
        It survives as a normal Wild for the *next* evaluation / cascade.
        Setting explode=False prevents it from being removed in the upcoming tumble.

        """
        marked_winners = getattr(self, "marked_winners_this_eval", [])
        converted = []
        for pos in marked_winners:
            r, row = pos["reel"], pos["row"]
            if self.board[r][row].check_attribute("marked"):
                wild_sym = self.create_symbol("W")
                self.board[r][row] = wild_sym
                # CRITICAL: new Wild must not explode in this cascade (v0.7 + 9.2)
                self.board[r][row].explode = False
                converted.append((r, row))

        # Improved pruning of win_data["wins"]:
        # After converting Marked→Wild, we must remove all converted positions from the
        # win lists so that the subsequent tumble_board_event (which builds its
        # "explodingSymbols" directly from win_data["wins"]) does not reference any
        # positions that were converted.
        #
        # Why this is necessary:
        # - Converted Wilds have .explode=False and must not be part of this tumble.
        # - The event sequence and book must reflect that the conversion happened
        #   before the tumble (per mapping 5.3 event order and 9.2 critical rules).
        # - In long FS cascades with many marked winners, a single win can contain
        #   a mix of marked and non-marked positions, or entire wins can be marked-only.
        # - We drop entire wins that end up with no remaining positions (they were
        #   entirely due to now-converted symbols).
        # - This makes the prune robust to the win structure returned by
        #   Ways.get_ways_data() (which always provides "positions" as list of
        #   {"reel":, "row":} dicts, but we use .get for safety).
        if converted:
            to_prune = set(converted)
            original_wins = self.win_data.get("wins", [])
            cleaned_wins = []
            for w in original_wins:
                if "positions" not in w:
                    cleaned_wins.append(w)
                    continue
                new_pos = [
                    p for p in w.get("positions", [])
                    if (p.get("reel"), p.get("row")) not in to_prune
                ]
                if new_pos:
                    w["positions"] = new_pos
                    cleaned_wins.append(w)
                # else: drop this win completely — it was 100% from converted marked
                # positions and must not influence the tumble event or analysis.
            self.win_data["wins"] = cleaned_wins

    def debug_print_state(self, label=""):
        """Temporary debug helper for Priority 1 (see mapping 11).
        Easy to comment out or guard with a flag.
        """
        print(f"[DEBUG] {label} | Mult: x{self.global_multiplier} | FS: {self.fs}/{self.tot_fs}")
