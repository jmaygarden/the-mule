#!/usr/bin/python

import json, pprint, sys
from mule import Game

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print 'usage: python lookup.py <id>'
        sys.exit(0)
    game = Game(1)
    with open('passwd.json') as fin:
        user = json.loads(fin.read())
    game.login(user['username'], user['password'])
    objId = int(sys.argv[1])
    obj = game.lookup(objId)
    pprint.pprint(obj.data if obj else None)
    sys.exit(0)

