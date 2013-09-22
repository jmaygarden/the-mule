#!/usr/bin/python

import json, pprint, sys
from mule import Game

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print 'usage: python find.py <name>'
        sys.exit(0)
    game = Game(1)
    with open('passwd.json') as fin:
        user = json.loads(fin.read())
    game.login(user['username'], user['password'])
    for obj in game.find(sys.argv[1]):
        pprint.pprint(obj.data)
        #print json.dumps(obj.data)
    sys.exit(0)

