''' Read a screenshot and generate a digital representation of a LYNE puzzle
'''
from PIL import Image
import numpy as np
from scipy.ndimage import label

# -----------------------------
# Configuration
# -----------------------------

COLORS = {
    'Square': (84, 99, 109), 
    'Triangle': (198, 162, 59), 
    'Diamond': (135, 79, 41), 
    'Number': (204, 185, 162),
    "White": (230, 221, 237)
    }


MIN_STRETCH = 5  # minimum number of consecutive pixels

COLORS = {k[0]: v for k, v in COLORS.items()}


def color_mask(np_image, colors, tolerance=1):
    ''' 
    Generate a True/False np array of the same shape as image,
    True where pixels match any of the colors within tolerance.

    Colors can be [(R, G, B), ...] or (R, G, B)

    tolerance: 0 = exact match; 1 = allow +/-1 per RGB channel
    '''

    if isinstance(colors, tuple):
        colors = [colors]

    mask = np.zeros(np_image.shape[:2], dtype=bool)

    # Convert once to avoid uint8 subtraction problems
    np_image_int = np_image.astype(int)

    for color in colors:
        color = np.array(color)
        diff = np.abs(np_image_int - color)
        match = np.all(diff <= tolerance, axis=2)
        mask |= match

    return mask

def find_ranges(values, min_length):
    ''' Given a list of booleans, return continuous True ranges.
    '''

    ranges = []
    start = None

    for i, value in enumerate(values):

        if value and start is None:
            start = i

        elif not value and start is not None:
            if i - start >= min_length:
                ranges.append((start, i - 1))

            start = None

    # Handle ending range
    if start is not None:
        if len(values) - start >= min_length:
            ranges.append((start, len(values)-1))

    return ranges


def find_axis_ranges(mask, axis=0, min_pixels=5):
    '''
    Find continuous ranges along one axis.

    axis=0 -> scan rows (horizontal projection)
    axis=1 -> scan columns (vertical projection)

    Returns list of (start, end) ranges
    '''

    hits = []

    if axis == 0:
        # scan rows
        for y in range(mask.shape[0]):
            count = np.sum(mask[y, :])
            hits.append(count >= min_pixels)

    elif axis == 1:
        # scan columns
        for x in range(mask.shape[1]):
            count = np.sum(mask[:, x])
            hits.append(count >= min_pixels)

    else:
        raise ValueError("axis must be 0 (rows) or 1 (columns)")

    return find_ranges(hits, 1)


def count_holes(mask):
    ''' Count enclosed empty regions inside a mask.
    '''

    # invert:
    # True = empty space
    empty = ~mask

    # label connected empty areas
    labeled, count = label(empty)

    holes = 0
    for i in range(1, count + 1):

        region = labeled == i

        # does this empty region touch image border?
        touches_border = (
            np.any(region[0, :]) or
            np.any(region[-1, :]) or
            np.any(region[:, 0]) or
            np.any(region[:, -1])
        )

        if not touches_border:
            holes += 1

    return holes

def classify_cell(image):
    ''' Classify image of one cropped out cell (node)
    '''
    image_np = np.array(image)

    detected = {}

    # detect all colors present in the cell
    for name, rgb in COLORS.items():

        mask = color_mask(image_np, rgb)

        detected[name] = np.any(mask)

    # Square / triangle / diamond
    for name in ["S", "T", "D"]:
        if detected.get(name, False):
            # If has white - it's the starting point
            if detected.get("W", False):
                return name   # uppercase
            # Otherwise midpoint
            return name.lower()  # lowercase

    # Numbers logic
    if detected.get("N", False):
        n_color_value = COLORS["N"]
        mask = color_mask(image_np, n_color_value)
        holes = count_holes(mask)
        return holes

    # nothing detected
    return " "

def classify_all_cells(image, rows, cols):
    ''' Read the image and return a list of string that solver can use
    '''

    puzzle = []

    for _, (y1, y2) in enumerate(rows):
        puzzle.append("")

        for _, (x1, x2) in enumerate(cols):

            # Crop out a cell
            cell = image.crop((x1, y1, x2 + 1, y2 + 1))
            # Classify it and add to teh puzzle
            value = classify_cell(cell)
            puzzle[-1] += str(value)

    return puzzle


def read_pic_into_puzzle(image):
    ''' Given the puzzle image, return a 2d list with decoded puzzle
    '''
    
    image_np = np.array(image)

    only_node_colors = [v for k, v in COLORS.items() if k != "W"]
    mask = color_mask(image_np, only_node_colors)

    rows = find_axis_ranges(mask, axis=0)
    cols = find_axis_ranges(mask, axis=1)

    puzzle = classify_all_cells(image, rows, cols)

    return puzzle, rows, cols

if __name__ == "__main__":

    path = "lyne_example.png"
    path = "lyne_screenshots/c-01.png"
    image = Image.open(path).convert("RGB")

    the_puzzle, _, _ = read_pic_into_puzzle(image)
    for line in the_puzzle:
        print(f"'{line}'")
