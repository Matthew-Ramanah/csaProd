from pyConfig import *
from modules import utility

host = "127.0.0.1"
livePort = 5009
historicalPort = 9100

backMonth = 'H24'

with open(cfg_file, 'r') as f:
    cfg = json.load(f)


def findIQFSymbols(cfg):
    refData = utility.loadRefData()
    symbols = []
    for i in cfg['fitParams']['basket']['symbolsNeeded']:
        if i[-1] in ['0', '=']:
            iqfSym = refData.loc[i]['iqfSym']
        else:
            frontSym = refData.loc[i[:-1] + '0']['iqfSym']
            iqfSym = frontSym[:-2] + backMonth
        symbols.append(iqfSym)
    return symbols


def openConnection():
    productID = 'SYDNEY_QUANTITATIVE_50907'
    version = "6.2.0.25"
    login = "514851"
    password = "yevv3cmf"
    subprocess.Popen(
        ["IQConnect.exe", f"‑product {productID} ‑version {version} ‑login {login} ‑password {password} ‑autoconnect"])
    time.sleep(10)
    return


def connectToSocket():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, livePort))
    s.sendall(b'S,SELECT UPDATE FIELDS,Symbol,Market Open,Settlement Date,Bid,Bid Size,Ask,Ask Size\r\n')
    s.sendall(b'S,TIMESTAMPSOFF\r\n')
    return s


def watchSymbols(s, iqfSymbols):
    for sym in iqfSymbols:
        message = f'w{sym}'
        s.sendall(bytes(message + "\r\n", "utf-8"))
    return


def refreshSymbols(s, iqfSymbols):
    # Refresh each symbol in case it hasn't ticked
    for sym in iqfSymbols:
        print(sym)
        message = f'b{sym}'
        s.sendall(bytes(message + "\r\n", "utf-8"))
        print(s.recv(2048))
        print("")
    return


def pullHistorical(s, iqfSymbols):
    for sym in iqfSymbols:
        print(sym)
        message = f'5MS,{sym},3600,1'
        print(message)
        s.sendall(bytes(message + "\r\n", "utf-8"))
        print(s.recv(2048))
        print("")

    return


iqfSymbols = findIQFSymbols(cfg)
print(iqfSymbols)
openConnection()
s = connectToSocket()
watchSymbols(s, iqfSymbols)
refreshSymbols(s, iqfSymbols)
s.close()
