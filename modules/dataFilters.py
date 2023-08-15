from pyConfig import *

def isSane(md):

    return True

def priceFilter(md):
    md['bid_price'] < md['ask_price']
    return