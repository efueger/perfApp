"""This module exports the stream2Bench class"""

from __future__ import print_function

import os
import subprocess
import time
import stat
import shutil
import json

from pyc.streamBench import streamBench

class stream2Bench(streamBench):
    """Class dedicated to the stream2 benchmark"""

    def __init__(self, args, prereq, url):
        """Initialize stream2 bench class instance"""
        streamBench.__init__(self, args, prereq, name="stream2")
        self.stream2Dir = "stream2"
        self.prereq = prereq
        self.url = url
        self.steps = ["FILL", "COPY", "DAXPY", "DOT"]

    def downloadTmp(self):
        """Download stream2 benchmark in the temporary directory"""
        os.chdir(self.tmp)
        if not os.path.exists(self.stream2Dir):
            os.makedirs(self.stream2Dir)
        os.chdir(self.stream2Dir)
        print("Downloading", self.bName, "...")
        self.dld.downloadFile(os.path.join(self.prereq, "mysecond.c"))
        self.dld.downloadFile(os.path.join(self.url, "stream2.f"))

    def build(self, cpl):
        """Build stream2 benchmark in the temporary directory"""
        buildDir = os.path.join(self.tmp, self.stream2Dir)
        if os.path.exists(buildDir):
            os.chdir(buildDir)
            if not os.path.exists("stream2.f"):
                return
            self.pbSize = self.args.size * 1024. ** 3 # 1GB by default
            self.pbSize = int(self.pbSize / 8)
            self.pbSize = int(self.pbSize / 2) # In stream2, 2 arrays are allocated
            if self.pbSize == 0:
                return
            stream2LOC = open("stream2.f", "r").readlines()
            for idx, loc in enumerate(stream2LOC):
                oldParam = "parameter (NMIN=30,NMAX=2 000 000)"
                if loc.find(oldParam) != -1:
                    newParam = "parameter (NMIN=30,NMAX=" + str(self.pbSize) + ")\n"
                    stream2LOC[idx] = loc.replace(oldParam, newParam)
                if self.args.more:
                    oldParam = "parameter (NTIMES=10,NUMSIZES=32)"
                    if loc.find(oldParam) != -1:
                        newParam = "parameter (NTIMES=20,NUMSIZES=64)"
                        stream2LOC[idx] = loc.replace(oldParam, newParam)
            stream2Run = "stream2.size=%s" % self.pbSize
            open(stream2Run + ".f", "w").writelines(stream2LOC)
            mkf = open("Makefile", "w")
            mkf.write("all:" + "\n")
            buildCmd = cpl["CC"] + " " + cpl["NOOPTFLAGS"] + " -o mysecond.o -c mysecond.c\n"
            mkf.write("\t" + buildCmd)
            buildCmd = cpl["FC"] + " " + cpl["NOOPTFLAGS"] + " -o " + stream2Run + ".o" + " "
            buildCmd += "-c " + stream2Run + ".f\n"
            mkf.write("\t" + buildCmd)
            buildCmd = cpl["FC"] + " " + cpl["NOOPTFLAGS"] + " -o " + stream2Run + ".exe" + " "
            buildCmd += stream2Run + ".o mysecond.o\n"
            mkf.write("\t" + buildCmd)
            mkf.close() # Flush file before make
            log = open("make.log", "w")
            print("Building", self.bName, "...", end="")
            start = time.time()
            rc = subprocess.call(["make", "VERBOSE=1"], stdout=log, stderr=log)
            if rc != 0:
                self.buildError(log)
            self.printStatus(start, rc)

    def runNT(self, n, t, runTokens, ext):
        """Run stream2 benchmark in the temporary directory for a given proc and thread configuration"""
        if n != 1:
            return
        runDir = os.path.join(self.tmp, self.stream2Dir)
        if os.path.exists(runDir):
            os.chdir(runDir)
            if self.pbSize == 0:
                return
            stream2Run = "stream2.size=%s" % self.pbSize
            if not os.path.exists(stream2Run + ".exe"):
                return
            stream2Log = self.buildLogName("stream2", [("size", self.pbSize, "s")] + runTokens, ext)
            print("Running", stream2Log, "...", end="")
            start = time.time()
            rc = 0
            if not os.path.exists(stream2Log) or self.args.force:
                log = open(stream2Log, "w")
                clDic = {}
                clDic["EXE"] = "./" + stream2Run + ".exe"
                rc = self.runCmdLine(log, clDic, begin=start, thd=t)
            self.printStatus(start, rc)

    def getMetric(self, printMax=True, getDict=False, getMaxInfo=False, filterLogs=False):
        """Getting stream2 benchmark metric from the temporary directory"""
        maxMBs = 0.
        dicMBs = {}
        maxInfo = {}
        runDir = os.path.join(self.tmp, self.stream2Dir)
        if os.path.exists(runDir):
            os.chdir(runDir)
            for log in self.__listLogs__(os.path.join(runDir, "stream2*.log"), filterLogs):
                lines = open(log, "r").readlines()
                foundDataBegin = False
                for idx in range(0, len(lines) - 1):
                    tokens = lines[idx].split()
                    if len(tokens) == 6 and tokens[0] == "Size" and tokens[5] == "DOT":
                        foundDataBegin = True
                        continue
                    if not foundDataBegin:
                        continue
                    if len(tokens) != 7:
                        break # End of relevant data
                    N = int(tokens[0])
                    for stepInfo in [("FILL", 2), ("COPY", 3), ("DAXPY", 4), ("DOT", 5)]:
                        if tokens[stepInfo[1]].lower() == "infinity":
                            continue
                        bwMB = float(tokens[stepInfo[1]])
                        mMBs, mInfo = self.__updateDicMetric__(maxMBs, bwMB, log, N, stepInfo[0], dicMBs)
                        if mMBs > maxMBs:
                            maxMBs = mMBs
                            maxInfo = mInfo
        self.__printMetricStatus__(printMax, maxMBs, maxInfo)
        return self.__returnMetric__(dicMBs, maxInfo, maxMBs, getDict=getDict, getMaxInfo=getMaxInfo)

    def genUseCase(self):
        """Generate a use case from the best stream2 benchmark run"""
        maxInfo = self.getMetric(printMax=False, getMaxInfo=True)
        if "LOG" in maxInfo:
            ucDir = self.__cleanUseCase__(os.path.join(self.args.tmp, "usc"), "pfb" + self.bName.title())
            os.chdir(ucDir)
            logTokens = self.splitLogName(maxInfo["LOG"])
            exe = "stream2." + logTokens["size="] + ".exe"
            runDir = os.path.join(self.tmp, self.stream2Dir)
            shutil.copyfile(os.path.join(runDir, exe), exe)
            os.chmod(exe, os.stat(exe).st_mode | stat.S_IEXEC) # chmod +x
            jsCfg = {}
            jsCfg["EXE"] = exe
            jsCfg["THD"] = str(logTokens["t="].split("=")[1])
            jsCfg["COLOR"] = "orange"
            jsCfg["MARKER"] = "."
            jsCfg["LABEL"] = self.bName
            json.dump(jsCfg, open("usc.json", "w"))
