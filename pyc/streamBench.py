"""This module exports the streamBench class"""

from __future__ import print_function

import os
import subprocess
import time
import stat
import shutil
import json

from pyc.bench import bench

class streamBench(bench):
    """Class dedicated to the stream benchmark"""

    def __init__(self, args, url, name="stream"):
        """Initialize stream bench class instance"""
        bench.__init__(self, args, name, "RAM-MB/s")
        self.streamDir = "stream"
        self.url = url
        self.pbSize = 0
        self.colors = ["r", "g", "b", "c"]
        self.steps = ["Copy", "Scale", "Add", "Triad"]

    def __updateDicMetric__(self, maxMBs, bwMB, log, N, step, dicMBs):
        """Update metric dictionnary"""
        maxInfo = {}
        if maxMBs < bwMB:
            maxMBs = bwMB
            maxInfo["LOG"] = os.path.basename(log)
            maxInfo["EXTRA"] = "N = " + str(N) + ", step = " + step
        logTokens = self.splitLogName(log)
        t = int(logTokens["t="].split("=")[1])
        nKey = logTokens["n="]
        if nKey not in dicMBs:
            dicMBs[nKey] = {}
        if N not in dicMBs[nKey]:
            dicMBs[nKey][N] = {}
        if t not in dicMBs[nKey][N]:
            dicMBs[nKey][N][t] = {}
        if step not in dicMBs[nKey][N][t]:
            dicMBs[nKey][N][t][step] = bwMB
        if dicMBs[nKey][N][t][step] < bwMB:
            dicMBs[nKey][N][t][step] = bwMB
        return maxMBs, maxInfo

    def downloadTmp(self):
        """Download stream benchmark in the temporary directory"""
        os.chdir(self.tmp)
        if not os.path.exists(self.streamDir):
            os.makedirs(self.streamDir)
        os.chdir(self.streamDir)
        print("Downloading", self.bName, "...")
        for f in ["Makefile", "mysecond.c", "stream.c", "stream.f", "HISTORY.txt", "LICENSE.txt"]:
            self.dld.downloadFile(os.path.join(self.url, f))

    def build(self, cpl):
        """Build stream benchmark in the temporary directory"""
        buildDir = os.path.join(self.tmp, self.streamDir)
        if os.path.exists(buildDir):
            os.chdir(buildDir)
            if not os.path.exists("Makefile"):
                return
            self.__modifMakefile__(["Makefile"], ["CC", "CFLAGS"], [cpl["CC"], cpl["FLAGS"]])
            self.__modifMakefile__(["Makefile"], ["FF", "FFLAGS"], [cpl["FC"], cpl["FLAGS"]])
            lines = open("Makefile", "r").readlines()
            self.pbSize = self.args.size * 1024. ** 3 # 1GB by default
            self.pbSize = int(self.pbSize / 8)
            if self.pbSize == 0:
                return
            target = "stream_pfa.exe: stream.c\n"
            buildCmd = "\t" + cpl["CC"] + " " + cpl["FLAGS"] + " -DSTREAM_ARRAY_SIZE=" + str(self.pbSize)
            if self.args.more:
                buildCmd += " -DNTIMES=20"
            streamRun = "stream.size=%s" % self.pbSize
            buildCmd += " -o " + streamRun + ".exe stream.c\n"
            if len(lines) == 22:
                lines.append(target)
                lines.append(buildCmd)
            else:
                lines[22] = target
                lines[23] = buildCmd
            open("Makefile", "w").writelines(lines)
            log = open("make.log", "w")
            print("Building", self.bName, "...", end="")
            start = time.time()
            rc = subprocess.call(["make", "all", "stream_pfa.exe", "VERBOSE=1"], stdout=log, stderr=log)
            if rc != 0:
                self.buildError(log)
            self.printStatus(start, rc)

    def runNT(self, n, t, runTokens, ext):
        """Run stream benchmark in the temporary directory for a given proc and thread configuration"""
        if n != 1:
            return
        runDir = os.path.join(self.tmp, self.streamDir)
        if os.path.exists(runDir):
            os.chdir(runDir)
            if self.pbSize == 0:
                return
            streamRun = "stream.size=%s" % self.pbSize
            if not os.path.exists(streamRun + ".exe"):
                return
            streamLog = self.buildLogName("stream", [("size", self.pbSize, "s")] + runTokens, ext)
            print("Running", streamLog, "...", end="")
            start = time.time()
            rc = 0
            if not os.path.exists(streamLog) or self.args.force:
                log = open(streamLog, "w")
                clDic = {}
                clDic["EXE"] = "./" + streamRun + ".exe"
                rc = self.runCmdLine(log, clDic, begin=start, thd=t)
            self.printStatus(start, rc)

    def getMetric(self, printMax=True, getDict=False, getMaxInfo=False, filterLogs=False):
        """Getting stream benchmark metric from the temporary directory"""
        maxMBs = 0.
        dicMBs = {}
        maxInfo = {}
        runDir = os.path.join(self.tmp, self.streamDir)
        if os.path.exists(runDir):
            os.chdir(runDir)
            for log in self.__listLogs__(os.path.join(runDir, "stream*.log"), filterLogs):
                lines = open(log, "r").readlines()
                N = -1
                foundFunction = False
                for line in lines:
                    tokens = line.split()
                    if len(tokens) >= 4 and " ".join(tokens[0:3]) == "Array size =":
                        N = int(tokens[3])
                        continue
                    if N > 0 and len(tokens) > 1 and tokens[0] == "Function":
                        foundFunction = True
                        continue
                    if not foundFunction:
                        continue
                    for s in self.steps:
                        if len(tokens) >= 2 and tokens[0] == s + ":" and tokens[1].lower() != "inf":
                            bwMB = float(tokens[1])
                            mMBs, mInfo = self.__updateDicMetric__(maxMBs, bwMB, log, N, s, dicMBs)
                            if mMBs > maxMBs:
                                maxMBs = mMBs
                                maxInfo = mInfo
                            break
        self.__printMetricStatus__(printMax, maxMBs, maxInfo)
        return self.__returnMetric__(dicMBs, maxInfo, maxMBs, getDict=getDict, getMaxInfo=getMaxInfo)

    def plotN(self, nKey):
        """Plotting stream benchmark results from the temporary directory for a given proc configuration"""
        n = int(nKey.split("=")[1])
        if n != 1:
            return
        dicMBs = self.getMetric(printMax=False, getDict=True, filterLogs=True)
        self.plt.setPlotAttr(colors=self.colors, yTickInt=True)
        steps = []
        t = 1 # Number of thread(s)
        while n * t <= max(self.args.proc):
            if nKey in dicMBs:
                for N in list(dicMBs[nKey].keys()):
                    if t in dicMBs[nKey][N]:
                        for s in list(dicMBs[nKey][N][t].keys()):
                            steps.append(s)
            steps = list(set(steps)) # Remove duplicates
            t *= 2
        if nKey in dicMBs:
            plotName = self.plt.buildPlotName([self.bName, nKey])
            self.plt.plot3DGraph(plotName, dicMBs[nKey], steps, "N", "Threads", "MB/s")

    def genUseCase(self):
        """Generate a use case from the best stream benchmark run"""
        maxInfo = self.getMetric(printMax=False, getMaxInfo=True)
        if "LOG" in maxInfo:
            ucDir = self.__cleanUseCase__(os.path.join(self.args.tmp, "usc"), "pfb" + self.bName.title())
            os.chdir(ucDir)
            logTokens = self.splitLogName(maxInfo["LOG"])
            exe = "stream." + logTokens["size="] + ".exe"
            runDir = os.path.join(self.tmp, self.streamDir)
            shutil.copyfile(os.path.join(runDir, exe), exe)
            os.chmod(exe, os.stat(exe).st_mode | stat.S_IEXEC) # chmod +x
            jsCfg = {}
            jsCfg["EXE"] = exe
            jsCfg["THD"] = str(logTokens["t="].split("=")[1])
            jsCfg["COLOR"] = "magenta"
            jsCfg["MARKER"] = "."
            jsCfg["LABEL"] = self.bName
            json.dump(jsCfg, open("usc.json", "w"))
