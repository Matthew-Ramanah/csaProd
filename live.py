barPath = '/data/misc/include/pybarsubscriber'
import sys

sys.path.append(barPath)
from dispatchers import livedispatcher, simdispatcher
from strategies import BaseStrategy
from triggers import TimeTrigger
from triggers import VolumeTrigger
from execution import FileEA
from execution import TcpEA
from datetime import datetime
import time
from data.binner import *


class Strategy(BaseStrategy):
    def onPositions(self, pnl):
        pass
        # print(f"onPositions : {pnl}")

    # you can set timer using addTimer and get a callback at the set time with whatever payload you've set
    def onTimer(self, timestamp, payload):
        print(str(timestamp) + " " + str(payload))


mode = 'LIVE'

# Sample time trigger
tmx_url = "10.254.29.12:12793"
tmx_t5triggerSymbols = ['CGBM23']
tmx_t5Trigger = TimeTrigger('tmx_5s_trigger', tmx_t5triggerSymbols, 10, 10)


s1 = Strategy()
s1.addTrigger(tmx_t5Trigger, tmx_url)
stratemails = "add.your.mail@alpha-grep.com"
d = livedispatcher
d.init([tmx_url, brz_url], "20220531", stratemails)
d.addSubscription("bar", mode=0)  # mode: {0: getLatest}, {1: localReplay}, {2: brokerReplay}

# add all instances of strategies to the dispatcher before starting
d.addStrategy(s1)

print("Starting main loop!")
# start the main loop
outputBarFile = open("test.csv", "w")
outputMdTradeFile = open("test.csv", "w")

d.start()