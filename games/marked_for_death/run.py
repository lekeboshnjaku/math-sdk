"""Main file for generating results for sample lines-pay game.

Temporary development / validation helpers are documented below.
See the "Development / Validation Mode Flags" block and per-flag sections.
All actual game logic lives in gamestate.py / game_executables.py etc.
"""

# Recommended usage (quick reference):
# - Normal validation (safe, no wincap/force): use_validation_distributions = True,  fs_test_mode = False
# - Testing Free Spins heavily:               use_validation_distributions = True,  fs_test_mode = True
# - Full real distributions (when ready):     use_validation_distributions = False, fs_test_mode = False
#   (also set fs_safety_cap = True with high-but-reasonable caps (400 spins / 300 mult) for proper samples)

from gamestate import GameState
from game_config import GameConfig
from game_optimization import OptimizationSetup
from optimization_program.run_script import OptimizationExecution
from utils.game_analytics.run_analysis import create_stat_sheet
from utils.rgs_verification import execute_all_tests
from src.state.run_sims import create_books
from src.write_data.write_configs import generate_configs
from uploads.aws_upload import upload_to_aws


def book_event_validation_guidance():
    """Small helper / documentation for manual book + event ordering validation.

    Usage:
        1. Ensure small settings above (num_sim_args ~5, run_sims=True, compression=False, upload=False).
           (num_threads is auto-lowered to 1 for small counts to prevent division-by-zero in RTP summary.)
        2. python run.py   (will run a handful of sims and write books to library/books/)
        3. Inspect the produced book JSON(s):
           - Load e.g. via json.load(...) or just open the file.
           - For a sim: book["events"]  --> list of {"index": , "type": "...", ...}
        4. Verify key ordering (base + FS) matches 5.3 Event Emission Order Requirements:
           reveal --> winInfo (and related win events) --> [internal convert after win, before tumble] -->
           updateGlobalMult (post paid win) --> tumbleBoard --> ... --> set_end_tumble effects.
        5. Cross reference with the [DEBUG] prints emitted to console (guarded in gamestate.py).
        6. See also: mapping 9.2 Critical Rules (esp. conversion timing, mult after paid), 10 Validation Checklist.

    This is for manual/small-test validation only. No automated asserts added.
    """
    # Example of how one might dump from a loaded book in a notebook / manual check:
    # event_types = [e["type"] for e in book.get("events", [])]
    # print(event_types)
    # Look for correct interleaving of reveal/winInfo/tumbleBoard/updateGlobalMult etc.
    pass


if __name__ == "__main__":

    import warnings
    warnings.filterwarnings("ignore", message="Compressed books file not found")

    # === Development / Validation Mode Flags (TEMPORARY) ===
    # These are temporary helpers used while implementing Priority 1 (cascades, marked promotion,
    # persistent multiplier, event ordering, etc.).
    #
    # They exist because:
    # - Real betmode distributions contain wincap and force_freegame criteria that the current
    #   implementation cannot satisfy (would cause infinite repeat loops in run_spin).
    # - Early marked_prob values + force_reel3 could produce extremely long FS rounds.
    # - We want fast, repeatable, inspectable books for manual + automated validation.
    #
    # HOW TO SWITCH TO MORE REALISTIC TESTING (before Phase 2 / full validation):
    # 1. Set fs_safety_cap = False  (remove / comment the safety guards in gamestate.py too).
    # 2. Set fs_test_mode = False.
    # 3. (Optionally) Set use_validation_distributions = False once wincap + forcing logic + better
    #    reels (e.g. cleaned FRWCAP) are ready.
    # 4. Increase num_sim_args, turn on run_analysis / optimization as needed.
    # 5. Review the entire "if fs_test_mode:" / "elif use_validation_distributions" block below
    #    and the fs_dists construction — these overrides should be removed when real
    #    distributions from game_config.py work reliably.
    #
    # Relationship between the three flags (priority order in distribution logic):
    # - fs_test_mode (highest): Forces many FS entries for targeted testing of x2 start, carry,
    #   force_reel3_marked, retriggers. Completely replaces betmode distributions and disables
    #   wincap paths.
    # - use_validation_distributions (middle, when fs_test_mode=False): Replaces the betmode
    #   distributions with a single safe "basegame" (quota=1.0) distribution. Prevents wincap/
    #   force criteria from being selected.
    # - fs_safety_cap (orthogonal runtime guard): Passed to GameState. Caps FS spin count and
    #   global_multiplier during testing to prevent pathological runs. Lives in gamestate.py
    #   (search for "safety_cap_enabled", MAX_FS_SPINS, MAX_MULT, [SAFETY] prints).
    #
    # See also: gamestate.py (run_freespin, safety checks, _fs_start_mult_pending),
    #           game_config.py (marked_prob, fs_reel3_marked_count),
    #           inspect_books.py (event ordering validation).

    rust_threads = 20
    batching_size = 50000
    compression = False
    profiling = False

    # === Book / Event Validation Support (small test runs) ===
    # Per IMPLEMENTATION_MAPPING_v1.2.md sections 5.3, 9.2, 10.
    # Use small num_sim_args + compression=False + the flags below to produce inspectable books.
    # After run: python games/marked_for_death/inspect_books.py --latest
    # Also watch [DEBUG] output from gamestate.py when DEBUG=True.

    num_sim_args = {
        "base": 100000,  # Final 100k-spin Option B baseline validation with real distributions
    }

    # === Core Temporary Validation Flags ===
    # Clean 100k real-dist validation (use_validation_distributions=False, fs_safety_cap=True)
    use_validation_distributions = False
    fs_test_mode = False
    fs_safety_cap = True

    # The three flags above + the distribution override logic below are the main temporary
    # development aids. Everything below this point (until the run_conditions) is either
    # constant infrastructure or the conditional distribution replacement code.

    num_threads = 8  # 8 threads for your 8 vCPU machine (parallelize the long FS rounds)

    run_conditions = {
        "run_sims": True,
        "run_optimization": False,
        "run_analysis": True,  # Attempt stat sheet + books for Option B baseline summary
        "upload_data": False,
    }
    target_modes = ["base"]

    config = GameConfig()
    gamestate = GameState(config)
    gamestate.fs_safety_cap = fs_safety_cap  # pass the temporary testing cap

    # Patch for uncapped test (ensure freegame reel_weights for natural FS start from real dists, prevent KeyError)
    for bm in config.bet_modes:
        for dist in (getattr(bm, '_distributions', None) or []):
            cond = getattr(dist, '_conditions', None) or getattr(dist, 'conditions', None)
            if cond and 'reel_weights' in cond:
                rw = cond['reel_weights']
                if config.freegame_type not in rw:
                    rw[config.freegame_type] = {'FR0': 1}

    # For real dists validation (wincap force not fully supported in current dev state, would cause repeat hangs):
    # zero wincap quota for this run (other quotas and conditions stay real).
    for bm in config.bet_modes:
        if bm.get_name() == 'base':
            for d in bm.get_distributions():
                if getattr(d, 'get_criteria', lambda: None)() == 'wincap':
                    d._quota = 0.0

    # === TEMP PATCH FOR UNCAPPED REAL DIST TEST ===
    # Disable force_ conditions in real dists so the simulator doesn't enter
    # infinite repeat loops when trying to force FS or wincap.
    # This lets us use real reel_weights and natural behavior with fs_safety_cap=False
    # without getting stuck after "All threads are online."
    # (Still uses the real freegame/base/0 quotas and reels.)
    for bm in config.bet_modes:
        if bm.get_name() == 'base':
            for d in bm.get_distributions():
                cond = getattr(d, '_conditions', None) or getattr(d, 'conditions', None)
                if cond:
                    cond['force_wincap'] = False
                    cond['force_freegame'] = False

    # Remove wincap distribution entirely for this test.
    # Even with quota=0, get_sim_splits does max(..., 1) so it allocates 1 sim
    # that then loops forever on win_criteria=wincap (especially bad with no safety cap).
    for bm in config.bet_modes:
        if bm.get_name() == 'base':
            bm._distributions = [d for d in bm.get_distributions() if getattr(d, 'get_criteria', lambda: None)() != 'wincap']

    # Neutralize win_criteria for the "0" distribution as well.
    # Otherwise, sims assigned "0" criteria will infinite-repeat (same seed => same outcome)
    # if their natural final_win != 0. This is the root cause of hangs when
    # use_validation_distributions=False with real betmodes (which include "0" quota 0.4).
    # Similar issue as wincap; validation mode avoids it by using unconstrained dist only.
    for bm in config.bet_modes:
        if bm.get_name() == 'base':
            for d in bm.get_distributions():
                if getattr(d, 'get_criteria', lambda: None)() == '0':
                    d._win_criteria = None

    # === Distribution Override Logic (TEMPORARY) ===
    # See the "Development / Validation Mode Flags" block near the top for the full priority
    # explanation and "how to switch to realistic testing" instructions.
    #
    # In short:
    # - fs_test_mode wins and installs a special FS-heavy set of distributions (no wincap).
    # - Otherwise, if use_validation_distributions, install a single safe basegame distribution.
    # - Otherwise fall through to whatever is in config.bet_modes (real distributions).
    if fs_test_mode:
        from src.config.distributions import Distribution

        # === Option 1 continued: Further reduced forced Free Spins intensity ===
        # Goal: Continue moving away from artificial fs_test_mode forcing toward natural behavior.
        # Previous step: freegame quota 0.09 → now 0.07 (small conservative reduction).
        # scatter_triggers kept at current strength. Basegame/0 quotas adjusted to total=1.0.
        #
        # Still using fs_test_mode=True + scatter_triggers for controlled FS exercise,
        # but moving closer to natural rates from the improved 300-stop reels.
        # Preparation before trying fs_test_mode=False.
        fs_dists = [
            Distribution(
                criteria="freegame",
                quota=0.07,
                conditions={
                    "reel_weights": {
                        config.basegame_type: {"BR0": 1},
                        config.freegame_type: {"FR0": 1},
                    },
                    "scatter_triggers": {3: 100, 4: 30, 5: 10},  # Still force 3+ scatters on freegame quota sims
                    "force_wincap": False,
                    "force_freegame": True,
                },
            ),
            Distribution(
                criteria="basegame",
                quota=0.63,
                conditions={
                    "reel_weights": {config.basegame_type: {"BR0": 1}},
                    "force_wincap": False,
                    "force_freegame": False,
                },
            ),
            Distribution(
                criteria="0",
                quota=0.30,
                win_criteria=0.0,
                conditions={
                    "reel_weights": {config.basegame_type: {"BR0": 1}},
                    "force_wincap": False,
                    "force_freegame": False,
                },
            ),
        ]
        for bm in config.bet_modes:
            if bm.get_name() == "base":
                bm._distributions = fs_dists
                break

    elif use_validation_distributions or num_sim_args.get("base", 100) <= 100:
        from src.config.distributions import Distribution
        easy_dist = Distribution(
            criteria="basegame",
            quota=1.0,
            conditions={
                "reel_weights": {config.basegame_type: {"BR0": 1}},
                "force_wincap": False,
                "force_freegame": False,
            },
        )
        for bm in config.bet_modes:
            if bm.get_name() == "base":
                bm._distributions = [easy_dist]
                break
    else:
        # Real betmode distributions from game_config.py are used (no temporary overrides applied).
        pass

    if run_conditions["run_optimization"]:
        optimization_setup_class = OptimizationSetup(config)

    if run_conditions["run_sims"]:
        create_books(
            gamestate,
            config,
            num_sim_args,
            batching_size,
            num_threads,
            compression,
            profiling,
        )

    generate_configs(gamestate)

    if run_conditions["run_optimization"]:
        OptimizationExecution().run_all_modes(config, target_modes, rust_threads)
        generate_configs(gamestate)

    if run_conditions["run_analysis"]:
        custom_keys = [{"symbol": "scatter"}]
        create_stat_sheet(config.game_id, custom_keys=custom_keys)

    if run_conditions["upload_data"]:
        upload_items = {
            "books": True,
            "lookup_tables": True,
            "force_files": True,
            "config_files": True,
        }
        upload_to_aws(
            gamestate,
            target_modes,
            upload_items,
        )
