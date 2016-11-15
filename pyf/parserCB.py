"""Manage parser callbacks"""

# Import modules

from __future__ import print_function

import os
import sys
import distutils.spawn
import glob

from pyc.useCase import useCase
from pyf.getCompilers import getCompilers
from pyf.plotRLM import plotRLM

# Functions

def checkCB(args):
    """Callback for check mode"""
    uc = useCase(args, needReg=False)
    for ucp in glob.glob(os.path.join(args.usc, "*")):
        if os.path.isdir(ucp):
            print("Checking", os.path.basename(ucp), "use case ...")
            uc.readConfig(ucp)

    print("Checking benchmarks ...")
    for bm in args.bmLs:
        bm.check()
    print("") # Output separator for clarity

    uc.getRegisters()
    print("To check out perf    events, type \"perf list\"")
    print("To check out libpfm4 events, type \"less ./tmp/libpfm-" + args.pfm4Vn + "/examples/showevtinfo.log\"")
    print("") # Output separator for clarity

def benchCB(args):
    """Callback for bench mode"""
    if args.ucase:
        for bm in args.bmLs:
            if args.bench == "All" or args.bench == bm.getName():
                print("Generating use case for", bm.getName(), "...")
                bm.genUseCase()
                print("") # Output separator for clarity
        return

    print("Looking for compilers ...")
    cpl = getCompilers(args)
    print("") # Output separator for clarity

    ext = ".more" if args.more else ".less" # Do not lost short results when re-running more runs
    ext += ".quick" if args.quick else ".long"
    ext = "." + ".".join(args.logID) + ext + ".log" if len(args.logID) > 0 else ext + ".log"
    for bm in args.bmLs:
        if args.bench == "All" or args.bench == bm.getName():
            print("Benchmarking", bm.getName(), "...")
            if bm.check():
                bm.build(cpl)
                bm.run(ext)
            print("") # Output separator for clarity

    print("Analysing benchmark logs ...")
    for bm in args.bmLs:
        if args.bench == "All" or args.bench == bm.getName():
            bm.getMetric() # Print best metrics
    print("") # Output separator for clarity

def ucaseCB(args):
    """Callback for ucase mode"""
    if not distutils.spawn.find_executable("perf"):
        sys.exit("ERROR: can't find perf, install it, allow users to run it (not paranoid mode) or run as root")

    if not args.stat and not args.report and not args.top:
        args.stat = True # Stat as default option

    uc = useCase(args)
    for ucp in glob.glob(os.path.join(args.usc, args.uc)):
        if os.path.isdir(ucp):
            if uc.readConfig(ucp):
                uc.runUseCase()

def plotCB(args):
    """Callback for plot mode"""
    uc = useCase(args) if args.uc or (args.rlm and args.rlm != -1) else None
    if args.uc:
        for ucp in glob.glob(os.path.join(args.usc, args.uc)):
            if os.path.isdir(ucp):
                if uc.readConfig(ucp):
                    print("Plotting", os.path.basename(ucp), "use case ...")
                    uc.plot()
                    print("") # Output separator for clarity

    if args.bench:
        print("Plotting benchmarks ...")
        for bm in args.bmLs:
            if args.bench == "All" or args.bench == bm.getName():
                bm.plot()
        print("") # Output separator for clarity

    if args.rlm:
        lsUCS = []
        if args.rlm != -1:
            for ucp in glob.glob(os.path.join(args.usc, args.rlm)):
                if os.path.isdir(ucp):
                    if uc.readConfig(ucp):
                        print("Analysing", os.path.basename(ucp), "use case statistics ...")
                        lsUCS += uc.getUseCaseStat()
                        print("") # Output separator for clarity
        plotRLM(lsUCS, args)
