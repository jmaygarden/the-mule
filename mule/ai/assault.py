import datetime, logging, re
from mule import *
from director import Director

class AssaultDirector(Director):
    def __init__(self, game):
        super(AssaultDirector, self).__init__(game)
        self.capital = game.worlds[game.userInfo['capitalObjID']]

    def _command(self):
        self.log.info('Dispatching assault fleets...')
        fleets = [fleet for fleet in self.game.fleets.values()
                if self.game.sovereignID == fleet.sovereignID and \
                        re.search('Assault', fleet.name, re.IGNORECASE)]
        exclusion = [fleet.destID for fleet in fleets
                if 'destID' in fleet.data]
        for fleet in fleets:
            if 'destID' in fleet.data and \
                    1 == self.game.worlds[fleet.destID].sovereignID:
                self.log.info("\t'%s' enroute to '%s' (%d)",
                        fleet.name, self.game.worlds[fleet.destID].name,
                        fleet.destID)
            elif 'anchorObjID' in fleet.data and \
                    1 == self.game.worlds[fleet.anchorObjID].sovereignID and \
                    self.game.worlds[fleet.anchorObjID].spaceForces < fleet.spaceForces / 10 and \
                    self.game.worlds[fleet.anchorObjID].groundForces < fleet.groundForces / 2:
                world = self.game.worlds[fleet.anchorObjID]
                self.log.info("\t'%s' invading '%s' (%d)",
                        fleet.name, world.name, world.id)
                self.game.attack(world.data, 'invasion')
            else:
                worlds = [
                        self.game.worlds[row[0]] for row
                        in self.game.cursor.execute("""
                        SELECT id FROM Worlds WHERE timestamp IS NOT NULL
                        AND spaceForces < ? AND groundForces < ?
                        ORDER BY spaceForces, groundForces
                        """,
                        (fleet.spaceForces / 10, fleet.groundForces / 2)
                        ).fetchall()
                        if 1 == self.game.worlds[row[0]].sovereignID and \
                                self.game.worlds[row[0]].id not in exclusion and \
                                Game.SECTOR_RADIUS > self.capital.distanceTo(self.game.worlds[row[0]])
                                ]
                def pick_world():
                    for world in worlds:
                        if 9 > world.techLevel:
                            return world
                world = pick_world() or self.capital
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

