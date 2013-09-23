import datetime, logging, pprint, re
from mule import *
from director import Director

class ArmadaDirector(Director):
    def __init__(self, game):
        super(ArmadaDirector, self).__init__(game)

    def _command(self):
        self.log.info('Dispatching armadas...')
        fleets = [fleet for fleet in self.game.fleets.values()
                if self.game.sovereignID == fleet.sovereignID and \
                        re.search('Armada', fleet.name, re.IGNORECASE)]
        exclusion = [fleet.destID for fleet in fleets \
                if 'destID' in fleet.data]
        exclusion.extend([fleet.anchorObjID for fleet in fleets \
                if 'anchorObjID' in fleet.data])
        worlds = self.filterSectorWorlds(
                self.game.worlds[row[0]] for row
                in self.game.cursor.execute("SELECT id FROM Worlds").fetchall()
                if 1 == self.game.worlds[row[0]].sovereignID and \
                        self.game.worlds[row[0]].id not in exclusion and \
                        9 > self.game.worlds[row[0]].techLevel
                        )
        for fleet in fleets:
            if 'destID' in fleet.data and \
                    1 == self.game.worlds[fleet.destID].sovereignID:
                self.log.info("\t'%s' enroute to '%s' (%d)",
                        fleet.name, self.game.worlds[fleet.destID].name,
                        fleet.destID)
            elif 'anchorObjID' in fleet.data and \
                    1 == self.game.worlds[fleet.anchorObjID].sovereignID:
                world = self.game.worlds[fleet.anchorObjID]
                self.log.info(
                        "\t'%s' establishing space supremacy at '%s' (%d)",
                        fleet.name, world.name, world.id)
                self.game.attack(world.data, 'spaceSupremacy')
            else:
                targets = sorted(worlds, key=lambda x: fleet.distanceTo(x))
                def pick_world():
                    for world in targets:
                        return world
                world = pick_world() or min(self.capitals, key=lambda x: fleet.distanceTo(x))
                if 'anchorObjID' in fleet.data and \
                        world.id == fleet.anchorObjID:
                    self.log.info("\t'%s' achoring at '%s' (%d)",
                            fleet.name, world.name, world.id)
                else:
                    self.log.info("\t'%s' to '%s' (%d)" % (
                        fleet.name, world.name, world.id))
                    fleet.setDestination(world)

    def update(self):
        self._command()

