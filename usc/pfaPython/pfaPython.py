#!/usr/bin/env python

"""This python script is a use case"""

# Import modules

from __future__ import print_function

import time
import sys
import numpy

# Functions

def doCacheMisses(n):
    """Do swaps to trigger cache misses"""
    print("Do cache misses with n =", n)
    ls = numpy.ones(n)
    for idx in range(n):
        tmp = ls[n-1-idx]
        ls[n-1-idx] = ls[idx]
        ls[idx] = tmp

def doFlops(n):
    """Do arithmetics to trigger cache misses"""
    print("Do flops with n =", n)
    nb = 0.0
    for idx in range(n):
        nb = nb + 2.0 * idx / 2 - idx

# Main program

def main():
    """Main function of the module"""
    start = time.time()
    doCacheMisses(int(sys.argv[1]) if len(sys.argv) >= 2 else 1000)
    doFlops(int(sys.argv[2]) if len(sys.argv) >= 3 else 1000)
    print("Total time = %11.3f sec\n" % (time.time() - start))

if __name__ == '__main__':
    main()
