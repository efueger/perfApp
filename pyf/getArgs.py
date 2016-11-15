"""Manage parser arguments"""

# Import modules

from __future__ import print_function

import os
import multiprocessing
import shutil
import glob

from pyf.getParser import getParser

def getArgs():
    """Get and return parser arguments"""
    parser = getParser()
    args = parser.parse_args()

    root = os.getcwd() # Current working directory
    args.root = root

    maxProc = args.nproc if args.nproc > 0 else multiprocessing.cpu_count()
    args.proc = []
    if hasattr(args, "quick") and args.quick:
        args.proc = [1, maxProc // 2, maxProc]
    else:
        n = 1
        while n <= maxProc:
            args.proc.append(n)
            n *= 2

    args.tmp = os.path.join(root, "tmp")
    args.usc = os.path.join(root, "tmp", "usc")
    if not os.path.exists(args.usc):
        os.makedirs(args.usc)
    for ucp in glob.glob(os.path.join(args.root, "usc", "*")):
        uct = os.path.join(args.usc, os.path.basename(ucp))
        if not os.path.exists(uct):
            if os.path.isdir(ucp):
                shutil.copytree(ucp, uct)
            else:
                shutil.copyfile(ucp, uct)

    args.plt = os.path.join(root, "tmp", "plt")

    return args
