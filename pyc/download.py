"""This module exports the download class"""

from __future__ import print_function

import os
import subprocess
import sys

class download(object):
    """Download class designed to handle downloads"""

    def __init__(self, tmp):
        """Initialize download class instance"""
        self.tmp = tmp
        if not os.path.exists(self.tmp):
            os.makedirs(self.tmp)

    @staticmethod
    def __checkNetwork__():
        """Check network availability"""
        cmdLine = ["ping", "-c", "1", "www.github.com"]
        pProc = subprocess.Popen(cmdLine, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (stdout, stderr) = pProc.communicate()
        if stdout.find("failure".encode()) != -1 or stderr.find("failure".encode()) != -1:
            sys.exit("ERROR: download KO, can not access network")

    def downloadFile(self, dldFile):
        """Download a file"""
        try:
            dFile = os.path.basename(dldFile)
            if not os.path.exists(dFile):
                self.__checkNetwork__()
                print("Downloading", dldFile, "...")
                rc = os.system("wget -a wget." + dFile + ".log " + dldFile)
                if rc != 0:
                    sys.exit("ERROR: download KO, error occured when downloading (web site may be down)")
            else:
                print("Downloading", dldFile, ": OK, no need to download")
        except RuntimeError:
            print("Downloading", dldFile, ": KO")

    def gitClone(self, url):
        """Clone a git repository"""
        try:
            dDir = os.path.basename(url).replace(".git", "")
            if not os.path.exists(dDir):
                self.__checkNetwork__()
                print("Downloading", url, "...")
                rc = os.system("git clone -q " + url)
                if rc != 0:
                    sys.exit("ERROR: download KO, error occured when downloading (web site may be down)")
            else:
                print("Downloading", url, ": OK, no need to clone")
        except RuntimeError:
            print("Downloading" + url + ": KO")
