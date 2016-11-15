"""This module exports the perfMonitor class"""

from __future__ import print_function

import os
import sys
import subprocess
import time
import distutils.spawn
import glob
import psutil

from pyc.runJob import runJob
from pyc.download import download

class perfMonitor(runJob):
    """Performance monitoring class designed to handle general purpose monitoring topics"""

    def __init__(self, args, needReg=True):
        """Initialize perfMonitor class instance"""
        runJob.__init__(self, args)
        self.dld = download(os.path.join(args.tmp))
        self.pfm4StGFReg = []
        self.pfm4StCMReg = []
        self.pfm4RpReg = []
        self.pfm4TpReg = []
        self.regInfo = []
        if needReg:
            self.getRegisters()

    @staticmethod
    def __addUserModifier__(lsOfEvtLs):
        """Add user modifier :u to events used for profiling"""
        for evtLs in lsOfEvtLs:
            for idx, evt in enumerate(evtLs):
                if evt[len(evt) - 2:] != ":u":
                    evtLs[idx] = evt + ":u" # Add user modifier

    def __getRegisterFromEvent__(self, evt, umask, descr, lsReg):
        """Get register associated to an event used for profiling"""
        chkEvt = os.path.join(os.getcwd(), "check_events") # Use absolute path as os.getcwd is not in PATH's
        cmdLine = [chkEvt, evt + ":" + umask] if umask != "none" else [chkEvt, evt]
        evtLog = "_".join(cmdLine) + ".log"
        log = open(evtLog, "w")
        log.write("\n\n" + "~>" + " ".join(cmdLine) + "\n\n")
        log.flush() # Flush needed before subprocess.call
        rc = subprocess.call(cmdLine, stdout=log, stderr=log)
        if rc != 0:
            print("Can not check HW events (" + evt + "/" + umask + "), skip it")
            return
        log.close() # Flush needed between write and read
        lines = open(evtLog, "r").readlines()
        lastLine = lines[len(lines) - 1]
        if lastLine.find("Codes") == -1:
            print("Can not get HW event code (" + evt + "/" + umask + "), skip it")
            return
        reg = lastLine.split()[2].replace("0x", "r") # Last line: Codes <=> register
        lsReg.append(reg)
        self.regInfo.append((reg, evt, umask, descr))

    def __findRegisterFromPfm4__(self, lines, evt, lsReg):
        """Find register in libpfm4 logs"""
        evtFound = False
        umFound = False
        evtName = evt
        umName = "ALL" # Look for all umasks
        nbReg = len(lsReg)
        if evt.find(":") != -1:
            evtName = evt.split(":")[0]
            umName = evt.split(":")[1]
        for line in lines:
            tokens = line.split()
            if len(tokens) >= 3 and tokens[0] == "Name" and tokens[1] == ":" and tokens[2] == evtName:
                evtFound = True
            if evtFound:
                if len(tokens) >= 3 and tokens[0].find("Umask") != -1 and tokens[1] == ":":
                    if umName != "ALL" and line.find(umName) == -1:
                        continue # Look for a specific umask
                    umFound = True
                    self.__getRegisterFromEvent__(evtName, tokens[2], " ".join(tokens[4:]), lsReg)
                if line[0] == "#" and line[1] == "-":
                    if not umFound:
                        self.__getRegisterFromEvent__(evtName, "none", "none", lsReg)
                    break
        if len(lsReg) == nbReg: # No register has been added
            print("Can not find HW event", evt, "(" + umName + ")")

    def __logMemoryHistory__(self, initLog, logTokens, ptChildren, elapsedTime):
        """Log memory history to a file"""
        if self.args.watch:
            m = "w" if initLog else "a"
            memLog = logTokens["root="] + ".mem" + "." + logTokens["n="] + "." + logTokens["t="] + ".log"
            mLog = open(memLog, m)
            if initLog:
                print("Watching memory in", memLog, "...")
                mLog.write("# pid " + " ".join([str(child.pid) for child in ptChildren]) + "\n")
                mLog.write("# time(sec) vms(Bytes) rss(Bytes) uss(Bytes) swap(Bytes)\n")
            for child in ptChildren:
                mLog.write("%d " % elapsedTime)
                mInfo = child.memory_full_info()
                if hasattr(mInfo, "vms"):
                    mLog.write("%d " % mInfo.vms)
                else:
                    mLog.write("-1")
                if hasattr(mInfo, "rss"):
                    mLog.write("%d " % mInfo.rss)
                else:
                    mLog.write("-1")
                if hasattr(mInfo, "uss"):
                    mLog.write("%d " % mInfo.uss)
                else:
                    mLog.write("-1")
                if hasattr(mInfo, "swap"):
                    mLog.write("%d " % mInfo.swap)
                else:
                    mLog.write("-1")
                mLog.write(" # pid " + str(child.pid) + "\n")
        return False

    def __logCpuUseHistory__(self, initLog, logTokens, ptChildren, elapsedTime):
        """Log CPU usage history to a file"""
        if self.args.watch:
            m = "w" if initLog else "a"
            cpuLog = logTokens["root="] + ".cpu" + "." + logTokens["n="] + "." + logTokens["t="] + ".log"
            cLog = open(cpuLog, m)
            if initLog:
                print("Watching cpu in", cpuLog, "...")
                cLog.write("# pid " + " ".join([str(child.pid) for child in ptChildren]) + "\n")
                cLog.write("# time(sec) cpu(%)\n")
            for child in ptChildren:
                cLog.write("%d " % elapsedTime)
                cInfo = child.cpu_percent()
                cLog.write("%d " % cInfo)
                cLog.write(" # pid " + str(child.pid) + "\n")
        return False

    @staticmethod
    def __cleanPerfTopHistory__(evt):
        """Clean perf-top history logs for a given event"""
        for logName in glob.glob(os.path.join("*.perf-top." + evt + ".*.log")):
            os.remove(logName) # Clean previous run before next run

    @staticmethod
    def __getPerfTopProc__(rProc, rPU, nKey):
        """Get the list of processus perf-top will have to spy"""
        ptChildren = []
        while rProc.poll() is None:
            time.sleep(0.1) # Wait for run.sh to start
            rChildren = rPU.children() # Sequential, or, mpirun processus
            rGrandChildren = [] # Nothing if sequential, or, MPI processes (under mpirun)
            for child in rChildren:
                rGrandChildren += child.children()
            n = int(nKey.split("=")[1])
            n = 1 if n == -1 else n # Sequential (n = -1) or MPI
            if len(rGrandChildren) == n: # MPI processes, look first
                ptChildren = rGrandChildren
            elif len(rChildren) == n: # Sequential
                ptChildren = rChildren
            if len(ptChildren) == n:
                break
        return ptChildren

    def __logPerfTopHistory__(self, ptChildren, perfLog, elapsedTime, cmdLine, top, tKey):
        """Log perf-top history to a file"""
        lsLog = []
        lsProc = []
        pLog, pProc = None, None
        try: # Some events may not be supported by perf-top
            nbThd = int(tKey.split("=")[1])
            for child in ptChildren:
                for thd in range(nbThd):
                    thdKey = ("%0" + str(len(str(nbThd))) + "d") % thd
                    pLogName = "%s.%s-%s.%06d.log" % (perfLog, str(child.pid), thdKey, int(elapsedTime))
                    if self.args.verbose:
                        print("Running", pLogName, "...")
                    pCmdLine = cmdLine + ["-p", str(child.pid), "-t", str(thd)]
                    pLog = open(pLogName, "w")
                    pLog.write("\n\n" + "~>" + " ".join(pCmdLine) + "\n\n")
                    pLog.flush() # Flush needed before subprocess.call
                    pProc = subprocess.Popen(pCmdLine, stdout=pLog, stderr=pLog, stdin=subprocess.PIPE)
                    lsLog.append(pLog)
                    lsProc.append(pProc)
        finally:
            time.sleep(float(top)) # Wait for perf-top to make an estimation of the current state
            for pLog in lsLog:
                pLog.flush() # Flush before to kill the process
            for pProc in lsProc:
                if not pProc.poll(): # Some events may not be supported by perf-top
                    pProc.stdin.write("q\n".encode()) # Send "q" to the process to quit perf-top
                    pProc.terminate()

    def downloadTmp(self):
        """Download libpfm4 in the temporary directory"""
        os.chdir(self.args.tmp)
        print("Downloading libpfm4 ...")
        pfm4TGZ = "libpfm-" + self.args.pfm4Vn + ".tar.gz"
        self.dld.downloadFile(os.path.join(self.args.pfm4URL + pfm4TGZ))
        pfm4Dir = "libpfm-" + self.args.pfm4Vn
        if not os.path.exists(pfm4Dir) and os.path.exists(pfm4TGZ):
            if subprocess.call(["tar", "-xzf", pfm4TGZ]) != 0:
                sys.exit("ERROR: can not download libpfm4")

    def getRegisters(self):
        """Get registers associated to events used for profiling"""
        print("Searching for registers with libpfm4 ...")
        self.build()
        self.showEvt()
        self.__addUserModifier__([self.args.perfStGFEvt, self.args.perfStCMEvt])
        self.__addUserModifier__([self.args.perfRpEvt, self.args.perfTpEvt])
        if os.path.exists("showevtinfo.log"):
            lines = open("showevtinfo.log", "r").readlines()
            for evt in self.args.pfm4StGFEvt:
                self.__findRegisterFromPfm4__(lines, evt, self.pfm4StGFReg)
            for evt in self.args.pfm4StCMEvt:
                self.__findRegisterFromPfm4__(lines, evt, self.pfm4StCMReg)
            for evt in self.args.pfm4RpEvt:
                self.__findRegisterFromPfm4__(lines, evt, self.pfm4RpReg)
            for evt in self.args.pfm4TpEvt:
                self.__findRegisterFromPfm4__(lines, evt, self.pfm4TpReg)
            self.__addUserModifier__([self.pfm4StGFReg, self.pfm4StCMReg, self.pfm4RpReg, self.pfm4TpReg])
            self.regInfo = list(set(self.regInfo)) # Remove duplicates
            self.regInfo.sort(key=lambda r: r[1] + r[2])
            for r in self.regInfo:
                print("Register", r[0], "is mapped to", r[1] + ":" + r[2])
        print("") # Output separator for clarity

    def build(self):
        """Build libpfm4 in the temporary directory"""
        pfm4Dir = "libpfm-" + self.args.pfm4Vn
        buildDir = os.path.join(self.args.tmp, pfm4Dir)
        if os.path.exists(buildDir):
            os.chdir(buildDir)
            log = open("make.log", "w")
            print("Building libpfm4 ...", end="")
            start = time.time()
            rc = subprocess.call(["make", "VERBOSE=1"], stdout=log, stderr=log)
            if rc != 0:
                self.buildError(log)
            self.printStatus(start, rc)

    def showEvt(self):
        """Show events from libpfm4 logs"""
        pfm4Dir = "libpfm-" + self.args.pfm4Vn
        runDir = os.path.join(self.args.tmp, pfm4Dir)
        if os.path.exists(runDir):
            os.chdir(runDir)
            print("Running libpfm4 ...")
            os.chdir("examples")
            shwEvt = os.path.join(os.getcwd(), "showevtinfo") # Use absolute path as os.getcwd is not in PATH's
            log = open("showevtinfo.log", "w")
            subprocess.call([shwEvt], stdout=log, stderr=log)
            log.close() # Flush needed between write and read

    def runPerfTop(self, perfLog, logTokens, runSh, t, cmdLine, top):
        """Run perf-top"""
        start = time.time()
        perfLog = perfLog + "." + logTokens["n="] + "." + logTokens["t="]
        for k in list(logTokens.keys()):
            if perfLog.find(logTokens[k]) == -1:
                perfLog = perfLog + "." + logTokens[k]
        print("Running", perfLog + ".sh.log", "...")
        if not os.path.exists(perfLog + ".sh.log") or self.args.force:
            initMemLog = True if self.args.watch else False
            initCpuLog = True if self.args.watch else False
            cEnv = self.__buildEnv__(t)
            rLog = open(perfLog + ".sh.log", "w")
            rProc = subprocess.Popen(["./" + runSh], env=cEnv, stdout=rLog, stderr=rLog)
            rPU = psutil.Process(rProc.pid)
            ptChildren = self.__getPerfTopProc__(rProc, rPU, logTokens["n="])
            if len(ptChildren) > 0:
                elapsedTime = 0.
                while rProc.poll() is None:
                    initMemLog = self.__logMemoryHistory__(initMemLog, logTokens, ptChildren, elapsedTime)
                    initCpuLog = self.__logCpuUseHistory__(initCpuLog, logTokens, ptChildren, elapsedTime)
                    self.__logPerfTopHistory__(ptChildren, perfLog, elapsedTime, cmdLine, top, logTokens["t="])
                    elapsedTime = time.time() - start
            rLog.close()
            return rProc.returncode, perfLog + ".sh.log"
        return 0, perfLog + ".sh.log"

    def runObjDump(self, odpLog, exe):
        """Run objdump"""
        if not distutils.spawn.find_executable("objdump"):
            return
        if not distutils.spawn.find_executable("grep"):
            return
        if not distutils.spawn.find_executable("wc"):
            return
        if not os.path.exists(odpLog) or self.args.force:
            log = open(odpLog, "w")
            for od in self.args.oDump:
                od = ["objdump", "-S", exe]
                gp = ["grep", "-w"]
                wc = ["wc", "-l"]
                cmdLine = od + ["|"] + gp + ["|"] + wc
                log.write("\n" + "~>" + " ".join(cmdLine) + "\n")
                log.flush() # Flush needed before subprocess.Popen
                odProc = subprocess.Popen(od, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                gpProc = subprocess.Popen(gp, stdin=odProc.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                wcProc = subprocess.Popen(wc, stdin=gpProc.stdout, stdout=log, stderr=log)
                wcProc.wait() # Make sure the command is over before flushing
            log.close() # Flush needed after subprocess.Popen

    def runPerf(self, logTokens, perfLog, exe, thd=None, prepend=None, args=None):
        """Run perf-record, perf-report or perf-stat"""
        perfLog = perfLog + "." + logTokens["n="] + "." + logTokens["t="]
        for k in list(logTokens.keys()):
            if perfLog.find(logTokens[k]) == -1:
                perfLog = perfLog + "." + logTokens[k]
        perfLog = perfLog + ".log"
        print("Running", perfLog, "...", end="")
        start = time.time()
        rc = 0
        if not os.path.exists(perfLog) or self.args.force:
            log = open(perfLog, "w")
            eInfo = "\n".join([ei[0] + " = " + ei[1] + "-" + ei[2] + " <=> " + ei[3] for ei in self.regInfo])
            log.write(eInfo) # Info: event <=> register
            clDic = {}
            clDic["EXE"] = exe
            if prepend:
                clDic["PREPEND"] = prepend
            if args:
                clDic["ARGS"] = args
            rc = self.runCmdLine(log, clDic, begin=start, thd=thd)
        self.printStatus(start, rc, printError=False)
        return rc
