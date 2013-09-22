import datetime, logging, re
from mule import *

class Director(object):
    def __init__(self, game):
        self.game = game
        self.log = logging.getLogger('%s.%s' % (
            __name__, self.__class__.__name__
            ))

    def update(self):
        pass

