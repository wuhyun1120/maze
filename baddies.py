'''
    baddies.py

    Definitions for some example baddies
'''
import random

from maze import Baddy, UP, DOWN, LEFT, RIGHT, STAY

class StaticBaddy(Baddy):
    ''' A static baddy - does not move from its initial position '''

    def take_turn(self, _obstruction, _ping_response):
        ''' Stay where we are '''
        return STAY

class RandomBaddy(Baddy):
    ''' A random-walking baddy '''

    def take_turn(self, obstruction, _ping_response):
        ''' Ignore any ping information, just choose a random direction to walk in. We can't ping. '''
        possibilities = [direction for direction in (UP, DOWN, LEFT, RIGHT) if not obstruction[direction]]
        return random.choice(possibilities)
