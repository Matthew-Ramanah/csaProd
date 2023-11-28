from pyConfig import *
from modules import dataFeed, utility

with open(cfg_file, 'r') as f:
    cfg = json.load(f)

# Load Seed Dump
researchFeeds = utility.loadResearchFeeds(cfg)
seeds = utility.constructSeeds(researchFeeds, cfg, prod=True)


def pullEmailCSV():
    server = poplib.POP3(posServer)
    server.user(posUser)
    server.pass_(posPass)

    # get amount of new mails and get the emails for them
    messages = [server.retr(n + 1) for n in range(len(server.list()[1]))]

    # for every message get the second item (the message itself) and convert it to a string with \n; then create python email with the strings
    emails = [email.message_from_string('\n'.join(message[1])) for message in messages]

    for mail in emails:
        # check for attachment;
        for part in mail.walk():
            if not mail.is_multipart():
                continue
            if mail.get('Content-Disposition'):
                continue
            file_name = part.get_filename()
            print(file_name)
            # check if email park has filename --> attachment part
            if file_name:
                file = open(file_name, 'w+')
                file.write(part.get_payload(decode=True))
                file.close()
    return


# Load Positions
def loadPositions(cfg):



    # Placeholder until I load in the email file
    positions = {}
    for sym in cfg['targets']:
        positions[sym] = 0

    return positions

def dumpSeeds(fitModels, md):
    # Dump latest MD

    # Dump midPrices & vols for all preds + target

    # Dump lastTS date

    # Dump last fxRate

    # Dump smooth, Z & vol for all features

    # Dump latest positions
    return

positions = loadPositions(cfg)

# Initialise models
fitModels = utility.initialiseModels(cfg, seeds=seeds, positions=positions, prod=True)

# Get latest md object
md = dataFeed.feed(cfg).pullLatestMD()

# Parse the same md through several times for now
for i in range(3):
    for sym in fitModels:
        # Update models
        fitModels[sym].mdUpdate(md)

        # Generate tradeFile

        # Dump new seeds & logs

lg.info("Completed.")
for sym in fitModels:
    print(sym)
    for j in fitModels[sym].log:
        print(j)
    print("")
