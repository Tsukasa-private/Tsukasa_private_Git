from django.shortcuts import render
from django.http import HttpResponseRedirect, HttpResponse
from django.urls import reverse
from .makeNetwork import makeSearchTermNetwork, makeStartEndNetwork
from .deleteOldGraphs import deleteOldGraphs
import networkx as nx # for exceptions
from .models import Graph
import json
from shutil import copyfile
from time import gmtime, strftime
import datetime

 # for filenames
 # there probably won't be any collisions, but it's not guaranteed
import random
random.seed()
from uuid import uuid4

from .readGraphData import getGraphData, extractGraphData
extractedData = extractGraphData(getGraphData())
renderParameters = {
    "pred_desc_id_map_JSON": extractedData["pred_desc_id_map_JSON"],
    "dic_id_map_JSON": extractedData["dic_id_map_JSON"],
    "creatorIds": extractedData["creatorIds"],
    "creatorIDToDicNamesJSON": extractedData["creatorIDToDicNamesJSON"],
    "graphs": [],
    "saved": False
}

def updateGraphs(renderParameters):
    renderParameters["allSavedGraphs"] = Graph.objects.all()
    renderParameters["graphIdentifiers"] = json.dumps(list(map(lambda g: g.identifier, Graph.objects.all())));

updateGraphs(renderParameters)

def renderError(condition, msg, request):
    if not condition:
        return render(request, 'dumpviewer/graph.html', dict(renderParameters, **{"error_message": msg}))
    else: return False

def welcome(request):
    renderParameters["graphs"] = [{"creatorIds": [], "fileName": "welcome"}]
    renderParameters["saved"] = True
    return render(request, 'dumpviewer/graph.html', renderParameters)

def index(request, search_terms, andOrField, NstepSelect, selectedDate, dicNamesList=extractedData["dicNames"], creator_ids=extractedData["creatorIds"], splitByCreatorId=False):
    print(search_terms)
    renderParameters["graphs"] = []
    renderParameters["saved"] = False
    fileName = str(uuid4())

    if splitByCreatorId:
        split_creator_ids = list(map(lambda x: [x], creator_ids))
    else:
        split_creator_ids = [creator_ids]

    for creator_id in split_creator_ids:
        nodeCount = makeSearchTermNetwork(fileName, search_terms, andOrField, NstepSelect, selectedDate, dicNamesList, creator_id)
        if nodeCount != 0:
            graphObject = {
                "creatorIds": creator_id,
                "fileName": fileName
            }
            renderParameters["graphs"].append(graphObject)
            fileName = str(uuid4())

    return render(request, 'dumpviewer/graph.html', renderParameters)

def path_search(request, start, middle, end, longPathsFirst, maxDepth, maxDepthEnd, maxCount, maxCountEnd, selectedDate, dicNames, creator_ids, splitByCreatorId=False):
    print(start, end)
    renderParameters["graphs"] = []
    renderParameters["saved"] = False
    fileName = str(uuid4())
    invalid_input_msg = "" # we change this if we encounter any errors

    if not maxDepthEnd: maxDepthEnd = -1
    if not maxCountEnd: maxCountEnd = -1

    if splitByCreatorId:
        split_creator_ids = list(map(lambda x: [x], creator_ids))
    else:
        split_creator_ids = [creator_ids]

    for creator_id in split_creator_ids:
        try:
            makeStartEndNetwork(fileName, start, middle, end, longPathsFirst, int(maxDepth), int(maxDepthEnd), int(maxCount), int(maxCountEnd), selectedDate, extractedData["dicNames"], creator_id)
            graphObject = {
                "creatorIds": creator_id,
                "fileName": fileName
            }
            renderParameters["graphs"].append(graphObject)
            fileName = str(uuid4())
        except (nx.NetworkXException, nx.NetworkXNoPath) as nxError:
            invalid_input_msg = str(nxError)

    return render(request, 'dumpviewer/graph.html', dict(renderParameters, **{"error_message": invalid_input_msg}))

def search(request):
    print(request.POST)
    deleteOldGraphs()
    splitByCreatorId = "split" in request.POST
    longPathsFirst = "longPathsFirst" in request.POST

    creatorIdNumbers = list(map(int, extractedData["creatorIds"])) if not request.POST.getlist("creator_ids") else list(map(int, request.POST.getlist("creator_ids")))
    dicNamesList = extractedData["dicNames"] if not request.POST.getlist("dicNames") else request.POST.getlist("dicNames")
    NstepSelect = 1 if not "NstepSelect" in request.POST else request.POST["NstepSelect"]

    selectedDate = datetime.datetime.strptime(request.POST["selectedDate"], "%Y/%m/%d %H:%M:%S")

    if "start" not in request.POST:
        return index(
            request,
            request.POST.getlist("keywords"),
            request.POST["andOrField"],
            NstepSelect,
            selectedDate,       
            dicNamesList,
            creatorIdNumbers,
            splitByCreatorId
        )
    else:
        return path_search(
            request,
            request.POST.getlist("start"),
            request.POST.getlist("middle"),
            request.POST.getlist("end"),
            longPathsFirst,
            request.POST["maxDepth"],
            request.POST["maxDepthEnd"],
            request.POST["maxCount"],
            request.POST["maxCountEnd"],
            selectedDate,
            dicNamesList,
            creatorIdNumbers,
            splitByCreatorId
        )

def save(request):
    graphSaveData = json.loads(request.body.decode("utf-8"))
    parameterString = graphSaveData["parameters"]
    graphsString = graphSaveData["graphs"]
    graphsData = json.loads(graphsString)
    staticFilePath = "dumpviewer/static/dumpviewer/"
    for graphObject in graphsData:
        for fileExtension in ["gv", "csv", "json"]:
            oldFilePath = "{0}temporaryGraphs/{1}.{2}".format(staticFilePath, graphObject["fileName"], fileExtension)
            newFilePath = "{0}savedGraphs/{1}.{2}".format(staticFilePath, graphObject["fileName"], fileExtension)
            copyfile(oldFilePath, newFilePath)
        JSONFilePath = "{0}temporaryGraphs/{1}.json".format(staticFilePath, graphObject["fileName"])
        with open(JSONFilePath) as f:
            graphObject["JSONString"] = f.read()
        graphModel = Graph(parameterString=parameterString, graphsString=json.dumps([graphObject]), timestamp=strftime("%Y%m%dT%H%M%S%z", gmtime()))
        graphModel.save()
    newGraphsString = json.dumps(graphsData)
    updateGraphs(renderParameters)
    return HttpResponse("200")

def saved(request, identifier):
    renderParameters["graphs"] = []
    renderParameters["saved"] = True
    # used when you get here via a url
    if identifier:
        identifiers = [identifier]
    else:
        identifiers = request.POST.getlist("viewSavedGraphs")
    print(identifiers)
    for identifier in identifiers:
        graphSaveData = Graph.objects.get(identifier=identifier)
        graphObjects = json.loads(graphSaveData.graphsString)
        for graphObject in graphObjects:
            graphObject["displayString"] = graphSaveData.displayString(True)
            graphObject["parameterString"] = graphSaveData.parameterString
            graphObject["timestamp"] = graphSaveData.timestamp
            renderParameters["graphs"].append(graphObject)
    return render(request, 'dumpviewer/graph.html', renderParameters)

def delete(request):
    identifiers = request.POST.getlist("deleteSavedGraphs")
    for identifier in identifiers:
        graphSaveData = Graph.objects.get(identifier=identifier)
        graphSaveData.delete()
    updateGraphs(renderParameters)
    return welcome(request)
