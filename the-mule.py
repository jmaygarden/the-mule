#!/usr/bin/python

import datetime, json, logging, pprint, requests, sys, time
from mule import *
from mule.ai import *

_log = logging.getLogger(__name__)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    game = Game(1)
    with open('passwd.json') as fin:
        user = json.loads(fin.read())
    game.login(user['username'], user['password'])
    game.initObjects()

    capital = game.worlds[game.userInfo['capitalObjID']]

    scout = ScoutDirector(game)
    scout.scoutAllWorlds = True
    assault = AssaultDirector(game)
    armada = ArmadaDirector(game)
    governor = WorldDirector(game)

    now = datetime.datetime.now()
    minute = now.minute
    hour = now.hour
    day = now.day

    try:
        while (True):
            try:
                if minute != now.minute:
                    minute = now.minute
                    _log.info('********** %s **********', now)
                    game.getObjects()
                    scout.update()
                    armada.update()
                    assault.update()
                    governor.gather(capital)
                    _log.info(
                            '**********       Watch Complete       **********')
                if hour != now.hour:
                    hour = now.hour
                    governor.update()
                    _log.info(
                            '**********        Hour Complete       **********')
                if day != now.day:
                    day = now.day
                    governor.deploy()
                    _log.info(
                            '**********        Day Complete        **********')
            except requests.exceptions.ConnectionError, e:
                _log.error(e)

            time.sleep(1.0)
            now = datetime.datetime.now()

    except KeyboardInterrupt:
        sys.exit(0)

