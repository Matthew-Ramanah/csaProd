import subprocess
import socket
import time

host = "127.0.0.1"
livePort = 5009
historicalPort = 9100

symbols = ['@TYZ23']
# Open Connection
subprocess.Popen(["IQConnect.exe",
                  "‑product SYDNEY_QUANTITATIVE_50907 ‑version 6.2.0.25 ‑login 514851 ‑password yevv3cmf ‑autoconnect"])
time.sleep(10)

# Connect To Socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((host, livePort))

# Format
s.sendall(b'S,SELECT UPDATE FIELDS,Symbol,Market Open,Settlement Date,Bid,Bid Size,Ask,Ask Size\r\n')
s.sendall(b'S,TIMESTAMPSOFF\r\n')

# Start watching all symbols needed
s.sendall(b'w@TYZ23\r\n')
print(s.recv(1024))
print(s.recv(1024))

# Refresh each symbol in case it hasn't ticked
print('refreshing')
s.sendall(b'f@TYZ23\r\n')
print(s.recv(1024))
print(s.recv(1024))
print('done')
s.close()
