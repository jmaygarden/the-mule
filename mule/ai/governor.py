import datetime, logging, pprint, re
from mule import *
from director import Director

class WorldDirector(Director):
    MIN_SPACE_FORCES = 250.0

    def __init__(self, game):
        super(WorldDirector, self).__init__(game)
        self.game = game
        self.log = logging.getLogger('%s.%s' % (
            __name__, self.__class__.__name__
            ))

    def _allocate(self, world, trait):
        if 'isFixed' in trait and trait['isFixed']:
            entry = self.game.types[trait['traitID']]
            if 4.0 > trait['allocation']:
                self.log.info("Set '%s' allocation to %f on '%s'." % (
                        entry['nameDesc'].encode('ascii', 'ignore'), 5.0,
                        world.name))
                self.game.setIndustryAlloc(world.data, entry['id'], 5.0)

    def _deallocate(self, world, trait):
        if 'isFixed' in trait and trait['isFixed']:
            entry = self.game.types[trait['traitID']]
            if 0.1 < trait['allocation']:
                self.log.info("Set '%s' allocation to %f on '%s'." % (
                        entry['nameDesc'].encode('ascii', 'ignore'), 0.0,
                        world.name))
                self.game.setIndustryAlloc(world.data, entry['id'], 0.0)

    def _upgrade(self, world):
        excludes = [11, 23, 126] # exclude defenses with a chromium requirement
        traits = []
        def exclude_precursor(trait):
            designType = self.game.types[trait]
            if 'buildUpgrade' in designType:
                for x in designType['buildUpgrade']:
                    excludes.append(x)
                    exclude_precursor(x)
        for trait in world.traits:
            if type(trait) is dict:
                if WorldDirector.MIN_SPACE_FORCES > world.spaceForces:
                    self._allocate(world, trait)
                else:
                    self._deallocate(world, trait)
                trait = trait['traitID']
            traits.append(trait)
            exclude_precursor(trait)
        def check_requirements(entry):
            return 'buildRequirements' not in entry \
                    or [i for i in entry['buildRequirements'] if i in traits]
        def check_upgrade(entry):
            return 'buildUpgrade' not in entry \
                    or set(entry['buildUpgrade']).issubset(traits)
        for entry in self.game.types.values():
            if 'category' in entry \
                    and 'improvement' == entry['category'] \
                    and 'buildTime' in entry \
                    and 'techLevelAdvance' not in entry:
                if entry['id'] not in traits \
                        and entry['id'] not in excludes \
                        and world.techLevel >= entry['minTechLevel'] \
                        and check_upgrade(entry) \
                        and check_requirements(entry):
                    self.log.info("Building '%s' on '%s'." % (
                        entry['nameDesc'].encode('ascii', 'ignore'),
                        world.name))
                    self.game.buildImprovement(world.data, entry)

    def update(self):
        self.log.info('Building upgrades...')
        for world in self.game.worlds.values():
            if self.game.sovereignID == world.sovereignID:
                self._upgrade(world)

    def deploy(self):
        for world in self.game.worlds.values():
            if self.game.sovereignID == world.sovereignID:
                resources = []
                for i in xrange(0, len(world.resources), 2):
                    resType = self.game.types[world.resources[i]]
                    resCount = world.resources[i+1]
                    if 'maneuveringUnit' == resType['category'] \
                            and 50.0 <= resType['FTL']:
                        resources.append(world.resources[i])
                        resources.append(world.resources[i+1])
                if 0 < len(resources):
                    self.log.info("Deploying from '%s'..." % world.name)
                    for j in xrange(0, len(resources), 2):
                        resType = self.game.types[resources[j]]
                        resCount = resources[j+1]
                        self.log.info('\t%s: %d' %(
                            resType['nameDesc'].encode('ascii', 'ignore'),
                            resCount))
                    world.deployFleet(resources)

    def gather(self, world):
        for fleet in self.game.find('Fleet'):
            if isinstance(fleet, Fleet) and \
                    self.game.sovereignID == fleet.sovereignID:
                if 'anchorObjID' in fleet.data and \
                        fleet.anchorObjID == world.id:
                    self.log.info('\t%s on %s', fleet.name, world.name)
                    fleet.transferFleet(world)
                elif 'destID' in fleet.data and fleet.destID == world.id:
                    self.log.info('\t%s enroute to %s', fleet.name, world.name)
                else:
                    self.log.info('\t%s to %s', fleet.name, world.name)
                    fleet.setDestination(world)

