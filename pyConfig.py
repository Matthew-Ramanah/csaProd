# Directories

root = "C:/Users/matth/PycharmProjects/SydneyQuantitative/csaProd/"
# root = "C:/Users/Owner/Desktop/CBCT/code/"
logRoot = f"{root}logs/AFBI/"
dataRoot = "C:/Users/matth/PycharmProjects/AlphaGrep/data/"

refDataPath = f'{root}asaRefData.csv'
riskPath = f"{root}models/AFBI/config/riskLimits.csv"
paperLogRoot = f"{logRoot}Paper/"
liveLogRoot = f"{logRoot}Live/"
tradeBlotterRoot = f"{logRoot}tradeBlotter/"
rawDataRoot = f"{dataRoot}raw/hourly/quotes/"
proDataRoot = f"{dataRoot}processed/"

# Constants
signalCap = 3
tradingDays = 252
daysPerYear = 365
minsPerYear = 60 * 24 * daysPerYear
logTwo = 1.4426950408889634
scoreFactor = 10
dollarFmt = '${x:,.0f}'
maxAssetDelta = 0.1
pctSlipTol = 0.2
reconTimezone = 'Australia/Sydney'
dayOfWeekMap = {0: "Monday", 1: "Tuesday", 2: "Wednesday", 3: "Thursday", 4: "Friday", 5: "Saturday", 6: "Sunday"}

# Run-time options
cfg_file = root + "models/AFBI/config/ftiRemoved.json"
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

# Deal with terribly designed data source
fxToInvert = ["CAD=", "JPY=", "CHF=", "ZAR=", "CNH=", "THB=", "SGD="]
priceMultipliers = {"HO0" : 100}

hardcodedContracts = {
    "ZL0": "@BOH24",
    "ZC0": "@CH24",
    "ZC1": "@CK24",
    "ZS0": "@SH24",
    "ZS1": "@SK24",
    "ZM0": "@SMH24",
    "ZW0": "@WH24",
    "KE0": "@KWH24",
    "LE0": "@LEG24",
    "GF0": "@GFF24",
    "HG0": "QHGH24",
    "HE0": "@HEG24",
    "HE1": "@HEJ24",
    "GC0": "QGCG24",
    "GC1": "QGCJ24",
    "SI0": "QSIH24",
    "PL0": "QPLH24",
    "PA0": "QPAH24",
    "RB0": "QRBG24",
    "CL0": "QCLH24",
    "HO0": "QHOH24",
    "RS0": "@RSH24",
    "RS1": "@RSK24",
    "W0": "QWH24",
    "VX0": "@VXF24",
    "ICE-US_MME0": "MEFH24",
    "ICE-US_CT0": "@CTH24",
    "ICE-EU_G0": "GASG24",
    "ICE-US_KC0": "@KCH24",
    "ICE-LL_R0": "LGH24",
    "ICE-LL_Z0": "LFH24",
    "ZB0": "@USH24",
    "ZN0": "@TYH24",
    "ZF0": "@FVH24",
    "ZT0": "@TUH24",
    "FBTP0": "BTPH24",
    "FGBL0": "BDH24",
    "FGBM0": "BLH24",
    "AP0": "SPIH24",
    "ES0": "@ESH24",
    "NQ0": "@NQH24",
    "RTY0": "@RTYH24",
    "FSMI0": "SWH24",
    "ALSI0": "ALJH24"
}

exchangeMap = {
    "asx_refinitiv_v4": [
        "XT0",
        "YT0",
        "AP0",
        "IR0",
        "IR1",
        "IR2",
        "IR3",
        "IR4",
        "IR5",
        "IR6",
        "IR7"
    ],
    "brazil_refinitiv_v4": [
        "DOL0",
        "IND0",
        "WDO0",
        "WIN0"
    ],
    "cboe_refinitiv_v4": [
        "VX0"
    ],
    "eurex_refinitiv_v4": [
        "CONF0",
        "FBTP0",
        "FDAX0",
        "FESB0",
        "FESX0",
        "FGBL0",
        "FGBM0",
        "FGBS0",
        "FGBX0",
        "FBTS0",
        "FOAT0",
        "FSMI0"
    ],
    "euronext_refinitiv_v4": [
        "FCE0",
        "FTI0",
        "EBM0",
        "ECO0"
    ],
    "ice_refinitiv_v4": [
        "ICE-EU_BRN0",
        "ICE-LX_C0",
        "ICE-US_CC0",
        "ICE-US_CT0",
        "ICE-US_CT1",
        "ICE-EU_G0",
        "ICE-US_KC0",
        "ICE-US_MFS0",
        "ICE-US_MME0",
        "ICE-LL_R0",
        "ICE-US_SB0",
        "ICE-LL_Z0",
        "RS0",
        "RS1",
        "W0",
        "W1",
        "DX0",
        "RC0",
        "RC1"
    ],
    "jse_refinitiv_v4": [
        "ALSI0"
    ],
    "sgx_refinitiv_v4": [
        "SGP0",
        "TW0",
        "TWN0"
    ],
    "cme_refinitiv_v4": [
        'HE0',
        "HE1",
        "LE1",
        "GF1",
        "CL0",
        "ES0",
        "GC0",
        "GC1",
        "GF0",
        "HG0",
        "HG1",
        "HO0",
        "LE0",
        "NIY0",
        "NQ0",
        "PA0",
        "PA1",
        "PL0",
        "PL1",
        "RB0",
        "RTY0",
        "SI0",
        "SI1",
        "UB0",
        "YM0",
        "ZT0",
        "ZF0",
        "ZN0",
        "ZB0",
        "NG0",
        "6A0",
        "6B0",
        "6C0",
        "6J0",
        "6E0",
        "6M0",
        "6N0",
        "6Z0",
        "ZC0",
        "ZC1",
        "ZL0",
        "ZL1",
        "ZM0",
        "ZM1",
        "ZS0",
        "ZS1",
        "ZW0",
        "ZW1",
        "KE0",
        "KE1"
    ],
    "fx_refinitiv_v3": [
        "AUD=",
        "BRL=",
        "CAD=",
        "CHF=",
        "CNH=",
        "CZK=",
        "EUR=",
        "GBP=",
        "HKD=",
        "HUF=",
        "ILS=",
        "INR=",
        "JPY=",
        "KRW=",
        "MXN=",
        "NOK=",
        "NZD=",
        "PLN=",
        "RUB=",
        "SEK=",
        "SGD=",
        "THB=",
        "TWD=",
        "ZAR="
    ],
}

noLiveData = {
    "hkex_refinitiv_v4": [
        "HHI0",
        "HSI0"
    ],
    "tmx_refinitiv_v4": [
        "CGB0",
        "SXF0"
    ],
    "krx_refinitiv_v4": [
        "10TB0",
        "BM30",
        "KS0",
        "USD0"
    ],
    "ose_refinitiv_v4": [
        "JBL0",
        "NK225M0",
        "TOPIXM0"],
    "taifex_refinitiv_v4": [
        "TX0"
    ],
}

deprecated = {"interest_rates": [
    "AUD10YZ=R",
    "AUD2YZ=R",
    "AUD5YZ=R",
    "AUGOV10YZ=R",
    "AUGOV2YZ=R",
    "AUGOV5YZ=R",
    "BRGOV10YZ=R",
    "BRGOV2YZ=R",
    "BRGOV5YZ=R",
    "BRL2YZ=R",
    "BRL5YZ=R",
    "CAD10YZ=R",
    "CAD2YZ=R",
    "CAD5YZ=R",
    "CHF10YZ=R",
    "CHF2YZ=R",
    "CHF5YZ=R",
    "CHGOV10YZ=R",
    "CHGOV2YZ=R",
    "CHGOV5YZ=R",
    "CNGOV10YZ=R",
    "CNGOV2YZ=R",
    "CNGOV5YZ=R",
    "CNH10YZ=R",
    "CNH2YZ=R",
    "CNH5YZ=R",
    "DEGOV10YZ=R",
    "DEGOV2YZ=R",
    "DEGOV5YZ=R",
    "EUGOV10YZ=R",
    "EUGOV2YZ=R",
    "EUGOV5YZ=R",
    "EUR10YZ=R",
    "EUR2YZ=R",
    "EUR5YZ=R",
    "FRGOV10YZ=R",
    "FRGOV2YZ=R",
    "FRGOV5YZ=R",
    "GBGOV10YZ=R",
    "GBGOV2YZ=R",
    "GBGOV5YZ=R",
    "GBP10YZ=R",
    "GBP2YZ=R",
    "GBP5YZ=R",
    "HKD10YZ=R",
    "HKD2YZ=R",
    "HKD5YZ=R",
    "HKGOV10YZ=R",
    "HKGOV2YZ=R",
    "HKGOV5YZ=R",
    "INGOV10YZ=R",
    "INGOV2YZ=R",
    "INGOV5YZ=R",
    "INR10YZ=R",
    "INR2YZ=R",
    "INR5YZ=R",
    "ITGOV10YZ=R",
    "ITGOV2YZ=R",
    "ITGOV5YZ=R",
    "JPGOV10YZ=R",
    "JPGOV2YZ=R",
    "JPGOV5YZ=R",
    "JPY10YZ=R",
    "JPY2YZ=R",
    "JPY5YZ=R",
    "KRGOV10YZ=R",
    "KRGOV2YZ=R",
    "KRGOV5YZ=R",
    "KRW10YZ=R",
    "KRW2YZ=R",
    "KRW5YZ=R",
    "MXGOV10YZ=R",
    "MXGOV2YZ=R",
    "MXGOV5YZ=R",
    "MXN10YZ=R",
    "MXN2YZ=R",
    "MXN5YZ=R",
    "NLGOV10YZ=R",
    "NLGOV2YZ=R",
    "NLGOV5YZ=R",
    "NOGOV10YZ=R",
    "NOGOV2YZ=R",
    "NOGOV5YZ=R",
    "NOK10YZ=R",
    "NOK2YZ=R",
    "NOK5YZ=R",
    "NZD10YZ=R",
    "NZD2YZ=R",
    "NZD5YZ=R",
    "NZGOV10YZ=R",
    "NZGOV2YZ=R",
    "NZGOV5YZ=R",
    "SEGOV10YZ=R",
    "SEGOV2YZ=R",
    "SEGOV5YZ=R",
    "SEK10YZ=R",
    "SEK2YZ=R",
    "SEK5YZ=R",
    "SGD10YZ=R",
    "SGD2YZ=R",
    "SGD5YZ=R",
    "SGGOV10YZ=R",
    "SGGOV2YZ=R",
    "SGGOV5YZ=R",
    "THB10YZ=R",
    "THB2YZ=R",
    "THB5YZ=R",
    "THGOV10YZ=R",
    "THGOV2YZ=R",
    "THGOV5YZ=R",
    "TWD10YZ=R",
    "TWD2YZ=R",
    "TWD5YZ=R",
    "TWGOV10YZ=R",
    "TWGOV2YZ=R",
    "TWGOV5YZ=R",
    "USD10YZ=R",
    "USD2YZ=R",
    "USD5YZ=R",
    "USGOV10YZ=R",
    "USGOV2YZ=R",
    "USGOV5YZ=R",
    "ZAGOV10YZ=R",
    "ZAGOV2YZ=R",
    "ZAGOV5YZ=R",
    "ZAR10YZ=R",
    "ZAR2YZ=R",
    "ZAR5YZ=R",
    "ESGOV2YZ=R",
    "ESGOV5YZ=R",
    "ESGOV10YZ=R"
]}
