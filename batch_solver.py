''' Batch testing of the Lyne solver on all 650 puzzles
'''

import json
import time
from pathlib import Path

import pandas as pd

from solver import Solver, Puzzle

def run_solver_batch(
    puzzle_file,
    output_file,
    solver_method,
    timeout=None
):
    """
    Run solver over all puzzles with restart support.
    """

    puzzle_file = Path(puzzle_file)
    output_file = Path(output_file)

    # --------------------------
    # Load puzzles
    # --------------------------

    with open(puzzle_file, "r", encoding="utf-8") as f:
        puzzles = json.load(f)


    # --------------------------
    # Load previous results
    # --------------------------

    if output_file.exists():
        stats_df = pd.read_excel(output_file)

        completed = set(stats_df["name"])

        results = stats_df.to_dict("records")

    else:
        completed = set()
        results = []


    # --------------------------
    # Process puzzles
    # --------------------------

    for item in puzzles:

        name = item["name"]

        if name in completed:
            print(f"Skipping {name} (already done)")
            continue


        print(f"Solving {name}...")

        start = time.time()

        puzzle = Puzzle(
            item["puzzle"],
            verbose=False
        )

        solver = Solver(puzzle, time_limit=timeout)

        solver_method(solver)

        elapsed = time.time() - start


        result = {
            "name": name,
            "solved": 0 if solver.solution is None else 1,
            "timed_out": 1 if solver.timed_out else 0,
            "time_seconds": round(elapsed, 3),
            "states_explored": solver.states_explored
        }

        results.append(result)


        # --------------------------
        # Checkpoint save
        # --------------------------

        pd.DataFrame(results).to_excel(
            output_file,
            index=False
        )

        print(result)


    return pd.DataFrame(results)

PUZZLE_FILE = "puzzles.json"

run_solver_batch(PUZZLE_FILE,
    "solve_dfs_restart.xlsx",
    Solver.solve_dfs_restart, timeout=10)

run_solver_batch(PUZZLE_FILE,
    "stats_bfs.xlsx",
    Solver.solve_bfs, timeout=10)

run_solver_batch(PUZZLE_FILE,
    "stats_dfs.xlsx",
    Solver.solve_dfs, timeout=10)
