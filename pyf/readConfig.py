"""Manage configuration"""

# Import modules

from __future__ import print_function

import json

from pyc.streamBench import streamBench
from pyc.stream2Bench import stream2Bench
from pyc.iozoneBench import iozoneBench
from pyc.iorBench import iorBench
from pyc.hplBench import hplBench
from pyc.hydroBench import hydroBench
from pyc.nasBench import nasBench

# Functions

def readConfig(args):
    """Read configuration file"""
    print("Configuring using file :", args.config.name, "...")
    jsCfg = json.load(args.config)
    readArchitectureConfig(args, jsCfg)
    readBuildTimeConfig(args, jsCfg)
    readRunTimeConfig(args, jsCfg)
    readPlotConfig(args, jsCfg)
    readBenchmarkConfig(args, jsCfg)
    readUseCaseConfig(args, jsCfg)

def readArchitectureConfig(args, jsCfg):
    """Read architecture features from the configuration file"""
    print("Configuring architecture features ...")
    args.clSize = 64
    args.flopPerPdSIMD = 1
    args.flopPerPdSSE = 1
    if "ARCHITECTURE" in jsCfg:
        aCfg = jsCfg["ARCHITECTURE"]
        if "CACHE_LINE_SIZE_IN_BYTES" in aCfg:
            print("Configuring cache line size with", aCfg["CACHE_LINE_SIZE_IN_BYTES"], "...")
            args.clSize = int(aCfg["CACHE_LINE_SIZE_IN_BYTES"])
        if "NB_FLOP_PER_PACKED_SIMD" in aCfg:
            print("Configuring flop per packed SIMD with", aCfg["NB_FLOP_PER_PACKED_SIMD"], "...")
            args.flopPerPdSIMD = int(aCfg["NB_FLOP_PER_PACKED_SIMD"])
        if "NB_FLOP_PER_PACKED_SSE" in aCfg:
            print("Configuring flop per packed SSE with", aCfg["NB_FLOP_PER_PACKED_SSE"], "...")
            args.flopPerPdSSE = int(aCfg["NB_FLOP_PER_PACKED_SSE"])

def readBuildTimeConfig(args, jsCfg):
    """Read build time customization from the configuration file"""
    print("Configuring build time ...")
    args.CC = None
    args.FC = None
    args.MPICC = None
    args.MPIF77 = None
    args.MPIF90 = None
    args.OMPFLAGS = None
    args.FLAGS = None
    args.NOOPTFLAGS = None
    args.LINKFLAGS = None
    if "BUILDTIME" in jsCfg:
        btCfg = jsCfg["BUILDTIME"]
        if "CC" in btCfg and btCfg["CC"] != "":
            print("Configuring CC with", btCfg["CC"], "...")
            args.CC = btCfg["CC"]
        if "FC" in btCfg and btCfg["FC"] != "":
            print("Configuring FC with", btCfg["FC"], "...")
            args.FC = btCfg["FC"]
        if "MPICC" in btCfg and btCfg["MPICC"] != "":
            print("Configuring MPICC with", btCfg["MPICC"], "...")
            args.MPICC = btCfg["MPICC"]
        if "MPIF77" in btCfg and btCfg["MPIF77"] != "":
            print("Configuring MPIF77 with", btCfg["MPIF77"], "...")
            args.MPIF77 = btCfg["MPIF77"]
        if "MPIF90" in btCfg and btCfg["MPIF90"] != "":
            print("Configuring MPIF90 with", btCfg["MPIF90"], "...")
            args.MPIF90 = btCfg["MPIF90"]
        if "OMPFLAGS" in btCfg and btCfg["OMPFLAGS"] != "":
            print("Configuring OMPFLAGS with", btCfg["OMPFLAGS"], "...")
            args.OMPFLAGS = btCfg["OMPFLAGS"]
        if "FLAGS" in btCfg and btCfg["FLAGS"] != "":
            print("Configuring FLAGS with", btCfg["FLAGS"], "...")
            args.FLAGS = btCfg["FLAGS"]
        if "NOOPTFLAGS" in btCfg and btCfg["NOOPTFLAGS"] != "":
            print("Configuring NOOPTFLAGS with", btCfg["NOOPTFLAGS"], "...")
            args.NOOPTFLAGS = btCfg["NOOPTFLAGS"]
        if "LINKFLAGS" in btCfg and btCfg["LINKFLAGS"] != "":
            print("Configuring LINKFLAGS with", btCfg["LINKFLAGS"], "...")
            args.LINKFLAGS = btCfg["LINKFLAGS"]

def readRunTimeConfig(args, jsCfg):
    """Read run time customization from the configuration file"""
    print("Configuring run time ...")
    args.mpirunOpt = None
    args.env = []
    args.logID = []
    if "RUNTIME" in jsCfg:
        rtCfg = jsCfg["RUNTIME"]
        if "MPIRUN_OPT" in rtCfg:
            print("Configuring run time with MPIRUN_OPT =", rtCfg["MPIRUN_OPT"], "...")
            args.mpirunOpt = rtCfg["MPIRUN_OPT"]
        if "OMP_PROC_BIND" in rtCfg:
            print("Configuring run time with OMP_PROC_BIND =", rtCfg["OMP_PROC_BIND"], "...")
            args.env.append(("OMP_PROC_BIND", rtCfg["OMP_PROC_BIND"]))
        if "GOMP_CPU_AFFINITY" in rtCfg:
            print("Configuring run time with GOMP_CPU_AFFINITY =", rtCfg["GOMP_CPU_AFFINITY"], "...")
            args.env.append(("GOMP_CPU_AFFINITY", rtCfg["GOMP_CPU_AFFINITY"]))
        if "KMP_AFFINITY" in rtCfg:
            print("Configuring run time with KMP_AFFINITY =", rtCfg["KMP_AFFINITY"], "...")
            args.env.append(("KMP_AFFINITY", rtCfg["KMP_AFFINITY"]))
        if "LOGID" in rtCfg:
            print("Configuring with log extension =", rtCfg["LOGID"])
            args.logID = rtCfg["LOGID"].split()

def readBenchmarkConfig(args, jsCfg):
    """Read benchmarks from the configuration file"""
    args.bmLs = []
    print("Configuring benchmark mode ...")
    if "BENCH" in jsCfg:
        readBWBenchmarkConfig(args, jsCfg["BENCH"])
        readGFBenchmarkConfig(args, jsCfg["BENCH"])

def readBWBenchmarkConfig(args, bCfg):
    """Read bandwidth benchmarks from the configuration file"""
    if "STREAM" in bCfg:
        strCfg = bCfg["STREAM"]
        if "URL" in strCfg:
            print("Configuring stream benchmark ...")
            args.bmLs.append(streamBench(args, strCfg["URL"]))
    if "STREAM2" in bCfg:
        strCfg = bCfg["STREAM2"]
        strPrereq = strCfg["PREREQ"] if "PREREQ" in strCfg else None
        strURL = strCfg["URL"] if "URL" in strCfg else None
        if strPrereq and strURL:
            print("Configuring stream2 benchmark ...")
            args.bmLs.append(stream2Bench(args, strPrereq, strURL))
    if "IOZONE" in bCfg:
        iozCfg = bCfg["IOZONE"]
        iozURL = iozCfg["URL"] if "URL" in iozCfg else None
        iozVersion = iozCfg["VERSION"] if "VERSION" in iozCfg else None
        iozMkArch = iozCfg["MKARCH"] if "MKARCH" in iozCfg else None
        if iozURL and iozVersion and iozMkArch:
            print("Configuring iozone benchmark ...")
            args.bmLs.append(iozoneBench(args, iozURL, iozVersion, iozMkArch))
    if "IOR" in bCfg:
        iorCfg = bCfg["IOR"]
        iorURL = iorCfg["URL"] if "URL" in iorCfg else None
        iorConfig = {}
        if "CONFIGURE" in iorCfg:
            cCfg = iorCfg["CONFIGURE"]
            iorConfig["OPTIONS"] = cCfg["OPTIONS"].split() if "OPTIONS" in cCfg else ["--with-posix", "--with-mpiio"]
            iorConfig["CFLAGS"] = cCfg["CFLAGS"] if "CFLAGS" in cCfg else ""
            iorConfig["LDFLAGS"] = cCfg["LDFLAGS"] if "LDFLAGS" in cCfg else ""
            iorConfig["LIBS"] = cCfg["LIBS"] if "LIBS" in cCfg else ""
        iorRun = {"-a" : [], "-b" : [], "-t" : [], "-J" : [], "OTHERS" : ""}
        if "RUN" in iorCfg:
            rCfg = iorCfg["RUN"]
            iorRun["-a"] = rCfg["-a"].split() if "-a" in rCfg else []
            iorRun["-b"] = rCfg["-b"].split() if "-b" in rCfg else []
            iorRun["-t"] = rCfg["-t"].split() if "-t" in rCfg else []
            iorRun["-J"] = rCfg["-J"].split() if "-J" in rCfg else []
            iorRun["OTHER"] = rCfg["OTHER"].split() if "OTHER" in rCfg else []
        if iorURL:
            print("Configuring IOR benchmark ...")
            iorLID = iorCfg["LOGID"].split() if "LOGID" in iorCfg else []
            args.bmLs.append(iorBench(args, iorURL, iorConfig, iorRun, iorLID))

def readGFBenchmarkConfig(args, bCfg):
    """Read GFlops benchmarks from the configuration file"""
    if "HPLINPACK" in bCfg:
        hplCfg = bCfg["HPLINPACK"]
        blasDic = {"URL" : None, "VERSION" : None, "LIBBLAS" : None}
        if "BLAS" in hplCfg:
            blasCfg = hplCfg["BLAS"]
            if "BUILDBLAS" in blasCfg:
                bldBlasCfg = blasCfg["BUILDBLAS"]
                blasDic["URL"] = bldBlasCfg["URL"] if "URL" in bldBlasCfg else None
                blasDic["VERSION"] = bldBlasCfg["VERSION"] if "VERSION" in bldBlasCfg else None
            if "USEBLAS" in blasCfg:
                useBlasCfg = blasCfg["USEBLAS"]
                blasDic["LIBBLAS"] = useBlasCfg["LIBBLAS"] if "LIBBLAS" in useBlasCfg else None
        hplURL = hplCfg["URL"] if "URL" in hplCfg else None
        hplVersion = hplCfg["VERSION"] if "VERSION" in hplCfg else None
        if ((blasDic["URL"] and blasDic["VERSION"]) or blasDic["LIB"]) and hplURL and hplVersion:
            print("Configuring HPLinpack benchmark ...")
            hplLID = hplCfg["LOGID"].split() if "LOGID" in hplCfg else []
            args.bmLs.append(hplBench(args, blasDic, hplURL, hplVersion, hplLID))
    if "HYDRO" in bCfg:
        hydroCfg = bCfg["HYDRO"]
        hydroURL = hydroCfg["URL"] if "URL" in hydroCfg else None
        hydroBuild = {}
        hydroBuild["CFLAGS_MPI"] = hydroCfg["CFLAGS_MPI"] if "CFLAGS_MPI" in hydroCfg else ""
        hydroBuild["LDFLAGS_MPI"] = hydroCfg["LDFLAGS_MPI"] if "LDFLAGS_MPI" in hydroCfg else ""
        hydroBuild["LIBNUMA"] = hydroCfg["LIBNUMA"] if "LIBNUMA" in hydroCfg else ""
        hydroRun = {}
        hydroRun["NXY"] = hydroCfg["NXY"] if "NXY" in hydroCfg else "100"
        hydroRun["NXYSTEP"] = hydroCfg["NXYSTEP"] if "NXYSTEP" in hydroCfg else "50"
        hydroRun["TEND"] = hydroCfg["TEND"] if "TEND" in hydroCfg else "100"
        if hydroURL:
            print("Configuring hydro benchmark ...")
            hydroLID = hydroCfg["LOGID"].split() if "LOGID" in hydroCfg else []
            args.bmLs.append(hydroBench(args, hydroURL, hydroBuild, hydroRun, hydroLID))
    if "NAS" in bCfg:
        nasCfg = bCfg["NAS"]
        nasURL = nasCfg["URL"] if "URL" in nasCfg else None
        nasVersion = nasCfg["VERSION"] if "VERSION" in nasCfg else None
        nasMPIID = nasCfg["MPIID"] if "MPIID" in nasCfg else ""
        nasVec = True if "VEC" in nasCfg and nasCfg["VEC"] == "YES" else False
        if nasURL and nasVersion:
            print("Configuring NAS benchmark ...")
            args.bmLs.append(nasBench(args, nasURL, nasVersion, nasMPIID, nasVec))

def readUseCaseConfig(args, jsCfg):
    """Read use case from the configuration file"""
    print("Configuring use case mode ...")
    readUseCasePfmConfig(args, jsCfg)
    readUseCaseEvtConfig(args, jsCfg)
    readUseCaseObjConfig(args, jsCfg)

def readUseCasePfmConfig(args, jsCfg):
    """Read pfm from the use case part of the configuration file"""
    args.pfm4Vn = "4.7.0"
    args.pfm4URL = ""
    if "UCASE" in jsCfg:
        if "LIBPFM4" in jsCfg["UCASE"]:
            pfm4Cfg = jsCfg["UCASE"]["LIBPFM4"]
            pfm4URL = pfm4Cfg["URL"] if "URL" in pfm4Cfg else None
            pfm4Vn = pfm4Cfg["VERSION"] if "VERSION" in pfm4Cfg else None
            if pfm4URL and pfm4Vn:
                print("Configuring libpfm4", pfm4Vn, ":", pfm4URL, "...")
                args.pfm4Vn = pfm4Vn
                args.pfm4URL = pfm4URL

def readUseCaseEvtConfig(args, jsCfg):
    """Read events from the use case part of the configuration file"""
    if "UCASE" in jsCfg:
        readUseCasePerfRpEvtConfig(args, jsCfg["UCASE"])
        readUseCasePerfTpEvtConfig(args, jsCfg["UCASE"])
        readUseCasePerfStEvtConfig(args, jsCfg["UCASE"])

def readUseCasePerfRpEvtConfig(args, uCfg):
    """Read perf-record/perf-report events from the use case part of the configuration file"""
    args.perfRpEvt = []
    args.pfm4RpEvt = []
    if "PERF-REPORT" in uCfg:
        perfCfg = uCfg["PERF-REPORT"]
        if "PERFLIST" in perfCfg:
            print("Configuring perf-report with perf-list :", perfCfg["PERFLIST"])
            args.perfRpEvt = perfCfg["PERFLIST"].split()
        if "LIBPFM4" in perfCfg:
            print("Configuring perf-report with libpfm4 :", perfCfg["LIBPFM4"])
            args.pfm4RpEvt = perfCfg["LIBPFM4"].split()

def readUseCasePerfTpEvtConfig(args, uCfg):
    """Read perf-top events from the use case part of the configuration file"""
    args.perfTpEvt = []
    args.pfm4TpEvt = []
    if "PERF-TOP" in uCfg:
        perfCfg = uCfg["PERF-TOP"]
        if "PERFLIST" in perfCfg:
            print("Configuring perf-top with perf-list :", perfCfg["PERFLIST"])
            args.perfTpEvt = perfCfg["PERFLIST"].split()
        if "LIBPFM4" in perfCfg:
            print("Configuring perf-top with libpfm4 :", perfCfg["LIBPFM4"])
            args.pfm4TpEvt = perfCfg["LIBPFM4"].split()

def readUseCasePerfStEvtConfig(args, uCfg):
    """Read perf-stat events from the use case part of the configuration file"""
    args.perfStGFEvt = []
    args.perfStCMEvt = []
    args.pfm4StGFEvt = []
    args.pfm4StCMEvt = []
    if "PERF-STAT" in uCfg:
        perfCfg = uCfg["PERF-STAT"]
        if "GFLOPS" in perfCfg:
            gfCfg = perfCfg["GFLOPS"]
            if "PERFLIST" in gfCfg:
                print("Configuring perf-stat for GFlops with perf-list :", gfCfg["PERFLIST"])
                args.perfStGFEvt = gfCfg["PERFLIST"].split()
            if "LIBPFM4" in gfCfg:
                print("Configuring perf-stat for GFlops with libpfm4 :", gfCfg["LIBPFM4"])
                args.pfm4StGFEvt = gfCfg["LIBPFM4"].split()
        if "CACHEMISSES" in perfCfg:
            cmCfg = perfCfg["CACHEMISSES"]
            if "PERFLIST" in cmCfg:
                print("Configuring perf-stat for cache misses with perf-list :", cmCfg["PERFLIST"])
                args.perfStCMEvt = cmCfg["PERFLIST"].split()
            if "LIBPFM4" in cmCfg:
                print("Configuring perf-stat for cache misses with libpfm4 :", cmCfg["LIBPFM4"])
                args.pfm4StCMEvt = cmCfg["LIBPFM4"].split()

def readUseCaseObjConfig(args, jsCfg):
    """Read objdump from the use case part of the configuration file"""
    args.oDump = []
    if "UCASE" in jsCfg:
        if "OBJDUMP" in jsCfg["UCASE"]:
            args.oDump = jsCfg["UCASE"]["OBJDUMP"].split()

def readGraphicConfig(args, pCfg):
    """Read graphic features from the configuration file"""
    args.figWidth = None
    args.figHeight = None
    args.dpi = None
    args.fontSize = None
    args.legendFontSize = None
    if "FIGWIDTH" in pCfg and float(pCfg["FIGWIDTH"]) > 0:
        print("Configuring plot with figure width", pCfg["FIGWIDTH"], "...")
        args.figWidth = float(pCfg["FIGWIDTH"])
    if "FIGHEIGHT" in pCfg and float(pCfg["FIGHEIGHT"]) > 0:
        print("Configuring plot with figure height", pCfg["FIGHEIGHT"], "...")
        args.figHeight = float(pCfg["FIGHEIGHT"])
    if "DPI" in pCfg and int(pCfg["DPI"]) > 0:
        print("Configuring plot with dpi", pCfg["DPI"], "...")
        args.dpi = int(pCfg["DPI"])
    if "FONTSIZE" in pCfg and int(pCfg["FONTSIZE"]) > 0:
        print("Configuring plot with font size", pCfg["FONTSIZE"], "...")
        args.fontSize = int(pCfg["FONTSIZE"])
        args.legendFontSize = args.fontSize
    if "LEGENDFONTSIZE" in pCfg and int(pCfg["LEGENDFONTSIZE"]) > 0:
        print("Configuring plot with legend font size", pCfg["LEGENDFONTSIZE"], "...")
        args.legendFontSize = int(pCfg["LEGENDFONTSIZE"])

def readRLMConfig(args, pCfg):
    """Read roof line model features from the configuration file"""
    if "RLM" in pCfg:
        rlmCfg = pCfg["RLM"]
        if "XMIN" in rlmCfg and rlmCfg["XMIN"] != "":
            print("Configuring roof line model with xmin", rlmCfg["XMIN"], "...")
            args.rlmXMin = float(rlmCfg["XMIN"])
        if "XMAX" in rlmCfg and rlmCfg["XMAX"] != "":
            print("Configuring roof line model with xmax", rlmCfg["XMAX"], "...")
            args.rlmXMax = float(rlmCfg["XMAX"])
        if "YMAX" in rlmCfg and rlmCfg["YMAX"] != "":
            print("Configuring roof line model with ymax", rlmCfg["YMAX"], "...")
            args.rlmYMax = float(rlmCfg["YMAX"])
        if "ANNOTATIONFONTSIZE" in rlmCfg and rlmCfg["ANNOTATIONFONTSIZE"] != "":
            print("Configuring roof line model with annotation font size", rlmCfg["ANNOTATIONFONTSIZE"], "...")
            args.rlmAFS = int(rlmCfg["ANNOTATIONFONTSIZE"])

def readPlotConfig(args, jsCfg):
    """Read plot from the configuration file"""
    print("Configuring plot mode ...")
    args.rlmXMin = None
    args.rlmXMax = None
    args.rlmYMax = None
    args.rlmAFS = None
    args.ptMinPct = 1.
    args.ptExclude = []
    args.prMinPct = 1.
    args.prExclude = []
    args.pltLogInclude = None
    args.pltLogExclude = None
    if "PLOT" in jsCfg:
        pCfg = jsCfg["PLOT"]
        readGraphicConfig(args, pCfg)
        readRLMConfig(args, pCfg)
        if "PERF-TOP" in pCfg:
            ptCfg = pCfg["PERF-TOP"]
            if "MINPERCENTAGE" in ptCfg and ptCfg["MINPERCENTAGE"] != "":
                print("Configuring perf-top plot with minimum percentage", ptCfg["MINPERCENTAGE"], "...")
                args.ptMinPct = float(ptCfg["MINPERCENTAGE"])
            if "EXCLUDE" in ptCfg and ptCfg["EXCLUDE"] != "":
                print("Configuring perf-top plot with exclude filter", ptCfg["EXCLUDE"], "...")
                args.ptExclude = ptCfg["EXCLUDE"].split()
        if "PERF-REPORT" in pCfg:
            prCfg = pCfg["PERF-REPORT"]
            if "MINPERCENTAGE" in prCfg and prCfg["MINPERCENTAGE"] != "":
                print("Configuring perf-report plot with minimum percentage", prCfg["MINPERCENTAGE"], "...")
                args.prMinPct = float(prCfg["MINPERCENTAGE"])
            if "EXCLUDE" in prCfg and prCfg["EXCLUDE"] != "":
                print("Configuring perf-report plot with exclude filter", prCfg["EXCLUDE"], "...")
                args.prExclude = prCfg["EXCLUDE"].split()
        if "LOGID_INCLUDE" in pCfg and pCfg["LOGID_INCLUDE"] != "":
            print("Configuring plot with include log filter", pCfg["LOGID_INCLUDE"], "...")
            args.pltLogInclude = pCfg["LOGID_INCLUDE"].split()
        if "LOGID_EXCLUDE" in pCfg and pCfg["LOGID_EXCLUDE"] != "":
            print("Configuring plot with exclude log filter", pCfg["LOGID_EXCLUDE"], "...")
            args.pltLogExclude = pCfg["LOGID_EXCLUDE"].split()
