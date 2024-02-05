# Directories
root = "C:/Users/matth/PycharmProjects/SydneyQuantitative/csaProd/"
# root = "C:/Users/Owner/Desktop/CBCT/code/"
logRoot = "C:/Users/matth/PycharmProjects/SydneyQuantitative/logs/"
# logRoot = "C:/Users/Owner/Desktop/CBCT/logs/"

rawDataRoot = "C:/Users/matth/PycharmProjects/SydneyQuantitative/data/recon/"
proDataRoot = "C:/Users/matth/PycharmProjects/SydneyQuantitative/data/processed/"
refDataPath = f'{root}csaRefData.csv'
riskPath = f"{root}models/AFBI/config/riskLimits.csv"
paperLogRoot = f"{logRoot}Paper/"
liveLogRoot = f"{logRoot}Live/"
tradeBlotterRoot = f"{logRoot}tradeBlotter/"

# Constants
signalCap = 3
tradingDays = 252
daysPerYear = 365
minsPerYear = 60 * 24 * daysPerYear
logTwo = 1.4426950408889634
scoreFactor = 8
dollarFmt = '${x:,.0f}'
noDec = 8
maxAssetDelta = 0.1
pctSlipTol = 0.1
dayOfWeekMap = {0: "Monday", 1: "Tuesday", 2: "Wednesday", 3: "Thursday", 4: "Friday", 5: "Saturday", 6: "Sunday"}
priceMultipliers = {"QHO#": 100}

# Run-time options
cfg_file = root + "models/AFBI/config/iqfRecon.json"
interfaceRoot = root + "models/AFBI/interface/"

# Global Packages
import pandas as pd
import numpy as np
import matplotlib

matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import logging as lg
import scipy
import math
import json
import h5py
import sys
import os
from collections import OrderedDict
import warnings
import random
import functools
import time
import statistics
import subprocess
import socket
import time
import base64
from io import BytesIO
from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools
import datetime
import pytz
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.utils import formatdate
from email import encoders
from dateutil import parser
import locale

# Environment Variables
lg.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s', level=lg.INFO, datefmt='%H:%M:%S')
pd.options.display.float_format = '{:.2f}'.format
pd.set_option('expand_frame_repr', False)
pd.options.mode.chained_assignment = None
warnings.simplefilter(action='ignore', category=pd.errors.PerformanceWarning)
lg.getLogger('googleapicliet.discovery_cache').setLevel(lg.ERROR)
locale.setlocale(locale.LC_ALL, '')
