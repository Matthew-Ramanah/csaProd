from pyConfig import *
from modules import syntheticMD, utility

with open(cfg_file, 'r') as f:
    cfg = json.load(f)
recon = pd.read_hdf(f"{proDataRoot}{cfg['modelTag']}/recon.h5", key='recon', mode='r')
recon = recon.head(10)

seeds = utility.constructSeeds(recon, cfg)
targets = utility.initialiseModels(cfg, seeds=seeds)

# Replace this with the live feed in production
feed = syntheticMD.loadSyntheticMD(cfg)
feed = feed.head(100)
lg.info("Feed Loaded.")

for i, md in feed.iterrows():
    lg.info(f"Update: {i}")
    for target in targets:
        target.mdUpdate(md)
        #lg.info(f'{target.sym} hOpt: {target.hOpt}')

        # Generate trades -> Apply tradeSizeCap from cfg here

        # Log
lg.info("Completed")
