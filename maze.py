'''
    maze.py

    The main maze library.

    This defines the Player abstract base class and to derived classes - Goody and Baddy.

    It also defines the game-playing classes:
        Maze - a container for holding the layout of a maze (walls and spaces) and for asking questions about
               particular positions in the maze

        Move - a small class whose instances represent the different moves that a player can take
            UP, DOWN, LEFT, RIGHT, STAY, PING
        Obstruction - a dict-like object, subscriptable by a Move, used to inform a player of their surroundings

        Position - a two-dimensional vector that supports some binary operations, and l1 norm, which might be helpful.

        Game - A class responsible for placing the players within the maze, asking them to take their turn, and
               detecting end-of-game conditions.

    Some utility function for repeatedly playing games, and the helper objects are also defined here:
        STEP, DX, DY, ZERO
        game_generator
        game_repeater
'''

import random
import unittest

from abc import ABC, abstractmethod


class Move(object):
    ''' An instruction returned by goodies and baddies.
        'name' is the human-readable name
    '''
    def __init__(self, name):
        if not isinstance(name, str):
            raise TypeError("'name' must be a string, got: {}".format(name))
        self.name = name

    def __str__(self):
        return self.name

    def __hash__(self):  # Make Moves usable as dict keys
        return hash((type(self), self.name))

    def __repr__(self):
        return self.name


STAY  = Move("stay")
UP    = Move("up")
LEFT  = Move("left")
DOWN  = Move("down")
RIGHT = Move("right")
PING  = Move("ping")

class Position(object):
    ''' A 2-dimensional x, y position, supporting addition and subtraction with other Position objects
        and 2-tuples of ints.
    '''
    __slots__ = ("x", "y")

    def __init__(self, x, y):
        self.x = x
        self.y = y

    @classmethod
    def _convert(cls, value):
        ''' Pass through values of the correct type, otherwise try to expand them as (x, y) coordinates '''
        return value if isinstance(value, cls) else cls(*value)

    def __add__(self, other):
        other = self._convert(other)
        return Position(self.x + other.x, self.y + other.y)  # Add components individually

    def __radd__(self, other):
        return self + other  # Commutative, so use the same implementation as above

    def __sub__(self, other):
        other = self._convert(other)
        return Position(self.x - other.x, self.y - other.y)

    def __rsub__(self, other):
        return self._convert(other) - self  # Convert 'other' to a Position, then use the implementation above

    def __repr__(self):
        return "{}({}, {})".format(type(self).__name__, self.x, self.y)

    def __str__(self):
        return "({}, {})".format(self.x, self.y)

    def __neg__(self):
        return Position(-self.x, -self.y)

    def __eq__(self, other):
        if isinstance(other, tuple):
            other = self._convert(other)  # Allow loose equality comparisons with 2-tuples
        elif not isinstance(other, Position):
            return False
        return self.x == other.x and self.y == other.y

    def __hash__(self):
        return hash((type(self), self.x, self.y))

    def __ne__(self, other):
        return not self == other

    def l1_norm(self):
        ''' Return the sum of the abs of the components '''
        return abs(self.x) + abs(self.y)

# Some common positions / position changes
ZERO = Position(0, 0)
DX = Position(1, 0)
DY = Position(0, 1)
STEP = {UP: DY, LEFT: -DX, DOWN: -DY, RIGHT: DX, STAY: ZERO}

def _cell_str(value):
    ''' Private function, used when printing mazes '''
    return "X" if value else " "

class Obstruction(object):
    ''' An object that tells a player about nearby obstructions.
        Subscript this with a direction to receive True if there is an obstruction, else False
        e.g. obstruction[UP]  # --> True or False
    '''
    def __init__(self, up, left, down, right):
        self._state = {UP: up, LEFT: left, DOWN: down, RIGHT: right}

    def __getitem__(self, key):
        if not isinstance(key, Move):
            raise ValueError("Obstructions must be looked up by direction (UP, DOWN, LEFT, RIGHT). Got: {}"
                             .format(key))
        return self._state[key]

    def __str__(self):
        return "\n".join(["." +            _cell_str(self[UP])         + ".",
                          _cell_str(self[LEFT]) + "o" + _cell_str(self[RIGHT]),
                          "." +            _cell_str(self[DOWN])       + "."])


class Player(ABC):
    ''' Common base class for goodies and baddies '''

    @abstractmethod
    def take_turn(self, obstruction, ping_response):
        ''' Decide how to move.

            'obstruction' will be an Obstruction object, which can be interrogated to find nearby walls.
            This will always be provided.

            'ping_response' will be None, unless someone PINGed last turn, in which case it will be a dict
            mapping the other players to their relative positions.

            The player must decide what to do and return one of the Move objects:
            UP, DOWN, LEFT, RIGHT, PING, or STAY

            Not all moves are allowed by all players.
        '''
        pass

class Goody(Player):
    ''' A Goody.

        A game contains two Goodies and one Baddy.

        A Goody's task is to meet up with the other Goody before either of them are caught by the Baddy.

        Goodies can move however they like - UP, DOWN, LEFT, RIGHT, or STAY.
        An attempt to move somewhere there is an obstacle will result in them loosing their turn.

        They can also decide to PING. They will remain at the same location, but next move they will
        learn the relative positions of the other Goody and the Baddy. The other players will also learn this!
    '''
    pass


class Baddy(Player):
    ''' A Baddy.

        The Baddy's task is to catch either of the Goodies before they meet up with one another.

        Baddies may move UP, DOWN, LEFT, RIGHT, or STAY - but they cannot PING.

        They do, however, learn the relative positions of the two Goodies whenever they PING.
    '''
    pass


class Maze(object):
    ''' A Maze.

        A maze can be initialised with a width and a height, and optionally a string of (width * height) 0's and 1's
        which designate each cell as either space (0) or wall (1).

        By default the maze is initialised as empty space.

        All mazes consider themselves to be bounded by walls outside the (width * height) area.

        The state of a cell can be interrogated by subscripting the object with an (x, y) pair, or a Position object
        e.g. maze[4, 5]  # -> Maze.space (== 0) or Maze.wall (== 1)
    '''
    space = 0
    wall  = 1

    def __init__(self, width, height, data=None):
        if not isinstance(width, int) or not isinstance(height, int):
            raise TypeError("width and height must both be ints. Got {} and {}".format(width, height))
        self.width = width
        self.height = height
        if data is not None:
            if not isinstance(data, str):
                raise TypeError("'data' must be a string, got: {}".format(data))
            if len(data) != width * height:
                raise ValueError("'data' must be a string of length {}, but it has length {}".format(
                                 width * height, len(data)))
        self._cells = []  # A list of lists, subscripted like this: _cells[y][x]
                          # Arranging the rows in this way makes it easier to print the maze

        # Initialise self._cells - either as a blank maze, or from the input data
        for y in range(self.height):
            if data is None:
                row = [Maze.space] * self.width
            else:
                row = list(map(int, data[y * self.width:(y + 1) * self.width]))
            self._cells.append(row)
        self._cells.reverse()

    def __getitem__(self, index):
        if isinstance(index, tuple):
            if len(index) != 2:
                raise ValueError("index must be a Position or an x, y pair. Got: {}".format(index))
            index = Position(*index)

        if not (0 <= index.x < self.width) or not (0 <= index.y < self.height):
            return Maze.wall
        else:
            return self._cells[index.y][index.x]

    def __setitem__(self, index, value):
        if isinstance(index, tuple):
            if len(index) != 2:
                raise ValueError("index must be a Position or an x, y pair. Got: {}".format(index))
            index = Position(*index)
        if value not in (Maze.wall, Maze.space):
            raise ValueError("value must be either Maze.space or Maze.wall")

        if not (0 <= index.x < self.width) or not (0 <= index.y < self.height):
            raise IndexError("{} is out of bounds (0-{}, 0-{})".format(index, self.width - 1, self.height - 1))

        self._cells[index.y][index.x] = value

    def __str__(self):
        parts = ["X" * (self.width + 2)]  # Top border
        for row in reversed(self._cells):
            parts.append("X" + "".join("X" if cell else " " for cell in row) + "X")  # Rows with left/right border
        parts.append(parts[0])  # Bottom border
        return "\n".join(parts)

    def __repr__(self):
        return "{}({}, {}, {})".format(type(self).__name__, self.width, self.height,
                                       "".join(str(cell) for row in self._cells for cell in row))

    def __getstate__(self):
        return (self.width, self.height, self._cells)

    def __setstate__(self, state):
        self.width, self.height, self._cells = state

    def obstruction(self, position):
        ''' Returns an Obstruction object for the given x, y position '''
        return Obstruction(bool(self[position + STEP[UP]]),
                           bool(self[position + STEP[LEFT]]),
                           bool(self[position + STEP[DOWN]]),
                           bool(self[position + STEP[RIGHT]]))

    def empty_cells(self):
        ''' Return the number of empty cells in this maze '''
        return sum(not cell for row in self._cells for cell in row)

    def __mul__(self, other):
        ''' Multiply a maze by a (x, y) tuple - return a new maze that is this one repeated 'x' times in the
            x directions and 'y' times in the y direction
        '''
        if not isinstance(other, tuple):
            raise TypeError("Can only multiple a maze by an (x, y) tuple, got:{}".format(other))
        x_repeats, y_repeats = other
        new_cells = []
        for _ in range(y_repeats):
            for y in range(self.height):
                new_cells.append(self._cells[y] * x_repeats)
        new_maze = Maze(self.width * x_repeats, self.height * y_repeats)
        new_maze._cells = new_cells
        return new_maze


class Game(object):
    ''' A Game takes a Maze, two Goodies and one Baddy.
        It places the three players at random empty cells in the maze, then allows them to take turns in moving,
        passing them any needed information.
    '''

    not_started = "not started"
    in_play = "in play"
    goodies_win = "goodies win"
    baddy_wins = "baddy wins"
    draw = "draw"

    def __init__(self, maze, goody0, goody1, baddy, max_rounds=10000):
        if (not isinstance(maze, Maze) or not isinstance(goody0, Goody) or not isinstance(goody1, Goody)
            or not isinstance(baddy, Baddy)):
            raise TypeError("A Game must be initialised with a maze, two goodies, and a baddy. Got:\n{}".format(
                            (maze, goody0, goody1, baddy)))
        self.maze = maze
        self.goody0 = goody0
        self.goody1 = goody1
        self.baddy = baddy

        self.players = (self.goody0, self.goody1, self.baddy)

        self.position = {}  # a dict mapping player to Position
        self._place_players()

        self.round = 0  # How many rounds of turns we've had so far
        self.max_rounds = max_rounds  # The maximum number of rounds we're allowed before calling it a draw
        self.ping = False  # Whether a ping should be triggered at the start of the next round
        self.status = Game.not_started

    def _place_players(self):
        ''' Randomly place the two goodies and the baddy in the maze '''
        taken = []
        max_attempts = 1000  # Just to avoid an infinite loop. We expect to place a player much sooner than this!
        for player in self.players:
            for _ in range(max_attempts):
                new_position = Position(random.randint(0, self.maze.width - 1), random.randint(0, self.maze.height - 1))
                if new_position not in taken and self.maze[new_position] == Maze.space:
                    taken.append(new_position)
                    self.position[player] = new_position
                    break
            else:
                # We've used up all our attempts! What sort of maze is this ?!?!
                raise ValueError("Failed to randomly place a player in {} attempts - the maze is too dense!"
                                 .format(max_attempts))

    def _ping_response_for_player(self, player):
        ''' Construct a ping response for the given player '''
        return {other_player: self.position[other_player] - self.position[player]
                for other_player in self.players
                if other_player is not player}

    def do_round(self):
        ''' Do a round of turns - goody1, goody2, then the baddy.
            If a ping was requested that is computed before anyone moves.
            Return the new status of the game.
        '''
        if self.status == Game.not_started:
            self.status = Game.in_play
        elif self.status != Game.in_play:
            return self.status

        self.round += 1
        if self.round == self.max_rounds:
            self.status = Game.draw
            return self.status

        if self.ping:
            # Prepare ping responses object for the goodies and baddy
            ping_response = {player: self._ping_response_for_player(player) for player in self.players}
            self.ping = False
        else:
            ping_response = dict.fromkeys(self.players, None)

        for player in self.players:
            obstruction = self.maze.obstruction(self.position[player])
            action = player.take_turn(obstruction, ping_response[player])

            # Handle the cases that result in no action
            if (action == STAY or
                action in (UP, DOWN, LEFT, RIGHT) and obstruction[action] or
                action == PING and isinstance(player, Baddy)):
                continue

            if action == PING:
                self.ping = True
            else:
                self.position[player] += STEP[action]

            # Check for game over
            if isinstance(player, Goody):
                if self.position[self.goody0] == self.position[self.goody1]:
                    # The goodies have met
                    self.status = Game.goodies_win
                    break
                elif self.position[player] == self.position[self.baddy]:
                    # The goody walked into the baddy
                    self.status = Game.baddy_wins
                    break
            else:
                if self.position[self.baddy] in (self.position[self.goody0], self.position[self.goody1]):
                    # The baddy caught a goody
                    self.status = Game.baddy_wins
                    break

        return self.status

    def play(self, hook=None):
        ''' Keep playing until there is a result. Returns the result and the number of rounds.
            'hook' will be called after each round. It should accept one argument - the game.
        '''
        while True:
            result = self.do_round()
            if callable(hook):
                hook(self)
            if result != Game.in_play:
                return result, self.round

    def __str__(self):
        ''' Pretty-printable version of the current state of the game '''
        maze_cells = [bytearray(row.encode("ascii")) for row in reversed(str(self.maze).splitlines())]
        maze_cells[self.position[self.goody0].y + 1][self.position[self.goody0].x + 1] = ord("G")
        maze_cells[self.position[self.goody1].y + 1][self.position[self.goody1].x + 1] = ord("G")
        maze_cells[self.position[self.baddy].y + 1][self.position[self.baddy].x + 1] = ord("B")
        maze = "\n".join(str(row.decode("ascii")) for row in reversed(maze_cells))
        parts = [maze,
                 "Status: " + self.status,
                 "Round: " + str(self.round),
                 "Goody0:" + str(self.position[self.goody0]),
                 "Goody1:" + str(self.position[self.goody1]),
                 "Baddy:"  + str(self.position[self.baddy])
                 ]
        return "\n".join(parts)

def game_generator(mazes, goody0s, goody1s, baddies, max_rounds=10000):
    ''' A generator that yields Games.
        Provide it with iterables of mazes, goodies (for goody 0 and 1), and baddies
    '''
    for maze, goody0, goody1, baddy in zip(mazes, goody0s, goody1s, baddies):
        yield Game(maze, goody0, goody1, baddy, max_rounds=max_rounds)

def game_repeater(maze, goody0_cls, goody1_cls, baddy_cls, max_rounds=10000)        :
    ''' A generator of instances of identical games '''
    while True:
        yield Game(maze, goody0_cls(), goody1_cls(), baddy_cls(), max_rounds=max_rounds)


class PositionTest(unittest.TestCase):
    ''' Test that the Position class is functioning as expected '''

    def setUp(self):
        ''' Define a couple of position objects to use in tests '''
        self.pos1 = Position(5, 7)
        self.pos2 = Position(-4, 9)

    def test_addition(self):
        self.assertEqual(self.pos1 + self.pos2, Position(1, 16))

    def test_subtraction(self):
        self.assertEqual(self.pos1 - self.pos2, Position(9, -2))

    def test_negation(self):
        self.assertEqual(-self.pos1, Position(-5, -7))

    def test_equality(self):
        self.assertTrue(self.pos1 == self.pos1)

    def test_l1_norm(self):
        self.assertTrue(self.pos1.l1_norm() == 12)
        self.assertTrue(self.pos2.l1_norm() == 13)

    def test_inequality(self):
        self.assertTrue(self.pos1 != self.pos2)


if __name__ == "__main__":
    # Run the unittests in this script, with a nice level of output
    unittest.main(verbosity=2)
