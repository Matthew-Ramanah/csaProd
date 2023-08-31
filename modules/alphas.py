from pyConfig import *
from modules import utility


class alpha:
    log = []

    def __init__(self, target, predictor, name, zHL, zSeed, smoothFactor, smoothSeed, volHL, volSeed, ncc, accel):
        self.target = target
        self.predictor = predictor
        self.name = name
        self.zInvTau = np.float64(1 / (zHL * logTwo))
        self.zVal = zSeed
        self.smoothInvTau = np.float64(1 / (smoothFactor * zHL * logTwo))
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
        Should always get overriden
        """
        lg.info(f"{self.name} Has No RawVal Calc , setting to 0...")
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
        thisLog = [self.rawVal, self.smoothVal, self.zVal, self.vol]
        self.log.append(thisLog)
        return


class move(alpha):
    def calcRawVal(self):
        self.rawVal = self.target.annPctChange
        return


class basis(alpha):
    def __init__(self, target, predictor, name, zHL, zSeed, smoothFactor, smoothSeed, volHL, volSeed, ncc, accel,
                 front):
        super().__init__(target, predictor, name, zHL, zSeed, smoothFactor, smoothSeed, volHL, volSeed, ncc, accel)
        self.front = front
        self.back = predictor

    def firstSaneUpdate(self):
        self.lastFrontMid = self.front.midPrice
        self.lastBackMid = self.back.midPrice
        return

    def calcRawVal(self):
        if (self.front.contractChange) | (self.front.midPrice == 0):
            frontDelta = 0
        else:
            frontDelta = (self.front.midPrice - self.lastFrontMid) / self.front.midPrice
        if (self.back.contractChange) | (self.back.midPrice == 0):
            backDelta = 0
        else:
            backDelta = (self.back.midPrice - self.lastBackMid) / self.back.midPrice

        self.rawVal = frontDelta - backDelta
        self.lastFrontMid = self.front.midPrice
        self.lastBackMid = self.back.midPrice
        return


class rv(alpha):
    def __init__(self, target, predictor, name, zHL, zSeed, smoothFactor, smoothSeed, volHL, volSeed, ncc, accel):
        super().__init__(target, predictor, name, zHL, zSeed, smoothFactor, smoothSeed, volHL, volSeed, ncc, accel)

    def firstSaneUpdate(self):
        self.lastRatio = self.target.midPrice / self.predictor.midPrice
        return

    def calcRawVal(self):
        thisRatio = self.target.midPrice / self.predictor.midPrice
        if (self.target.contractChange) | (self.predictor.contractChange) | (self.predictor.midPrice == 0):
            self.rawVal = 0
        else:
            self.rawVal = thisRatio - self.lastRatio
        self.lastRatio = thisRatio
        return
