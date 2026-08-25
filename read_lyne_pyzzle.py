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

THEMES = {
    '01-original': {
        'background': (121, 189, 154),
        'colors': {
            'Diamond': (59, 134, 134),
            'Number': (167, 219, 216),
            'Square': (194, 120, 92),
            'Triangle': (168, 219, 168),
            'White': (233, 241, 223)}},
    '02-tulip': {
        'background': (151, 114, 177),
        'colors': {
            'Diamond': (149, 183, 137),
            'Number': (222, 168, 202),
            'Square': (105, 151, 190),
            'Triangle': (192, 81, 129),
            'White': (238, 224, 248)}},
    '03-deep-space': {
        'background': (30, 30, 30),
        'colors': {
            'Diamond': (74, 178, 255),
            'Number': (209, 207, 184),
            'Square': (198, 0, 0),
            'Triangle': (206, 137, 48),
            'White': (239, 235, 223)}},
    '04-tangerine': {
        'background': (211, 144, 110),
        'colors': {
            'Diamond': (147, 150, 29),
            'Number': (184, 200, 211),
            'Square': (38, 169, 224),
            'Triangle': (221, 151, 205),
            'White': (239, 232, 223)}},
    '05-moonbase': {
        'background': (146, 148, 151),
        'colors': {
            'Diamond': (122, 117, 124),
            'Number': (190, 214, 142),
            'Square': (115, 148, 175),
            'Triangle': (170, 123, 123),
            'White': (233, 239, 242)}},
    '06-kind-of-blue': {
        'background': (45, 162, 219),
        'colors': {
            'Diamond': (213, 191, 100),
            'Number': (167, 219, 215),
            'Square': (78, 93, 169),
            'Triangle': (157, 204, 215),
            'White': (223, 232, 237)}},
    '07-stone-in-focus': {
        'background': (116, 149, 153),
        'colors': {
            'Diamond': (216, 138, 85),
            'Number': (186, 108, 123),
            'Square': (88, 89, 91),
            'Triangle': (186, 190, 204),
            'White': (232, 240, 222)}},
    '08-smoking-room': {
        'background': (82, 69, 86),
        'colors': {
            'Diamond': (135, 79, 41),
            'Number': (204, 185, 163),
            'Square': (84, 100, 109),
            'Triangle': (198, 162, 60),
            'White': (229, 221, 237)}},
    '09-velvet-ice': {
        'background': (155, 97, 119),
        'colors': {
            'Diamond': (191, 64, 64),
            'Number': (214, 135, 131),
            'Square': (20, 19, 19),
            'Triangle': (61, 168, 196),
            'White': (242, 237, 247)}},
    '10-desert': {
        'background': (196, 178, 148),
        'colors': {
            'Diamond': (181, 116, 111),
            'Number': (86, 86, 86),
            'Square': (38, 169, 224),
            'Triangle': (232, 159, 54),
            'White': (239, 234, 223)}},
    '11-electro': {
        'background': (20, 20, 20),
        'colors': {
            'Diamond': (30, 214, 30),
            'Number': (251, 174, 23),
            'Square': (112, 232, 228),
            'Triangle': (216, 158, 212),
            'White': (235, 245, 247)}},
    '12-paddlepop': {
        'background': (214, 185, 135),
        'colors': {
            'Diamond': (107, 249, 107),
            'Number': (188, 145, 81),
            'Square': (214, 50, 136),
            'Triangle': (111, 109, 188),
            'White': (247, 243, 238)}}
    }


MIN_STRETCH = 5  # minimum number of consecutive pixels


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

def classify_cell(image, colors):
    ''' Classify image of one cropped out cell (node)
    '''
    image_np = np.array(image)

    detected = {}

    # detect all colors present in the cell
    for name, rgb in colors.items():

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
        n_color_value = colors["N"]
        mask = color_mask(image_np, n_color_value)
        holes = count_holes(mask)
        return holes

    # nothing detected
    return " "

def classify_all_cells(image, rows, cols, colors):
    ''' Read the image and return a list of string that solver can use
    '''

    puzzle = []

    for _, (y1, y2) in enumerate(rows):
        puzzle.append("")

        for _, (x1, x2) in enumerate(cols):

            # Crop out a cell
            cell = image.crop((x1, y1, x2 + 1, y2 + 1))
            # Classify it and add to teh puzzle
            value = classify_cell(cell, colors)
            puzzle[-1] += str(value)

    return puzzle


def get_background_color(image, grid_size=20, tolerance=1):
    ''' Sample grid of pixels and find the most prevalent color from THEMES' background
    '''
    width, height = image.size

    # Get the known background colors from all themes
    theme_colors = [
        theme["background"]
        for theme in THEMES.values()
    ]

    # Sample the image on a grid
    samples = []

    for row in range(grid_size):
        for col in range(grid_size):
            x = int((col + 0.5) * width / grid_size)
            y = int((row + 0.5) * height / grid_size)

            samples.append(image.getpixel((x, y)))

    # Count how many samples match each theme background
    # within the specified tolerance.
    scores = []

    for color in theme_colors:
        count = sum(
            all(
                abs(sample[channel] - color[channel]) <= tolerance
                for channel in range(3)
            )
            for sample in samples
        )

        scores.append((count, color))

    # Return the background color matched by the most samples
    return max(scores, key=lambda x: x[0])[1]


def select_colors(image):
    ''' Given the background color, pick other colors from THEMES
    '''
    background = get_background_color(image)

    for theme_name, theme in THEMES.items():
        if theme["background"] == background:
            print(f"Selected theme: {theme_name}")
            return theme["colors"]

    raise ValueError(
        f"No theme found for background color: {background}"
    )


def read_pic_into_puzzle(image):
    ''' Given the puzzle image, return a 2d list with decoded puzzle
    '''

    colors = select_colors(image)
    colors = {k[0]: v for k, v in colors.items()}

    image_np = np.array(image)

    only_node_colors = [v for k, v in colors.items() if k != "W"]
    mask = color_mask(image_np, only_node_colors)

    rows = find_axis_ranges(mask, axis=0)
    cols = find_axis_ranges(mask, axis=1)

    puzzle = classify_all_cells(image, rows, cols, colors)

    return puzzle, rows, cols

if __name__ == "__main__":

    path = "lyne_example.png"
    path = "lyne_screenshots/c-01.png"
    path = "lyne_themes/11-electro.png"

    image_sample = Image.open(path).convert("RGB")

    the_puzzle, _, _ = read_pic_into_puzzle(image_sample)
    for line in the_puzzle:
        print(f"'{line}'")
