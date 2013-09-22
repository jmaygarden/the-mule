import datetime, logging, re
from mule import *
from director import Director

class ScoutDirector(Director):
    def __init__(self, game):
        super(ScoutDirector, self).__init__(game)
        self.capital = game.worlds[game.userInfo['capitalObjID']]

    def _observe(self):
        self.log.info('Observing world resources...')
        TIMESTAMP = datetime.datetime.now()
        for world in self.game.worlds.values():
            if 'resources' in world.data:
                self.game.cursor.execute("""
                INSERT OR REPLACE INTO Worlds
                (id, timestamp, groundForces, spaceForces)
                VALUES (?, ?, ?, ?)
                """, (
                    world.id,
                    TIMESTAMP,
                    world.groundForces,
                    world.spaceForces))
            else:
                count = self.game.cursor.execute(
                        "SELECT COUNT(*) FROM Worlds WHERE id = ?",
                        (world.id,)).fetchone()[0]
                if 0 == count:
                    self.log.info('Adding %s to the database' % world.name)
                    self.game.cursor.execute(
                            "INSERT INTO Worlds (id) VALUES (?)",
                            (world.id,))
        self.game.connection.commit()

    def _command(self):
        self.log.info('Dispatching scouts...')
        worlds = [
                self.game.worlds[row[0]] for row in self.game.cursor.execute("""
        SELECT id FROM Worlds
        ORDER BY (CASE WHEN timestamp IS NULL THEN 1 ELSE 0 END) DESC,
        timestamp ASC
        """).fetchall()
                #if Game.SECTOR_RADIUS > self.capital.distanceTo(
                    #self.game.worlds[row[0]])
                ]
        scouts = [fleet for fleet in self.game.fleets.values()
                if self.game.sovereignID == fleet.sovereignID and \
                    re.search('Scout', fleet.name, re.IGNORECASE)]
        exclusion = [fleet.destID for fleet in scouts
                if 'destID' in fleet.data]
        class WorldIterator(object):
            def __init__(self, worlds, exclusion):
                self.worlds = worlds
                self.exclusion = exclusion
                self.index = 0
            def next(self):
                while self.index < len(self.worlds):
                    world = self.worlds[self.index]
                    self.index += 1
                    if world.id not in self.exclusion:
                        return world
        iterator = WorldIterator(worlds, exclusion)
        for fleet in scouts:
            if 'destID' in fleet.data:
                self.log.info("\t'%s' enroute to '%s' (%d)",
                        fleet.name, self.game.worlds[fleet.destID].name,
                        fleet.destID)
            else:
                world = iterator.next() or self.capital
                self.log.info("\t'%s' to '%s' (%d)" % (
                    fleet.name, world.name, world.id))
                fleet.setDestination(world)

    def update(self):
        self._observe()
        self._command()

