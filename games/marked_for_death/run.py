"""Main file for generating results for Marked for Death (v0.5 design)."""

from gamestate import GameState
from game_config import GameConfig
from game_optimization import OptimizationSetup
from optimization_program.run_script import OptimizationExecution
from utils.game_analytics.run_analysis import create_stat_sheet
from utils.rgs_verification import execute_all_tests
from src.state.run_sims import create_books
from src.write_data.write_configs import generate_configs
import types

if __name__ == "__main__":

    # Settings for heavy real simulations on 8 vCPU / 32 GB RAM VM
    # - num_threads=4: safe concurrency for 8 cores, leaves headroom
    # - batching_size=20000: good balance for heavy sims (adjust down if memory pressure)
    # - compression=True: produces .zst files, saves disk, standard for heavy runs
    # - For millions of sims, monitor with htop; if OOM reduce threads or batch
    # Real reels required for non-zero RTP, proper FS/cascades, real numbers.
    # Placeholders will give 0.0 RTP and degenerate results.
    num_threads = 1          # Use 1 for VM/quick tests (4+ only for big runs on strong machines)
    rust_threads = 1
    batching_size = 200      # Match or larger than your test size
    compression = True
    profiling = False

    num_sim_args = {
        "base": 200,           # your test size
    }

    run_conditions = {
        "run_sims": True,
        "run_optimization": False,
        "run_analysis": False,
        "upload_data": False,
    }
    target_modes = ["base"]

    config = GameConfig()
    gamestate = GameState(config)

    # === Quick test patch for small runs (e.g. 200) ===
    # Force ALL sims into the "basegame" criteria which has no win_criteria.
    # This prevents the long retry loops on "wincap" (25000) or exact-0 that make
    # it look stuck after "All threads are online."
    # Remove this patch for real distribution runs.
    for d in gamestate.get_betmode("base").get_distributions():
        if d.get_criteria() == "basegame":
            d._quota = 1.0
        else:
            d._quota = 0.0

    # === Dev speed patch: prevent scatter-triggered repeats in check_freespin_entry for this test ===
    # Without this, "basegame" criteria will retry every time 3+ scatters land (to simulate no-fs).
    # This makes 200 sims finish fast with visible progress.
    orig_check = gamestate.check_freespin_entry
    def test_check_freespin_entry(self, scatter_key="scatter"):
        conds = self.get_current_distribution_conditions()
        if conds.get("force_freegame", False):
            if len(self.special_syms_on_board.get(scatter_key, [])) >= min(self.config.freespin_triggers.get(self.gametype, {}).keys() or [3]):
                return True
        return False   # never force repeat for test speed
    gamestate.check_freespin_entry = types.MethodType(test_check_freespin_entry, gamestate)
    if run_conditions["run_optimization"] or run_conditions["run_analysis"]:
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
        run(config.game_id, custom_keys=custom_keys)

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
