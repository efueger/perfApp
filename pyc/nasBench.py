"""This module exports the nasBench class"""

from __future__ import print_function

import os
import sys
import subprocess
import time
import shutil
import glob
import stat
import json

from pyc.bench import bench

class nasBench(bench):
    """Class dedicated to the NAS benchmark"""

    def __init__(self, args, nasURL, nasVn, nasMPIID, nasVec):
        """Initialize NAS bench class instance"""
        bench.__init__(self, args, "NAS", "GF")
        self.nasURL = nasURL
        self.nasDir = "NPB" + nasVn
        self.nasTGZ = "NPB" + nasVn +".tar.gz"
        self.nasMPIID = nasMPIID
        self.nasVec = nasVec
        self.benchLs = []
        self.classLs = []

    def __writeSuite__(self, nasImpl):
        """Write suite file for NAS builds"""
        suite = open("suite.def", "w")
        self.benchLs = ["bt", "cg", "ep", "ft", "is", "lu", "mg", "sp"]
        self.benchLs += ["dc", "ua"] if nasImpl.find("MPI") == -1 else ["dt"]
        if self.args.quick:
            if "dc" in self.benchLs:
                self.benchLs.remove("dc") # Long test: remove it for quick benchmark
            if "sp" in self.benchLs:
                self.benchLs.remove("sp") # Long test: remove it for quick benchmark
        for benchName in self.benchLs:
            self.classLs = ["S", "W", "A", "B", "C"] if self.args.more else ["S", "W", "A"]
            for className in self.classLs:
                if nasImpl.find("MPI") == -1:
                    suite.write(benchName + " " + className + "\n")
                else:
                    for n in self.args.proc:
                        suite.write(benchName + " " + className + " " + str(n) + "\n")
        suite.close() # Flush file before make

    def __runBenchClass__(self, benchName, className, n, t, runTokens, ext):
        """Run NAS benchmark for a given bench type and class"""
        runDir = os.getcwd()
        for nasImpl in sorted(os.listdir(runDir)):
            if nasImpl.find("NPB") == -1:
                continue
            if not os.path.isdir(nasImpl):
                continue
            if nasImpl.find("SER") != -1 and t != 1:
                continue
            os.chdir(os.path.join(runDir, nasImpl, "bin"))
            for exe in glob.glob("*" + benchName + "*" + className + "*"):
                if os.access(exe, os.X_OK) is False:
                    continue # Skip logs, data generated by previous runs, ...
                idx = exe.rfind(".") + 1
                np = 1 if exe[idx:] == "x" else int(exe[idx:])
                if np != n:
                    continue
                nasExt = ".vec" + ext if self.nasVec else ext
                nasExt = ".seq" + nasExt if exe[idx:] == "x" else ".mpi" + nasExt
                nasExt = nasExt.replace(".more", "") # For NAS, more/less is included in the problem class
                nasExt = nasExt.replace(".less", "") # For NAS, more/less is included in the problem class
                nasExt = nasExt.replace(".quick", "") # For NAS, quick/long is included in the bench type
                nasExt = nasExt.replace(".long", "") # For NAS, quick/long is included in the bench type
                if len(self.nasMPIID) > 0:
                    if exe[idx:] == "x":
                        nasExt = "." + "x" * len(self.nasMPIID) + nasExt
                    else:
                        nasExt = "." + self.nasMPIID + nasExt
                runNASTokens = [("impl", nasImpl, "s")] + [("bench", benchName, "s")] + [("class", className, "s")]
                runNASTokens += runTokens
                nasLog = self.buildLogName("NAS", runNASTokens, nasExt)
                print("Running", nasLog, "...", end="")
                start = time.time()
                rc = 0
                if not os.path.exists(nasLog) or self.args.force:
                    log = open(nasLog, "w")
                    clDic = {}
                    clDic["EXE"] = "./" + exe
                    if nasImpl.find("MPI") != -1:
                        clDic["PREPEND"] = ["mpirun", "-n", str(n)]
                    rc = self.runCmdLine(log, clDic, begin=start, thd=t)
                self.printStatus(start, rc)
            os.chdir(runDir)

    def __getMetricFromFile__(self, log, maxGFlops, dicGFlops, maxInfo, nasImpl):
        """Get metric from a given log file"""
        lines = open(log, "r").readlines()
        benchName = None
        className = None
        for line in lines:
            if line.find("Benchmark Completed") != -1:
                benchName = line.split()[0]
            if line.find("Class") != -1:
                className = line.split()[2]
            if line.find("Mop/s total") != -1:
                if benchName and className:
                    GF = float(line.split()[3]) / 1000.
                    if maxGFlops < GF:
                        maxGFlops = GF
                        maxInfo["LOG"] = os.path.basename(log)
                    if benchName not in dicGFlops:
                        dicGFlops[benchName] = {}
                    if className not in dicGFlops[benchName]:
                        dicGFlops[benchName][className] = {}
                    logTokens = self.splitLogName(log)
                    step = nasImpl[-3:] + "." + logTokens["n="] + "." + logTokens["t="]
                    if step not in dicGFlops[benchName][className]:
                        dicGFlops[benchName][className][step] = GF
                    if dicGFlops[benchName][className][step] < GF:
                        dicGFlops[benchName][className][step] = GF
                    break # End of relevant data
        return maxGFlops, maxInfo

    def downloadTmp(self):
        """Download NAS benchmark in the temporary directory"""
        os.chdir(self.tmp)
        print("Downloading", self.bName, "...")
        self.dld.downloadFile(os.path.join(self.nasURL, self.nasTGZ))
        if not os.path.exists(self.nasDir) and os.path.exists(self.nasTGZ):
            if subprocess.call(["tar", "-xzf", self.nasTGZ]) != 0:
                sys.exit("ERROR: can not untar " + self.bName)

    def build(self, cpl):
        """Build NAS benchmark in the temporary directory"""
        buildDir = os.path.join(self.tmp, self.nasDir)
        if os.path.exists(buildDir):
            os.chdir(buildDir)
            print("Building", self.bName, "...")
            for nasImpl in sorted(os.listdir(buildDir)):
                if nasImpl.find("NPB") == -1:
                    continue
                if not os.path.isdir(nasImpl):
                    continue
                os.chdir(os.path.join(buildDir, nasImpl, "bin"))
                os.chdir(os.path.join(buildDir, nasImpl, "config"))
                if not os.path.exists("make.def"): # Create config/make.def
                    shutil.copyfile("make.def.template", "make.def")
                    oldOptions = ["F77", "MPIF77", "FFLAGS", "FLINKFLAGS"]
                    newOptions = [cpl["FC"], cpl["MPIFC"], cpl["FLAGS"], cpl["LINKFLAGS"]]
                    oldOptions += ["CC", "MPICC", "UCC"]
                    newOptions += [cpl["CC"], cpl["MPICC"], cpl["CC"]]
                    oldOptions += ["CFLAGS", "CLINKFLAGS"]
                    newOptions += [cpl["FLAGS"], cpl["LINKFLAGS"]]
                    self.__modifMakefile__(["make.def"], oldOptions, newOptions)
                self.__writeSuite__(nasImpl)
                os.chdir(os.path.join(buildDir, nasImpl))
                log = open("make.log", "w")
                print("Building", self.bName, ":", nasImpl, "...", end="")
                start = time.time()
                cmdLine = ["make", "suite", "VERSION=VEC"] if self.nasVec else ["make", "suite"]
                rc = subprocess.call(cmdLine, stdout=log, stderr=log)
                if rc != 0:
                    self.buildError(log)
                self.printStatus(start, rc)
                os.chdir(buildDir)

    def runNT(self, n, t, runTokens, ext):
        """Run NAS benchmark in the temporary directory for a given proc and thread configuration"""
        runDir = os.path.join(self.tmp, self.nasDir)
        if os.path.exists(runDir):
            for benchName in self.benchLs:
                for className in self.classLs:
                    os.chdir(runDir)
                    self.__runBenchClass__(benchName, className, n, t, runTokens, ext)
                    if self.args.quick:
                        break

    def getMetric(self, printMax=True, getDict=False, getMaxInfo=False, filterLogs=False):
        """Getting NAS benchmark metric from the temporary directory"""
        maxGFlops = 0.
        dicGFlops = {}
        maxInfo = {}
        runDir = os.path.join(self.tmp, self.nasDir)
        if os.path.exists(runDir):
            os.chdir(runDir)
            for nasImpl in sorted(os.listdir(runDir)):
                if nasImpl.find("NPB") == -1:
                    continue
                if not os.path.isdir(nasImpl):
                    continue
                for log in self.__listLogs__(os.path.join(runDir, nasImpl, "bin", "NAS*.log"), filterLogs):
                    mGFlops, mInfo = self.__getMetricFromFile__(log, maxGFlops, dicGFlops, maxInfo, nasImpl)
                    if mGFlops > maxGFlops:
                        maxGFlops = mGFlops
                        maxInfo = mInfo
        self.__printMetricStatus__(printMax, maxGFlops, maxInfo)
        return self.__returnMetric__(dicGFlops, maxInfo, maxGFlops, getDict=getDict, getMaxInfo=getMaxInfo)

    def plotN(self, nKey):
        """Plotting NAS benchmark results from the temporary directory for a given proc configuration"""
        dicGFlops = self.getMetric(printMax=False, getDict=True, filterLogs=True)
        steps = []
        for bn in list(dicGFlops.keys()):
            for cn in list(dicGFlops[bn].keys()):
                for s in list(dicGFlops[bn][cn].keys()):
                    if s.find(nKey) != -1:
                        steps.append(s)
        steps = list(set(steps)) # Remove duplicates
        self.plt.setPlotAttr(xTickStr=True, yTickStr=True)
        plotName = self.plt.buildPlotName([self.bName, nKey])
        self.plt.plot3DGraph(plotName, dicGFlops, steps, "Bench", "Class", "GFlops")

    def genUseCase(self):
        """Generate a use case from the best NAS benchmark run"""
        maxInfo = self.getMetric(printMax=False, getMaxInfo=True)
        if "LOG" in maxInfo:
            ucDir = self.__cleanUseCase__(os.path.join(self.args.tmp, "usc"), "pfb" + self.bName)
            os.chdir(ucDir)
            logTokens = self.splitLogName(maxInfo["LOG"])
            nasImpl = logTokens["impl="].split("=")[1]
            nasImpl = self.nasDir[0:6] + nasImpl[-4:]
            runDir = os.path.join(self.tmp, self.nasDir, nasImpl, "bin")
            exe = logTokens["bench="].split("=")[1] + "." + logTokens["class="].split("=")[1]
            n = int(logTokens["n="].split("=")[1])
            exe += ".x" if "seq" in logTokens else "." + str(n)
            shutil.copyfile(os.path.join(runDir, exe), exe)
            os.chmod(exe, os.stat(exe).st_mode | stat.S_IEXEC) # chmod +x
            jsCfg = {}
            jsCfg["EXE"] = exe
            if "mpi" in logTokens:
                jsCfg["MPI"] = str(logTokens["n="].split("=")[1])
            else: # Force MPI if seq as validation tests may broke (different machines, different best use case)
                jsCfg["MPI"] = "-1" # Force MPI="-1" if sequential (insure same "Configuring" keyword count)
            jsCfg["THD"] = str(logTokens["t="].split("=")[1])
            jsCfg["COLOR"] = "black"
            jsCfg["MARKER"] = "."
            jsCfg["LABEL"] = self.bName
            json.dump(jsCfg, open("usc.json", "w"))
