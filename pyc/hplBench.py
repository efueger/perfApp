"""This module exports the hplBench class"""

from __future__ import print_function

import os
import sys
import platform
import subprocess
import time
import shutil
import math
import stat
import json

from pyc.bench import bench

class hplBench(bench):
    """Class dedicated to the HPLinpack benchmark"""

    def __init__(self, args, blasDic, hplURL, hplVn, hplLID):
        """Initialize HPLinpack bench class instance"""
        bench.__init__(self, args, "HPLinpack", "GF")
        self.blasURL = blasDic["URL"]
        self.blasDir = "BLAS-" + blasDic["VERSION"] if blasDic["VERSION"] else None
        self.blasLib = blasDic["LIBBLAS"]
        self.hplDir = "hpl-" + hplVn
        self.hplURL = hplURL
        self.hplLID = hplLID
        self.arch = platform.system() + "_" + platform.machine()

    def __buildBlas__(self, cpl):
        """Build BLAS for HPLinpack"""
        if self.blasLib:
            return # Use specified blas lib if specified
        buildDir = os.path.join(self.tmp, self.blasDir)
        if os.path.exists(buildDir):
            os.chdir(buildDir)
            self.__modifMakefile__(["make.inc"], ["PLAT"], [""])
            self.__modifMakefile__(["make.inc"], ["FORTRAN", "LOADER"], [cpl["FC"], cpl["FC"]])
            self.__modifMakefile__(["make.inc"], ["OPTS"], [cpl["FLAGS"]])
            log = open("make.log", "w")
            print("Building BLAS for", self.bName, "...", end="")
            start = time.time()
            rc = subprocess.call(["make", "VERBOSE=1"], stdout=log, stderr=log)
            if rc != 0:
                self.buildError(log)
            self.printStatus(start, rc)

    def __buildHPL__(self, cpl):
        """Build HPLinpack"""
        buildDir = os.path.join(self.tmp, self.hplDir)
        if os.path.exists(buildDir):
            os.chdir(buildDir)
            if not os.path.exists("Make." + self.arch): # Create hpl/Make.arch
                rc = subprocess.call(["sh", "make_generic"], cwd="setup") # Create hpl/setup/Make.UNKNOWN
                if rc == 0:
                    shutil.copyfile("setup/Make.UNKNOWN", "Make." + self.arch)
            oldOptions = ["ARCH", "arch", "HPL_OPTS", "CC", "LINKER"]
            newOptions = [self.arch, self.arch, cpl["FLAGS"], cpl["MPICC"], cpl["MPIFC"]]
            self.__modifMakefile__(["Makefile", "Make.top", "Make." + self.arch], oldOptions, newOptions)
            oldOptions = ["TOPdir"]
            newOptions = [os.path.join(self.tmp, self.hplDir)]
            oldOptions += ["LAlib"]
            if self.blasLib:
                newOptions += [self.blasLib]
            else:
                newOptions += [os.path.join(self.tmp, self.blasDir, "blas.a")]
            oldOptions += ["CCNOOPT"] # HPL_dlamch.c: aggressive optimisations trigger inifinite loops
            newOptions += ["$(F2CDEFS) " + cpl["NOOPTFLAGS"] + " $(HPL_INCLUDES)"]
            oldOptions += ["LINKFLAGS"]
            newOptions += [cpl["LINKFLAGS"]]
            self.__modifMakefile__(["Make." + self.arch], oldOptions, newOptions)
            log = open("make.log", "w")
            print("Building", self.bName, "...", end="")
            start = time.time()
            rc = subprocess.call(["make", "arch=" + self.arch, "VERBOSE=1"], stdout=log, stderr=log)
            if rc != 0:
                self.buildError(log)
            self.printStatus(start, rc)

    def __writeHPLFile__(self, hplPS, hplDiv, hplBlock, n):
        """Write input file for HPLinpack runs"""
        lines = open("HPL.dat.ini", "r").readlines()
        lines[4] = "1" + "\n" # Number of problems
        lines[5] = str(hplPS // hplDiv) + "\n" # Problem size
        lines[6] = "1" + "\n"
        lines[7] = str(hplPS // hplDiv // hplBlock) + "\n" # Problem block size
        if n > 1 and int(math.sqrt(n)) ** 2 == n: # Number of process grid
            lines[9] = "2" + "\n" # Play on load balancing
            lines[10] = str(n) + " " + str(int(math.sqrt(n))) + "\n"
            lines[11] = "1" + " " + str(int(math.sqrt(n))) + "\n"
        else: # Number of process grid
            lines[9] = "1" + "\n"
            lines[10] = str(n) + "\n"
            lines[11] = "1" + "\n"
        if not self.args.more:
            lines[13] = "1" + "\n"
            lines[14] = "0" + "\n" # PFACTs
            lines[15] = "1" + "\n"
            lines[16] = "2" + "\n" # NBMINs
            lines[19] = "1" + "\n"
            lines[20] = "0" + "\n" # RFACTs
        open("HPL.dat", "w").writelines(lines)

    def __getMetricFromLine__(self, line, maxGFlops, log, dicGFlops):
        """Get metric from a line of a log"""
        maxInfo = {}
        if len(line.split()) == 7:
            if len(line) > 1 and line[0] == "W":
                GF = float(line.split()[6])
                N = int(line.split()[1])
                NB = int(line.split()[2])
                if maxGFlops < GF:
                    maxGFlops = GF
                    maxInfo["LOG"] = os.path.basename(log)
                    maxInfo["EXTRA"] = "N = " + str(N) + ", NB = " + str(NB)
                if N not in dicGFlops:
                    dicGFlops[N] = {}
                if NB not in dicGFlops[N]:
                    dicGFlops[N][NB] = {}
                logTokens = self.splitLogName(log)
                step = logTokens["n="] + "." + logTokens["t="]
                if step not in dicGFlops[N][NB]:
                    dicGFlops[N][NB][step] = GF
                if dicGFlops[N][NB][step] < GF:
                    dicGFlops[N][NB][step] = GF
        return maxGFlops, maxInfo

    def downloadTmp(self):
        """Download HPLinpack benchmark in the temporary directory"""
        os.chdir(self.tmp)
        print("Downloading BLAS for", self.bName, "...")
        blasTGZ = "blas-" + self.blasDir[5:] + ".tgz"
        self.dld.downloadFile(os.path.join(self.blasURL, blasTGZ))
        if not os.path.exists(self.blasDir) and os.path.exists(blasTGZ):
            if subprocess.call(["tar", "-xzf", blasTGZ]) != 0:
                sys.exit("ERROR: can not untar BLAS")
        print("Downloading", self.bName, "...")
        hplTGZ = "hpl-" + self.hplDir[4:] + ".tar.gz"
        self.dld.downloadFile(os.path.join(self.hplURL, hplTGZ))
        if not os.path.exists(self.hplDir) and os.path.exists(hplTGZ):
            if subprocess.call(["tar", "-xzf", hplTGZ]) != 0:
                sys.exit("ERROR: can not untar " + self.bName)

    def check(self):
        """Check HPLinpack benchmark consistency"""
        print("Checking", self.bName, "benchmark ...", end="")
        if self.blasLib:
            if not os.path.exists(self.blasLib):
                print(" KO :", self.blasLib, "does not exists, configure json")
                return False
        else:
            if not self.blasURL or not self.blasDir:
                print(" KO : URL and VERSION must be specified, configure json")
                return False
        print(" OK")
        return True

    def build(self, cpl):
        """Build HPLinpack benchmark in the temporary directory"""
        self.__buildBlas__(cpl)
        self.__buildHPL__(cpl)

    def runNT(self, n, t, runTokens, ext):
        """Run HPLinpack benchmark in the temporary directory for a given proc and thread configuration"""
        runDir = os.path.join(self.tmp, self.hplDir, "bin", self.arch)
        if os.path.exists(runDir):
            os.chdir(runDir)
            if not os.path.exists("HPL.dat.ini"): # Save a copy of the very first file version
                shutil.copyfile("HPL.dat", "HPL.dat.ini")
            hplPS = self.args.size * 1024. ** 3 # 1GB by default
            hplPS = int(hplPS / 8)
            hplPS = int(math.sqrt(hplPS)) # According to HPL tuning guide
            for hplDiv in [4096, 2048, 1024, 512, 256, 128, 64, 32, 16, 8, 4]:
                minBlockNb = 4
                if self.args.quick:
                    if hplPS // hplDiv // minBlockNb > 8:
                        break # Big blocks are less efficient
                hplBlockSize = [bs for bs in range(minBlockNb, 11)] # Up to 10%
                if self.args.more:
                    hplBlockSize = [bs for bs in range(minBlockNb, 21)] # Up to 5%
                for hplBlock in hplBlockSize:
                    if hplPS // hplDiv // hplBlock <= 0:
                        continue
                    hplTokens = [("size", hplPS, "s"), ("div", hplDiv, "d", 4096)]
                    hplTokens += [("block", hplBlock, "d", max(hplBlockSize))]
                    hplTokens += runTokens
                    hplExt = ext
                    for logID in self.hplLID:
                        hplExt = "." + logID + ext
                    hplLog = self.buildLogName("HPL", hplTokens, hplExt)
                    print("Running", hplLog, "...", end="")
                    start = time.time()
                    rc = 0
                    if not os.path.exists(hplLog) or self.args.force:
                        self.__writeHPLFile__(hplPS, hplDiv, hplBlock, n)
                        log = open(hplLog, "w")
                        clDic = {}
                        clDic["PREPEND"] = ["mpirun", "-n", str(n)]
                        clDic["EXE"] = "./xhpl"
                        rc = self.runCmdLine(log, clDic, begin=start, thd=t)
                    self.printStatus(start, rc)

    def getMetric(self, printMax=True, getDict=False, getMaxInfo=False, filterLogs=False):
        """Getting HPLinpack benchmark metric from the temporary directory"""
        maxGFlops = 0.
        dicGFlops = {}
        maxInfo = {}
        runDir = os.path.join(self.tmp, self.hplDir, "bin", self.arch)
        if os.path.exists(runDir):
            os.chdir(runDir)
            for log in self.__listLogs__(os.path.join(runDir, "HPL*.log"), filterLogs):
                lines = open(log, "r").readlines()
                for line in lines:
                    mGFlops, mInfo = self.__getMetricFromLine__(line, maxGFlops, log, dicGFlops)
                    if maxGFlops < mGFlops:
                        maxGFlops = mGFlops
                        maxInfo = mInfo
        self.__printMetricStatus__(printMax, maxGFlops, maxInfo)
        return self.__returnMetric__(dicGFlops, maxInfo, maxGFlops, getDict=getDict, getMaxInfo=getMaxInfo)

    def plotN(self, nKey):
        """Plotting HPLinpack benchmark results from the temporary directory for a given proc configuration"""
        dicGFlops = self.getMetric(printMax=False, getDict=True, filterLogs=True)
        steps = self.__getStepsFromKey__(dicGFlops, nKey)
        plotName = self.plt.buildPlotName([self.bName, nKey])
        self.plt.plot3DGraph(plotName, dicGFlops, steps, "N", "NB", "GFlops")

    def genUseCase(self):
        """Generate a use case from the best HPLinpack benchmark run"""
        maxInfo = self.getMetric(printMax=False, getMaxInfo=True)
        if "LOG" in maxInfo:
            ucDir = self.__cleanUseCase__(os.path.join(self.args.tmp, "usc"), "pfb" + self.bName)
            os.chdir(ucDir)
            runDir = os.path.join(self.tmp, self.hplDir, "bin", self.arch)
            shutil.copyfile(os.path.join(runDir, "xhpl"), "xhpl")
            os.chmod("xhpl", os.stat("xhpl").st_mode | stat.S_IEXEC) # chmod +x
            if os.path.exists(os.path.join(runDir, "HPL.dat.ini")):
                shutil.copyfile(os.path.join(runDir, "HPL.dat.ini"), "HPL.dat.ini")
                logTokens = self.splitLogName(maxInfo["LOG"])
                hplPS = int(logTokens["size="].split("=")[1])
                hplDiv = int(logTokens["div="].split("=")[1])
                hplBlock = int(logTokens["block="].split("=")[1])
                n = int(logTokens["n="].split("=")[1])
                self.__writeHPLFile__(hplPS, hplDiv, hplBlock, n)
                runSh = open("run.sh", "w")
                runSh.write("#!/bin/bash" + "\n")
                runSh.write("cp ../HPL.dat ." + "\n") # Copy HPLinpack input file
                runSh.close() # Flush
                jsCfg = {}
                jsCfg["EXE"] = "xhpl"
                jsCfg["MPI"] = str(logTokens["n="].split("=")[1])
                jsCfg["THD"] = str(logTokens["t="].split("=")[1])
                jsCfg["COLOR"] = "red"
                jsCfg["MARKER"] = "."
                jsCfg["LABEL"] = self.bName
                json.dump(jsCfg, open("usc.json", "w"))
