"""This module exports the plot class"""

from __future__ import print_function

import os
import matplotlib
import matplotlib.pyplot
import numpy

class plot(object):
    """Plot class designed to handle plots"""

    def __init__(self, args):
        """Initialize plot class instance"""
        self.args = args
        self.colors = None
        self.xTickStr = False
        self.yTickStr = False
        self.xTickInt = False
        self.yTickInt = False
        matplotlib.rcParams["xtick.major.pad"] = 8 # Add space between tick labels and axis
        matplotlib.rcParams["ytick.major.pad"] = 8 # Add space between tick labels and axis
        if self.args.figWidth and self.args.figHeight: # Figure size: (width, height) in inches
            matplotlib.rcParams["figure.figsize"] = self.args.figWidth, self.args.figHeight
        if self.args.fontSize: # Increase font size to get readable plots
            matplotlib.rcParams["font.size"] = self.args.fontSize
        if self.args.legendFontSize:
            matplotlib.rcParams["legend.fontsize"] = self.args.legendFontSize
        self.save = True if hasattr(self.args, "save") and self.args.save else False
        if self.save:
            if not os.path.exists(self.args.plt):
                os.makedirs(self.args.plt)

    @staticmethod
    def __setLogScale__(axis, values, xyz):
        """Set log scale"""
        values = numpy.log10(values)
        powers = [int(v) for v in values]
        powers = list(set(powers)) # Remove duplicates
        powers.remove(min(powers)) # Remove mininum value
        tickLabels = ["10e%d" % p for p in powers]
        if xyz == "x":
            axis.set_xticks(powers)
            axis.set_xticklabels(tickLabels)
        if xyz == "y":
            axis.set_yticks(powers)
            axis.set_yticklabels(tickLabels)
        return values

    def __get3DMeshGrid__(self, mKeys, sKeys, axis):
        """Get mesh grid for 3D plot"""
        if not self.xTickStr and (abs(min(mKeys)) > 1.e-12 and 1000 * min(mKeys) < max(mKeys)):
            mKeys = self.__setLogScale__(axis, mKeys, "x")
        if not self.yTickStr and (abs(min(sKeys)) > 1.e-12 and 1000 * min(sKeys) < max(sKeys)):
            sKeys = self.__setLogScale__(axis, sKeys, "y")
        mGrid, sGrid = None, None
        if self.xTickStr and not self.yTickStr:
            mGrid, sGrid = numpy.meshgrid(numpy.arange(len(mKeys)), sKeys)
            axis.set_xticks(numpy.arange(len(mKeys)))
            axis.set_xticklabels(mKeys, ha="left")
        elif not self.xTickStr and self.yTickStr:
            mGrid, sGrid = numpy.meshgrid(mKeys, numpy.arange(len(sKeys)))
            axis.set_yticks(numpy.arange(len(sKeys)))
            axis.set_yticklabels(sKeys, ha="right")
        elif self.xTickStr and self.yTickStr:
            mGrid, sGrid = numpy.meshgrid(numpy.arange(len(mKeys)), numpy.arange(len(sKeys)))
            axis.set_xticks(numpy.arange(len(mKeys)))
            axis.set_yticks(numpy.arange(len(sKeys)))
            axis.set_xticklabels(mKeys, ha="left")
            axis.set_yticklabels(sKeys, ha="right")
        else:
            mGrid, sGrid = numpy.meshgrid(mKeys, sKeys)
            if self.xTickInt:
                axis.set_xticks(mKeys)
            if self.yTickInt:
                axis.set_yticks(sKeys)
        return mGrid, sGrid

    @staticmethod
    def __get3DPlotData__(mKeys, sKeys, plotDic, s):
        """get 3D data to plot"""
        plotData = numpy.zeros((len(sKeys), len(mKeys)))
        for idxMK, mK in enumerate(mKeys):
            for idxSK, sK in enumerate(sKeys):
                if mK in plotDic and sK in plotDic[mK] and s in plotDic[mK][sK]:
                    plotData[idxSK][idxMK] = plotDic[mK][sK][s]
        return plotData

    @staticmethod
    def __get2DPlotMax__(plotData, mKeys, steps):
        """Get the maximum on a 2D plot"""
        maxVal = -1.
        maxMKey = None
        for mK in mKeys:
            for s in steps:
                if mK in plotData and s in plotData[mK]:
                    if float(plotData[mK][s]) > maxVal:
                        maxVal = float(plotData[mK][s])
                        maxMKey = mK
        return maxMKey, maxVal

    def __get3DPlotMax__(self, plotData, mKeys, sKeys, steps):
        """Get the maximum on a 3D plot"""
        maxVal = -1.
        maxMKey = None
        maxSKey = None
        for idxMK, mK in enumerate(mKeys):
            for s in steps:
                for idxSK, sK in enumerate(sKeys):
                    if mK in plotData and sK in plotData[mK] and s in plotData[mK][sK]:
                        if float(plotData[mK][sK][s]) > maxVal:
                            maxVal = float(plotData[mK][sK][s])
                            maxMKey = idxMK if self.xTickStr else mK
                            maxSKey = idxSK if self.yTickStr else sK
        return maxMKey, maxSKey, maxVal

    def __annotateMax__(self, plotData, mKeys, sKeys, steps, axis):
        """Annotate the maximum on a plot"""
        if not self.args.annotate:
            return
        maxVal = 0.
        maxMKey = None
        maxSKey = None
        if sKeys:
            maxMKey, maxSKey, maxVal = self.__get3DPlotMax__(plotData, mKeys, sKeys, steps)
            if maxMKey and maxSKey:
                axis.text(maxMKey, maxSKey, 1.02 * maxVal, "%.2f" % maxVal)
        else:
            maxMKey, maxVal = self.__get2DPlotMax__(plotData, mKeys, steps)
            if maxMKey:
                axis.annotate("%.2f" % maxVal, xy=(maxMKey, maxVal), xytext=(maxMKey, 1.02 * maxVal))

    @staticmethod
    def getAutoColor(idx, n):
        """Create automatic color"""
        rgb = float(idx)/float(n)
        col = (1 - rgb, rgb, rgb)
        if idx % 3 == 1:
            col = (rgb, 1 - rgb, rgb)
        if idx % 3 == 2:
            col = (rgb, rgb, 1 - rgb)
        return col

    def plotOrSave(self, plotName):
        """Plot or save a graph"""
        if self.save:
            png = os.path.join(self.args.plt, plotName + ".png")
            if self.args.force:
                if os.path.exists(png):
                    os.remove(png)
            if not os.path.exists(png):
                if self.args.dpi:
                    matplotlib.pyplot.savefig(png, dpi=self.args.dpi)
                else:
                    matplotlib.pyplot.savefig(png)
                matplotlib.pyplot.close() # Close the (current) saved figure
        else:
            matplotlib.pyplot.show()

    def setPlotAttr(self, colors=None, xTickStr=False, yTickStr=False, xTickInt=False, yTickInt=False):
        """Set plot attributes before plotting"""
        # Reset always all parameters (override previous values)
        self.colors = colors
        self.xTickStr = xTickStr
        self.yTickStr = yTickStr
        self.xTickInt = xTickInt
        self.yTickInt = yTickInt

    def filterLog(self, logName):
        """Filter log if filter is required"""
        if self.args.pltLogInclude:
            for key in self.args.pltLogInclude:
                if logName.find(key) == -1:
                    return True
        if self.args.pltLogExclude:
            for key in self.args.pltLogExclude:
                if logName.find(key) != -1:
                    return True
        return False

    def buildPlotName(self, plotTokens):
        """Build the name of a plot from tokens"""
        plotName = ".".join(plotTokens)
        if self.args.pltLogInclude:
            for key in self.args.pltLogInclude:
                plotName = plotName + "." + key
        if self.args.pltLogExclude:
            for key in self.args.pltLogExclude:
                plotName = plotName + "." + "no-" + key
        return plotName

    def plot2DGraph(self, plotName, plotDic, steps, xLabel, yLabel):
        """Plot dictionnary as a 2D graph"""
        N = list(plotDic.keys())
        N.sort()
        print("Plotting", plotName, "...")
        if len(N) == 0 or len(steps) == 0:
            print("  - No data available, check run logs")
            return
        matplotlib.pyplot.figure() # New figure, forget the previous one
        matplotlib.pyplot.suptitle(plotName)
        axis = matplotlib.pyplot.subplot(1, 1, 1)
        for idxS, s in enumerate(steps):
            nGrid = [n for n in N if n in plotDic and s in plotDic[n]]
            plotData = [plotDic[n][s] for n in N if n in plotDic and s in plotDic[n]]
            if self.colors and idxS < len(self.colors):
                axis.plot(nGrid, plotData, marker="o", label=s, color=self.colors[idxS])
            else:
                axis.plot(nGrid, plotData, marker="o", label=s, color=self.getAutoColor(idxS, len(steps)))
        axis.set_xlabel(xLabel)
        if self.xTickInt:
            axis.set_xticks(N)
        axis.set_ylabel(yLabel)
        if len(N) > 1: # Do NOT call set_xlim when there is only one point on x-axis
            axis.set_xlim([min(N), max(N)])
        ymax = 1.25 * max([plotDic[n][s] for n in N for s in steps if s in plotDic[n]])
        ymin = 0.75 * min([plotDic[n][s] for n in N for s in steps if s in plotDic[n]])
        if abs(ymax - ymin) > 1.e-12:
            axis.set_ylim([ymin, ymax])
        else:
            if abs(ymax + ymin) < 1.e-12: # Plot around zero
                axis.set_ylim([-1., 1.])
            else:
                axis.set_ylim([0.9 * ymin, 1.1 * ymax])
        matplotlib.pyplot.legend(loc="upper right", bbox_to_anchor=(1.1, 1.1))
        self.__annotateMax__(plotDic, N, None, steps, axis)
        self.plotOrSave(plotName)

    def plot3DGraph(self, plotName, plotDic, steps, xLabel, yLabel, zLabel):
        """Plot dictionnary as a 3D graph"""
        mKeys = list(plotDic.keys()) # Master keys
        mKeys = list(set(mKeys)) # Remove duplicates
        mKeys.sort()
        sKeys = [sK for mK in mKeys for sK in list(plotDic[mK].keys())] # Sub keys
        sKeys = list(set(sKeys)) # Remove duplicates
        sKeys.sort()
        print("Plotting", plotName, "...")
        if len(mKeys) == 0 or len(sKeys) == 0 or len(steps) == 0:
            print("  - No data available, check run logs")
            return
        fig = matplotlib.pyplot.figure() # New figure, forget the previous one
        fig.suptitle(plotName)
        from mpl_toolkits.mplot3d import Axes3D
        axis = fig.add_subplot(1, 1, 1, projection="3d")
        mGrid, sGrid = self.__get3DMeshGrid__(mKeys, sKeys, axis)
        for idxS, s in enumerate(steps):
            plotData = self.__get3DPlotData__(mKeys, sKeys, plotDic, s)
            if self.colors and idxS < len(self.colors):
                axis.plot_wireframe(mGrid, sGrid, plotData, label=s, color=self.colors[idxS])
            else:
                axis.plot_wireframe(mGrid, sGrid, plotData, label=s, color=self.getAutoColor(idxS, len(steps)))
        if xLabel:
            axis.set_xlabel(xLabel, labelpad=40)
        if yLabel:
            axis.set_ylabel(yLabel, labelpad=40)
        if zLabel:
            axis.set_zlabel(zLabel, labelpad=40)
        axis.view_init(elev=15., azim=60.)
        matplotlib.pyplot.legend(loc="upper right", bbox_to_anchor=(1.1, 1.1))
        self.__annotateMax__(plotDic, mKeys, sKeys, steps, axis)
        self.plotOrSave(plotName)
