"""This module exports the class designed to run jobs"""

from __future__ import print_function

import subprocess
import time
import os
import sys
import glob

from pyc.plot import plot

class runJob(object):
    """Run time class designed to handle jobs and associated logs"""

    def __init__(self, args):
        """Initialize run time class instance"""
        self.plt = plot(args)
        self.args = args
        self.lsMsg = []

    def __listLogs__(self, logRegExp, filterLogs):
        """List logs to consider according to eventual filter to apply"""
        lsLogs = []
        for logName in sorted(glob.glob(logRegExp)):
            if filterLogs:
                if self.plt.filterLog(logName):
                    continue
            lsLogs.append(logName)
        return lsLogs

    def __tailLog__(self, logName):
        """Get the tail of a log"""
        self.lsMsg = []
        self.lsMsg.append("  current working directory : " + os.getcwd())
        self.lsMsg.append("  log tail :")
        lines = open(logName, "r").readlines()
        nbLinesToPrint = min(30, len(lines))
        while nbLinesToPrint > 0:
            line = lines[len(lines)-nbLinesToPrint].strip()
            if len(line) == 0:
                nbLinesToPrint = nbLinesToPrint - 1
                continue
            self.lsMsg.append("    " + line)
            nbLinesToPrint = nbLinesToPrint - 1

    def __addMpiOptToCmdLine__(self, cmdLine):
        """Add mpirun options to a command line"""
        for idx, cl in enumerate(cmdLine):
            if cl == "mpirun":
                for opt in self.args.mpirunOpt.split():
                    idx = idx + 1
                    cmdLine.insert(idx, opt)
                break

    def __buildEnv__(self, thd):
        """Build environment to run a job"""
        cEnv = os.environ.copy()
        for vv in self.args.env:
            cEnv[vv[0]] = vv[1]
        if thd:
            cEnv["OMP_NUM_THREADS"] = str(thd)
        return cEnv

    def __printError__(self, rc):
        """Print errors"""
        for msg in self.lsMsg:
            print(msg)
        self.lsMsg = [] # Reset after print
        if rc != 0:
            if self.args.stop:
                sys.exit("ERROR: stop")

    def buildError(self, log, msg=None):
        """Print information if build fails"""
        logName = log.name
        log.close() # Flush is needed
        if os.path.exists(logName):
            self.__tailLog__(logName)
            if msg:
                self.lsMsg.append(msg)

    @staticmethod
    def buildLogName(baseName, runTokens, ext):
        """Build log name from tokens"""
        logName = baseName
        for token in runTokens:
            infoBase = "." + token[0] + "="
            logName += infoBase
            infoVal = token[1]
            infoType = token[2]
            if infoType == "s": # String
                logName += str(infoVal).replace(".", "-") # Suppress "." as splitLogName is based on "."
            elif infoType == "4s": # String
                logName += infoVal.rjust(4, "0").replace(".", "-") # Suppress "." as splitLogName is based on "."
            elif infoType == "d": # Integer
                tnMax = token[3]
                logName += ("%0" + str(len(str(tnMax))) + "d") % infoVal
        logName += ext
        return logName

    @staticmethod
    def splitLogName(logName):
        """Split log name to get information from it"""
        logTokens = {}
        for token in os.path.basename(logName).split("."):
            if token == "log":
                continue
            if "root=" not in logTokens:
                logTokens["root="] = token
                continue
            if token.find("n=") == 0:
                logTokens["n="] = token
            elif token.find("t=") == 0:
                logTokens["t="] = token
            elif token.find("=") != -1:
                logTokens[token.split("=")[0] + "="] = token
            else:
                logTokens[token] = token
        return logTokens

    def runCmdLine(self, log, clDic, begin=None, thd=None):
        """Run a command line"""
        if not "EXE" in clDic or (clDic["EXE"] != "perf" and not os.path.exists(clDic["EXE"])):
            log.write("\nERROR : binary not found - " + str(clDic["EXE"]))
            log.close() # Flush is needed
            return 1 # Avoid crash if exe doesn't exist (if build KO)
        self.lsMsg = [] # Reset before new run
        cmdLine = [clDic["EXE"]]
        if "PREPEND" in clDic:
            cmdLine = clDic["PREPEND"] + cmdLine
        if "ARGS" in clDic:
            cmdLine = cmdLine + clDic["ARGS"]
        self.__addMpiOptToCmdLine__(cmdLine)
        log.write("\n\n" + "~>" + " ".join(cmdLine) + "\n\n")
        log.flush() # Flush needed before subprocess.call
        cEnv = self.__buildEnv__(thd)
        rc = subprocess.call(cmdLine, env=cEnv, stdout=log, stderr=log)
        if rc == 0:
            if begin:
                log.write("\ntime = %11.3f sec" % (time.time() - begin))
            log.close() # Flush is needed
        else:
            logName = log.name
            log.close() # Flush is needed
            self.__tailLog__(logName)
        return rc

    def printStatus(self, start, rc, printError=True):
        """Print the status of a run (OK or KO)"""
        if rc == 0:
            print(" OK", end="")
        else:
            print(" KO", end="")
        print(" (time = %11.3f sec)" % (time.time() - start))
        if printError:
            self.__printError__(rc)
