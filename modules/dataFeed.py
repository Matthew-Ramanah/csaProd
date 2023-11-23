from pyConfig import *
from modules import utility


class feed():
    host = "127.0.0.1"
    port = 9100
    receiveSize = 1024

    productID = 'SYDNEY_QUANTITATIVE_50907'
    version = "6.2.0.25"
    login = "514851"
    password = "yevv3cmf"

    def __init__(self, cfg):
        self.aggregation = str(cfg['inputParams']['aggFreq'])
        self.symbolsNeeded = cfg['fitParams']['basket']['symbolsNeeded']

        return

    def findBackMonth(self, baseSym):
        """
        Request futures symbol chain from IQF and pick up the current back month symbol
        """
        message = f"CFU,{baseSym},,0123456789,2"
        self.sendSocketMessage(message)
        symList = self.clientSocket.recv(self.receiveSize).decode('utf-8').split('\n')[0].split(',')
        return symList[1]

    def constructSymbolMap(self):
        refData = utility.loadRefData()
        self.symbolMap = {}
        for i in self.symbolsNeeded:
            if i[-1] in ['0', '=']:
                iqfSym = refData.loc[i]['iqfSym']
            else:
                baseSym = refData.loc[i[:-1] + '0']['iqfSym'][:-2]
                iqfSym = self.findBackMonth(baseSym)
            self.symbolMap[i] = iqfSym
        return self.symbolMap

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

    def updateDataMap(self):
        self.constructSymbolMap()

        lg.info("Pulling Latest Prices...")
        self.dataMap = {}
        for sym in self.symbolMap:
            message = f'HIX,{self.symbolMap[sym]},{self.aggregation},1'
            self.sendSocketMessage(message)
            self.dataMap[sym] = self.clientSocket.recv(self.receiveSize).decode('utf-8').split('\n')[0].split(',')
            lg.info(f'{sym} {self.symbolMap[sym]} {self.dataMap[sym]}')

            # Flush the socket of the !ENDMSG! before requesting next symbol
            self.clientSocket.recv(self.receiveSize)
        return

    def closeSocket(self):
        self.clientSocket.close()
        lg.info("Socket Closed.")
        return

    def constructMD(self):
        md = {}
        for sym in self.dataMap:
            if len(self.dataMap[sym]) == 8:
                md[f'{sym}_lastTS'] = pd.Timestamp(self.dataMap[sym][0])
                md[f'{sym}_midPrice'] = float(self.dataMap[sym][4])
                md[f'{sym}_symbol'] = self.dataMap[sym]
            else:
                md[f'{sym}_lastTS'] = np.nan
                md[f'{sym}_midPrice'] = np.nan
                md[f'{sym}_symbol'] = np.nan
        return pd.Series(md)

    def pullLatestMD(self):
        self.openConnection()
        self.createClientSocket()
        self.updateDataMap()
        self.closeSocket()
        return self.constructMD()
