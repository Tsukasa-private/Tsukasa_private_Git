from os.path import getctime
import os
from time import time

def deleteOldGraphs():
    filePath = "dumpviewer/static/dumpviewer/temporaryGraphs"
    for fileName in os.listdir(filePath):
        fullFileName = "{0}/{1}".format(filePath, fileName)
        if isFileOlderThan(fullFileName, 24):
            print("Deleting {0}".format(fileName))
            os.remove(fullFileName)


def getFileAgeInSeconds(fileName):
    return time() - getctime(fileName)


def isFileOlderThan(fileName, hours):
    seconds = hours * 60 * 60
    return getFileAgeInSeconds(fileName) > seconds
