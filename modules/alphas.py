from pyConfig import *
import utility


class alpha:
    rawVal = float()

    def __init__(self, target, name, decay, zHL, zSeed, smoothFactor, smoothSeed, volHL, volSeed, accel, ncc):
        self.target = target
        self.decay = decay
        self.name = name
        self.zInvTau = np.float64(1 / (zHL * logTwo))
        self.zVal = zSeed
        self.smoothInvTau = np.float64(1 / (smoothFactor * zHL * logTwo))
        self.smoothVal = smoothSeed
        self.lastSmoothVal = smoothSeed
        self.volInvTau = np.float64(1 / (volHL * logTwo))
        self.vol = volSeed
        self.accel = accel
        self.ncc = ncc

    def onMdhUpdate(self):
        self.decayCalc()
        self.calcRawVal()
        self.updateSmoothVal()
        self.updateZVal()
        self.updateVolatility()
        self.updateFeatVal()
        self.updateAlphaVal()
        return

    def decayCalc(self):
        """
        May get overloaded
        """
        self.decay = self.target.timeDecay
        return

    def calcRawVal(self):
        """
        Should always get overriden
        """
        lg.info(f"{self.name} Has No RawVal Calc")
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
        self.vol = np.sqrt(utility.emaUpdate(self.vol ** 2, self.zVal ** 2, self.decay, self.volInvTau))
        return

    def updateFeatVal(self):
        self.featVal = np.clip(self.zVal / self.vol, -signalCap, signalCap)
        return

    def updateAlphaVal(self):
        self.alphaVal = self.ncc * self.featVal * self.target.vol
        return


class move(alpha):
    def calcRawVal(self):
        self.rawVal = self.target.annPctChange
        return


class basis(alpha):
    def __init__(self, target, name, decay, zHL, zSeed, smoothFactor, smoothSeed, volHL, volSeed, front, back):
        super().__init__(target, name, decay, zHL, zSeed, smoothFactor, smoothSeed, volHL, volSeed)
        self.front = front
        self.lastFrontMid = front.midPrice
        self.back = back
        self.lastBackMid = back.midPrice

    def calcRawVal(self):
        if self.front.contractChange:
            frontDelta = 0
        else:
            frontDelta = (self.front.midPrice - self.lastFrontMid) / self.front.midPrice
        if self.back.contractChange:
            backDelta = 0
        else:
            backDelta = (self.back.midPrice - self.lastBackMid) / self.back.midPrice

        self.rawVal = frontDelta - backDelta
        self.lastFrontMid = self.front.midPrice
        self.lastBackMid = self.back.midPrice
        return


class rv(alpha):
    def __init__(self, target, name, decay, zHL, zSeed, smoothFactor, smoothSeed, volHL, volSeed, pred):
        super().__init__(target, name, decay, zHL, zSeed, smoothFactor, smoothSeed, volHL, volSeed)
        self.pred = pred
        self.lastRatio = target.midPrice / pred.midPrice

    def calcRawVal(self):
        thisRatio = self.target.midPrice / self.pred.midPrice
        if (self.target.contractChange) | (self.pred.contractChange):
            self.rawVal = 0
        else:
            self.rawVal = thisRatio - self.lastRatio
        self.lastRatio = thisRatio
        return
