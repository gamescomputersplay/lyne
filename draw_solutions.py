import os
import ast
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


from read_lyne_pyzzle import read_pic_into_puzzle

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


def interpolate_color(start, end, t):
    """Interpolate between two hex colors. t is between 0.0 and 1.0."""

    start = tuple(int(start[i:i+2], 16) for i in (1, 3, 5))
    end = tuple(int(end[i:i+2], 16) for i in (1, 3, 5))

    return tuple(
        round(start[i] + (end[i] - start[i]) * t)
        for i in range(3)
    )


def draw_gradient_path(draw, points, start_color, end_color, width=10):
    """
    Draw a path whose color gradually changes from start_color to end_color.
    """

    num_segments = len(points) - 1

    for i, (p1, p2) in enumerate(zip(points, points[1:])):

        # Position along the path: 0 at start, 1 at finish
        t = i / (num_segments - 1) if num_segments > 1 else 0

        color = interpolate_color(start_color, end_color, t)

        draw.line(
            (p1, p2),
            fill=color,
            width=width,
            joint="curve"
        )
    

def draw_solution(image, solution, rows, cols, duration=0.03):
    """
    Play a solution by dragging through each path.

    solution:
        [
            [(x, y), (x, y), ...],
            [(x, y), (x, y), ...],
            ...
        ]
    """

    colors = [
        ("#ff0055", "#ff88aa"),  # neon pink-red
        ("#0055ff", "#88aaff"),  # neon blue
        ("#00ff00", "#88ff88"),  # neon green
    ]

    draw = ImageDraw.Draw(image)


    for color_i, path in enumerate(solution):



        if not path:
            continue

        color = colors[color_i]

        # Convert logical coordinates to physical screen coordinates
        points = [
            logical_to_screen(x, y, rows, cols)
            for x, y in path
        ]

        # Move to the beginning of the path
        draw.line(
            points,
            fill="#333333",
            width=30,
            joint="curve"
        )        
        draw.line(
            points,
            fill="#000000",
            width=25,
            joint="curve"
        )
        draw.line(
            points,
            fill=color[1],
            width=15,
            joint="curve"
        )

        draw_gradient_path(draw, points, color[0], color[1], width=15)


    return image



def draw_solution_for_a_puzzle(file, output_file):

    output_dir = os.path.dirname(output_file)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    # Take screenshot
    image = Image.open(file)

    # Detect puzzle
    puzzle_text, rows, cols = read_pic_into_puzzle(image)

    print("Detected puzzle:")
    for line in puzzle_text:
        print(f"  {line}")

    # Find solution
    puzzle_id, solution = find_solution(puzzle_text)

    if solution is not None:
        print(f"Found archived solution: {puzzle_id}")
    else:
        print("No solution found!")
        return None

    print("Solution:")
    for line in solution:
        print(line)

    solution = draw_solution(image, solution, rows, cols)

    # Write the puzzle name:
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(f"./Arial Bold", 120)
    draw.text((50, 50), puzzle_id.upper(), font=font,         
        fill="white",
        stroke_width=3,
        stroke_fill="black",)

    solution.save(output_file)
    print("Done!\n")


if __name__ == "__main__":

    input_folder = Path("./lyne_screenshots")
    output_folder = Path("./solution_pics")

    for lyne_file in sorted(
            (p for p in input_folder.rglob("*") if p.is_file() and p.suffix.lower() == ".png")
            ):
        
        relative_path = lyne_file.relative_to(input_folder)
        output_file = output_folder / relative_path.with_suffix(".png")

        output_file.parent.mkdir(parents=True, exist_ok=True)

        print(f"\n{lyne_file} -> {output_file}")

        draw_solution_for_a_puzzle(lyne_file, output_file)

