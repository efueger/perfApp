"""Manage memory leaks"""

# Import modules

from __future__ import print_function

def getMLK(mlkTrk):
    """Get the memory leak status"""
    if mlkTrk:
        print("MLK report:")
        mlkTrk.print_diff()
        print("") # Output separator for clarity
