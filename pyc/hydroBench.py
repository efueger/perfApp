"""This module exports the hydroBench class"""

from __future__ import print_function

import os
import shutil
import subprocess
import time
import stat
import json

from pyc.bench import bench

class hydroBench(bench):
    """Class dedicated to the Hydro benchmark"""

    def __init__(self, args, url, hydroBuild, hydroRun, hydroLID):
        """Initialize Hydro bench class instance"""
        bench.__init__(self, args, "Hydro", "GF")
        self.hydroDir = "Hydro"
        self.url = url
        self.hydroBuild = hydroBuild
        self.hydroNxy = hydroRun["NXY"]
        self.hydroNxyStep = hydroRun["NXYSTEP"]
        self.hydroTend = hydroRun["TEND"]
        self.hydroLID = hydroLID

    def __writeNML__(self, hydroImpl, nxy, nxyStep, runTokens):
        """Write input file (.nml) for hydro"""
        nmlTokens = [("impl", hydroImpl, "s")]
        maxNxy = max([int(i) for i in self.hydroNxy.split()])
        maxNxyStep = max([int(i) for i in self.hydroNxyStep.split()])
        nmlTokens += [("nxy", int(nxy), "d", maxNxy), ("nxystep", int(nxyStep), "d", maxNxyStep)] + runTokens
        nmlLog = self.buildLogName("Hydro", nmlTokens, ".nml")
        if not os.path.exists(nmlLog):
            log = open(nmlLog, "w")
            log.write("&MESH" + "\n")
            log.write("nx=" + nxy + "\n")
            log.write("ny=" + nxy + "\n")
            log.write("nxystep=" + nxyStep + "\n")
            log.write("/" + "\n\n")
            log.write("&RUN" + "\n")
            log.write("tend=" + self.hydroTend + "\n")
            log.write("/" + "\n\n")
            log.close() # Flush
        return nmlLog

    def downloadTmp(self):
        """Download Hydro benchmark in the temporary directory"""
        os.chdir(self.tmp)
        if not os.path.exists(self.hydroDir):
            os.makedirs(self.hydroDir)
        os.chdir(self.hydroDir)
        print("Downloading", self.bName, "...")
        self.dld.gitClone(self.url)

    def check(self):
        """Check Hydro benchmark consistency"""
        print("Checking", self.bName, "benchmark ...", end="")
        if "LIBNUMA" in self.hydroBuild and self.hydroBuild["LIBNUMA"] != "":
            if not os.path.exists(self.hydroBuild["LIBNUMA"]):
                print(" KO :", self.hydroBuild["LIBNUMA"], "does not exists, configure json")
                return False
        print(" OK")
        return True

    def build(self, cpl):
        """Build Hydro benchmark in the temporary directory"""
        hydroImpl = "HydroC99_2DMpi"
        buildDir = os.path.join(self.tmp, self.hydroDir, "Hydro", "HydroC", hydroImpl, "Src")
        if os.path.exists(buildDir):
            os.chdir(buildDir)
            shutil.copyfile(os.path.join(self.tmp, self.hydroDir, "Hydro", "Arch", "make_gcc_mpi"), "make.inc")
            oldOptions = ["MPIROOT", "FTIROOT"]
            newOptions = ["", ""]
            oldOptions += ["CC", "F90", "MPICC", "MPIF90"]
            newOptions += [cpl["MPICC"], cpl["MPIF90"], cpl["MPICC"], cpl["MPIF90"]]
            oldOptions += ["CFLAGS", "FFLAGS", "LDFLAGS"]
            newOptions += [cpl["FLAGS"], cpl["FLAGS"], cpl["LINKFLAGS"] + " " + self.hydroBuild["LIBNUMA"]]
            oldOptions += ["CFLAGS_OMP", "NVCFLAGS_OMP", "FFLAGS_OMP", "LDFLAGS_OMP"]
            newOptions += [cpl["OMPFLAGS"], "", cpl["OMPFLAGS"], cpl["OMPFLAGS"]]
            oldOptions += ["CFLAGS_MPI", "NVCFLAGS_MPI", "FFLAGS_MPI", "LDFLAGS_MPI"]
            newOptions += ["-DMPI" + " " + self.hydroBuild["CFLAGS_MPI"], "", "", self.hydroBuild["LDFLAGS_MPI"]]
            oldOptions += ["CFLAGS_FTI", "LDFLAGS_FTI"]
            newOptions += ["-DFTI=0", ""]
            self.__modifMakefile__(["make.inc"], oldOptions, newOptions)
            self.__modifMakefile__(["Makefile"], [], [], comments=["vec-report"])
            log = open("make.log", "w")
            print("Building", self.bName, ":", hydroImpl, "...", end="")
            start = time.time()
            rc = subprocess.call(["make"], stdout=log, stderr=log)
            if rc != 0:
                m = self.bName + " (" + hydroImpl + ", needs libnuma.a)"
                self.buildError(log, msg=m)
            self.printStatus(start, rc)

    def runNT(self, n, t, runTokens, ext):
        """Run Hydro benchmark in the temporary directory for a given proc and thread configuration"""
        hydroImpl = "HydroC99_2DMpi"
        runDir = os.path.join(self.tmp, self.hydroDir, "Hydro", "HydroC", hydroImpl, "Src")
        if os.path.exists(runDir):
            os.chdir(runDir)
            if len(self.hydroNxy.split()) != len(self.hydroNxyStep.split()):
                print("Running Hydro KO: nxy and nxystep must have the same size")
                return
            for idx, nxy in enumerate(self.hydroNxy.split()):
                nxyStep = self.hydroNxyStep.split()[idx]
                nmlLog = self.__writeNML__(hydroImpl, nxy, nxyStep, runTokens)
                hydroExt = ext if len(self.hydroLID) == 0 else "." + ".".join(self.hydroLID) + ext
                hydroLog = nmlLog.replace(".nml", hydroExt)
                print("Running", hydroLog, "...", end="")
                start = time.time()
                rc = 0
                if not os.path.exists(hydroLog) or self.args.force:
                    log = open(hydroLog, "w")
                    clDic = {}
                    clDic["PREPEND"] = ["mpirun", "-n", str(n)]
                    clDic["EXE"] = "./hydro"
                    clDic["ARGS"] = ["-i", "./" + nmlLog]
                    rc = self.runCmdLine(log, clDic, begin=start, thd=t)
                self.printStatus(start, rc)
                if self.args.quick:
                    break

    def getMetric(self, printMax=True, getDict=False, getMaxInfo=False, filterLogs=False):
        """Getting Hydro benchmark metric from the temporary directory"""
        maxGFlops = 0.
        dicGFlops = {}
        maxInfo = {}
        hydroImpl = "HydroC99_2DMpi"
        runDir = os.path.join(self.tmp, self.hydroDir, "Hydro", "HydroC", hydroImpl, "Src")
        if os.path.exists(runDir):
            os.chdir(runDir)
            for log in self.__listLogs__(os.path.join(runDir, "Hydro*.log"), filterLogs):
                mGFlops, mInfo, nxy, nxystep = None, {}, None, None
                lines = open(log, "r").readlines()
                for line in lines:
                    if line.find("|nx=") != -1:
                        nxy = line.split("=")[1]
                        nxy = int(nxy.split()[0])
                    if line.find("|nxystep=") != -1:
                        nxystep = line.split("=")[1]
                        nxystep = int(nxystep.split()[0])
                    if line.find("Hydro ends") != -1:
                        mGFlops = float(line.split()[5].replace("<", ""))
                        mGFlops = mGFlops / 1024.
                        mInfo["LOG"] = os.path.basename(log)
                        mInfo["EXTRA"] = "nxy = " + str(nxy) +", nxystep = " + str(nxystep)
                if not nxy or not nxystep or not mGFlops:
                    continue
                if nxy not in dicGFlops:
                    dicGFlops[nxy] = {}
                if nxystep not in dicGFlops[nxy]:
                    dicGFlops[nxy][nxystep] = {}
                logTokens = self.splitLogName(log)
                step = logTokens["n="] + "." + logTokens["t="]
                if step not in dicGFlops[nxy][nxystep]:
                    dicGFlops[nxy][nxystep][step] = mGFlops
                if dicGFlops[nxy][nxystep][step] < mGFlops:
                    dicGFlops[nxy][nxystep][step] = mGFlops
                if maxGFlops < mGFlops:
                    maxGFlops = mGFlops
                    maxInfo = mInfo
        self.__printMetricStatus__(printMax, maxGFlops, maxInfo)
        return self.__returnMetric__(dicGFlops, maxInfo, maxGFlops, getDict=getDict, getMaxInfo=getMaxInfo)

    def plotN(self, nKey):
        """Plotting Hydro benchmark results from the temporary directory for a given proc configuration"""
        dicGFlops = self.getMetric(printMax=False, getDict=True, filterLogs=True)
        steps = self.__getStepsFromKey__(dicGFlops, nKey)
        plotName = self.plt.buildPlotName([self.bName, nKey])
        self.plt.plot3DGraph(plotName, dicGFlops, steps, "nxy", "nxystep", "GFlops")

    def genUseCase(self):
        """Generate a use case from the best Hydro benchmark run"""
        maxInfo = self.getMetric(printMax=False, getMaxInfo=True)
        if "LOG" in maxInfo:
            ucDir = self.__cleanUseCase__(os.path.join(self.args.tmp, "usc"), "pfb" + self.bName)
            os.chdir(ucDir)
            hydroImpl = "HydroC99_2DMpi"
            runDir = os.path.join(self.tmp, self.hydroDir, "Hydro", "HydroC", hydroImpl, "Src")
            shutil.copyfile(os.path.join(runDir, "hydro"), "hydro")
            os.chmod("hydro", os.stat("hydro").st_mode | stat.S_IEXEC) # chmod +x
            logTokens = self.splitLogName(maxInfo["LOG"])
            nmlLog = "Hydro" + "." + logTokens["impl="]
            nmlLog = nmlLog + "." + logTokens["nxy="] + "." + logTokens["nxystep="]
            nmlLog = nmlLog + "." + logTokens["n="] + "." + logTokens["t="] + ".nml"
            shutil.copyfile(os.path.join(runDir, nmlLog), nmlLog)
            runSh = open("run.sh", "w")
            runSh.write("#!/bin/bash" + "\n")
            runSh.write("cp ../" + nmlLog + " ." + "\n") # Copy Hydro input file
            runSh.close() # Flush
            jsCfg = {}
            jsCfg["EXE"] = "hydro"
            jsCfg["MPI"] = str(logTokens["n="].split("=")[1])
            jsCfg["THD"] = str(logTokens["t="].split("=")[1])
            jsCfg["ARGS"] = "-i " + nmlLog
            jsCfg["COLOR"] = "green"
            jsCfg["MARKER"] = "."
            jsCfg["LABEL"] = self.bName
            json.dump(jsCfg, open("usc.json", "w"))
