"""Plot the roof line model"""

# Import modules

from __future__ import print_function

from pyc.plot import plot

# Functions

def plotRLM(lsUCS, args):
    """Plot the roof line model"""
    maxGFlops, maxRAMMBs = analysingBenchmarkLogs(args)
    if maxGFlops <= 0. or maxRAMMBs <= 0.:
        return
    print("Plotting the roof line model", end="")
    maxFlops = maxGFlops * 1000. ** 3
    maxBs = maxRAMMBs * 1024. ** 2
    ridgePt = (maxFlops / maxBs, maxGFlops)
    print(": ridge point = (", "%11.3f" % ridgePt[0], ",", "%11.3f" % ridgePt[1], ")", "...")
    groundPt = (0., 0.)
    xScope = [ucs[0] / ucs[1] for ucs in lsUCS]
    xStart = 0. if len(lsUCS) == 0 else 0.7 * min([groundPt[0], min(xScope)])
    if xStart < ridgePt[0]:
        xStart = 0.
    if args.rlmXMin:
        xStart = args.rlmXMin
    xStop = 2. * ridgePt[0] if len(lsUCS) == 0 else 1.3 * max([ridgePt[0], max(xScope)])
    if args.rlmXMax:
        xStop = args.rlmXMax
    endPt = (xStop, ridgePt[1])
    import matplotlib.pyplot
    matplotlib.pyplot.suptitle("roof line model")
    axis = matplotlib.pyplot.subplot(1, 1, 1)
    xRLM = [groundPt[0], ridgePt[0], endPt[0]]
    yRLM = [groundPt[1], ridgePt[1], endPt[1]]
    axis.plot(xRLM, yRLM, marker="o", linewidth=2, color="r", label="roof line model")
    annotateRLM(ridgePt, args, axis, maxRAMMBs, maxGFlops)
    plotRLMUseCase(lsUCS, axis, args)
    axis.set_xlim([xStart, xStop])
    ymax = args.rlmYMax if args.rlmYMax else (1.1 + len(lsUCS) * 0.1) * endPt[1]
    axis.set_ylim([0., ymax])
    axis.set_xlabel("Flop/Byte")
    axis.set_ylabel("GFlops")
    axis.legend(loc="upper right", scatterpoints=1, bbox_to_anchor=(1.1, 1.1))
    print("") # Output separator for clarity
    p = plot(args)
    p.plotOrSave("roofLineModel")

def analysingBenchmarkLogs(args):
    """Analyse benchmark logs to get maximum values"""
    print("Analysing benchmark logs ...")
    maxGF, maxRAMMBs = 0., 0.
    for bm in args.bmLs:
        bMc = bm.getMetric()
        if bm.getType() == "GF" and bMc > maxGF:
            maxGF = bMc
        if bm.getType() == "RAM-MB/s" and bMc > maxRAMMBs:
            maxRAMMBs = bMc
    print("") # Output separator for clarity
    return maxGF, maxRAMMBs

def plotRLMUseCase(lsUCS, axis, args):
    """Plot use cases on the roof line model"""
    for ucs in lsUCS:
        x = ucs[0] / ucs[1]
        y = ucs[0] / (1000. ** 3)
        axis.scatter(x, y, color=ucs[2], marker=ucs[3], label=ucs[4], linewidth=2)
        if args.annotate:
            msg = "%11.3f MB/s\n%11.3f GFlops\n%11.3f sec"
            if args.rlmAFS:
                axis.annotate(msg % (ucs[1] / (1024. ** 2), y, ucs[5]), xy=(x, y), size=args.rlmAFS)
            else:
                axis.annotate(msg % (ucs[1] / (1024. ** 2), y, ucs[5]), xy=(x, y))

def annotateRLM(ridgePt, args, axis, maxRAMMBs, maxGFlops):
    """Annotate the ridge point of the roof line model"""
    msg = "%11.3f MB/s\n%11.3f GFlops"
    xy = (0.75 * ridgePt[0], 1.05 * ridgePt[1])
    if args.rlmAFS:
        axis.annotate(msg % (maxRAMMBs, maxGFlops), xy=ridgePt, xytext=xy, size=args.rlmAFS)
    else:
        axis.annotate(msg % (maxRAMMBs, maxGFlops), xy=ridgePt, xytext=xy)
