from pyConfig import *
from modules import utility


class feed():
    productID = 'SYDNEY_QUANTITATIVE_50907'
    version = "6.2.0.25"
    login = "514851"
    password = "yevv3cmf"
    host = "127.0.0.1"
    port = 9100
    receiveSize = 1024

    def __init__(self, cfgs):
        self.symbolsNeeded = self.findSymbolsNeeded(cfgs)
        self.execSyms = utility.findIqfTradedSyms()
        return

    @staticmethod
    def findSymbolsNeeded(cfgs):
        symsNeeded = utility.findProdSyms()
        for investor in cfgs:
            symsNeeded += cfgs[investor]['fitParams']['basket']['symbolsNeeded']

        symsNeeded = list(set(symsNeeded))
        symsNeeded.sort()
        return symsNeeded

    def findNthSymbol(self, baseSym, n):
        """
        Request futures symbol chain from IQF and pick up the current back month symbol
        """
        message = f"CFU,{baseSym},,0123456789,2"
        self.sendSocketMessage(message)
        symList = self.clientSocket.recv(self.receiveSize).decode('utf-8').split('\n')[0].split(',')
        return symList[n]

    def sendSocketMessage(self, message):
        self.clientSocket.sendall(bytes(message + "\r\n", "utf-8"))
        return

    def openConnection(self, sleepTime=5):
        lg.info("Opening IQF Connection...")
        subprocess.Popen(
            ["IQConnect.exe",
             f"‑product {self.productID} ‑version {self.version} ‑login {self.login} ‑password {self.password} ‑autoconnect"])
        time.sleep(sleepTime)
        return

    def createClientSocket(self):
        self.clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clientSocket.connect((self.host, self.port))
        return

    @staticmethod
    def recvDataIsSane(recvData):
        if len(recvData) == 8:
            return True
        return False

    def updateDataMap(self):
        lg.info(f"Pulling Data For {len(self.symbolsNeeded)} Model Symbols...")
        self.dataMap = {}
        for sym in self.symbolsNeeded:
            message = f'HIX,{sym},{aggFreq},1'
            self.sendSocketMessage(message)
            self.dataMap[sym] = self.clientSocket.recv(self.receiveSize).decode('utf-8').split('\n')[0].split(',')
            # lg.info(f'{sym} {self.dataMap[sym]}')

            if self.recvDataIsSane(self.dataMap[sym]):
                # Flush the socket of the !ENDMSG! before requesting next symbol
                self.clientSocket.recv(self.receiveSize)
            else:
                lg.info(f"{sym} Received bad data. Check contract in config.")
        return

    def closeSocket(self):
        self.clientSocket.close()
        lg.info("Socket Closed.")
        return

    def constructMD(self, syntheticIncrement):
        md = {}
        for sym in self.dataMap:
            if self.recvDataIsSane(self.dataMap[sym]):
                md[f'{sym}_lastTS'] = pd.Timestamp(self.dataMap[sym][0]) + datetime.timedelta(hours=syntheticIncrement)
                md[f'{sym}_close'] = float(self.dataMap[sym][4])
                md[f'{sym}_cumDailyVolume'] = int(self.dataMap[sym][5])
                md[f'{sym}_intervalVolume'] = int(self.dataMap[sym][6])
            else:
                md[f'{sym}_lastTS'] = np.nan
                md[f'{sym}_close'] = np.nan
                md[f'{sym}_cumDailyVolume'] = np.nan
                md[f'{sym}_intervalVolume'] = 0
        md['timeSig'] = utility.createTimeSig()
        return pd.Series(md)

    def pullLatestMD(self, syntheticIncrement=0):
        self.openConnection()
        self.createClientSocket()
        self.updateDataMap()
        return self.constructMD(syntheticIncrement)

    def pullExecMD(self):
        self.updateExecMap()
        self.closeSocket()
        return self.constructExecMD()

    def updateExecMap(self):
        lg.info(f"Pulling Data For {len(self.execSyms)} Execution Symbols...")
        self.execMap = {}
        for sym in self.execSyms:
            message = f'HIX,{sym},{aggFreq},1'
            self.sendSocketMessage(message)
            self.execMap[sym] = self.clientSocket.recv(self.receiveSize).decode('utf-8').split('\n')[0].split(',')
            # lg.info(f'{sym} {self.dataMap[sym]}')

            if self.recvDataIsSane(self.execMap[sym]):
                # Flush the socket of the !ENDMSG! before requesting next symbol
                self.clientSocket.recv(self.receiveSize)
            else:
                lg.info(f"{sym} Received bad data. Check contract in config.")
        return

    def constructExecMD(self):
        execMD = {}
        for sym in self.execMap:
            if self.recvDataIsSane(self.execMap[sym]):
                execMD[f'{sym}_lastTS'] = pd.Timestamp(self.execMap[sym][0])
                execMD[f'{sym}_close'] = float(self.execMap[sym][4])
            else:
                execMD[f'{sym}_lastTS'] = np.nan
                execMD[f'{sym}_close'] = np.nan
        execMD['timeSig'] = utility.createTimeSig()
        return pd.Series(execMD)


def monitorMdhSanity(fitModels, md):
    staleAssets = []
    for sym in fitModels:
        staleAssets += fitModels[sym].staleAssets
    staleAssets = list(set(staleAssets))
    for i in staleAssets:
        lg.info(f"{i} MD Update Not Sane. Last Updated: {md[f'{i}_lastTS']}")
    return
