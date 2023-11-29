from pyConfig import *
from modules import utility


class alpha:
    def __init__(self, target, predictor, name, hl, zSeed, smoothSeed, volHL, volSeed, ncc, accel):
        self.target = target
        self.predictor = predictor
        self.name = name
        self.zInvTau = np.float64(1 / (scoreFactor * hl * logTwo))
        self.zVal = zSeed
        self.smoothInvTau = np.float64(1 / (hl * logTwo))
        self.smoothVal = smoothSeed
        self.lastSmoothVal = smoothSeed
        self.volInvTau = np.float64(1 / (volHL * logTwo))
        self.vol = volSeed
        self.ncc = ncc
        self.accel = accel

    def firstSaneUpdate(self):
        """
        May get overloaded
        """
        return

    def onMdhUpdate(self):
        self.decayCalc()
        self.calcRawVal()
        self.updateSmoothVal()
        self.updateZVal()
        self.updateVolatility()
        self.updateFeatVal()
        self.updateAlphaVal()
        self.updateLog()
        return

    def decayCalc(self):
        """
        May get overloaded
        """
        self.decay = self.target.timeDelta
        return

    def calcRawVal(self):
        """
        Should always get overloaded
        """
        lg.info(f"{self.name} Has No RawVal Calc, Keeping it at 0")
        self.rawVal = 0
        return

    def updateSmoothVal(self):
        thisSmoothVal = utility.emaUpdate(self.lastSmoothVal, self.rawVal, self.decay, self.smoothInvTau)
        if self.accel:
            self.smoothVal = thisSmoothVal - self.lastSmoothVal
        else:
            self.smoothVal = thisSmoothVal
        self.lastSmoothVal = thisSmoothVal
        return

    def updateZVal(self):
        self.zVal = utility.emaUpdate(self.zVal, self.smoothVal, self.decay, self.zInvTau)
        return

    def updateVolatility(self):
        self.vol = np.sqrt(utility.emaUpdate(self.vol ** 2, (self.zVal) ** 2, self.decay, self.volInvTau))
        return

    def updateFeatVal(self):
        self.featVal = np.clip(self.zVal / self.vol, -signalCap, signalCap)
        return

    def updateAlphaVal(self):
        self.alphaVal = self.ncc * self.featVal * self.target.vol
        return

    def updateLog(self):
        thisLog = [self.target.timestamp, self.decay, self.rawVal, self.smoothVal, self.zVal, self.vol, self.featVal]
        self.log.append(thisLog)
        return


class move(alpha):
    def __init__(self, target, predictor, name, hl, zSeed, smoothSeed, volHL, volSeed, ncc, accel):
        super().__init__(target, predictor, name, hl, zSeed, smoothSeed, volHL, volSeed, ncc, accel)
        self.log = []

    def calcRawVal(self):
        self.rawVal = self.predictor.midDelta
        return

    def decayCalc(self):
        """
        May get overloaded
        """
        self.decay = self.predictor.timeDelta
        return


class vsr(alpha):
    def __init__(self, target, predictor, name, hl, zSeed, smoothSeed, volHL, volSeed, ncc, accel, predSeed):
        super().__init__(target, predictor, name, hl, zSeed, smoothSeed, volHL, volSeed, ncc, accel)
        self.log = []
        self.lastPredMid = predSeed

    def firstSaneUpdate(self):
        self.lastPredMid = self.predictor.midPrice
        return

    def calcRawVal(self):
        if self.predictor.contractChange:
            predDelta = 0
        else:
            predDelta = self.predictor.midPrice - self.lastPredMid

        self.rawVal = predDelta / self.predictor.vol - self.target.midDelta / self.target.vol
        self.lastPredMid = self.predictor.midPrice
        return

    def decayCalc(self):
        """
        May get overloaded
        """
        self.decay = self.predictor.timeDelta
        return


class basis(alpha):
    def __init__(self, target, predictor, name, hl, zSeed, smoothSeed, volHL, volSeed, ncc, accel, front, basisSeed):
        super().__init__(target, predictor, name, hl, zSeed, smoothSeed, volHL, volSeed, ncc, accel)
        self.front = front
        self.back = predictor
        self.log = []
        self.lastBasis = basisSeed

    def firstSaneUpdate(self):
        self.lastBasis = self.front.midPrice - self.back.midPrice
        return

    def calcRawVal(self):
        thisBasis = self.front.midPrice - self.back.midPrice
        if (self.front.contractChange) | (self.back.contractChange):
            self.rawVal = 0
        else:
            self.rawVal = thisBasis - self.lastBasis

        self.lastBasis = self.front.midPrice - self.back.midPrice
        return
