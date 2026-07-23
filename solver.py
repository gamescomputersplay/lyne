''' Solver for the game LYNE
'''

from dataclasses import dataclass
from enum import Enum, auto
from collections import defaultdict

## Legend:
# d|s|t - diamond | square | triangle - basic node
# D|S|T - same, starting node
# 2|3|4 - no shape node that has to be visited that many times
# [space] - no node

test_puzzle = [
    "T sSS",
    "tts3s",
    "tT22d",
    "Dd22D",
]
test_puzzle = [
    "Tt",
    "Tt",
]

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


        # Lookup table {node_id:[edge_id,...], ...}
        self.edge_overlaps = self.generate_edge_overlaps()



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

                if char.lower() == "t":
                    shape = NodeShape.TRIANGLE
                    visits = 1

                elif char.lower() == "s":
                    shape = NodeShape.SQUARE
                    visits = 1

                elif char.lower() == "d":
                    shape = NodeShape.DIAMOND
                    visits = 1

                elif char.isdigit():
                    shape = NodeShape.ANY
                    visits = int(char)

                else:
                    raise ValueError(f"Unknown symbol: {char}")

                nodes.append(
                    Node(
                        id=node_id,
                        row=row,
                        col=col,
                        shape=shape,
                        required_visits=visits
                    )
                )

                if char.isupper():
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

@dataclass
class GameState:
    ''' One iteration in the search of the solution.
    Contains the information about remaining visits and available nodes
    '''
    remaining_visits: list[int]
    edge_available: list[bool]
    frontier: dict[NodeShape, list[int]]
    path: list[int]

    def copy(self):
        ''' Create a copy of itself
        '''
        return GameState(
            remaining_visits=self.remaining_visits.copy(),
            edge_available=self.edge_available.copy(),
            frontier={
                shape: nodes.copy()
                for shape, nodes in self.frontier.items()
            },
            path=self.path.copy()
        )



def main():
    ''' Lyne solver
    '''

    puzzle = Puzzle(test_puzzle, verbose=True)

if __name__ == "__main__":
    main()
