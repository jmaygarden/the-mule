import json, logging, math, re, requests, sqlite3, sys
import pprint

class Game:
    SECTOR_RADIUS = 250.0

    def __init__(self, gameID):
        self.gameID = gameID
        self.types = {}
        self.fleets = {}
        self.worlds = {}
        self.connection = sqlite3.connect('game%d.db' % gameID)
        self.cursor = self.connection.cursor()
        self.check_schema()
        self.pp = pprint.PrettyPrinter()
        self.log = logging.getLogger(__name__)
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'The Mule/0.1',
            })

    def __del__(self):
        self.connection.close()

    def check_schema(self):
        try:
            self.cursor.execute("SELECT key, value FROM KVStore LIMIT 1")
            self.cursor.execute("SELECT id, data FROM Types LIMIT 1")
            self.cursor.execute("SELECT id, data FROM Objects LIMIT 1")
            self.cursor.execute("""
            SELECT id, timestamp, spaceForces, groundForces, fleetForces FROM Worlds LIMIT 1
            """)
        except sqlite3.OperationalError:
            self.cursor.execute(
                    "CREATE TABLE KVStore(key TEXT NOT NULL, value TEXT)")
            self.cursor.execute(
                    "CREATE TABLE Objects(id INTEGER PRIMARY KEY, data TEXT)")
            self.cursor.execute(
                    "CREATE TABLE Types(id INTEGER PRIMARY KEY, data TEXT)")
            self.cursor.execute("""
            CREATE TABLE Worlds(id INTEGER PRIMARY KEY,
                                timestamp TEXT,
                                spaceForces REAL,
                                groundForces REAL,
                                fleetForces REAL)
            """)
            self.connection.commit()

    def get(self, key):
        self.cursor.execute("SELECT value FROM KVStore WHERE key = ?", (key,))
        row = self.cursor.fetchone()
        if row:
            return row[0]

    def set(self, key, value):
        self.cursor.execute(
                "INSERT OR REPLACE INTO KVStore (key, value) VALUES (?, ?)",
                (key, value)
                )

    def post(self, action, data):
        return self.session.post(
                "http://anacreon.kronosaur.com/api/%s" % action,
                data=json.dumps(data)
                )

    def login(self, username, password):
        self.authToken = self.get('authToken')
        if self.authToken is None:
            self.log.debug('Logging into the Kronosaur server...')
            data = {
                    "actual": True,
                    "username": username,
                    "password": password
                    }
            r = self.post("login", data)
            self.set('login', json.dumps(r.json))
            self.authToken = r.json['authToken']
            self.set('authToken', self.authToken)
        self.userInfo = self.get('userInfo')
        if self.userInfo is None:
            self.log.debug('Retrieving information for game %d...' % (
                self.gameID,
                ))
            self.getGameInfo()
        else:
            self.userInfo = json.loads(self.userInfo)
        self.log.debug('Populating game information data structures...')
        self.sovereignID = int(self.get('sovereignID'))
        self.scenarioInfo = json.loads(self.get('scenarioInfo'))
        self.cursor.execute("SELECT id, data FROM Types")
        rows = self.cursor.fetchall()
        for typeId, data in rows:
            self.types[typeId] = json.loads(data)
        self.sequence = self.get('sequence')
        if self.sequence is None:
            self.sequence = 0
        else:
            self.sequence = json.loads(self.sequence)
        self.log.debug('Populating game object data structures...')
        self.cursor.execute("SELECT id, data FROM Objects")
        rows = self.cursor.fetchall()
        for objId, data in rows:
            data = json.loads(data)
            objClass = data['class']
            if 'fleet' == objClass:
                self.fleets[objId] = Fleet(self, data)
            elif 'world' == objClass:
                self.worlds[objId] = World(self, data)

    def getGameInfo(self):
        data = {
                "authToken": self.authToken,
                "gameID": self.gameID
                }
        r = self.post("getGameInfo", data)
        self.userInfo = r.json['userInfo']
        self.set('userInfo', json.dumps(self.userInfo))
        self.set('sovereignID', self.userInfo['sovereignID'])
        for designType in r.json['scenarioInfo']:
            if 'class' in designType and designType['class'] == 'scenario':
                self.set('scenarioInfo', json.dumps(designType))
            else:
                self.cursor.execute(
                        "INSERT OR REPLACE INTO Types (id, data) VALUES (?, ?)",
                        (designType['id'], json.dumps(designType))
                        )
        self.connection.commit()

    def update(self, objects):
        if objects is None:
            pass
        elif "AEON2011:hexeError:v1" == objects[0]:
            self.log.error(self.pp.pprint(objects))
        else:
            self.log.debug('Processing game update...')
            try:
                for data in objects:
                    objClass = data['class']

                    if 'destroyedSpaceObject' == objClass:
                        objId = data['id']
                        if objId in self.fleets:
                            del self.fleets[objId]
                        if objId in self.worlds:
                            del self.worlds[objId]
                        self.cursor.execute("DELETE FROM Objects WHERE id = ?",
                                (objId,))
                    elif 'fleet' == objClass:
                        self.fleets[data['id']] = Fleet(self, data)
                        self.cursor.execute("""
                        INSERT OR REPLACE INTO Objects (id, data)
                        VALUES (?, ?)
                        """, (data['id'], json.dumps(data)))
                    elif 'world' == objClass:
                        self.worlds[data['id']] = World(self, data)
                        self.cursor.execute("""
                        INSERT OR REPLACE INTO Objects (id, data) VALUES (?, ?)
                        """, (data['id'], json.dumps(data)))
                    elif 'update' == objClass:
                        self.sequence = data['sequence']
                        self.set('sequence', json.dumps(self.sequence))
            except:
                self.log.error(self.pp.pprint(objects))
                raise
            self.connection.commit()

    def initObjects(self):
        self.cursor.execute("DELETE FROM Objects")
        self.fleets = {}
        self.world = {}
        self.sequence = 0
        self.getObjects()

    def getObjects(self):
        data = {
                "authToken": self.authToken,
                "gameID": self.gameID,
                "sovereignID": self.sovereignID,
                "sequence": self.sequence
                }
        r = self.post("getObjects", data)
        self.update(r.json)

    def setDestination(self, fleet, dest):
        data = {
                "authToken": self.authToken,
                "gameID": self.gameID,
                "sovereignID": self.sovereignID,
                "objID": fleet['id'],
                "dest": dest['id'],
                "sequence": self.sequence
                }
        r = self.post("setDestination", data)
        self.update(r.json)

    def attack(self, world, objective):
        data = {
                "authToken": self.authToken,
                "gameID": self.gameID,
                "sovereignID": self.sovereignID,
                "attackerObjID": world['id'],
                "battlePlan": {
                    "battleFieldID": world['id'],
                    "objective": objective,
                    "enemySovereignIDs": [ world['sovereignID'], ],
                    },
                "sequence": self.sequence
                }
        r = self.post("attack", data)
        self.update(r.json)

    def deployFleet(self, src, resources):
        data = {
                "authToken": self.authToken,
                "gameID": self.gameID,
                "sovereignID": self.sovereignID,
                "sourceObjID": src['id'],
                "resources": resources,
                "sequence": self.sequence
                }
        r = self.post("deployFleet", data)
        self.update(r.json)

    def transferFleet(self, src, dst, resources):
        # There appears to be a bug where fleetObjID and destObjID are reversed
        data = {
                "authToken": self.authToken,
                "gameID": self.gameID,
                "sovereignID": self.sovereignID,
                "fleetObjID": src['id'],
                "destObjID": dst['id'],
                "resources": resources,
                "sequence": self.sequence
                }
        r = self.post("transferFleet", data)
        self.update(r.json)

    def buildImprovement(self, world, improvement):
        data = {
                "authToken": self.authToken,
                "gameID": self.gameID,
                "sovereignID": self.sovereignID,
                "sourceObjID": world['id'],
                "improvementID": improvement['id'],
                "sequence": self.sequence
                }
        r = self.post("buildImprovement", data)
        self.update(r.json)

    def setIndustryAlloc(self, world, industryID, value):
        data = {
                "authToken": self.authToken,
                "gameID": self.gameID,
                "sovereignID": self.sovereignID,
                "objID": world['id'],
                "industryID": industryID,
                "allocValue": value,
                "sequence": self.sequence
                }
        r = self.post("setIndustryAlloc", data)
        self.update(r.json)

    def renameObject(self, objID, newName):
        data = {
                "authToken": self.authToken,
                "gameID": self.gameID,
                "sovereignID": self.sovereignID,
                "objID": objID,
                "name": newName,
                "sequence": self.sequence
                }
        r = self.post("renameObject", data)
        self.update(r.json)

    def find(self, name):
        for fleet in self.fleets.values():
            if re.search(name, fleet.name, re.IGNORECASE):
                yield fleet
        for world in self.worlds.values():
            if re.search(name, world.name, re.IGNORECASE):
                yield world

    def lookup(self, objId):
        if objId in self.fleets:
            return self.fleets[objId]
        elif objId in self.worlds:
            return self.worlds[objId]

    def calcForceComposition(self, resources):
        spaceForces = 0
        groundForces = 0
        for i in xrange(0, len(resources), 2):
            resType = self.types[resources[i]]
            resCount = resources[i+1]
            if 'attackValue' in resType:
                attackValue = resType['attackValue']
                category = resType['category']
                if 'groundUnit' == category:
                    groundForces += attackValue * resCount
                else:
                    spaceForces += attackValue * resCount
        return (spaceForces * 0.01, groundForces * 0.01)


class Object(object):
    def __init__(self, game, data):
        for k, v in data.items():
            if 'name' != k:
                setattr(self, k, v)
        self.data = data
        self.game = game

    @property
    def name(self):
        return self.data['name'].encode('ascii', 'ignore')

    def rename(self, name):
        self.game.renameObject(self.id, name)

    def calcForceComposition(self):
        self._spaceForces, self._groundForces = \
                self.game.calcForceComposition(self.data['resources'])

    @property
    def groundForces(self):
        try:
            return self._groundForces
        except AttributeError:
            if 'resources' in self.data:
                self.calcForceComposition()
                return self._groundForces
            else:
                return None

    @property
    def spaceForces(self):
        try:
            return self._spaceForces
        except AttributeError:
            if 'resources' in self.data:
                self.calcForceComposition()
                return self._spaceForces
            else:
                return None

    def deployFleet(self, resources):
        self.game.deployFleet(self.data, resources)

    def distanceTo(self, obj):
        x = self.pos
        y = obj.pos
        return math.sqrt(sum([(a-b)**2 for a, b in zip(self.pos, obj.pos)]))

class Fleet(Object):
    def __init__(self, game, data):
        super(Fleet, self).__init__(game, data)

    def setDestination(self, world):
        self.game.setDestination(self.data, world.data)

    def transferFleet(self, dst):
        resources = []
        for i in xrange(0, len(self.resources), 2):
            resources.append(self.resources[i])
            resources.append(-self.resources[i+1])
        self.game.transferFleet(self.data, dst.data, resources)


class World(Object):
    def __init__(self, game, data):
        super(World, self).__init__(game, data)

    def __calcForceComposition(self):
        if 'resources' in self.data and self.resources is not None:
            self.calcForceComposition()
        else:
            self._spaceForces = None
        if 'nearObjIDs' in self.data and self.nearObjIDs is not None:
            self._fleetForces = 0.0
            for objID in self.nearObjIDs:
                try:
                    fleet = self.game.fleets[objID]
                    if self.sovereignID == fleet.sovereignID:
                        self._fleetForces += fleet.spaceForces
                except KeyError:
                    self.game.log.error('Fleet %d does not exist.', objID)
            if self._spaceForces is None:
                self._spaceForces = self._fleetForces
            else:
                self._spaceForces += self._fleetForces
        else:
            self._fleetForces = None

    @property
    def spaceForces(self):
        try:
            return self._spaceForces
        except AttributeError:
            self.__calcForceComposition()
            return self._spaceForces

    @property
    def fleetForces(self):
        try:
            return self._fleetForces
        except AttributeError:
            self.__calcForceComposition()
            return self._fleetForces

if __name__ == '__main__':
    game = Game(1)

    print "Logging in..."
    with open('passwd.json') as fin:
        user = json.loads(fin.read())
    game.login(user['username'], user['password'])
    print "Fetching game objects..."
    game.initObjects()
    print "Update complete."

