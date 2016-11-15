"""Manage the parser"""

# Import modules

import argparse

from pyf.parserCB import checkCB
from pyf.parserCB import benchCB
from pyf.parserCB import ucaseCB
from pyf.parserCB import plotCB

# Functions

# If getParser is modified, update README.md with:
# ~>(./perfApp.py -h | sed -e 's/^  /\n  /' -e 's/^then/\nthen/' -e 's/  ~>/    ~>/' -e 's/  -/    -/') > README.md
def getParser():
    """Get the parser"""
    d = "perfApp helps improving performances of (compute or bandwidth bounded) applications on each specific machine\n"
    d += "or architecture: it runs several benchmarks to feature the architecture, generates both statistical report\n"
    d += "and instantaneous time line, and plots a roof line model to \"see\" performances"
    e = "notes:\n"
    e += "  1. application instrumentation (which may be complex) reduces to adding -g to compile flags\n"
    e += "  2. this tool is based on linux perf tools: run as root, or allow users to run perf (not paranoid mode)\n"
    e += "  3. json's enable to customise BUILDTIME, RUNTIME, BENCH, UCASE, PLOT (use LOGID for later plot filtering)\n"
    e += "  4. forecast disk space, the tmp directory (created to handle benchmarks and logs) may be big (10-100 GB)\n"
    e += "\n"
    e += "first, know about HW events your architecture can support, and, tune your json configuration accordingly:\n"
    e += "  ~>./perfApp.py check;\n"
    e += "then, run benchmarks (play with bench -s -m):\n"
    e += "  ~>./perfApp.py bench -s 0.01 -q -m; ./perfApp.py bench -q; ./perfApp.py bench -s 1.0 -q;\n"
    e += "  ~>./perfApp.py plot -b -v;\n"
    e += "then, run use cases:\n"
    e += "  ~>sudo ./perfApp.py ucase -s -r -t -w -v;\n"
    e += "  ~>./perfApp.py plot -u -r -t -w -a -v;\n"
    e += "then, plot a roof line model to see how your application fits your architecture:\n"
    e += "  ~>./perfApp.py plot -m pfa*;\n"
    e += "finally, generate use cases from benchmarks to compare them to your application on a plot:\n"
    e += "  ~>./perfApp.py bench -u; sudo ./perfApp.py ucase -u pfb* -s;\n"
    e += "  ~>./perfApp.py plot -m pf*"
    parser = argparse.ArgumentParser(description=d, epilog=e, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("-f", "--force", action="store_true", help="force re-run even if previous log exists")
    jsDef = "./jsn/perfApp.json"
    jsHelp = "json configuration file (J defaults to " + jsDef + ")"
    parser.add_argument("-c", "--config", type=argparse.FileType("r"), default=jsDef, help=jsHelp, metavar="J")
    parser.add_argument("-d", "--dlonly", action="store_true", help="download only (don't build, don't run)")
    parser.add_argument("-n", "--nproc", type=int, default=0, help="specify max number of processus", metavar="N")
    parser.add_argument("-s", "--stop", action="store_true", help="stop if build or run error occur")
    addSubParsers(parser)
    return parser

def addSubParsers(parser):
    """Add subparsers to the main parser"""
    subParser = parser.add_subparsers(dest="mode")
    addCheckSubParser(subParser)
    addBenchSubParser(subParser)
    addUCaseSubParser(subParser)
    addPlotSubParser(subParser)

def addCheckSubParser(subParser):
    """Add check subparser to the main parser"""
    d = "check configuration, HW events and registers before bench/ucase"
    checkParser = subParser.add_parser("check", description=d, help=d, formatter_class=argparse.RawTextHelpFormatter)
    rlmHelp = "for each use case, check roof line model plot attributes"
    checkParser.add_argument("-r", "--rlm", action="store_true", help=rlmHelp)
    checkParser.set_defaults(func=checkCB)

def addBenchSubParser(subParser):
    """Add bench subparser to the main parser"""
    d = "run benchmarks to get features of the given machine/architecture"
    benchParser = subParser.add_parser("bench", description=d, help=d, formatter_class=argparse.RawTextHelpFormatter)
    benchParser.set_defaults(func=benchCB)

    benchParser.add_argument("-i", "--intel", action="store_true", help="use intel compilers to build benchmarks")
    szHelp = "number of GB used to size benchmark problems (S defaults to 0.1)\n"
    szHelp += "depending on benchmarks, this size may be used (HPL, ...) or not (NAS, ...)"
    benchParser.add_argument("-s", "--size", type=float, default=0.1, help=szHelp, metavar="S")
    bhHelp = "run benchmark B (B defaults to All)"
    benchParser.add_argument("-b", "--bench", type=str, default="All", const="All", nargs="?", help=bhHelp, metavar="B")
    benchParser.add_argument("-q", "--quick", action="store_true", help="run a quick version of all benchmarks")
    benchParser.add_argument("-m", "--more", action="store_true", help="run more benchmark configurations")
    ucHelp = "generate a use case (./tmp/usc/pfb*) from the best benchmark run"
    benchParser.add_argument("-u", "--ucase", action="store_true", help=ucHelp)

def addUCaseSubParser(subParser):
    """Add ucase subparser to the main parser"""
    d = "run use cases to get metrics from the application"
    ucaseParser = subParser.add_parser("ucase", description=d, help=d, formatter_class=argparse.RawTextHelpFormatter)
    ucaseParser.set_defaults(func=ucaseCB)

    mpHelp = "multiplexing perf event frequency (M defaults to 1000)"
    ucaseParser.add_argument("-m", "--mp", type=int, default=1000, const=1000, nargs="?", help=mpHelp, metavar="M")
    uscHelp = "run ./usc/U use cases (U defaults to *)\n"
    uscHelp += "customise U with ./usc/U/usc.json"
    uscHelp += " (EXE=/relative/path/to/exe, MPI=-1 for sequential, add \"|\" in ARGS for weak scaling)\n"
    uscHelp += "if needed, prepare the run with prep.sh (build: add -g to get symbols when running -r -t, preprocess)\n"
    uscHelp += "if needed, customise run with run.sh (export, module load)\n"
    ucaseParser.add_argument("-u", "--uc", type=str, default="*", const="*", nargs="?", help=uscHelp, metavar="U")
    staHelp = "if added to -u, generate use case statistics with perf-stat\n"
    staHelp += "perf-stat metrics (GFLOPS, CACHEMISSES) can be customised in the json file (UCASE, PERF-STAT)"
    ucaseParser.add_argument("-s", "--stat", action="store_true", help=staHelp)
    repHelp = "if added to -u, generate use case report with perf-record/perf-report\n"
    repHelp += "perf-report metrics can be customised in the json file (UCASE, PERF-REPORT)"
    ucaseParser.add_argument("-r", "--report", action="store_true", help=repHelp)
    topHelp = "if added to -u, generate use case profiles with perf-top (sampled every S seconds, S defaults to 10)\n"
    topHelp += "perf-top metrics can be customised in the json file (UCASE, PERF-TOP)"
    ucaseParser.add_argument("-t", "--top", default=False, const=10, nargs="?", help=topHelp, metavar="S")
    watHelp = "if added to -t, watch over use case memory/cpu usage"
    ucaseParser.add_argument("-w", "--watch", action="store_true", help=watHelp)
    ucaseParser.add_argument("-v", "--verbose", action="store_true", help="verbose, detail use case runs")

def addPlotSubParser(subParser):
    """Add plot subparser to the main parser"""
    d = "plot benchmark/use case results (filter with json LOGID_INCLUDE/LOGID_EXCLUDE)"
    plotParser = subParser.add_parser("plot", description=d, help=d, formatter_class=argparse.RawTextHelpFormatter)
    plotParser.set_defaults(func=plotCB)

    bhHelp = "plot results of benchmark B (B defaults to All)"
    plotParser.add_argument("-b", "--bench", default=False, const="All", nargs="?", help=bhHelp, metavar="B")
    uscHelp = "plot ./usc/U use case (watched) information (U defaults to *)"
    plotParser.add_argument("-u", "--uc", default=False, const="*", nargs="?", help=uscHelp, metavar="U")
    repHelp = "if added to -u, plot use case profiles generated by perf-report"
    plotParser.add_argument("-r", "--report", action="store_true", help=repHelp)
    topHelp = "if added to -u, plot use case profiles generated by perf-top with ucase -t (T defaults to \"n=\")"
    plotParser.add_argument("-t", "--top", default=False, const="n=", nargs="?", help=topHelp, metavar="T")
    watHelp = "if added to -u, plot use case memory/cpu usage history with ucase -w (W defaults to \"n=\")"
    plotParser.add_argument("-w", "--watch", default=False, const="n=", nargs="?", help=watHelp, metavar="W")
    rlmHelp = "plot the roof line model with ./usc/U use case spots (no spot if U not specified)\n"
    rlmHelp += "use case plot attributes must be specified in ./usc/U/usc.json (COLOR, MARKER, LABEL)\n"
    rlmHelp += "documentation can be found here: www.eecs.berkeley.edu/~waterman/papers/roofline.pdf\n"
    rlmHelp += "if a use case is before/after the ridge point, the use case is bandwidth/compute bounded"
    plotParser.add_argument("-m", "--rlm", default=False, const=-1, nargs="?", help=rlmHelp, metavar="U")
    plotParser.add_argument("-a", "--annotate", action="store_true", help="annotate plots")
    plotParser.add_argument("-v", "--verbose", action="store_true", help="verbose before plot, detail plotted data")
    svHelp = "save plot as png in ./tmp/plt (do not plot)\n"
    svHelp += "plot features (font size, dpi, ...) can be customised in the json file (PLOT)"
    plotParser.add_argument("-s", "--save", action="store_true", help=svHelp)
