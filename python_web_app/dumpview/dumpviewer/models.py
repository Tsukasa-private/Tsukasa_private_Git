from __future__ import unicode_literals

from django.dispatch import receiver
from django.db import models
import json
import os

class Graph(models.Model):

    identifier = models.AutoField(primary_key=True)
    parameterString = models.TextField(default=None)
    graphsString = models.TextField(default=None)
    timestamp = models.CharField(max_length=100)

    def __str__(self):
        return self.displayString()

    def displayString(self, html=False):
        if html:
            delimiter = "<br>"
        else:
            delimiter = ", "
        stringRepresentation = ""
        parameterJSON = json.loads(self.parameterString)
        fieldNameMap = {"selectedDate": "DB date"}
        parameterJSON["radioDisplay"] = parameterJSON["radioDisplay"].replace("creatorSearch", "keywordSearch")
        stringRepresentation += "{0}: {1}{2}".format("Search type", parameterJSON["radioDisplay"], delimiter)
        parameterList = ""
        parameters = parameterJSON["parameters"]
        importantFields = []
        if parameterJSON["radioDisplay"] in ["keywordSearch"]:
            importantFields += ["keywords"]
        if parameterJSON["radioDisplay"] in ["pathSearch"]:
            importantFields += ["start", "middle", "end"]
        form = parameters[0] if parameterJSON["radioDisplay"] == "keywordSearch" else parameters[1]
        if not "dateWasSelected" in form:
            form["dateWasSelected"] = "No"
        elif form["dateWasSelected"] == "yes":
            form["dateWasSelected"] = "Yes"
        elif form["dateWasSelected"] == "no":
            form["dateWasSelected"] = "No"
        for field in form:
            if field in importantFields:
                if form[field]:
                    if field in fieldNameMap:
                        parameterList += "{0}: {1}{2}".format(fieldNameMap[field], form[field], delimiter)
                    else:
                        parameterList += "{0}: {1}{2}".format(field, form[field], delimiter)
        parameterList += "{0}: {1}{2}".format("Specified date", form["dateWasSelected"], delimiter)
        if "selectedDate" in form: parameterList += "{0}: {1}{2}".format("DB date", form["selectedDate"], delimiter)
        if not (parameterList):
            parameterList = "no parameters specified"
        stringRepresentation += parameterList
        if stringRepresentation[-len(delimiter):] == delimiter:
            stringRepresentation = stringRepresentation[:-len(delimiter)]
        return stringRepresentation



@receiver(models.signals.post_delete, sender=Graph)
def delete_file(sender, instance, *args, **kwargs):
    graphObjects = json.loads(instance.graphsString)
    for graphObject in graphObjects:
        for fileExtension in ["gv", "csv", "json"]:
            filePath = "dumpviewer/static/dumpviewer/savedGraphs/{0}.{1}".format(graphObject["fileName"], fileExtension)
            if os.path.isfile(filePath):
                os.remove(filePath)
