''' Solver for the game LYNE
'''

from dataclasses import dataclass
from enum import Enum, auto
from collections import defaultdict, deque
import time
import json
import random

## Legend:
# d|s|t - diamond | square | triangle - basic node
# D|S|T - same, starting node
# 2|3|4 - no shape node that has to be visited that many times
# [space] - no node

STRATEGY = "BFS"
STRATEGY = "DFS"
STRATEGY = "RESTART"
STRATEGY = "SMART RESTART"

class NodeShape(Enum):
    ''' Enumeration for the node shapes
    '''
    ANY = auto()
    TRIANGLE = auto()
    SQUARE = auto()
    DIAMOND = auto()


@dataclass(frozen=True, slots=True)
class Node:
    ''' Nodes in the puzzle
    '''
    # ID to use in a solution
    id: int
    # Position on the original grid
    row: int
    col: int

    shape: NodeShape
    required_visits: int

    @property
    def position(self):
        ''' Node coordinates, for the final solution export
        '''
        return (self.col, self.row)

class Puzzle:
    ''' Class that holds all information about the puzzle setup
    '''

    def __init__(self, puzzle_definition, verbose=False):
        # Nodes in the puzzle
        self.nodes, self.starts = self.generate_nodes(puzzle_definition)

        # Lookup for node positions
        self.node_position_lookup = {
            (node.row, node.col): node
            for node in self.nodes
        }

        # Edges of the puzzle. Invalid edges (triangle to square) already removed
        self.edges = self.generate_edges()

        # Lookup table {node_id:[edge_id,...], ...}
        self.node_edges = self.generate_node_edges()

        # Overlapping edges (crossing diagonally)
        self.edge_overlaps = self.generate_edge_overlaps()

        # Neighbor nodes (which nodes are connected with one edge)
        self.neighbor_nodes = self.generate_neighbor_nodes()

        # Generate shortcut edges (so given ABC nodes: AB is a shortcut for [BC, AC]
        # This dict is: {node: {far_edge: (near_edge1, near_edge2),...},...),
        self.shortcuts = self.generate_shortcuts()

        if verbose:
            self.print_info()

    def generate_nodes(self, puzzle):
        ''' Parse human-read puzzle into a list of nodes
        '''
        nodes = []
        starts = {
            NodeShape.TRIANGLE: [],
            NodeShape.SQUARE: [],
            NodeShape.DIAMOND: []
        }

        for row, line in enumerate(puzzle):
            for col, char in enumerate(line):

                if char == " ":
                    continue

                node_id = len(nodes)

                is_start = char.isupper()

                if char.lower() == "t":
                    shape = NodeShape.TRIANGLE

                elif char.lower() == "s":
                    shape = NodeShape.SQUARE

                elif char.lower() == "d":
                    shape = NodeShape.DIAMOND

                elif char.isdigit():
                    shape = NodeShape.ANY

                else:
                    raise ValueError(f"Unknown symbol: {char}")


                if shape == NodeShape.ANY:
                    visits = int(char)
                else:
                    visits = 0 if is_start else 1

                nodes.append(
                    Node(
                        id=node_id,
                        row=row,
                        col=col,
                        shape=shape,
                        required_visits=visits
                    )
                )

                if is_start:
                    starts[shape].append(node_id)

        return nodes, starts

    def can_connect(self, node1, node2):
        ''' Condition if the two nodes can have a valid edge'''
        return (
            node1.shape == NodeShape.ANY
            or node2.shape == NodeShape.ANY
            or node1.shape == node2.shape
        )

    def generate_edges(self):
        ''' Given list of nodes, generate a list of edges that connect those nodes
        '''


        edges = set()

        # Lookup table: {(x,y): node, }
        node_by_position = {
            (node.row, node.col): node
            for node in self.nodes
        }

        directions = [
            (-1,-1), (-1,0), (-1,1),
            (0,-1),          (0,1),
            (1,-1),  (1,0),  (1,1)
        ]

        for node in self.nodes:

            for dr, dc in directions:
                neighbor_pos = (
                    node.row + dr,
                    node.col + dc
                )

                neighbor = node_by_position.get(neighbor_pos)

                if neighbor is None:
                    continue

                if self.can_connect(node, neighbor):
                    edge = (
                        min(node.id, neighbor.id),
                        max(node.id, neighbor.id)
                    )

                    edges.add(edge)

        return sorted(list(edges))

    def generate_node_edges(self):
        ''' Create a node_edges dict from available edges
        '''
        node_edges = defaultdict(list)
        for edge_id, edge in enumerate(self.edges):
            for node_id in edge:
                node_edges[node_id].append(edge_id)
        return node_edges

    def generate_edge_overlaps(self):
        ''' Generate a dict of edges that overlap (diagonally)
        '''
        edge_overlaps = {}

        # (node1_id, node2_id) -> edge_id
        edge_lookup = {
            edge: edge_id
            for edge_id, edge in enumerate(self.edges)
        }

        for edge_id, (a_id, b_id) in enumerate(self.edges):

            a = self.nodes[a_id]
            b = self.nodes[b_id]

            # Only diagonals can cross
            if abs(a.row - b.row) != 1 or abs(a.col - b.col) != 1:
                continue

            # Opposite corners of the square
            node1 = self.node_position_lookup.get((a.row, b.col))
            node2 = self.node_position_lookup.get((b.row, a.col))

            # One of the corners is missing
            if node1 is None or node2 is None:
                continue

            # Does the opposite diagonal exist?
            other_edge = tuple(sorted((node1.id, node2.id)))
            other_edge_id = edge_lookup.get(other_edge)

            if other_edge_id is None or other_edge_id == edge_id:
                continue

            edge_overlaps[edge_id] = other_edge_id

        return edge_overlaps

    def generate_neighbor_nodes(self):
        ''' Generate a dict: {node_id: {a, b, c}, ...}
        With neighbors of this node
        '''
        neighbor_nodes = {}
        for node in self.nodes:
            node_id = node.id
            neighbors = set()
            for edge_id in self.node_edges[node_id]:
                a, b = self.edges[edge_id]
                if node_id == a:
                    neighbors.add(b)
                else:
                    neighbors.add(a)
            neighbor_nodes[node_id] = neighbors
        return neighbor_nodes

    def generate_shortcuts(self):
        ''' Generate dict of shortcuts: which pairs of edges this edge is a shortcut for
        This dict is: {node: {far_edge: (near_edge1, near_edge2),...},...),
        '''
        shortcuts = {}
        for edge_id, (a, b) in enumerate(self.edges):
            neighbors_a = self.neighbor_nodes[a]
            neighbors_b = self.neighbor_nodes[b]
            shared_neighbors = neighbors_a.intersection(neighbors_b)
            for shared_neighbor in shared_neighbors:
                shortcut_1 = self.edges.index((min(a, shared_neighbor), max(a, shared_neighbor)))
                shortcut_2 = self.edges.index((min(b, shared_neighbor), max(b, shared_neighbor)))

                #shortcuts[(shared_neighbor, edge_id)] = (shortcut_1, shortcut_2)
                if shared_neighbor not in shortcuts:
                    shortcuts[shared_neighbor] = {}
                shortcuts[shared_neighbor][edge_id]= (shortcut_1, shortcut_2)
        return shortcuts

    def print_info(self):
        ''' Nice print of puzzle internal data structure
        '''
        print("\nNodes:")
        for node in self.nodes:
            print(
                f"  {node.id}: "
                f"pos=({node.row},{node.col}), "
                f"shape={node.shape.name}, "
                f"visits={node.required_visits}"
            )

        print("\nStarting nodes:")
        for shape, starts in self.starts.items():
            print(f"  {shape.name}: {starts}")

        print("\nEdges:")
        for edge_id, edge in enumerate(self.edges):
            print(f"  {edge_id}: {edge}")

        print("\nNode -> edges:")
        for node_id, edges in self.node_edges.items():
            print(f"  {node_id}: {edges}")

        print("\nEdge overlaps:")
        print(self.edge_overlaps)

        print("\nNeighbor nodes:")
        for node_id, neighbors in self.neighbor_nodes.items():
            print(f"  {node_id}: {neighbors}")

        print("\nShortcuts node:, (far_edge (near_edge1, near_edge2))")
        for node_id, shortcuts in self.shortcuts.items():
            for far_edge, (near_edge1, near_edge2) in shortcuts.items():
                print(f"  {node_id}: {far_edge, (near_edge1, near_edge2)}")

        print("\n")

    def export_solution(self, state):
        ''' Export a human friendly solution: a list of lists of coordinates
        '''
        if state is None:
            return []

        solution = []

        for path in state.complete_paths:

            coordinates = []

            current = path.start_node
            coordinates.append(
                self.nodes[current].position
            )

            for edge_id in path.edges:
                a, b = self.edges[edge_id]

                if a == current:
                    current = b
                else:
                    current = a

                coordinates.append(
                    self.nodes[current].position
                )

            solution.append(coordinates)

        return solution

@dataclass
class Path:
    ''' A path from a starting point
    '''
    shape: NodeShape
    start_node: int
    current_node: int | None # None for the complete path
    edges: list[int]

    def copy(self):
        ''' Create a deep copy of the path '''
        return Path(
            shape=self.shape,
            start_node=self.start_node,
            current_node=self.current_node,
            edges=self.edges.copy()
        )

@dataclass
class GameState:
    ''' One iteration in the search of the solution.
    Contains the information about remaining visits and available nodes
    '''
    remaining_visits: list[int]
    edge_available: list[bool]
    active_paths: list[Path]
    complete_paths: list[Path]

    @classmethod
    def from_puzzle(cls, puzzle):
        ''' Create new GameState object from a parsed puzzle
        '''
        remaining_visits = [
            node.required_visits
            for node in puzzle.nodes
        ]

        edge_available = [
            True
            for _ in puzzle.edges
        ]

        paths = []

        for shape, starts in puzzle.starts.items():
            for node_id in starts:
                paths.append(
                    Path(
                        shape=shape,
                        start_node=node_id,
                        current_node=node_id,
                        edges=[]
                    )
                )

        return cls(
            remaining_visits=remaining_visits,
            edge_available=edge_available,
            active_paths=paths,
            complete_paths=[]
        )

    def copy(self):
        ''' Copy the Game state (deep copy)
        '''
        return GameState(
            remaining_visits=self.remaining_visits.copy(),
            edge_available=self.edge_available.copy(),
            active_paths=[
                    path.copy()
                    for path in self.active_paths
                ],
            complete_paths=[
                    path.copy()
                    for path in self.complete_paths
                ]
        )

    def available_moves(self, puzzle):
        ''' Return list of available moves from this state as:
        [ (<Path>, [edge_id_1, edge_id_2, edge_id_3]),...]
        '''

        def can_enter_node(path, destination):
            ''' Can a path go into that destination node
            '''
            destination_shape = puzzle.nodes[destination].shape
            if destination_shape != NodeShape.ANY and destination_shape != path.shape:
                return False
            # Node has remaining visits - legit
            if self.remaining_visits[destination] > 0:
                return True


            # If does not have remaining visits,
            # but it is a frontier of the same shape - legit
            for other_path in self.active_paths:
                if (
                    other_path is not path
                    and other_path.shape == path.shape
                    and other_path.current_node == destination
                ):
                    return True

            return False

        result = []

        random.shuffle(self.active_paths)
        for path in self.active_paths:
            moves = []
            current = path.current_node

            random.shuffle(puzzle.node_edges[current])
            for edge_id in puzzle.node_edges[current]:
                if not self.edge_available[edge_id]:
                    continue

                a, b = puzzle.edges[edge_id]
                destination = b if a == current else a

                if not can_enter_node(path, destination):
                    continue

                moves.append(edge_id)

            result.append((path, moves))

        return result

    def find_matching_path(self, shape, node_id, exclude_path):
        ''' Helper for merging paths:
        Find another active path of the same shape ending at node_id.
        '''
        for path in self.active_paths:
            if (
                path is not exclude_path
                and path.shape == shape
                and path.current_node == node_id
            ):
                return path
        return None

    def find_destination_for_move(self, puzzle, path, edge_id):
        ''' Given path and edge (move parameters), find destination node
        '''
        a, b = puzzle.edges[edge_id]
        if path.current_node == a:
            destination = b
        else:
            destination = a
        return destination

    def apply_move(self, puzzle, path, edge_id):
        ''' Create a new state with a move applied.
        input: the puzzle,
        Path object (from where to start the move)
        Edge id where to go
        '''

        new_state = self.copy()

        # Find the same path in copied state
        path_index = self.active_paths.index(path)
        new_path = new_state.active_paths[path_index]

        source = new_path.current_node
        destination = self.find_destination_for_move(puzzle, path, edge_id)

        # Consume destination visit
        if new_state.remaining_visits[destination] > 0:
            new_state.remaining_visits[destination] -= 1

        else:
            # Destination must be a frontier: merge paths and mark them complete
            # Which two paths to merge
            path1 = new_path
            path2 = new_state.find_matching_path(
                shape=path1.shape,
                node_id=destination,
                exclude_path=path1
                )
            merged = Path(
                shape=path1.shape,
                start_node=path1.start_node,
                current_node=path2.start_node,
                edges=(
                    path1.edges
                    + [edge_id]
                    + list(reversed(path2.edges))
                )
                )
            # Add complete paths, remove those we just merged
            new_state.complete_paths.append(merged)
            new_state.active_paths.remove(path1)
            new_state.active_paths.remove(path2)


        # Disable used edge
        new_state.edge_available[edge_id] = False

        # Disable conflicting edges
        if edge_id in puzzle.edge_overlaps:
            overlapping_edge = puzzle.edge_overlaps[edge_id]
            new_state.edge_available[overlapping_edge] = False

        # # If no remaining visits at source node, disable all edges from there
        if self.remaining_visits[source] == 0:
            for edge_id_to_disable in puzzle.node_edges[source]:
                new_state.edge_available[edge_id_to_disable] = False

        # Extend path
        new_path.current_node = destination
        new_path.edges.append(edge_id)

        return new_state

    def expand_path(self, puzzle):
        ''' If path can be expanded to an orphaned node, do it
        '''

        # Find orphan nodes (1 remaining visit, 0 available edges)
        for node_id, remaining in enumerate(self.remaining_visits):
            if remaining != 1:
                continue
            available_edges = sum(
                self.edge_available[edge_id]
                for edge_id in puzzle.node_edges[node_id]
            )
            if available_edges != 0:
                continue

            for far_edge, (near_edge1, near_edge2) in puzzle.shortcuts[node_id].items():
                # Find far_edge in a path with the same shape
                for path in self.active_paths + self.complete_paths:
                    if path.shape != puzzle.nodes[node_id].shape:
                        continue
                    if far_edge not in path.edges:
                        continue
                    # Check if the near paths are not blocked
                    if near_edge1 in puzzle.edge_overlaps and \
                       not self.edge_available[puzzle.edge_overlaps[near_edge1]]:
                        continue
                    if near_edge2 in puzzle.edge_overlaps and \
                       not self.edge_available[puzzle.edge_overlaps[near_edge2]]:
                        continue
                    #print(node_id, ":", far_edge, (near_edge1, near_edge2))
                    #print(path)

                    # Find the first node of the edge to replace (first in path order)
                    # That is, either node, same for -1 and -2 element:
                    edge_index_to_replace = path.edges.index(far_edge)
                    if edge_index_to_replace > 0:
                        first_node_to_replace = \
                            next(iter(set(puzzle.edges[path.edges[edge_index_to_replace]]) \
                                 & set(puzzle.edges[path.edges[edge_index_to_replace-1]])))
                    # If this is a first edge in the path,
                    # it would be the starting point of the path
                    else:
                        first_node_to_replace = path.start_node
                    # Figure out the right order
                    if first_node_to_replace in puzzle.edges[near_edge1]:
                        replacement_1, replacement_2 = near_edge1, near_edge2
                    else:
                        replacement_1, replacement_2 = near_edge2, near_edge1

                    # Do the replacement
                    path.edges[edge_index_to_replace:edge_index_to_replace + 1] = \
                        [replacement_1, replacement_2]
                    #print("replaced:", path)
                    # Mark the visit
                    self.remaining_visits[node_id] -= 1

                    # Disable conflicting edges
                    for replacement in [replacement_1, replacement_2]:
                        if replacement in puzzle.edge_overlaps:
                            overlapping_edge = puzzle.edge_overlaps[replacement]
                            self.edge_available[overlapping_edge] = False

                    # # If no remaining visits at source node, disable all edges from there
                    if self.remaining_visits[node_id] == 0:
                        for edge_id_to_disable in puzzle.node_edges[node_id]:
                            self.edge_available[edge_id_to_disable] = False

                    # Enable edge that we have replaced
                    self.edge_available[far_edge] = True
                    return True

        return False

    def is_solved(self):
        ''' Check whether the puzzle has been solved.
        '''
        return (
            # All node were visited required number of times
            sum(self.remaining_visits) == 0
            # All paths were connected
            and len(self.active_paths) == 0
        )

    def is_viable_by_shapes(self, puzzle):
        ''' Compare the shapes of the remaining nodes and the shapes of the active paths.
        If there are shapes in remaining nodes, but not in active paths, the puzzle is not viable.
        '''
        shapes_in_puzzle = set()
        for node in puzzle.nodes:
            if self.remaining_visits[node.id] > 0 and node.shape != NodeShape.ANY:
                shapes_in_puzzle.add(node.shape)
        shapes_in_paths = set()
        for path in self.active_paths:
            shapes_in_paths.add(path.shape)
        return shapes_in_puzzle <= shapes_in_paths


    def is_viable(self, puzzle):
        '''Return False if the puzzle can no longer be solved.
        '''

        # Check that each node has 2 available edges for each required visit
        for node_id, remaining in enumerate(self.remaining_visits):

            if remaining == 0:
                continue

            available_edges = sum(
                self.edge_available[edge_id]
                for edge_id in puzzle.node_edges[node_id]
            )

            if available_edges < remaining * 2:
                return False

        # Check every active path can continue
        for _, moves in self.available_moves(puzzle):
            if len(moves) == 0:
                return False

        # Check that the shapes of the remaining nodes and the active paths match
        if not self.is_viable_by_shapes(puzzle):
            return False

        return True

    def state_hash(self):
        ''' Hash of a state, that include nodes, edges and frontiers
        (No need to hash paths before the frontiers)
        '''
        return hash(
            (
                tuple(self.remaining_visits),
                tuple(self.edge_available),
                tuple(
                    (path.shape.value, path.current_node)
                    for path in sorted(
                        self.active_paths,
                        key=lambda p: (p.shape.value, p.current_node)
                    )
                )
            )
        )

    def print_info(self):
        ''' List current state information: remaining visits and available edges
        '''
        print("\nRemaining visits")
        print(" ", self.remaining_visits)
        print("Available nodes")
        print(" ", self.edge_available)
        print("Active paths")
        for path in self.active_paths:
            print(" ", path)
        print("Complete paths")
        for path in self.complete_paths:
            print(" ", path)


class Solver:
    ''' Class to collect solving methods and statistics
    '''

    def __init__(self, puzzle, time_limit=10):
        self.puzzle = puzzle

        # Search statistics
        self.states_explored = 0

        # Solution status
        self.is_solved = False
        self.solution = None

        # Time control
        self.time_limit = time_limit
        self.start_time = None
        self.timed_out = False

    def time_exceeded(self):
        '''Check whether the solver has exceeded its time limit.
        '''
        if self.time_limit is None:
            return False
        return (time.time() - self.start_time) > self.time_limit


    def choose_next_state(self, stack):
        ''' In the "reset state" strategy, choose next state
        (BFS, then DFS, sometimes reset to a previous state)
        '''
        if STRATEGY == "BFS":
            return stack.popleft()
        if STRATEGY == "DFS":
            return stack.pop()

        puzzle_size = len(self.puzzle.nodes)

        if STRATEGY == "RESTART":
            puzzle_size = int(puzzle_size * 1.1)

        # BFS in the beginning
        if self.states_explored < puzzle_size**2 * 5:
            return stack.popleft()
        # BFS done, shuffle those states
        if self.states_explored == puzzle_size**2 * 5:
            random.shuffle(stack)
            return stack.pop()

        # Most of the time - DFS
        if self.states_explored % puzzle_size:
            return stack.pop()

        # But occasionally, reset to a previous state, or even to the one of teh BFS states
        if STRATEGY == "RESTART":
            depths = [1]
        elif STRATEGY == "SMART RESTART":
            #depths = [0.10, 0.25, 0.5] * 3 + [0.75, 1]
            depths = [0.10, 0.25, 0.5, 0.10, 0.25, 0.5, 0.10, 0.25, 0.5, 0.75, 1]

        depth = depths[(self.states_explored // puzzle_size) % len(depths)]
        idx = int((1 - depth) * len(stack))
        item = stack[idx]
        del stack[idx]
        return item

    def solve(self):
        ''' 
        Depth-first search with custom logic to choose the next state (regular restarts)
        '''
        random.seed(0)
        self.start_time = time.time()

        # Initiate the queue with teh starting GameState
        initial = GameState.from_puzzle(self.puzzle)

        stack = deque([initial])

        # Initialize the cache
        visited = set()
        visited.add(initial.state_hash())

        while stack:

            # Check timeout
            if self.time_exceeded():
                self.timed_out = True
                return None

            state = self.choose_next_state(stack)

            self.states_explored += 1

            if state.is_solved():
                self.is_solved = True
                self.solution = state
                return state

            if not state.is_viable(self.puzzle):
                continue

            for path, moves in state.available_moves(self.puzzle):

                for edge_id in moves:

                    new_state = state.apply_move(
                        self.puzzle,
                        path,
                        edge_id
                    )

                    # while new_state.expand_path(self.puzzle):
                    #     pass

                    # Add state to the queue if not cached
                    state_id = new_state.state_hash()
                    if state_id in visited:
                        continue
                    visited.add(state_id)
                    stack.append(new_state)

        return None


    def print_stats(self):
        '''Brief stats for the solver status'''

        print(f"States explored: {self.states_explored}")

        if self.timed_out:
            print("Search timed out")
        elif self.solution is None:
            print("Puzzle is not solved")
        else:
            print("Puzzle is solved")

        if self.start_time:
            elapsed = time.time() - self.start_time
            print(f"Time elapsed: {elapsed:.2f}s")


def main():
    ''' Lyne solver
    '''
    puzzle_file = "puzzles.json"
    puzzle_name = "f-01"
    puzzle_text = ""
    with open(puzzle_file, "r", encoding="utf-8") as f:
        puzzles = json.load(f)
        for puzzle in puzzles:
            if puzzle["name"] == puzzle_name:
                puzzle_text = puzzle["puzzle"]

    # Solve one puzzle
    puzzle = Puzzle(puzzle_text, verbose=True)

    for STRATEGY in ["BFS", "DFS", "RESTART", "SMART RESTART"]:
        print(f"\nUsing strategy: {STRATEGY}")
        solver = Solver(puzzle, time_limit=100)

        solver.solve()
        solver.print_stats()
        human_solution = puzzle.export_solution(solver.solution)
        for line in human_solution:
            print(line)

if __name__ == "__main__":
    main()
