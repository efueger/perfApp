"""This module exports the iozoneBench class"""

from __future__ import print_function

import os
import subprocess
import sys
import time
import stat
import shutil
import json

from pyc.bench import bench

class iozoneBench(bench):
    """Class dedicated to the iozone benchmark"""

    def __init__(self, args, url, iozVn, iozMkArch):
        """Initialize iozone bench class instance"""
        bench.__init__(self, args, "iozone", "IO-MB/s")
        self.iozURL = url
        self.iozDir = "iozone" + iozVn
        self.iozTAR = "iozone" + iozVn + ".tar"
        self.iozMkArch = iozMkArch
        self.steps = []

    def __getMetricFromLine__(self, tokens, dicMBs, step):
        """Get metric from a line of a log"""
        fsMB = int(tokens[0]) // 1024
        if fsMB not in dicMBs:
            dicMBs[fsMB] = {}
        rlkB = int(tokens[1])
        if rlkB not in dicMBs[fsMB]:
            dicMBs[fsMB][rlkB] = {}
        if len(tokens) >= 6:
            dicMBs[fsMB][rlkB][step + "." + "write"] = int(tokens[2]) / 1024.
            dicMBs[fsMB][rlkB][step + "." + "rewrite"] = int(tokens[3]) / 1024.
            dicMBs[fsMB][rlkB][step + "." + "read"] = int(tokens[4]) / 1024.
            dicMBs[fsMB][rlkB][step + "." + "reread"] = int(tokens[5]) / 1024.
            self.steps.append(step + "." + "write")
            self.steps.append(step + "." + "rewrite")
            self.steps.append(step + "." + "read")
            self.steps.append(step + "." + "reread")
        if len(tokens) == 15:
            dicMBs[fsMB][rlkB][step + "." + "random read"] = int(tokens[6]) / 1024.
            dicMBs[fsMB][rlkB][step + "." + "random write"] = int(tokens[7]) / 1024.
            dicMBs[fsMB][rlkB][step + "." + "bkwd read"] = int(tokens[8]) / 1024.
            dicMBs[fsMB][rlkB][step + "." + "record rewrite"] = int(tokens[9]) / 1024.
            dicMBs[fsMB][rlkB][step + "." + "stride read"] = int(tokens[10]) / 1024.
            dicMBs[fsMB][rlkB][step + "." + "fwrite"] = int(tokens[11]) / 1024.
            dicMBs[fsMB][rlkB][step + "." + "frewrite"] = int(tokens[12]) / 1024.
            dicMBs[fsMB][rlkB][step + "." + "fread"] = int(tokens[13]) / 1024.
            dicMBs[fsMB][rlkB][step + "." + "freread"] = int(tokens[14]) / 1024.
            self.steps.append(step + "." + "random read")
            self.steps.append(step + "." + "random write")
            self.steps.append(step + "." + "bkwd read")
            self.steps.append(step + "." + "record rewrite")
            self.steps.append(step + "." + "stride read")
            self.steps.append(step + "." + "fwrite")
            self.steps.append(step + "." + "frewrite")
            self.steps.append(step + "." + "fread")
            self.steps.append(step + "." + "freread")
        return fsMB, rlkB

    def downloadTmp(self):
        """Download iozone benchmark in the temporary directory"""
        os.chdir(self.tmp)
        print("Downloading", self.bName, "...")
        self.dld.downloadFile(os.path.join(self.iozURL, self.iozTAR))
        if not os.path.exists(self.iozDir) and os.path.exists(self.iozTAR):
            if subprocess.call(["tar", "-xf", self.iozTAR]) != 0:
                sys.exit("ERROR: can not untar " + self.bName)

    def build(self, cpl):
        """Build iozone benchmark in the temporary directory"""
        buildDir = os.path.join(self.tmp, self.iozDir, "src", "current")
        if os.path.exists(buildDir):
            os.chdir(buildDir)
            oldOptions = ["CC", "C89", "GCC", "CCS", "NACC"]
            newOptions = [cpl["CC"], cpl["CC"], cpl["CC"], cpl["CC"], cpl["CC"]]
            oldOptions += ["CFLAGS"]
            newOptions += [cpl["FLAGS"]]
            self.__modifMakefile__(["makefile"], oldOptions, newOptions)
            log = open("make.log", "w")
            print("Building", self.bName, "...", end="")
            start = time.time()
            rc = subprocess.call(["make", self.iozMkArch, "VERBOSE=1"], stdout=log, stderr=log)
            if rc != 0:
                m = self.bName + " (with makefile arch keyword:" + self.iozMkArch + ")"
                self.buildError(log, msg=m)
            self.printStatus(start, rc)

    def runNT(self, n, t, runTokens, ext):
        """Run iozone benchmark in the temporary directory for a given proc and thread configuration"""
        if n != 1:
            return
        runDir = os.path.join(self.tmp, self.iozDir, "src", "current")
        if os.path.exists(runDir):
            os.chdir(runDir)
            kBSize = int(self.args.size * 1024. ** 2)
            kBMinSize = str(int(kBSize))
            kBMaxSize = str(int(kBSize))
            nb = 2 if self.args.more else 1
            n = 1
            while n <= nb:
                if int(kBSize / n) > 0:
                    kBMinSize = str(int(kBSize / n))
                kBMaxSize = str(int(kBSize * n))
                n *= 2
            kBMinRecSize = "1"
            kBMaxRecSize = "128"
            if self.args.more:
                kBMaxRecSize = "1024"
            iozTokens = [("size", kBSize, "s")]
            iozTokens = iozTokens + [("MinSz", kBMinSize, "s"), ("MaxSz", kBMaxSize, "s")]
            iozTokens = iozTokens + [("MinRec", kBMinRecSize, "s"), ("MaxRec", kBMaxRecSize, "s")]
            iozTokens = iozTokens + runTokens
            iozLog = self.buildLogName("iozone", iozTokens, ext)
            print("Running", iozLog, "...", end="")
            start = time.time()
            rc = 0
            if not os.path.exists(iozLog) or self.args.force:
                log = open(iozLog, "w")
                clDic = {}
                clDic["EXE"] = "./iozone"
                clDic["ARGS"] = ["-a", "-e", "-c", "-r", "#k", "-n", kBMinSize, "-g", kBMaxSize]
                clDic["ARGS"] = clDic["ARGS"] + ["-y", kBMinRecSize, "-q", kBMaxRecSize]
                if self.args.quick:
                    clDic["ARGS"] = clDic["ARGS"] + ["-i", "0", "-i", "1"]
                rc = self.runCmdLine(log, clDic, begin=start, thd=t)
            self.printStatus(start, rc)

    def getMetric(self, printMax=True, getDict=False, getMaxInfo=False, filterLogs=False):
        """Getting iozone benchmark metric from the temporary directory"""
        maxMBs = 0.
        dicMBs = {}
        maxInfo = {}
        runDir = os.path.join(self.tmp, self.iozDir, "src", "current")
        if os.path.exists(runDir):
            os.chdir(runDir)
            for log in self.__listLogs__(os.path.join(runDir, "iozone*.log"), filterLogs):
                lines = open(log, "r").readlines()
                foundMc = False
                for line in lines:
                    tokens = line.split()
                    if len(tokens) >= 2:
                        if tokens[0] == "kB" and tokens[1] == "reclen":
                            foundMc = True
                            continue
                    if not foundMc:
                        continue
                    if line.find("iozone test complete") != -1:
                        break # End of relevant data
                    if len(tokens) < 2:
                        continue
                    logTokens = self.splitLogName(log)
                    step = logTokens["n="] + "." + logTokens["t="]
                    fsMB, rlkB = self.__getMetricFromLine__(tokens, dicMBs, step)
                    self.steps = list(set(self.steps)) # Remove duplicates
                    for s in self.steps:
                        if s in dicMBs[fsMB][rlkB] and dicMBs[fsMB][rlkB][s] > maxMBs:
                            maxMBs = dicMBs[fsMB][rlkB][s]
                            maxInfo["LOG"] = os.path.basename(log)
                            maxInfo["EXTRA"] = "file size = " + str(fsMB) + " MB, record size = " + str(rlkB) + " kB"
                            maxInfo["EXTRA"] += ", step = " + s.split(".")[2]
        self.__printMetricStatus__(printMax, maxMBs, maxInfo)
        return self.__returnMetric__(dicMBs, maxInfo, maxMBs, getDict=getDict, getMaxInfo=getMaxInfo)

    def plotN(self, nKey):
        """Plotting iozone benchmark results from the temporary directory for a given proc configuration"""
        n = int(nKey.split("=")[1])
        if n != 1:
            return
        dicMBs = self.getMetric(printMax=False, getDict=True, filterLogs=True)
        t = 1 # Number of thread(s)
        while n * t <= max(self.args.proc):
            tKey = ("t=%0" + str(len(str(max(self.args.proc)))) + "d") % t
            steps = [s for s in self.steps if s.find("read") != -1 and s.find(nKey) != -1 and s.find(tKey) != -1]
            plotName = self.plt.buildPlotName([self.bName, "read", nKey, tKey])
            self.plt.plot3DGraph(plotName, dicMBs, steps, "File size (MB)", "Record length (kB)", "MB/s")
            steps = [s for s in self.steps if s.find("write") != -1 and s.find(nKey) != -1 and s.find(tKey) != -1]
            plotName = self.plt.buildPlotName([self.bName, "write", nKey, tKey])
            self.plt.plot3DGraph(plotName, dicMBs, steps, "File size (MB)", "Record length (kB)", "MB/s")
            t *= 2

    def genUseCase(self):
        """Generate a use case from the best iozone benchmark run"""
        maxInfo = self.getMetric(printMax=False, getMaxInfo=True)
        if "LOG" in maxInfo:
            ucDir = self.__cleanUseCase__(os.path.join(self.args.tmp, "usc"), "pfb" + self.bName.title())
            os.chdir(ucDir)
            runDir = os.path.join(self.tmp, self.iozDir, "src", "current")
            shutil.copyfile(os.path.join(runDir, "iozone"), "iozone")
            os.chmod("iozone", os.stat("iozone").st_mode | stat.S_IEXEC) # chmod +x
            logTokens = self.splitLogName(maxInfo["LOG"])
            exeArg = "-a -e -c -r \"#k\""
            exeArg += " -n " + logTokens["MinSz="].split("=")[1] + " -g " + logTokens["MaxSz="].split("=")[1]
            exeArg += " -y " + logTokens["MinRec="].split("=")[1] + " -q " + logTokens["MaxRec="].split("=")[1]
            if "quick" in logTokens:
                exeArg += " -i 0 -i 1"
            jsCfg = {}
            jsCfg["EXE"] = "iozone"
            jsCfg["THD"] = str(logTokens["t="].split("=")[1])
            jsCfg["ARGS"] = str(exeArg)
            jsCfg["COLOR"] = "blue"
            jsCfg["MARKER"] = "."
            jsCfg["LABEL"] = self.bName
            json.dump(jsCfg, open("usc.json", "w"))
