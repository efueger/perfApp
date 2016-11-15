usage: perfApp.py [-h] [-f] [-c J] [-d] [-n N] [-s]

                  {check,bench,ucase,plot} ...

perfApp helps improving performances of (compute or bandwidth bounded) applications on each specific machine
or architecture: it runs several benchmarks to feature the architecture, generates both statistical report
and instantaneous time line, and plots a roof line model to "see" performances

positional arguments:

  {check,bench,ucase,plot}

    check               check configuration, HW events and registers before bench/ucase

    bench               run benchmarks to get features of the given machine/architecture

    ucase               run use cases to get metrics from the application

    plot                plot benchmark/use case results (filter with json LOGID_INCLUDE/LOGID_EXCLUDE)

optional arguments:

    -h, --help            show this help message and exit

    -f, --force           force re-run even if previous log exists

    -c J, --config J      json configuration file (J defaults to ./jsn/perfApp.json)

    -d, --dlonly          download only (don't build, don't run)

    -n N, --nproc N       specify max number of processus

    -s, --stop            stop if build or run error occur

notes:

  1. application instrumentation (which may be complex) reduces to adding -g to compile flags

  2. this tool is based on linux perf tools: run as root, or allow users to run perf (not paranoid mode)

  3. json's enable to customise BUILDTIME, RUNTIME, BENCH, UCASE, PLOT (use LOGID for later plot filtering)

  4. forecast disk space, the tmp directory (created to handle benchmarks and logs) may be big (10-100 GB)

first, know about HW events your architecture can support, and, tune your json configuration accordingly:

    ~>./perfApp.py check;

then, run benchmarks (play with bench -s -m):

    ~>./perfApp.py bench -s 0.01 -q -m; ./perfApp.py bench -q; ./perfApp.py bench -s 1.0 -q;

    ~>./perfApp.py plot -b -v;

then, run use cases:

    ~>sudo ./perfApp.py ucase -s -r -t -w -v;

    ~>./perfApp.py plot -u -r -t -w -a -v;

then, plot a roof line model to see how your application fits your architecture:

    ~>./perfApp.py plot -m pfa*;
finally, generate use cases from benchmarks to compare them to your application on a plot:

    ~>./perfApp.py bench -u; sudo ./perfApp.py ucase -u pfb* -s;

    ~>./perfApp.py plot -m pf*
