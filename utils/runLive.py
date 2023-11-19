from pyConfig import *
from modules import utility

host = "127.0.0.1"
livePort = 5009
backMonth = 'H24'

with open(cfg_file, 'r') as f:
    cfg = json.load(f)


def findIQFSymbols(cfg):
    refData = utility.loadRefData()
    symbolMap = {}
    for i in cfg['fitParams']['basket']['symbolsNeeded']:
        if i[-1] in ['0', '=']:
            iqfSym = refData.loc[i]['iqfSym']
        else:
            frontSym = refData.loc[i[:-1] + '0']['iqfSym']
            iqfSym = frontSym[:-2] + backMonth
        symbolMap[i] = iqfSym
    return symbolMap


def openConnection():
    productID = 'SYDNEY_QUANTITATIVE_50907'
    version = "6.2.0.25"
    login = "514851"
    password = "yevv3cmf"
    lg.info("Opening Connection...")
    subprocess.Popen(
        ["IQConnect.exe", f"‑product {productID} ‑version {version} ‑login {login} ‑password {password} ‑autoconnect"])
    time.sleep(10)
    return


def createClientSocket(port='historical'):
    lg.info("Creating Socket...")
    clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    clientSocket.connect((host, livePort))
    sendSocketMessage(clientSocket,
                      "S,SELECT UPDATE FIELDS,Symbol,Market Open,Settlement Date,Bid,Bid Size,Ask,Ask Size")
    printSocketData(clientSocket.recv(1024))

    sendSocketMessage(clientSocket, "S,TIMESTAMPSOFF")
    printSocketData(clientSocket.recv(1024))

    lg.info("Socket Created.")
    return clientSocket


def watchSymbols(s, iqfSymbolMap):
    lg.info("Adding Symbols to Watchlist...")
    for sym in iqfSymbolMap:
        message = f'w{iqfSymbolMap[sym]}'
        sendSocketMessage(s, message)
    return


def refreshSymbols(s, iqfSymbolMap):
    lg.info("Refreshing Symbols...")
    for sym in iqfSymbolMap:
        message = f'f{iqfSymbolMap[sym]}'
        sendSocketMessage(s, message)
    return


def printSocketData(data):
    out = data.decode('utf-8').split('\n')
    for i in out:
        print(i)
    return out


def sendSocketMessage(s, message):
    s.sendall(bytes(message + "\r\n", "utf-8"))
    return


iqfSymbolMap = findIQFSymbols(cfg)
openConnection()
clientSocket = createClientSocket(port='historical')
watchSymbols(clientSocket, iqfSymbolMap)
printSocketData(clientSocket.recv(1024))
refreshSymbols(clientSocket, iqfSymbolMap)
printSocketData(clientSocket.recv(1024))

clientSocket.close()
lg.info("Socket Closed.")
