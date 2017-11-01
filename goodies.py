'''
    goodies.py

    Definitions for some example goodies
'''

import random

from maze import Goody, UP, DOWN, LEFT, RIGHT, STAY, PING, Position
from maze import STEP

OPPOSITE = {UP: DOWN, DOWN: UP, LEFT: RIGHT, RIGHT: LEFT}

class StaticGoody(Goody):
    ''' A static goody - does not move from its initial position '''

    def take_turn(self, _obstruction, _ping_response):
        ''' Stay where we are '''
        return STAY

class RandomGoody(Goody):
    ''' A random-walking goody '''

    def take_turn(self, obstruction, _ping_response):
        ''' Ignore any ping information, just choose a random direction to walk in, or ping '''
        possibilities = [direction for direction in [UP, DOWN, LEFT, RIGHT] if not obstruction[direction]] + [PING]
        return random.choice(possibilities)


class TPWGoody(Goody):
    ''' A goody with some preferences moving left/down unless it is stuck.
    When it is stuck (i.e. both left and down are blocked), it moves to the point where there are more than two free ways.
    It also remembers dead ends and consider them as walls '''

    def __init__(self):
        self.turn = 1
        self.position = Position(0, 0)  # Goody's position relative to its initial point.
        self.known_walls = []
        self.known_spaces = []
        self.is_stuck = False
        self.last_move = LEFT

    def take_turn(self, obstruction, _ping_response):
        # Identify adjacent walls and spaces and remember the new ones
        adjacent_walls = []
        adjacent_spaces = []
        allowed = []
        for direction in [UP, DOWN, LEFT, RIGHT]:
            pos = self.position + STEP[direction]
            if pos in self.known_walls:
                adjacent_walls.append(pos)
            elif obstruction[direction]:
                adjacent_walls.append(pos)
                self.known_walls.append(pos)
            else:
                adjacent_spaces.append(pos)
                allowed.append(direction)
                if pos not in self.known_spaces:
                    self.known_spaces.append(pos)

        # If there are at most one wall, free it from the 'stuck' mode
        if len(adjacent_walls) <= 1:
            self.is_stuck = False
        # Identify dead ends as walls
        elif len(adjacent_walls) == 3:
            self.known_walls.append(self.position)
        # See if it's stuck at a left down corner. If yes, change into the 'stuck' mode
        if DOWN not in allowed and LEFT not in allowed:
            self.is_stuck = True

        if self.is_stuck:
            move = self.stuck_choice(allowed)
        else:
            move = self.normal_choice(allowed)

        # Save the move and update the new position
        self.last_move = move
        self.position = self.position + STEP[move]
        return move

    def normal_choice(self, allowed):
        ''' A normal move choice. Biased towards taking DOWN or LEFT'''
        possibilities = [direction for direction in [UP, DOWN, DOWN, DOWN, DOWN, LEFT, LEFT, LEFT, LEFT, RIGHT] if
                         direction in allowed]
        move = random.choice(possibilities)
        return move

    def stuck_choice(self, allowed):
        ''' A 'stuck' state move choice. Move away from its previous position, unless it is a dead end'''
        if len(allowed) == 1:
            return allowed[0]
        elif len(allowed) == 2:
            return [direction for direction in allowed if direction != OPPOSITE[self.last_move]][0]
        else:
            print("Should not reach this point. The variable 'is_stuck' is not properly turned off")
            exit(1)

