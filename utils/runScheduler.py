import sys

sys.path.insert(0, "C:/Users/matth/PycharmProjects/SydneyQuantitative/csaProd/")
# sys.path.insert(0, "C:/Users/Owner/Desktop/CBCT/code/")

from pyConfig import *
import schedule

lg.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s', level=lg.INFO, datefmt='%H:%M:%S')


def callRunLive():
    lg.info("Calling runLive...")
    exec(open('runLive.py').read())
    return


def callRunPaper():
    lg.info("Calling runPaper...")
    exec(open('runPaper.py').read())
    return


schedule.every().hour.at(":05").do(callRunLive)

lg.info("Starting scheduler...")
while True:
    schedule.run_pending()
