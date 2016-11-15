"""This module exports the bench class"""

from __future__ import print_function

import os
import stat
import re
import shutil

from pyc.runJob import runJob
from pyc.download import download

class bench(runJob):
    """Bench class designed to handle general purpose benchmark topics"""

    def __init__(self, args, name, bType):
        """Initialize bench class instance"""
        runJob.__init__(self, args)
        self.tmp = os.path.join(args.tmp, "bench")
        self.dld = download(self.tmp)
        self.bName = name
        self.bType = bType

    @staticmethod
    def __modifMakefile__(makefiles, keys, values, comments=None):
        """Modify Makefiles by replacing key values by new ones or commenting lines"""
        if len(keys) != len(values):
            return
        for mk in makefiles:
            os.chmod(mk, stat.S_IRUSR | stat.S_IWUSR)
            if not os.path.exists(mk + ".ini"): # Save a copy of the very first file version
                shutil.copyfile(mk, mk + ".ini")
            lines = open(mk, "r").readlines()
            for idxl, line in enumerate(lines):
                if comments:
                    for comment in comments:
                        if line.find(comment) != -1 and len(line) >= 1 and line[0] != "#":
                            lines[idxl] = "#" + line
                            break # The line is commented
                for idxp, key in enumerate(keys):
                    if re.search("^" + key + " *= *", line): # Search for "key = " from line start
                        lines[idxl] = key + " = " + values[idxp] + "\n"
                        break # Each file can fit only one pattern
            open(mk, "w").writelines(lines)

    def __printMetricStatus__(self, printMax, maxMc, maxInfo):
        """Print the status of the benchmark metric"""
        if printMax:
            if maxMc == 0.:
                print("Analysing %9s: benchmark has not been run" % self.bName)
            else:
                unitMc = "GFlop/s" if self.bType == "GF" else "MB/s"
                print("Analysing %9s: maximum = %11.3f %7s," % (self.bName, maxMc, unitMc), maxInfo["LOG"])
                if "EXTRA" in maxInfo:
                    print("%51s" % " ", maxInfo["EXTRA"])

    @staticmethod
    def __getStepsFromKey__(dic, nKey):
        """Get steps that match a given key"""
        steps = []
        for mK in list(dic.keys()):
            for sK in list(dic[mK].keys()):
                for s in list(dic[mK][sK].keys()):
                    if s.find(nKey) != -1:
                        steps.append(s)
        return list(set(steps)) # Remove duplicates

    @staticmethod
    def __returnMetric__(dic, maxInfo, maxMc, getDict=False, getMaxInfo=False):
        """Return the best metric in different ways"""
        if getDict:
            return dic
        if getMaxInfo:
            return maxInfo
        return maxMc

    @staticmethod
    def __cleanUseCase__(tmp, ucDir):
        """Clean use case directory"""
        if os.path.exists(tmp):
            os.chdir(tmp)
            if os.path.exists(ucDir):
                shutil.rmtree(ucDir)
        ucPth = os.path.join(tmp, ucDir)
        os.makedirs(ucPth)
        return ucPth

    def getName(self):
        """Get benchmark name"""
        return self.bName

    def getType(self):
        """Get benchmark type"""
        return self.bType

    def run(self, ext):
        """Run benchmark over all possible proc and thread configurations"""
        print("Running", self.bName, "...")
        for n in self.args.proc:
            t = 1 # Number of thread(s)
            while n * t <= max(self.args.proc):
                runTokens = [("n", n, "d", max(self.args.proc))]
                runTokens += [("t", t, "d", max(self.args.proc))]
                self.runNT(n, t, runTokens, ext)
                t *= 2

    def plot(self):
        """Plot benchmark results over all possible configurations"""
        print("Plotting", self.bName, "...")
        for n in self.args.proc:
            nKey = ("n=%0" + str(len(str(max(self.args.proc)))) + "d") % n
            self.plotN(nKey)

    def downloadTmp(self):
        """Download benchmark in the temporary directory"""
        pass # To be overriden by inherited class

    def check(self):
        """Check benchmark consistency"""
        print("Checking", self.bName, "benchmark ... OK")
        return True

    def build(self, cpl):
        """Build benchmark in the temporary directory"""
        pass # To be overriden by inherited class

    def runNT(self, n, t, runTokens, ext):
        """Run benchmark in the temporary directory for a given proc and thread configuration"""
        pass # To be overriden by inherited class

    def getMetric(self, printMax=True, getDict=False, getMaxInfo=False, filterLogs=False):
        """Getting benchmark metric from the temporary directory"""
        pass # To be overriden by inherited class

    def plotN(self, nKey):
        """Plotting benchmark results from the temporary directory for a given proc configuration"""
        pass # To be overriden by inherited class

    def genUseCase(self):
        """Generate a use case from the best benchmark run"""
        pass # To be overriden by inherited class
