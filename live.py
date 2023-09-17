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


# Strategy class needs to derive from the BaseStrategy class and overrride only the onBars Method and onTimer method
class Strategy(BaseStrategy):
    def stop(self):
        print("Received stop callback")

    # overrride this method with the logic of what to do on receiving the bars
    def onBars(self, trigger, bars, brokerurl, ts=0):
        symlist = sorted(bars.keys())
        for barkey in symlist:
            dumpString = f"{str(bars[barkey])} brokerurl:{brokerurl}"
            outputBarFile.write(dumpString + "\n")
        outputBarFile.flush()

    # callback called on receiving a trade update in MD.
    def onMdTrade(self, mdTrades):
        pass

    # callback called on receiving trade
    def onTrade(self, trade):
        pass
        # print(f"onTrade : {trade}")

    def onPositions(self, pnl):
        pass
        # print(f"onPositions : {pnl}")

    # you can set timer using addTimer and get a callback at the set time with whatever payload you've set
    def onTimer(self, timestamp, payload):
        print(str(timestamp) + " " + str(payload))


def getTradingDate():
    now = datetime.now()
    now1 = None
    if (now.hour >= 16):
        now1 = now.replace(day=now.day - 1)
    else:
        now1 = now
    date = now1.strftime("%Y%m%d")
    print(date)
    return date


mode = 'LIVE'

tmx_url = "10.254.29.12:12793"
tmx_t5triggerSymbols = ['CGBM23']
tmx_t5Trigger = TimeTrigger('tmx_5s_trigger', tmx_t5triggerSymbols, 10, 10)

brz_url = "10.254.31.11:12793"
brz_t5triggerSymbols = ['DI1F29', 'DI1F26', 'DI1F30']
brz_t5Trigger = TimeTrigger('brz_5s_trigger', brz_t5triggerSymbols, 1, 1)

s1 = Strategy()
s1.addTrigger(tmx_t5Trigger, tmx_url)
s1.addTrigger(brz_t5Trigger, brz_url)

stratemails = "add.your.mail@alpha-grep.com"
if (mode == 'LIVE'):
    print("in live")
    d = livedispatcher
    # date = getTradingDate()
    d.init([tmx_url, brz_url], "20220531", stratemails)

    d.addSubscription("bar", mode=0)  # mode: {0: getLatest}, {1: localReplay}, {2: brokerReplay}
    # d.addSubscription("trade", mode=0)
    # d.addSubscription("pos", mode=0)
else:
    d = simdispatcher
    d.init("futBars.csv", stratemails)

# add all instances of strategies to the dispatcher before starting
d.addStrategy(s1)

print("Starting main loop!")
# start the main loop
outputBarFile = open("test.csv", "w")
outputMdTradeFile = open("test.csv", "w")

d.start()