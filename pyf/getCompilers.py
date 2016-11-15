"""Manage compilers"""

from __future__ import print_function

import sys
import distutils.spawn

def getCompilers(args):
    """Get and return compilers"""
    cpl = {}
    cpl["CC"] = distutils.spawn.find_executable(args.CC if args.CC else "gcc")
    cpl["FC"] = distutils.spawn.find_executable(args.FC if args.FC else "gfortran")
    cpl["MPICC"] = distutils.spawn.find_executable(args.MPICC if args.MPICC else "mpicc")
    cpl["MPIF77"] = distutils.spawn.find_executable(args.MPIF77 if args.MPIF77 else "mpif77")
    cpl["MPIF90"] = distutils.spawn.find_executable(args.MPIF90 if args.MPIF90 else "mpif90")
    cpl["OMPFLAGS"] = args.OMPFLAGS if args.OMPFLAGS else "-fopenmp -fopenmp-simd"
    cpl["FLAGS"] = "-O3 -g -march=native -funroll-loops -ffast-math -ftree-vectorize -fopt-info-optall=gnu.txt"
    cpl["FLAGS"] += " -mcmodel=large"
    if args.FLAGS:
        cpl["FLAGS"] = args.FLAGS
    cpl["NOOPTFLAGS"] = args.NOOPTFLAGS if args.NOOPTFLAGS else "-O2 -march=native -mcmodel=large"
    cpl["LINKFLAGS"] = args.LINKFLAGS if args.LINKFLAGS else "-mcmodel=large"
    if args.intel:
        cpl["CC"] = distutils.spawn.find_executable("icc")
        cpl["FC"] = distutils.spawn.find_executable("ifort")
        cpl["MPICC"] = distutils.spawn.find_executable("mpiicc")
        cpl["MPIF77"] = distutils.spawn.find_executable("mpiifort")
        cpl["MPIF90"] = distutils.spawn.find_executable("mpiifort")
        cpl["OMPFLAGS"] = args.OMPFLAGS if args.OMPFLAGS else "-qopenmp"
        cpl["FLAGS"] = "-O3 -g -xHost -qopt-report=5 -qopt-report-phase=vec -qopt-report-file=intel.txt"
        cpl["FLAGS"] += " -mcmodel=large"
        if args.FLAGS:
            cpl["FLAGS"] = args.FLAGS
        cpl["NOOPTFLAGS"] = args.NOOPTFLAGS if args.NOOPTFLAGS else "-O2 -xHost -mcmodel=large"
        cpl["LINKFLAGS"] = args.LINKFLAGS if args.LINKFLAGS else "-nofor-main -mcmodel=large"

    cpl["MPIFC"] = cpl["MPIF90"] if cpl["MPIF90"] else cpl["MPIF77"]
    cpl["FLAGS"] += " " + cpl["OMPFLAGS"]
    cpl["LINKFLAGS"] += " " + cpl["OMPFLAGS"]

    for k in ["CC", "FC", "MPICC", "MPIF77", "MPIF90", "MPIFC", "OMPFLAGS", "FLAGS", "NOOPTFLAGS", "LINKFLAGS"]:
        print(k, "=", cpl[k])
    if not cpl["CC"] or not cpl["MPICC"] or not cpl["FC"] or not cpl["MPIFC"]:
        sys.exit("ERROR: can not find C/Fortran compilers")
    return cpl
