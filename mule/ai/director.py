import datetime, logging, re
from mule import *

class Director(object):
    def __init__(self, game):
        self.game = game
        self.log = logging.getLogger('%s.%s' % (
            __name__, self.__class__.__name__
            ))
        self.capitals = [world for world in self.getCapitals()]

    def getCapitals(self):
        for world in self.game.worlds.values():
            if self.game.sovereignID == world.sovereignID \
                    and any(x == world.designation for x in (27, 147)):
                yield world

    def filterSectorWorlds(self, worlds):
        for world in worlds:
            if any(Game.SECTOR_RADIUS > world.distanceTo(capital) \
                    for capital in self.capitals):
                yield world

    def update(self):
        pass

