''' Batch testing of the Lyne solver on all 650 puzzles
'''

import json
import time
from pathlib import Path

import pandas as pd

from solver import Solver, Puzzle

def save_puzzle(puzzle_name, puzzle_text, solution, filename="solutions.json"):
    ''' Save puzzle solution in a separate json file (if solution is not there yet)
    '''
    path = Path(filename)

    # Load existing data, or start with an empty dict
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {}

    # Don't overwrite an existing puzzle
    if puzzle_name in data:
        return False

    data[puzzle_name] = {
        "text": puzzle_text,
        "solution": str(solution)
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            dict(sorted(data.items())),
            f,
            indent=2
        )

    return True

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
        puzzle_text = item["puzzle"]

        if name in completed:
            print(f"Skipping {name} (already done)")
            continue


        print(f"Solving {name}...")

        start = time.time()

        puzzle = Puzzle(
            puzzle_text,
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

        # Save to teh solutions file
        if solver.solution is not None:
            human_solution = puzzle.export_solution(solver.solution)
            save_puzzle(name, puzzle_text, human_solution)


    # Print stats summary
    solved_count = sum(r["solved"] for r in results)
    print(f"Total puzzles solved: {solved_count} / {len(puzzles)}",
          f" ({solved_count / len(puzzles) * 100:.1f}%)")

    return pd.DataFrame(results)

if __name__ == "__main__":

    PUZZLE_FILE = "puzzles.json"

    run_solver_batch(PUZZLE_FILE,
        "stats_bfs.xlsx",
        Solver.solve_bfs, timeout=10)

    run_solver_batch(PUZZLE_FILE,
        "stats_dfs.xlsx",
        Solver.solve_dfs, timeout=10)

    run_solver_batch(PUZZLE_FILE,
        "solve_dfs_restart.xlsx",
        Solver.solve_dfs_restart, timeout=10)


    with open("solutions.json", "r", encoding="utf-8") as file:
        json_data = json.load(file)
        print(f"Total solutions so far: {len(json_data)}")
