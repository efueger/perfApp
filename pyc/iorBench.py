"""This module exports the iorBench class"""

from __future__ import print_function

import os
import subprocess
import time
import shutil
import stat
import json

from pyc.bench import bench

class iorBench(bench):
    """Class dedicated to the IOR benchmark"""

    def __init__(self, args, url, optCfg, runCfg, logID):
        """Initialize IOR bench class instance"""
        bench.__init__(self, args, "IOR", "IO-MB/s")
        self.iorDir = "IOR"
        self.url = url
        self.optCfg = optCfg
        self.runCfg = runCfg
        self.logID = logID
        self.steps = []
        self.moreOpt = [("POSIX", "-e", "fsync")]
        self.moreOpt += [("MPIIO", "-c", "colIO"), ("MPIIO", "-V", "fview"), ("MPIIO", "-p", "alloc")]
        self.moreOpt += [("HDF5", "-c", "colIO"), ("HDF5", "-I", "indds")]

    def __runBTJMore__(self, moreTokens, iorExt, clDic, opt):
        """Run more configurations from a given IOR test"""
        iorLog = self.buildLogName("IOR", moreTokens, iorExt)
        print("Running", iorLog, "...", end="")
        start = time.time()
        rc = 0
        if not os.path.exists(iorLog) or self.args.force:
            log = open(iorLog, "w")
            cpClDic = clDic
            cpClDic["ARGS"] = cpClDic["ARGS"] + [opt]
            rc = self.runCmdLine(log, cpClDic, begin=start)
        self.printStatus(start, rc)

    def __runBTJ__(self, idx, n, runTokens, ext):
        """Run one IOR test"""
        b = self.runCfg["-b"][idx]
        t = self.runCfg["-t"][idx]
        j = self.runCfg["-J"][idx]
        iorTokens = [("block", b, "4s")]
        iorTokens += [("transfer", t, "4s")]
        iorTokens += [("align", j, "4s")]
        for a in self.runCfg["-a"]:
            if a == "POSIX" and n != 1:
                continue
            iorA = "PHDF5" if a == "HDF5" else a
            iorExt = ext if len(self.logID) == 0 else "." + ".".join(self.logID) + ext
            iorLog = self.buildLogName("IOR", iorTokens + [("a", iorA, "s")] + runTokens, "." + "xxxxx" + iorExt)
            print("Running", iorLog, "...", end="")
            start = time.time()
            rc = 0
            clDic = {}
            if not os.path.exists(iorLog) or self.args.force:
                log = open(iorLog, "w")
                clDic = {}
                clDic["EXE"] = "./ior"
                clDic["ARGS"] = ["-a", a, "-b", b, "-t", t, "-J", j, "-r", "-w", "-vvv"]
                for opt in self.runCfg["OTHER"]:
                    clDic["ARGS"] = clDic["ARGS"] + [opt]
                if n > 1:
                    clDic["PREPEND"] = ["mpirun", "-n", str(n)]
                rc = self.runCmdLine(log, clDic, begin=start)
            self.printStatus(start, rc)
            if self.args.more:
                for opt in self.moreOpt:
                    if opt[0].find(a) != -1:
                        iorA = "PHDF5" if a == "HDF5" else a
                        moreTokens = iorTokens + [("a", iorA, "s")] + runTokens
                        self.__runBTJMore__(moreTokens, "." + opt[2] + iorExt, clDic, opt[1])

    def downloadTmp(self):
        """Download IOR benchmark in the temporary directory"""
        os.chdir(self.tmp)
        if not os.path.exists(self.iorDir):
            os.makedirs(self.iorDir)
        os.chdir(self.iorDir)
        print("Downloading", self.bName, "...")
        self.dld.gitClone(self.url)

    def build(self, cpl):
        """Build IOR benchmark in the temporary directory"""
        buildDir = os.path.join(self.tmp, self.iorDir, "ior")
        if os.path.exists(buildDir):
            os.chdir(buildDir)
            if not os.path.exists("configure"):
                log = open("bootstrap.log", "w")
                rc = subprocess.call(["./bootstrap"], stdout=log, stderr=log)
                if rc != 0:
                    m = self.bName + " (bootstrap KO)"
                    self.buildError(log, msg=m)
            log = open("configure.log", "w")
            cEnv = os.environ.copy()
            cEnv["CC"] = cpl["CC"]
            cEnv["MPICC"] = cpl["MPICC"]
            cEnv["CFLAGS"] = self.optCfg["CFLAGS"]
            cEnv["LDFLAGS"] = self.optCfg["LDFLAGS"]
            cEnv["LIBS"] = self.optCfg["LIBS"]
            rc = subprocess.call(["./configure"] + self.optCfg["OPTIONS"], stdout=log, stderr=log, env=cEnv)
            if rc != 0:
                m = self.bName + " (configure KO)"
                self.buildError(log, msg=m)
            log = open("make.log", "w")
            print("Building", self.bName, "...", end="")
            start = time.time()
            rc = subprocess.call(["make"], stdout=log, stderr=log)
            if rc != 0:
                m = self.bName + " (build KO)"
                self.buildError(log, msg=m)
            self.printStatus(start, rc)

    def runNT(self, n, t, runTokens, ext):
        """Run IOR benchmark in the temporary directory for a given proc and thread configuration"""
        if t != 1:
            return
        if len(self.runCfg["-b"]) != len(self.runCfg["-t"]):
            print("Running IOR KO: -b and -t must have the same size")
            return
        if len(self.runCfg["-b"]) != len(self.runCfg["-J"]):
            print("Running IOR KO: -b and -J must have the same size")
            return
        runDir = os.path.join(self.tmp, self.iorDir, "ior", "src")
        if os.path.exists(runDir):
            os.chdir(runDir)
            for idx in range(len(self.runCfg["-b"])):
                self.__runBTJ__(idx, n, runTokens, ext)

    def getMetric(self, printMax=True, getDict=False, getMaxInfo=False, filterLogs=False):
        """Getting IOR benchmark metric from the temporary directory"""
        maxMBs = 0.
        dicMBs = {}
        maxInfo = {}
        runDir = os.path.join(self.tmp, self.iorDir, "ior", "src")
        if os.path.exists(runDir):
            os.chdir(runDir)
            for log in self.__listLogs__(os.path.join(runDir, "IOR*.log"), filterLogs):
                logTokens = self.splitLogName(log)
                b = logTokens["block="].split("=")[1]
                t = logTokens["transfer="].split("=")[1]
                if b not in dicMBs:
                    dicMBs[b] = {}
                if t not in dicMBs[b]:
                    dicMBs[b][t] = {}
                step = logTokens["align="].split("=")[1]
                step += "." + logTokens["a="].split("=")[1]
                step += "." + logTokens["n="] + "." + logTokens["t="]
                for opt in self.moreOpt:
                    if opt[2] in logTokens:
                        step += "." + opt[2]
                lines = open(log, "r").readlines()
                for line in lines:
                    if line.find("Max Write") != -1:
                        dicMBs[b][t][step + "." + "write"] = float(line.split()[4][1:])
                        self.steps.append(step + "." + "write")
                    if line.find("Max Read") != -1:
                        dicMBs[b][t][step + "." + "read"] = float(line.split()[4][1:])
                        self.steps.append(step + "." + "read")
                    self.steps = list(set(self.steps)) # Remove duplicates
                for s in self.steps:
                    if s in dicMBs[b][t] and dicMBs[b][t][s] > maxMBs:
                        maxMBs = dicMBs[b][t][s]
                        maxInfo["LOG"] = os.path.basename(log)
                        maxInfo["EXTRA"] = "block size = " + b
                        maxInfo["EXTRA"] += ", transfer size = " + t
                        maxInfo["EXTRA"] += ", step = " + s.split(".")[2]
        self.__printMetricStatus__(printMax, maxMBs, maxInfo)
        return self.__returnMetric__(dicMBs, maxInfo, maxMBs, getDict=getDict, getMaxInfo=getMaxInfo)

    def plotN(self, nKey):
        """Plotting IOR benchmark results from the temporary directory for a given proc configuration"""
        dicMBs = self.getMetric(printMax=False, getDict=True, filterLogs=True)
        self.plt.setPlotAttr(xTickStr=True, yTickStr=True)
        steps = [s for s in self.steps if s.find("read") != -1 and s.find(nKey) != -1]
        plotName = self.plt.buildPlotName([self.bName, "read", nKey])
        self.plt.plot3DGraph(plotName, dicMBs, sorted(steps), "Block size", "Transfer size", "MB/s")
        steps = [s for s in self.steps if s.find("write") != -1 and s.find(nKey) != -1]
        plotName = self.plt.buildPlotName([self.bName, "write", nKey])
        self.plt.plot3DGraph(plotName, dicMBs, sorted(steps), "Block size", "Transfer size", "MB/s")

    def genUseCase(self):
        """Generate a use case from the best IOR benchmark run"""
        maxInfo = self.getMetric(printMax=False, getMaxInfo=True)
        if "LOG" in maxInfo:
            ucDir = self.__cleanUseCase__(os.path.join(self.args.tmp, "usc"), "pfb" + self.bName)
            os.chdir(ucDir)
            runDir = os.path.join(self.tmp, self.iorDir, "ior", "src")
            shutil.copyfile(os.path.join(runDir, "ior"), "ior")
            os.chmod("ior", os.stat("ior").st_mode | stat.S_IEXEC) # chmod +x
            logTokens = self.splitLogName(maxInfo["LOG"])
            iorA = logTokens["a="].split("=")[1]
            iorA = "HDF5" if iorA == "PHDF5" else iorA
            exeArg = "-a " + iorA
            exeArg += " -b " + logTokens["block="].split("=")[1]
            exeArg += " -t " + logTokens["transfer="].split("=")[1]
            exeArg += " -r -w"
            for opt in self.moreOpt:
                if opt[2] in logTokens:
                    exeArg += " " + opt[1]
            for o in self.runCfg["OTHER"]:
                exeArg = exeArg + " " + o
            jsCfg = {}
            jsCfg["EXE"] = "ior"
            jsCfg["MPI"] = str(logTokens["n="].split("=")[1])
            jsCfg["THD"] = str(logTokens["t="].split("=")[1])
            jsCfg["ARGS"] = str(exeArg)
            jsCfg["COLOR"] = "pink"
            jsCfg["MARKER"] = "."
            jsCfg["LABEL"] = self.bName
            json.dump(jsCfg, open("usc.json", "w"))
