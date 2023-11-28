from pyConfig import *
import gmail

GMAIL_CREDENTIALS_PATH = root + "credentials.json"
GMAIL_TOKEN_PATH = root + "token.json"
lg.info("Starting")

searchQuery = "CBCT EOD POSITIONS"
service = gmail.get_gmail_service(GMAIL_CREDENTIALS_PATH, GMAIL_TOKEN_PATH)
latestEmail = gmail.pullLatestPosFile(service, searchQuery)

# 1st Attachment found:
df = latestEmail['data']
print('email: ' + latestEmail['emailsubject'])
print('filename: ' + latestEmail['filename'])
print("data sample: ")
print(df.head())
