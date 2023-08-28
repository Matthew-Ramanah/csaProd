from pyConfig import *


def emaUpdate(lastValue, thisValue, decay, invTau):
    alpha = np.exp(invTau * decay)
    return alpha * thisValue + (1 - alpha) * lastValue


def loadRefData():
    refData = pd.read_csv(f'{root}asaRefData.csv')
    return refData.set_index('symbol')
