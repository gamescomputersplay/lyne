import ast
import json
import time
import keyboard

import pyautogui


from read_lyne_pyzzle import read_pic_into_puzzle
from solver import Solver, Puzzle

SOLUTIONS_FILE = "solutions.json"


def range_middle(r):
    """Return the middle coordinate of a range."""
    return (r[0] + r[1] - 1) / 2


def logical_to_screen(x, y, rows, cols):
    """
    Convert puzzle coordinates (x, y) into physical screen coordinates.

    x -> column
    y -> row
    """
    screen_x = range_middle(cols[x])
    screen_y = range_middle(rows[y])

    return screen_x, screen_y


def find_solution(puzzle_text, solutions_file=SOLUTIONS_FILE):
    """Find a solution for a puzzle in solutions.json."""

    with open(solutions_file, "r", encoding="utf-8") as f:
        solutions = json.load(f)

    for puzzle_id, item in solutions.items():
        if item["text"] == puzzle_text:
            return puzzle_id, ast.literal_eval(item["solution"])

    return None, None


def play_solution(solution, rows, cols, duration=0.03):
    """
    Play a solution by dragging through each path.

    solution:
        [
            [(x, y), (x, y), ...],
            [(x, y), (x, y), ...],
            ...
        ]
    """

    for path in solution:

        if not path:
            continue

        # Convert logical coordinates to physical screen coordinates
        points = [
            logical_to_screen(x, y, rows, cols)
            for x, y in path
        ]

        # Move to the beginning of the path
        pyautogui.moveTo(*points[0])

        # Hold mouse button and drag through the path
        pyautogui.mouseDown()

        for point in points[1:]:
            pyautogui.moveTo(*point, duration=duration)
            time.sleep(0.01)

        pyautogui.mouseUp()

        # Small pause between paths
        time.sleep(0.1)


def main():

    # Take screenshot
    screenshot = pyautogui.screenshot()

    # Detect puzzle
    puzzle_text, rows, cols = read_pic_into_puzzle(screenshot)

    print("Detected puzzle:")
    for line in puzzle_text:
        print(f"  {line}")

    print(f"Rows: {rows}")
    print(f"Cols: {cols}")

    # Find solution
    puzzle_id, solution = find_solution(puzzle_text)

    if solution is None:
        print("Haven't found archived solution, trying to solve the puzzle")
        # Solve one puzzle
        puzzle = Puzzle(puzzle_text, verbose=True)
        solver = Solver(puzzle, time_limit=100)

        solver.solve_dfs_restart()
        solution = puzzle.export_solution(solver.solution)

        if not solution:
            print("No solution found in solutions.json")
            return

    print(f"Found solution: {puzzle_id}")
    print(solution)

    # Give yourself a moment to make sure the game is ready
    print("Starting in 0.1 second...")
    time.sleep(.1)

    # Play it
    play_solution(solution, rows, cols)

    print("Done!")


if __name__ == "__main__":
    keyboard.add_hotkey('f10', main)
    keyboard.wait('esc')
