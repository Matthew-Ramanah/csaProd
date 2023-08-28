# Directories
root = "C:/Users/matth/PycharmProjects/asaProd/"
data_root = "C:/Users/matth/OneDrive/Documents/AlphaGrep/data/"

# Constants
signalCap = 3
tradingDays = 252
daysPerYear = 365
minsPerYear = 60 * 24 * daysPerYear
logTwo = 1.4426950408889634
aggFreq = 60

# Run-time options
cfg_file = root + "config/refined.json"

# Global Packages
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import logging as lg
import scipy
import math
import seaborn as sns
import json
import h5py
import sys
import os
from collections import OrderedDict
import warnings
import random

# Environment Variables
lg.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s', level=lg.INFO, datefmt='%H:%M:%S')
pd.options.display.float_format = '{:.2f}'.format
pd.set_option('expand_frame_repr', False)
pd.options.mode.chained_assignment = None
warnings.simplefilter(action='ignore', category=pd.errors.PerformanceWarning)

exchangeMap = {
    "asx_refinitiv_v4": [
        "XT0",
        "YT0",
        "AP0"
    ],
    "bme_refinitiv_v4": [
        "FIBX0"
    ],
    "bmv_refinitiv_v4": [
        "IPC0"
    ],
    "borsa_refinitiv_v4": [
        "FIB0"
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
        "OBF0",
        "EBM0",
        "ECO0"
    ],
    "hkex_refinitiv_v4": [
        "HHI0",
        "HSI0"
    ],
    "ice_refinitiv_v4": [
        "ICE-EU_BRN0",
        "ICE-LX_C0",
        "ICE-US_CC0",
        "ICE-US_CT0",
        "ICE-EU_G0",
        "ICE-US_KC0",
        "ICE-US_MFS0",
        "ICE-US_MME0",
        "ICE-LL_R0",
        "ICE-US_SB0",
        "ICE-LL_Z0",
        "RS0",
        "W0",
        "DX0",
        "KMF0",
        "RC0"
    ],
    "jse_refinitiv_v4": [
        "ALSI0"
    ],
    "krx_refinitiv_v4": [
        "10TB0",
        "BM30",
        "KS0",
        "USD0"
    ],
    "moscow_refinitiv_v4": [
        "RIRTS0"
    ],
    "nasdaq_nordic_refinitiv_v4": [
        "OMXS300"
    ],
    "ose_refinitiv_v4": [
        "JBL0",
        "NK225M0",
        "TOPIXM0"
    ],
    "sgx_refinitiv_v4": [
        "IN0",
        "SGP0",
        "TW0",
        "TWN0",
        "NIY0"
    ],
    "taifex_refinitiv_v4": [
        "TX0"
    ],
    "tmx_refinitiv_v4": [
        "CGB0",
        "SXF0"
    ],
    "cme_refinitiv_v4": [
        "CL0",
        "ES0",
        "GC0",
        "GF0",
        "HG0",
        "HO0",
        "LE0",
        "NIY0",
        "NQ0",
        "PA0",
        "PL0",
        "RB0",
        "RTY0",
        "SI0",
        "UB0",
        "YM0",
        "ZT0",
        "ZF0",
        "ZN0",
        "ZB0",
        "GE0",
        "GE1",
        "GE2",
        "GE3",
        "GE4",
        "GE5",
        "GE6",
        "GE7",
        "GE8",
        "GE9",
        "GE10",
        "GE11",
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
        "KE1",
        "1UB0",
        "1ZL0",
        "1ZC0",
        "1CL0",
        "1ES0",
        "1GF0",
        "1ZF0",
        "1GC0",
        "1HG0",
        "1HO0",
        "1LE0",
        "1HE0",
        "1PA0",
        "1PL0",
        "1RB0",
        "1RTY0",
        "1ZS0",
        "1SI0",
        "1ZM0",
        "1ZT0",
        "1ZN0",
        "1ZB0",
        "1ZW0",
        "1YM0"
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
    "interest_rates": [
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
    ]
}
