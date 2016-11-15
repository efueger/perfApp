#!/usr/bin/env python

"""This python script is the entry point of perfApp"""

# Import modules

from __future__ import print_function

import time
import sys
import os
if "PFA_MLK" in os.environ:
    from pympler import tracker

from pyf.getArgs import getArgs
from pyf.readConfig import readConfig
from pyf.getMLK import getMLK
from pyc.perfMonitor import perfMonitor

# Main program

def main():
    """Main function of the module"""
    mlkTrk = tracker.SummaryTracker() if "PFA_MLK" in os.environ else None

    start = time.time()
    args = getArgs()

    print("Configuring ...")
    readConfig(args)
    print("") # Output separator for clarity

    print("Downloading ...")
    if args.mode == "bench":
        for bm in args.bmLs:
            if args.bench == "All" or args.bench == bm.getName():
                bm.downloadTmp()
    else:
        pm = perfMonitor(args, needReg=False)
        pm.downloadTmp()
    print("") # Output separator for clarity
    if args.dlonly:
        sys.exit()

    getMLK(mlkTrk)
    args.func(args) # Run parser mode
    print("Total time = %11.3f sec\n" % (time.time() - start))
    getMLK(mlkTrk)

if __name__ == '__main__':
    main()
