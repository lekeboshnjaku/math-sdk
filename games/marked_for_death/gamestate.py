"""Handles the state and output for a single simulation round"""

from game_override import GameStateOverride
from src.events.events import reveal_event, update_global_mult_event


class GameState(GameStateOverride):
    """Handle all game-logic and event updates for a given simulation number.
    Basic cascade skeleton per Priority 1 of IMPLEMENTATION_MAPPING_v1.2.md (7.3).
    """
    DEBUG = False  # Temp disabled for Option A uncapped 150-spin run (prevents massive debug logs during long FS). Revert to True after.

    def run_spin(self, sim, simulation_seed=None):
        """Run a single simulation spin (base game), including possible FS trigger.

        Overall flow:
        - Reset RNG for reproducibility.
        - Loop while the spin must repeat (for distribution criteria like win_criteria or force_freegame).
        - Inside each attempt:
          1. Reset book state.
          2. Draw initial board + promote initial marked symbols.
          3. Evaluate, emit wins, handle multiplier for this level.
          4. Cascade loop (while wins): convert marked → tumble → promote new → re-evaluate → emit.
          5. End the tumble sequence.
          6. Check for FS trigger and run it if conditions met.
          7. Finalize wins and check if this attempt satisfies the criteria (repeat if not).

        Key responsibilities:
        - Handle base-game cascade with marked symbol conversion to wilds.
        - Manage global multiplier (+1 after paid cascades).
        - Trigger and delegate to run_freespin() when scatters meet criteria.
        - Support repeat logic for specific betmode distributions.

        Important timing (per IMPLEMENTATION_MAPPING_v1.2.md 3.3, 7.3, 9.2):
        - Multiplier updated only after paid win events (after emit), before the cascade
          actions and before the next evaluation that should see the new value.
        - Marked conversion happens after win emission but before tumble (so converted
          wilds do not explode in this cascade).
        - Update happens after first paid level and after every subsequent paid cascade.

        See also sections 5.3 (event ordering) and 9.2 (critical state & timing rules).
        """
        self.reset_seed(sim)
        self.repeat = True
        while self.repeat:
            # --- Initial board setup ---
            self.reset_book()
            self.draw_board(emit_event=True)
            if self.DEBUG:
                self.debug_print_state("after draw_board (initial)")  # temporary debug for Priority 1
            if self.DEBUG:
                print("[DEBUG] After draw/reveal")  # temporary validation aid for event ordering (per mapping 5.3)
            self.promote_marked_symbols(is_drop=False)  # after draw_board for initial board (per mapping 7.2)

            # --- First evaluation + paid level handling ---
            self.evaluate_ways_board()
            self.emit_tumble_win_events()
            if self.DEBUG:
                print("[DEBUG] After initial emit")  # temporary validation aid for event ordering (per mapping 5.3)

            # Multiplier +1 after this paid level's win events (before its cascade/tumble
            # and before the next evaluation). Restores required ordering for inspector:
            # winInfo/updateTumbleWin --> updateGlobalMult --> (convert) --> tumbleBoard.
            # The inner-loop updates handle subsequent cascades after their post-tumble emits.
            # Per mapping 9.2: +1 after paid win, before next eval that should use the bumped value.
            if self.win_data.get("totalWin", 0) > 0:
                if getattr(self, 'fs_safety_cap', False) and self.global_multiplier >= 200:
                    if self.DEBUG:
                        print(f"[SAFETY] Skipping mult update (already at cap 200)")
                else:
                    self.update_global_mult()
                if self.DEBUG:
                    self.debug_print_state("after mult update")  # temporary debug for Priority 1
                if self.DEBUG:
                    print("[DEBUG] After update_global_mult (after first paid level)")  # per 9.2 and inspector expectation

            # --- Cascade loop (while this level still has wins) ---
            while self.win_data.get("totalWin", 0) > 0 and not getattr(self, "wincap_triggered", False):
                self.convert_marked_to_wild()  # after emit/payment, before tumble (per 7.1/9.2)
                if self.DEBUG:
                    print("[DEBUG] After convert_marked_to_wild")  # temporary validation aid for event ordering (per mapping 5.3)
                self.tumble_game_board()
                if self.DEBUG:
                    print("[DEBUG] After tumble_game_board")  # temporary validation aid for event ordering (per mapping 5.3)
                self.promote_marked_symbols(is_drop=True)  # after tumble for newly dropped symbols (per mapping 7.2)
                self.evaluate_ways_board()
                self.emit_tumble_win_events()

                # Multiplier +1 only after this *cascade* produced a paid win (post-tumble emit).
                # Ensures correct value for any further cascades in this chain.
                if self.win_data.get("totalWin", 0) > 0:
                    if getattr(self, 'fs_safety_cap', False) and self.global_multiplier >= 200:
                        if self.DEBUG:
                            print(f"[SAFETY] Skipping mult update (already at cap 200)")
                    else:
                        self.update_global_mult()
                    if self.DEBUG:
                        self.debug_print_state("after mult update")  # temporary debug for Priority 1
                    if self.DEBUG:
                        print("[DEBUG] After update_global_mult (after paid cascade)")  # per 9.2: after the cascade's win events, before next eval uses new value

            # --- End of this spin's tumble sequence ---
            if self.DEBUG:
                print("[DEBUG] Before set_end_tumble_event")  # temporary validation aid for event ordering (per mapping 5.3)
            self.set_end_tumble_event()
            if self.DEBUG:
                print("[DEBUG] After set_end_tumble_event")  # temporary validation aid for event ordering (per mapping 5.3)
            self.win_manager.update_gametype_wins(self.gametype)

            # --- Possible FS trigger from this base spin ---
            if self.check_fs_condition() and self.check_freespin_entry():
                self.run_freespin_from_base()

            self.evaluate_finalwin()
            self.check_repeat()

        self.imprint_wins()

        if self.DEBUG:
            # Simple book event dump helper for small test validation (guarded by DEBUG).
            # After running small sims via run.py, inspect self.book.events sequence here in console:
            #   "reveal", "winInfo", ..., "updateGlobalMult", "tumbleBoard", ...
            # Confirms convert after win events + before tumble, mult after paid, set_end handling.
            # Per mapping 5.3 / 9.2 / 10. (Use together with the [DEBUG] timing prints above.)
            try:
                event_types = [e.get("type") for e in self.book.events]
                print(f"[DEBUG] Book event types (sim {getattr(self, 'sim', '?')}): {event_types}")
            except Exception:
                pass  # safe if book not populated in all paths

    def run_freespin(self):
        """Run one complete Free Spins (FS) round, including all individual FS spins and possible retriggers.

        Overall flow:
        - Called from base run_spin() when FS is triggered.
        - Reset FS state and set starting multiplier to x2 (new round).
        - Loop while there are remaining FS spins (fs < tot_fs).
        - Each iteration = one FS spin:
          1. Advance FS counter + reset per-spin state.
          2. Draw board, promote marked (initial + force full reel 3).
          3. Evaluate, emit, handle multiplier.
          4. Inner cascade loop with marked conversion.
          5. End tumble sequence.
          6. Check for retrigger (add more spins to tot_fs).
        - After all spins: emit end-of-FS event.
        - Safety cap (temporary, controlled by run.py:fs_safety_cap) can force early exit.

        Key responsibilities:
        - Implement FS-specific marked rules (elevated promotion on reels 2/4 + guaranteed full reel 3).
        - Maintain multiplier carry: starts at x2 for the round, +1 after paid cascades, never resets between spins.
        - Handle retriggers without resetting the multiplier.
        - Reuse the same cascade structure as base game (evaluate → emit → convert → tumble → ...).

        Important timing (per IMPLEMENTATION_MAPPING_v1.2.md 3.3, 5.2, 7.3, 9.2):
        - Multiplier set to x2 once at round start and emitted; then +1 only after paid cascades (same rules as base).
        - Marked conversion after win events but before tumble (same as base).
        - force_reel3_marked() applied at the start of every individual FS spin (including after retriggers), after previous cascades complete.
        - Retrigger adds spins but does not reset or affect the current multiplier.

        Safety: When fs_safety_cap is True, caps FS spins and multiplier to avoid pathological behavior during early testing.

        See also sections 3.3 (FS multiplier), 7.3 (FS cascade loop), and 9.2 (critical timing rules).
        """
        # --- FS round initialization ---
        # Start of new FS round (per IMPLEMENTATION_MAPPING_v1.2.md 3.3, 5.2, 7.3)
        self.reset_fs_spin()
        # FS round start multiplier (x2) + carry rules:
        # - Every new FS round begins at exactly x2 (even if base game had a higher multiplier).
        # - The multiplier is never reset inside the round (neither in reset_fs_spin nor update_freespin).
        # - It only grows via the normal +1 path after paid cascades.
        # - Retriggers simply extend tot_fs; the current grown value carries forward.
        # This implements the persistent global multiplier required by mapping 3.3 / 5.2.
        self.global_multiplier = 2
        # IMPORTANT FIX for event ordering (inspector):
        # Do NOT emit updateGlobalMult(2) immediately here.
        # Emitting right after freeSpinTrigger (esp. after a 0-win base spin's setTotalWin)
        # produced: reveal → setTotalWin → freeSpinTrigger → updateGlobalMult
        # which the inspector flagged as "updateGlobalMult at idx 3 without a preceding win event".
        #
        # Instead, set the value now (so first FS eval uses x2 correctly),
        # and emit the starting x2 updateGlobalMult AFTER the first FS spin's first
        # win emission (emit_tumble_win_events / winInfo or setTotalWin).
        # This guarantees a preceding win-related event for the FS-start updateGlobalMult
        # in the book, satisfying both the "win before updateGlobalMult" heuristic and
        # the requirement to announce the x2 start value.
        # Functional behavior unchanged: x2 applies to first FS board's wins; carry still works.
        self._fs_start_mult_pending = True
        if self.DEBUG:
            self.debug_print_state("FS round start (x2 value set; emit deferred)")  # temporary debug for Priority 1

        # === Temporary FS safety cap (controlled from run.py via fs_safety_cap) ===
        # This guard is active only while fs_safety_cap=True (a development/testing aid).
        # It prevents extremely long FS rounds / runaway multipliers during early development
        # (caused by aggressive marked promotion + force_reel3 + cascade chains).
        #
        # See run.py "Development / Validation Mode Flags" block for how/when to turn it off.
        # When the cap triggers we still call end_freespin cleanly.
        #
        # Values (MAX_FS_SPINS / MAX_MULT) are intentionally high so we can still exercise
        # long-but-not-infinite chains during validation.
        safety_cap_enabled = getattr(self, 'fs_safety_cap', False)
        # High finite caps for proper testing (after detailed analysis of 1700+ spin monster round in book 29).
        # Analysis showed:
        # - The length explosion is driven primarily by retrigger frequency (avg ~12-13 spins per retrigger on FR0)
        #   rather than deep per-spin cascades (most spins are 0 or 1-level win).
        # - ~31% of spins produce a win that bumps the persistent mult.
        # - A round can sustain for 1700+ spins / 600x+ while the retrigger buffer stays positive.
        #
        # Chosen caps (400 spins / 300 mult) allow:
        #   - ~30 retriggers and mult growth to ~100-130x — plenty to see the intended marked + carry + retrigger chaining.
        #   - Prevents any single round from dominating 150-300 spin samples or making books/RTP unusable.
        # These are used only while fs_safety_cap=True (development/testing aid).
        MAX_FS_SPINS = 400
        MAX_MULT = 300

        # --- Per-FS-spin logic ---
        # force_reel3_marked() is called on *every* individual FS spin (incl. first + retriggers),
        # after previous spin's cascades have completed (per mapping 3.4 / 5.1 / 7.3).
        while self.fs < self.tot_fs:
            if safety_cap_enabled:
                if self.fs >= MAX_FS_SPINS:
                    if self.DEBUG:
                        print(f"[SAFETY] FS safety cap hit: fs={self.fs} >= {MAX_FS_SPINS}")
                    break
                if self.global_multiplier >= MAX_MULT:
                    if self.DEBUG:
                        print(f"[SAFETY] FS safety cap hit: global_multiplier={self.global_multiplier} >= {MAX_MULT}")
                    # Cap so the final evaluation of this spin still sees a sane multiplier.
                    self.global_multiplier = MAX_MULT
                    break

            # --- FS spin setup ---
            self.update_freespin()
            self.draw_board(emit_event=True)
            if self.DEBUG:
                self.debug_print_state("after draw_board (FS initial)")  # temporary debug for Priority 1
            if self.DEBUG:
                print("[DEBUG] After draw/reveal")  # temporary validation aid for event ordering (per mapping 5.3)
            self.promote_marked_symbols(is_drop=False)  # after draw_board for initial board (per mapping 7.2)
            # Force full reel 3 with Marked symbols for *this* FS spin.
            # Must happen after any previous spin's cascades have finished (mapping 5.1/7.2).
            self.force_reel3_marked()  # Full Marked on reel 3 for this FS spin (called every spin)
            if self.DEBUG:
                self.debug_print_state("after force_reel3_marked")  # temporary debug for Priority 1

            # --- First evaluation of this FS spin + paid level handling ---
            self.evaluate_ways_board()
            self.emit_tumble_win_events()
            if self.DEBUG:
                print("[DEBUG] After initial emit")  # temporary validation aid for event ordering (per mapping 5.3)

            # Deferral of FS x2 start updateGlobalMult (refined):
            # Emit the FS round-start value ONLY after a paid level (totalWin > 0) on the first
            # level that produces win* events. This guarantees the emitted updateGlobalMult(2)
            # for FS start is always preceded by winInfo/updateTumbleWin/etc.
            # - If first FS spin is 0-win, the emit waits until the first paying spin in the round.
            # - When base spin ended at exactly x2, may produce duplicate '2' in list, but inspector
            #   tolerates (cur==2 and fs) and no 'without preceding win' because we condition on >0.
            # - Preserves: value set before any FS eval; first win calc uses x2; 2 appears for detection.
            if getattr(self, '_fs_start_mult_pending', False) and self.win_data.get("totalWin", 0) > 0:
                update_global_mult_event(self)
                if self.DEBUG:
                    print("[DEBUG] After initial emit (deferred FS x2 updateGlobalMult after first paid win level)")
                self._fs_start_mult_pending = False

            # Restore: update after the initial (first) paid level's win events.
            # This ensures winInfo/updateTumbleWin --> updateGlobalMult --> (convert) --> tumbleBoard
            # for the first level of a spin/FS spin.
            # The inner updates (after post-tumble emits) handle subsequent cascades.
            # Per mapping 9.2: +1 after paid win, before next eval that uses it.
            if self.win_data.get("totalWin", 0) > 0:
                if safety_cap_enabled and self.global_multiplier >= MAX_MULT:
                    if self.DEBUG:
                        print(f"[SAFETY] Skipping mult update (cap {MAX_MULT})")
                else:
                    self.update_global_mult()
                if self.DEBUG:
                    self.debug_print_state("after mult update")  # temporary debug for Priority 1
                if self.DEBUG:
                    print("[DEBUG] After update_global_mult (after first paid level)")  # per 9.2 and inspector expectation

            # --- Cascade loop inside this FS spin ---
            while self.win_data.get("totalWin", 0) > 0 and not getattr(self, "wincap_triggered", False):
                # convert_marked_to_wild must run AFTER the win events for this level
                # but BEFORE the tumble that will remove symbols. This is required so
                # that marked winners become non-exploding Wilds for the current cascade.
                # See IMPLEMENTATION_MAPPING_v1.2.md 7.1 (sequence) and 9.2 (conversion timing).
                self.convert_marked_to_wild()
                if self.DEBUG:
                    print("[DEBUG] After convert_marked_to_wild")  # temporary validation aid for event ordering (per mapping 5.3)
                self.tumble_game_board()
                if self.DEBUG:
                    print("[DEBUG] After tumble_game_board")  # temporary validation aid for event ordering (per mapping 5.3)
                self.promote_marked_symbols(is_drop=True)  # after tumble_game_board for newly dropped symbols (per mapping 7.2)
                self.evaluate_ways_board()
                self.emit_tumble_win_events()

                if self.win_data.get("totalWin", 0) > 0:
                    if safety_cap_enabled and self.global_multiplier >= MAX_MULT:
                        if self.DEBUG:
                            print(f"[SAFETY] Skipping mult update (cap {MAX_MULT})")
                    else:
                        self.update_global_mult()
                    if self.DEBUG:
                        self.debug_print_state("after mult update")  # temporary debug for Priority 1
                    if self.DEBUG:
                        print("[DEBUG] After update_global_mult (after paid cascade)")  # per 9.2: after the cascade's win events, before next eval uses new value

            # --- End of this FS spin's tumble sequence ---
            if self.DEBUG:
                print("[DEBUG] Before set_end_tumble_event")  # temporary validation aid for event ordering (per mapping 5.3)
            self.set_end_tumble_event()
            if self.DEBUG:
                print("[DEBUG] After set_end_tumble_event")  # temporary validation aid for event ordering (per mapping 5.3)
            self.win_manager.update_gametype_wins(self.gametype)

            # --- Possible retrigger (adds more spins to this round, does not reset multiplier) ---
            if self.check_fs_condition():
                if safety_cap_enabled and (self.fs >= MAX_FS_SPINS or self.global_multiplier >= MAX_MULT):
                    if self.DEBUG:
                        print(f"[SAFETY] Skipping FS retrigger (cap)")
                else:
                    # Retrigger adds spins to this round but does not touch the multiplier.
                    # The grown value simply carries into the newly added spins.
                    self.update_fs_retrigger_amt()

            # Re-check safety cap after potential retrigger
            if safety_cap_enabled:
                if self.fs >= MAX_FS_SPINS or self.global_multiplier >= MAX_MULT:
                    if self.DEBUG:
                        print(f"[SAFETY] Breaking FS loop (cap)")
                    break

        # --- End of entire FS round ---
        self.end_freespin()

        if self.DEBUG:
            # (See also the book dump at end of run_spin + [DEBUG] prints throughout.)
            # FS events should show continued mult growth (no reset between spins) + per-spin force + proper order.
            pass  # dump already handled at spin level for small validation runs
