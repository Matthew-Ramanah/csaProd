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

    def __init__(self, cfg):
        self.aggregation = str(cfg['inputParams']['aggFreq'])
        self.symbolsNeeded = cfg['fitParams']['basket']['symbolsNeeded']
        self.symbolsNeeded.sort()

        return

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

    def openConnection(self):
        lg.info("Opening IQF Connection...")
        subprocess.Popen(
            ["IQConnect.exe",
             f"‑product {self.productID} ‑version {self.version} ‑login {self.login} ‑password {self.password} ‑autoconnect"])
        time.sleep(10)
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
        self.dataMap = {}
        for sym in self.symbolsNeeded:
            message = f'HIX,{sym},{self.aggregation},1'
            self.sendSocketMessage(message)
            self.dataMap[sym] = self.clientSocket.recv(self.receiveSize).decode('utf-8').split('\n')[0].split(',')
            lg.info(f'{sym} {self.dataMap[sym]}')

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
                md[f'{sym}_intervalVolume'] = int(self.dataMap[sym][6])
            else:
                md[f'{sym}_lastTS'] = np.nan
                md[f'{sym}_close'] = np.nan
                md[f'{sym}_intervalVolume'] = 0
        md['timeSig'] = utility.createTimeSig()
        lg.info(f"MD Constructed for timeSig: {md['timeSig']}")

        return pd.Series(md)

    def pullLatestMD(self, syntheticIncrement=0):
        self.openConnection()
        self.createClientSocket()
        self.updateDataMap()
        self.closeSocket()
        return self.constructMD(syntheticIncrement)


def monitorMdhSanity(fitModels, md):
    staleAssets = []
    for sym in fitModels:
        staleAssets += fitModels[sym].staleAssets
    staleAssets = list(set(staleAssets))
    for i in staleAssets:
        lg.info(f"{i} MD Update Not Sane. Last Updated: {md[f'{i}_lastTS']}")
    return


def monitorContractChanges(fitModels):
    contractChanges = []
    for sym in fitModels:
        contractChanges += fitModels[sym].contractChanges
    contractChanges = list(set(contractChanges))
    for i in contractChanges:
        lg.info(f"{i} contractChange Detected!")
    return
