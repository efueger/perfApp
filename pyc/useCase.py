"""This module exports the useCase class"""

from __future__ import print_function

import os
import subprocess
import glob
import json
import stat
import time

from pyc.perfMonitor import perfMonitor

class useCase(perfMonitor):
    """Use case class designed to handle general purpose use case run-time topics"""

    def __init__(self, args, needReg=True):
        """Initialize useCase class instance"""
        perfMonitor.__init__(self, args, needReg)
        self.verbose = args.verbose if hasattr(args, "verbose") else None
        self.pth = None
        self.logID = []
        self.exe = {}
        self.rlm = {}

    def __defaultConfig__(self):
        """Set defaults to the use case configuration"""
        if "THD" not in self.exe:
            self.exe["THD"] = [1] # At least one core
        if "THD" in self.exe and not "MPI" in self.exe:
            self.exe["MPI"] = [-1] * len(self.exe["THD"]) # Sequential
        if "MPI" in self.exe and not "THD" in self.exe:
            self.exe["THD"] = [1] * len(self.exe["MPI"])
        if "ARGS" in self.exe:
            if len(self.exe["ARGS"]) == 1: # If there's only one argument, use it for all runs
                self.exe["ARGS"] = [self.exe["ARGS"][0]] * len(self.exe["MPI"])

    def __checkConfig__(self):
        """Check the use case configuration"""
        rc = True
        if "EXE" not in self.exe:
            print("Configuring", os.path.basename(self.pth), "KO : EXE must be specified")
            rc = False
        if len(self.exe["MPI"]) != len(self.exe["THD"]):
            print("Configuring", os.path.basename(self.pth), "KO : number of MPI must equal number of THD")
            rc = False
        if "ARGS" in self.exe:
            if len(self.exe["MPI"]) != len(self.exe["ARGS"]):
                print("Configuring", os.path.basename(self.pth), "KO : number of MPI must equal number of ARGS")
                rc = False
        if hasattr(self.args, "rlm") and self.args.rlm != -1:
            if "COLOR" not in self.rlm or "MARKER" not in self.rlm or "LABEL" not in self.rlm:
                print("Configuring", os.path.basename(self.pth), "KO : missing COLOR or MARKER or LABEL (mandatory)")
                rc = False
            if len(self.exe["MPI"]) != len(self.rlm["COLOR"]):
                print("Configuring", os.path.basename(self.pth), "KO : number of MPI must equal number of COLOR")
                rc = False
            if len(self.exe["MPI"]) != len(self.rlm["MARKER"]):
                print("Configuring", os.path.basename(self.pth), "KO : number of MPI must equal number of MARKER")
                rc = False
        return rc

    def __createRunShell__(self, n, t, a, logTokens):
        """Create run shell if not present"""
        runSh = "run." + logTokens["n="] + "." + logTokens["t="] + ".sh"
        if not os.path.exists(runSh):
            runLOC = []
            ucRunLOC = os.path.join(self.pth, "run.sh")
            if os.path.exists(ucRunLOC):
                runLOC = open(ucRunLOC, "r").readlines()
            else:
                runLOC.append("#!/bin/bash" + "\n")
            runLOC.append("export OMP_NUM_THREADS=" + str(t) + "\n")
            exe = os.path.join("..", self.exe["EXE"]) # EXE should be set as a relative path
            if a:
                exe = exe + " " + a
            if n == -1: # Sequential
                runLOC.append(exe + "\n")
            else:
                cmdLine = ["mpirun", "-n ", str(n)] + exe.split()
                self.__addMpiOptToCmdLine__(cmdLine)
                runLOC.append(" ".join(cmdLine) + "\n")
            open(runSh, "w").writelines(runLOC)
            os.chmod(runSh, os.stat(runSh).st_mode | stat.S_IEXEC) # chmod +x
        return runSh

    def __getUseCaseStatLog__(self, ntKey, lsMsg, msg):
        """Get use case statistics log"""
        perfLog = None
        logPath = os.path.join(os.path.basename(self.pth) + ".perf-stat" + ntKey + "*")
        for logName in glob.glob(logPath):
            allLogIDFound = True
            for logID in self.logID + self.args.logID:
                if logName.find(logID) == -1:
                    allLogIDFound = False
            if not allLogIDFound:
                continue
            perfLog = logName
            lsMsg.append("  - %4s : log found %s" % (msg, perfLog))
            break
        if not perfLog:
            lsMsg.append("  - %4s : can not find log in %s" % (msg, os.getcwd()))
            return perfLog
        if not os.path.exists(perfLog):
            lsMsg.append("  - %4s : missing %s" % (msg, os.path.basename(perfLog)))
            perfLog = None
        return perfLog

    def __getUseCaseMetricFromEvt__(self, evt, evtScore, GFOrCM):
        """Get use case metric (GF or CM) from event"""
        evtMc = int(evtScore.replace(",", ""))
        factor, unit = 0, 1.
        if GFOrCM == "GF":
            factor = 1. / (1000. ** 3)
            unit = "GFlops"
            for r in self.regInfo:
                if r[0] != evt and r[0] + ":u" != evt: # perf may drop :u
                    continue
                if r[3].lower().find("packed") != -1:
                    if r[3].lower().find("simd"):
                        evtMc = evtMc * self.args.flopPerPdSIMD
                    if r[3].lower().find("sse"):
                        evtMc = evtMc * self.args.flopPerPdSSE
                break
        else:
            factor = 1. / (1024. ** 2)
            unit = "MB/s"
            evtMc = evtMc * self.args.clSize
        return evtMc, factor, unit

    def __getUseCaseStat__(self, ntKey, lsEvt, GFOrCM):
        """Get use case statistics"""
        mc = 0
        elapsedSec = 0.
        lsMsg = []
        perfLog = self.__getUseCaseStatLog__(ntKey, lsMsg, GFOrCM)
        if not perfLog:
            return mc, elapsedSec, lsMsg
        factor, unit = 1., ""
        lines = open(perfLog, "r").readlines()
        for evt in lsEvt:
            foundCounter = False
            foundEvt = False
            for line in lines:
                if line.find("Performance counter stats") != -1:
                    foundCounter = True
                if not foundCounter:
                    continue
                tokens = line.split()
                if len(tokens) >= 2 and (tokens[1] == evt or tokens[1] + ":u" == evt): # perf may drop :u
                    evtMc, factor, unit = self.__getUseCaseMetricFromEvt__(evt, tokens[0], GFOrCM)
                    mc += evtMc
                    foundEvt = True
                    if self.verbose:
                        lsMsg.append("  - %4s : %30s %20d (%20d)" % (GFOrCM, evt, evtMc, mc))
                if foundEvt:
                    if len(tokens) == 4 and " ".join(tokens[1:]) == "seconds time elapsed":
                        elapsedSec = float(tokens[0])
            if self.verbose:
                if not foundEvt:
                    lsMsg.append("  - %4s : %30s not found" % (GFOrCM, evt))
                else:
                    lastMsgIdx = len(lsMsg) - 1
                    lastMsg = lsMsg[lastMsgIdx]
                    lastMsg += " - %11.3f" % elapsedSec + " sec "
                    lastMsg += " - %11.3f" % (mc * factor / elapsedSec) + " " + unit
                    lsMsg[lastMsgIdx] = lastMsg
        return mc, elapsedSec, lsMsg

    def __runUseCaseNTError__(self, rc):
        """Handle use case error"""
        self.__printError__(rc)

    def __runUseCaseNTPerfStat__(self, logTokens, runSh, t):
        """Run perf-stat for a given use case"""
        if hasattr(self.args, "stat") and self.args.stat: # Statistics can not be deduced from perf-record
            perfLog = os.path.basename(self.pth) + ".perf-stat"
            perfGFCMEvt = self.args.perfStGFEvt + self.args.perfStCMEvt
            pfm4GFCMReg = self.pfm4StGFReg + self.pfm4StCMReg
            evt = ",".join([r for r in perfGFCMEvt + pfm4GFCMReg])
            rc = self.runPerf(logTokens, perfLog, "./" + runSh, thd=t, prepend=["perf", "stat", "-e", evt])
            if rc != 0:
                self.__runUseCaseNTError__(rc)

    def __runUseCaseNTPerfReport__(self, logTokens, runSh, t):
        """Run perf-report for a given use case"""
        if hasattr(self.args, "report") and self.args.report:
            perfLog = os.path.basename(self.pth) + ".perf-record"
            mp = str(self.args.mp) if hasattr(self.args, "mp") else "1000"
            evt = ",".join([r for r in self.args.perfRpEvt + self.pfm4RpReg])
            rc = self.runPerf(logTokens, perfLog, "./" + runSh, thd=t, prepend=["perf", "record", "-F", mp, "-e", evt])
            if rc != 0:
                self.__runUseCaseNTError__(rc)
            perfLog = os.path.basename(self.pth) + ".perf-report"
            rc = self.runPerf(logTokens, perfLog, "perf", args=["report", "--stdio"])
            if rc != 0:
                self.__runUseCaseNTError__(rc)

    def __runUseCaseNTPerfTop__(self, logTokens, runSh, t):
        """Run perf-top for a given use case"""
        if hasattr(self.args, "top") and self.args.top:
            for evt in self.pfm4TpReg + self.args.perfTpEvt:
                perfLog = os.path.basename(self.pth) + ".perf-top" + "." + evt
                if not os.path.exists(perfLog + ".sh.log") or self.args.force:
                    self.__cleanPerfTopHistory__(evt)
                cmdLine = ["perf", "top", "--stdio", "-K", "-e", evt] # Only one event can be handled by perf-top
                rc, perfLog = self.runPerfTop(perfLog, logTokens, runSh, t, cmdLine, self.args.top)
                if rc != 0:
                    self.__tailLog__(perfLog)
                    self.__runUseCaseNTError__(rc)

    def __getUseCaseMemoryHistory__(self, nKey, tKey):
        """Get use case memory information"""
        dicMB = None
        lsPID = []
        lsMsg = []
        log = os.path.join(os.path.basename(self.pth) + ".mem" + "." + nKey + "." + tKey + ".log")
        if os.path.exists(log):
            lsMsg.append("  - log found " + log)
            if not dicMB:
                dicMB = {}
            mega = 1024. ** 2
            lines = open(log, "r").readlines()
            lsPID = lines[0].split()[2:]
            for pid in lsPID:
                dicMB[pid] = {}
                for idx in range(2, len(lines)):
                    tokens = lines[idx].split()
                    t = int(tokens[0])
                    if t not in dicMB[pid]:
                        dicMB[pid][t] = {}
                    dicMB[pid][t]["vms"] = float(tokens[1]) / mega
                    dicMB[pid][t]["rss"] = float(tokens[2]) / mega
                    dicMB[pid][t]["uss"] = float(tokens[3]) / mega
                    dicMB[pid][t]["swap"] = float(tokens[4]) / mega
                if self.verbose:
                    for step in ["vms", "rss", "uss", "swap"]:
                        mb = [dicMB[pid][t][step] for t in dicMB[pid].keys()]
                        msg = "  - PID " + pid + ", %4s" % step + " : min %11.3f, max %11.3f" % (min(mb), max(mb))
                        lsMsg.append(msg)
        if not dicMB:
            lsMsg.append("  - Memory history not available")
        return dicMB, lsPID, lsMsg

    def __plotReport__(self):
        """Plot perf-report statistics"""
        dicPct, lsStep = self.__getReport__()
        if dicPct:
            plotName = os.path.basename(self.pth) + ".perf-report"
            self.plt.setPlotAttr(xTickStr=True, yTickStr=True)
            self.plt.plot3DGraph(plotName, dicPct, lsStep, None, None, "%")

    def __getReport__(self):
        """Get perf-report statistics"""
        dicPct = None
        lsFct = []
        lsStep = []
        mc = None
        for log in self.__listLogs__(os.path.join("n=*.t=*", "*.perf-report.*.log"), True):
            if not dicPct:
                dicPct = {}
            logTokens = self.splitLogName(log)
            step = logTokens["n="] + "." + logTokens["t="]
            lines = open(log, "r").readlines()
            for line in lines:
                tokens = line.split()
                if len(tokens) >= 2 and tokens[0] == "#" and tokens[1] == "Samples:":
                    mc = tokens[len(tokens)-1]
                if mc and len(tokens) >= 1 and tokens[0].find("%") != -1:
                    pct = float(tokens[0].replace("%", ""))
                    if float(pct) < self.args.prMinPct:
                        continue
                    fct = tokens[len(tokens)-1]
                    fctExcluded = False
                    for excFct in self.args.prExclude:
                        if fct.find(excFct) != -1:
                            fctExcluded = True
                    if fctExcluded:
                        continue
                    if mc not in dicPct:
                        dicPct[mc] = {}
                    if fct not in dicPct[mc]:
                        dicPct[mc][fct] = {}
                    dicPct[mc][fct][step] = pct
                    lsFct.append(fct)
                    lsFct = list(set(lsFct)) # Remove duplicates
                    lsStep.append(step)
                    lsStep = list(set(lsStep)) # Remove duplicates
        self.__fillDictMissingDataWithZero__(dicPct, lsFct, lsStep)
        return dicPct, lsStep

    def __plotMemoryHistory__(self, nKey, tKey):
        """Plot use case memory history"""
        n = int(nKey.split("=")[1])
        t = int(tKey.split("=")[1])
        print("Analysing", os.path.basename(self.pth), "memory history for n =", n, "and for t =", t, "...", end="")
        dicMB, lsPID, lsMsg = self.__getUseCaseMemoryHistory__(nKey, tKey)
        print(" OK" if dicMB else " No result found")
        if self.verbose: # Print verbose message after OK message
            for msg in lsMsg:
                print(msg)
        if dicMB:
            zSteps = ["vms", "rss", "uss", "swap"]
            plotName = os.path.basename(self.pth) + ".memory"
            plotName += "." + nKey if n != -1 else ".seq"
            plotName += "." + tKey
            self.plt.setPlotAttr(colors=["r", "g", "b", "c"], xTickStr=True)
            if len(lsPID) == 1:
                self.plt.plot2DGraph(plotName, dicMB[lsPID[0]], zSteps, "Time (sec)", "MB")
            else:
                self.plt.plot3DGraph(plotName, dicMB, zSteps, "PID", "Time (sec)", "MB")

    def __getUseCaseCpuHistory__(self, nKey, tKey):
        """Get use case cpu usage information"""
        dicCPU = None
        lsPID = []
        lsMsg = []
        log = os.path.join(os.path.basename(self.pth) + ".cpu" + "." + nKey + "." + tKey + ".log")
        if os.path.exists(log):
            lsMsg.append("  - log found " + log)
            if not dicCPU:
                dicCPU = {}
            lines = open(log, "r").readlines()
            lsPID = lines[0].split()[2:]
            for pid in lsPID:
                dicCPU[pid] = {}
                for idx in range(2, len(lines)):
                    tokens = lines[idx].split()
                    t = int(tokens[0])
                    if t not in dicCPU[pid]:
                        dicCPU[pid][t] = {}
                    dicCPU[pid][t]["cpu"] = float(tokens[1])
                if self.verbose:
                    pc = [dicCPU[pid][t]["cpu"] for t in dicCPU[pid].keys()]
                    msg = "  - PID " + pid + ", %4s" % "cpu" + " : min %11.3f, max %11.3f" % (min(pc), max(pc))
                    lsMsg.append(msg)
        if not dicCPU:
            lsMsg.append("  - CPU usage history not available")
        return dicCPU, lsPID, lsMsg

    def __plotCpuHistory__(self, nKey, tKey):
        """Plot use case cpu usage history"""
        n = int(nKey.split("=")[1])
        t = int(tKey.split("=")[1])
        print("Analysing", os.path.basename(self.pth), "cpu usage history for n =", n, "and for t =", t, "...", end="")
        dicCPU, lsPID, lsMsg = self.__getUseCaseCpuHistory__(nKey, tKey)
        print(" OK" if dicCPU else " No result found")
        if self.verbose: # Print verbose message after OK message
            for msg in lsMsg:
                print(msg)
        if dicCPU:
            plotName = os.path.basename(self.pth) + ".cpu"
            plotName += "." + nKey if n != -1 else ".seq"
            plotName += "." + tKey
            self.plt.setPlotAttr(xTickStr=True)
            if len(lsPID) == 1:
                self.plt.plot2DGraph(plotName, dicCPU[lsPID[0]], ["cpu"], "Time (sec)", "%")
            else:
                self.plt.plot3DGraph(plotName, dicCPU, ["cpu"], "PID", "Time (sec)", "%")

    def __getUseCasePerfTopLog__(self, logName, dicPT, t, pidThd):
        """Get use case perf-top information for a given file of a given event"""
        lsFctLog = []
        foundPerfTop = False
        lines = open(logName, "r").readlines()
        for line in lines:
            if line.find("PerfTop") != -1:
                foundPerfTop = True
                continue
            if not foundPerfTop:
                continue
            if line.lower().find("mapped keys") != -1: # May appear when perf-top is killed
                break # End of relevant data
            tokens = line.split()
            if len(tokens) != 4:
                continue
            pct = tokens[0].replace("%", "")
            if float(pct) < self.args.ptMinPct:
                continue
            fct = tokens[3]
            fctExcluded = False
            for excFct in self.args.ptExclude:
                if fct.find(excFct) != -1:
                    fctExcluded = True
            if fctExcluded:
                continue
            lsFctLog.append(fct)
            if fct not in dicPT[t]:
                dicPT[t][fct] = {}
            dicPT[t][fct][pidThd] = pct
        return lsFctLog

    @staticmethod
    def __fillDictMissingDataWithZero__(dic, lsSdKeys, lsTdKeys):
        """Fill dictionnary with zeros where data are missing"""
        if not dic:
            return
        for mK in dic.keys():
            for sK in lsSdKeys:
                if sK not in dic[mK]:
                    dic[mK][sK] = {}
                for tK in lsTdKeys:
                    if tK not in dic[mK][sK]:
                        dic[mK][sK][tK] = 0. # If no data, fill with zero

    def __getUseCasePerfTopHistory__(self, evt, nKey, tKey):
        """Get use case perf-top information for a given event"""
        dicPT = None
        lsFct = []
        lsPIDThd = []
        lsMsg = []
        nbEmptyLogs = 0
        logPath = os.path.join(os.path.basename(self.pth) + ".perf-top." + evt + "." + nKey + "." + tKey + "*.log")
        for logName in glob.glob(logPath):
            tokens = logName.split(".")
            if tokens[-2] == "sh":
                continue
            if not dicPT:
                dicPT = {}
            t = float(tokens[-2])
            if t not in dicPT:
                dicPT[t] = {}
            pidThd = tokens[-3]
            lsPIDThd.append(pidThd)
            lsPIDThd = list(set(lsPIDThd)) # Remove duplicates
            lsFctLog = self.__getUseCasePerfTopLog__(logName, dicPT, t, pidThd)
            if len(lsFctLog) == 0:
                nbEmptyLogs += 1
            lsFct += lsFctLog
            lsFct = list(set(lsFct)) # Remove duplicates
        self.__fillDictMissingDataWithZero__(dicPT, lsFct, lsPIDThd)
        if nbEmptyLogs > 0:
            lsMsg.append("  - For " + evt + ", " + str(nbEmptyLogs) + " empty perf-top log(s) (increase top slot)")
        if not dicPT:
            lsMsg.append("  - For " + evt + ", perf-top history not available")
        return dicPT, lsPIDThd, lsMsg

    def __plotPerfTopHistory__(self, nKey, tKey):
        """Plot use case perf-top history"""
        n = int(nKey.split("=")[1])
        t = int(tKey.split("=")[1])
        uc = os.path.basename(self.pth)
        print("Analysing", uc, "perf-top history for n =", n, "and for t =", t, "...")
        lsEvt = self.pfm4TpReg + self.args.perfTpEvt
        for evt in lsEvt:
            print("Analysing", uc, "perf-top history for n =", n, "and for t =", t, "and for", evt, "...", end="")
            dicPT, lsPIDThd, lsMsg = self.__getUseCasePerfTopHistory__(evt, nKey, tKey)
            print(" OK" if dicPT else " No result found")
            if self.verbose: # Print verbose message after OK message
                for msg in lsMsg:
                    print(msg)
            if dicPT:
                plotName = os.path.basename(self.pth) + ".perf-top." + evt
                plotName += "." + nKey if n != -1 else ".seq"
                plotName += "." + tKey
                self.plt.setPlotAttr(yTickStr=True)
                self.plt.plot3DGraph(plotName, dicPT, lsPIDThd, "Time (sec)", None, "%")

    def __getUseCaseGFStat__(self, ntKey):
        """Get use case GFlops statistics for a given proc and thread configuration"""
        lsEvt = self.args.perfStGFEvt + self.pfm4StGFReg
        fo, elapseFO, lsMsgGF = self.__getUseCaseStat__(ntKey, lsEvt, "GF")
        return fo, elapseFO, lsMsgGF

    def __getUseCaseCMStat__(self, ntKey):
        """Get use case cache-misses statistics for a given proc and thread configuration"""
        lsEvt = self.args.perfStCMEvt + self.pfm4StCMReg
        cm, elapseCM, lsMsgCM = self.__getUseCaseStat__(ntKey, lsEvt, "CM")
        return cm, elapseCM, lsMsgCM

    def __getElapsedTimeDict__(self):
        """Get the elapsed time dictionnary"""
        nbRuns = 0
        dicET = {}
        if os.path.exists(self.pth):
            os.chdir(self.pth)
            for nt in sorted(os.listdir(os.getcwd())):
                if not os.path.isdir(nt):
                    continue
                os.chdir(nt)
                nKey, tKey = nt.split(".")
                n = int(nKey.split("=")[1])
                if n == -1: # Sequential
                    n = 1
                t = int(tKey.split("=")[1])
                lsMsg = []
                perfLog = self.__getUseCaseStatLog__("." + nKey + "." + tKey, lsMsg, "SU")
                if not perfLog:
                    if self.verbose: # Print verbose message after OK message
                        for msg in lsMsg:
                            print(msg)
                else:
                    lines = open(perfLog, "r").readlines()
                    lastLine = lines[len(lines)-1].split() if len(lines) >= 1 else []
                    if len(lastLine) >= 3 and lastLine[0] == "time":
                        elapsedTime = float(lastLine[2])
                        if n not in dicET:
                            dicET[n] = {}
                        if t not in dicET[n]:
                            dicET[n][t] = {}
                        dicET[n][t]["elapse"] = elapsedTime
                        nbRuns += 1
                os.chdir(self.pth)
        return nbRuns, dicET

    def readConfig(self, ucPath):
        """Read the use case json configuration"""
        self.pth = ucPath
        self.logID = []
        self.exe = {}
        self.rlm = {}
        if os.path.exists(self.pth):
            os.chdir(self.pth)
            if not os.path.exists("usc.json"):
                print("Missing usc.json")
                return False
            jsCfg = json.load(open("usc.json", "r"))
            if "LOGID" in jsCfg:
                print("Configuring", os.path.basename(self.pth), "with LOGID =", jsCfg["LOGID"])
                self.logID = jsCfg["LOGID"].split()
            if "EXE" in jsCfg:
                print("Configuring", os.path.basename(self.pth), "with EXE =", jsCfg["EXE"])
                self.exe["EXE"] = jsCfg["EXE"]
            if "ARGS" in jsCfg:
                print("Configuring", os.path.basename(self.pth), "with ARGS =", jsCfg["ARGS"])
                self.exe["ARGS"] = jsCfg["ARGS"].split("|") # Enable weak scaling : use "|" to separate run arguments
            if "MPI" in jsCfg:
                print("Configuring", os.path.basename(self.pth), "with MPI =", jsCfg["MPI"])
                self.exe["MPI"] = [int(n) for n in jsCfg["MPI"].split()]
            if "THD" in jsCfg:
                print("Configuring", os.path.basename(self.pth), "with THD =", jsCfg["THD"])
                self.exe["THD"] = [int(t) for t in jsCfg["THD"].split()]
            if "COLOR" in jsCfg:
                print("Configuring", os.path.basename(self.pth), "with COLOR =", jsCfg["COLOR"])
                self.rlm["COLOR"] = jsCfg["COLOR"].split()
            if "MARKER" in jsCfg:
                print("Configuring", os.path.basename(self.pth), "with MARKER =", jsCfg["MARKER"])
                self.rlm["MARKER"] = jsCfg["MARKER"].split()
            if "LABEL" in jsCfg:
                print("Configuring", os.path.basename(self.pth), "with LABEL =", jsCfg["LABEL"])
                self.rlm["LABEL"] = jsCfg["LABEL"]
        self.__defaultConfig__()
        rc = self.__checkConfig__()
        print("") # Output separator for clarity
        return rc

    def prepUseCase(self):
        """Prepare the use case"""
        rc = 0
        if os.path.exists(self.pth):
            os.chdir(self.pth)
            if os.path.exists("prep.sh"): # Always run prep: if run -u, then run -r, prep must be ran twice
                log = open("prep.log", "w")
                print("Preparing", os.path.basename(self.pth), "...", end="")
                start = time.time()
                rc = subprocess.call(["./prep.sh"], stdout=log, stderr=log)
                if rc != 0:
                    self.buildError(log)
                self.printStatus(start, rc)
                print("") # Output separator for clarity
        return rc

    def runUseCase(self):
        """Run the use case over all possible proc and thread configurations"""
        rc = self.prepUseCase()
        if rc == 0:
            if "EXE" in self.exe:
                self.runObjDump(os.path.basename(self.pth) + ".objdump.log", self.exe["EXE"])
            for idx in range(len(self.exe["MPI"])):
                n = self.exe["MPI"][idx]
                if self.args.nproc > 0 and int(n) > self.args.nproc:
                    continue
                t = self.exe["THD"][idx]
                a = self.exe["ARGS"][idx] if "ARGS" in self.exe else None
                runTokens = [("n", n, "d", max(self.exe["MPI"]))]
                runTokens += [("t", t, "d", max(self.exe["MPI"]))]
                self.runUseCaseNT(n, t, a, runTokens)
                print("") # Output separator for clarity

    def runUseCaseNT(self, n, t, a, runTokens):
        """Run the use case for a given proc and thread configuration"""
        ext = ""
        for logID in self.logID + self.args.logID:
            ext = "." + logID + ext
        if os.path.exists(self.pth):
            os.chdir(self.pth)
            logTokens = self.splitLogName(self.buildLogName(os.path.basename(self.pth), runTokens, ext + ".log"))
            runDir = logTokens["n="] + "." + logTokens["t="]
            if not os.path.exists(runDir):
                os.makedirs(runDir)
            os.chdir(runDir)
            runSh = self.__createRunShell__(n, t, a, logTokens)
            self.__runUseCaseNTPerfStat__(logTokens, runSh, t)
            self.__runUseCaseNTPerfReport__(logTokens, runSh, t)
            self.__runUseCaseNTPerfTop__(logTokens, runSh, t)

    def getUseCaseStat(self):
        """Get use case statistics"""
        lsUCS = []
        idxNT = 0
        if os.path.exists(self.pth):
            os.chdir(self.pth)
            print("Analysing", os.path.basename(self.pth), "statistics ...")
            for nt in sorted(os.listdir(os.getcwd())):
                if not os.path.isdir(nt):
                    continue
                ucs = self.getUseCaseStatNT(nt, idxNT)
                if ucs:
                    lsUCS.append(ucs)
                os.chdir(self.pth)
                idxNT += 1
        return lsUCS

    def getUseCaseStatNT(self, nt, idxNT):
        """Get use case statistics for a given proc and thread configuration"""
        os.chdir(os.path.join(self.pth, nt))
        nKey, tKey = nt.split(".")
        n = nKey.split("=")[1]
        t = tKey.split("=")[1]
        print("Analysing", os.path.basename(self.pth), "statistics for n =", n, "and t =", t, "...", end="")
        fo, elapseFO, lsMsgGF = self.__getUseCaseGFStat__("." + nKey + "." + tKey)
        cm, elapseCM, lsMsgCM = self.__getUseCaseCMStat__("." + nKey + "." + tKey)
        if fo == 0 or cm == 0:
            print(" No result available, checks logs")
            return None
        fs, bs, lbl = None, None, None
        if fo <= 0 or abs(elapseFO) < 1.e-6 or cm <= 0 or abs(elapseCM) < 1.e-6:
            print(" KO")
        else:
            fs = fo / elapseFO # Flop per second
            bs = cm / elapseCM # Byte per second
            lbl = self.rlm["LABEL"]
            lbl += ", " + n + " MPI" if int(n) != -1 else ", SEQ"
            lbl += ", " + t + " THD"
            msg = " OK : MB/s = %11.3f, GFlops = %11.3f, F/B = %11.3f"
            print(msg % (bs / (1024. ** 2), fs / (1000. ** 3), fs / bs))
        if self.verbose: # Print verbose message after OK message
            for msg in lsMsgGF + lsMsgCM:
                print(msg)
        if not fs or not bs:
            return None
        return (fs, bs, self.rlm["COLOR"][idxNT], self.rlm["MARKER"][idxNT], lbl, elapseFO)

    def plot(self):
        """Plot use case"""
        if os.path.exists(self.pth):
            os.chdir(self.pth)
            if hasattr(self.args, "report") and self.args.report:
                self.__plotReport__()
            for nt in sorted(os.listdir(os.getcwd())):
                if not os.path.isdir(nt):
                    continue
                self.plotNT(nt)
                os.chdir(self.pth)
            self.plotSpeedUp()

    def plotNT(self, nt):
        """Plot use case for a given proc and thread configuration"""
        nKey, tKey = nt.split(".")
        os.chdir(os.path.join(self.pth, nt))
        if hasattr(self.args, "top") and self.args.top:
            if self.args.top != "*" and nt.find(self.args.top) == -1:
                return
            self.__plotPerfTopHistory__(nKey, tKey)
        if hasattr(self.args, "watch") and self.args.watch:
            if self.args.watch != "*" and nt.find(self.args.watch) == -1:
                return
            self.__plotMemoryHistory__(nKey, tKey)
            self.__plotCpuHistory__(nKey, tKey)

    def plotSpeedUp(self):
        """Plot use case speed up"""
        nbRuns, dicET = self.__getElapsedTimeDict__()
        if nbRuns > 1:
            plotName = os.path.basename(self.pth) + ".elapse"
            if len(dicET.keys()) == 1 and 1 in dicET:
                self.plt.setPlotAttr(xTickInt=True)
                self.plt.plot2DGraph(plotName, dicET[1], ["elapse"], "Threads", "Time (sec)")
            else:
                self.plt.setPlotAttr(xTickInt=True, yTickInt=True)
                self.plt.plot3DGraph(plotName, dicET, ["elapse"], "Proc.", "Threads", "Time (sec)")
            if 1 in dicET and 1 in dicET[1]:
                refElapsedTime = dicET[1][1]["elapse"] # 1 proc, 1 thread
                for nKey in dicET.keys():
                    for tKey in dicET[nKey].keys():
                        if nKey in dicET and tKey in dicET[nKey]:
                            dicET[nKey][tKey]["speedup"] = refElapsedTime / dicET[nKey][tKey]["elapse"]
                plotName = os.path.basename(self.pth) + ".speedup"
                if len(dicET.keys()) == 1 and 1 in dicET:
                    self.plt.setPlotAttr(xTickInt=True)
                    self.plt.plot2DGraph(plotName, dicET[1], ["speedup"], "Threads", "Speed up")
                else:
                    self.plt.setPlotAttr(xTickInt=True, yTickInt=True)
                    self.plt.plot3DGraph(plotName, dicET, ["speedup"], "Proc.", "Threads", "Speed up")
