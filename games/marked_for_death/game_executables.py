from game_calculations import GameCalculations
from src.calculations.ways import Ways


class GameExecutables(GameCalculations):
    """Ways evaluation for cascading game. Sets explode for tumble."""

    def evaluate_ways_board(self):
        """Calculate 1024 Ways wins, set .explode on winners, update win manager.
        Also collect marked winners for later conversion (after emit, before tumble).
        """
        self.win_data = Ways.get_ways_data(
            self.config, self.board, global_multiplier=self.global_multiplier
        )

        # DEBUG
        marked_count = len(getattr(self, 'marked_winners_this_eval', []))
        wins_count = len(self.win_data.get('wins', []))
        print(f"[DEBUG] evaluate_ways_board -> marked: {marked_count}, wins: {wins_count}")

        if self.win_data["totalWin"] > 0:
            Ways.record_ways_wins(self)
            self.win_manager.update_spinwin(self.win_data["totalWin"])
            self.win_manager.tumble_win = self.win_data["totalWin"]

        # Ways does not set explode; must do it here for tumble_game_board to work
        for win in self.win_data.get("wins", []):
            for pos in win.get("positions", []):
                self.board[pos["reel"]][pos["row"]].explode = True

        # Collect positions of marked symbols in current wins (for conversion)
        self.marked_winners_this_eval = []
        for win in self.win_data.get("wins", []):
            for pos in win.get("positions", []):
                if self.board[pos["reel"]][pos["row"]].check_attribute("marked"):
                    self.marked_winners_this_eval.append(pos)

    def promote_marked_symbols(self):
        """Promote Low/High symbols on reels 2-3-4 to marked after board creation or tumble.
        Reels 2 and 4 have elevated rate in FS. Reel 3 uses base (force overrides at FS spin start).
        """
        import random
        is_fs = self.gametype == self.config.freegame_type
        base_prob = 0.25
        fs_prob = 0.45
        for reel in [1, 2, 3]:  # reels 2,3,4 (0-indexed)
            for row in range(self.config.num_rows[reel]):
                sym = self.board[reel][row]
                if sym.name[0] in ("H", "L") and not sym.check_attribute("wild", "scatter"):
                    if reel == 2:  # reel 3: base rate (full force at start of FS spin)
                        prob = base_prob
                    else:  # reels 2 and 4: elevated in FS
                        prob = fs_prob if is_fs else base_prob
                    if random.random() < prob:
                        sym.assign_attribute({"marked": True})

    def force_reel3_marked(self):
        """Force reel 3 (index 2) to a full vertical stack of Marked symbols.
        Called at the start of each free spin, after draw (after previous cascades).
        """
        reel = 2
        for row in range(self.config.num_rows[reel]):
            sym = self.board[reel][row]
            if sym.name[0] in ("H", "L") and not sym.check_attribute("wild", "scatter"):
                sym.assign_attribute({"marked": True})

    def convert_marked_to_wild(self):
        """Convert marked in wins to Wild AFTER emit_tumble_win_events (paid)
        but BEFORE tumble_game_board.
        Set .explode = False so the new Wild survives the current cascade.
        """
        # DEBUG
        marked_count = len(getattr(self, 'marked_winners_this_eval', []))
        print(f"[DEBUG] convert_marked_to_wild called -> marked count: {marked_count}")

        to_prune = set()
        for win in self.win_data.get("wins", []):
            for pos in win.get("positions", []):
                r, row = pos.get("reel"), pos.get("row")
                if r is not None and row is not None and self.board[r][row].check_attribute("marked"):
                    to_prune.add((r, row))
                    # bypass special func for W to avoid mult_values KeyError
                    old_funcs = self.special_symbol_functions
                    self.special_symbol_functions = {k: v for k, v in old_funcs.items() if k != "W"}
                    wild_sym = self.create_symbol("W")
                    self.special_symbol_functions = old_funcs
                    self.board[r][row] = wild_sym
                    self.board[r][row].explode = False

        if to_prune:
            for w in self.win_data.get("wins", []):
                w["positions"] = [
                    p for p in w.get("positions", [])
                    if (p.get("reel"), p.get("row")) not in to_prune
                ]

