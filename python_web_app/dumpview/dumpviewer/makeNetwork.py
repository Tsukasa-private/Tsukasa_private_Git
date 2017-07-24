import networkx as nx
import json
from networkx.readwrite import json_graph
import codecs
from .readGraphData import getGraphData, extractGraphData
from networkx.drawing.nx_pydot import write_dot
import pandas

import datetime
epoch = datetime.datetime.utcfromtimestamp(0)
def unix_time_millis(dt):
    return (dt - epoch).total_seconds() * 1000.0

def writeGraph(graph, fileName):
    json_data = json_graph.node_link_data(graph)

    json_string = json.dumps(json_data)

    filePath = "dumpviewer/static/dumpviewer/temporaryGraphs"

    with open('{0}/{1}.json'.format(filePath, fileName), 'w') as outfile:
        outfile.write(json_string)

    with codecs.open('{0}/{1}.csv'.format(filePath, fileName), 'w', "utf-8-sig") as outfile:
        for edge in graph.edges():
            outfile.write("{0},{1}\n".format(edge[0], edge[1]))

    with codecs.open('{0}/{1}.gv'.format(filePath, fileName), 'w', "utf-8-sig") as outfile:
        write_dot(graph, outfile)

def neighborhood(G, node, n):
    path_lengths = nx.single_source_dijkstra_path_length(G, node)
    return [node for node, length in iter(path_lengths.items()) if length == n]

def add_node_from(fromGraph, toGraph, nodeName):
    toGraph.node[nodeName] = fromGraph.node[nodeName]


def add_nodes_from(fromGraph, toGraph, nodeIter):
    for nodeName in nodeIter:
        add_node_from(fromGraph, toGraph, nodeName)

def add_edges_from(fromGraph, toGraph):
    for start, end in fromGraph.edges():
        if start in toGraph and end in toGraph:
            if not start in toGraph.edge:
                toGraph.edge[start] = {}
            toGraph.edge[start][end] = fromGraph.edge[start][end]

def dbTime(timeval):
    return pandas.to_datetime(timeval)

def makeCompleteGraph(data, creator_ids, dicNames, selectedDate):
    completeGraph = nx.DiGraph()

    for pmid in data:
        for did in data[pmid]:

            comparableItems = data[pmid][did]

            maxItem = False
            maxScore = 0
            deleted = False
            for item in comparableItems:
                
                timeOK = True
                isNewer = True
                itemScore = 0
                creatorMatch = True
                dicMatch = True

                if not item["C_id"] in creator_ids:
                    creatorMatch = False

                if not item["Dic_name"] in dicNames:
                    dicMatch = False

                for timeKey in ["P_modified_time", "D_modified_time"]:
                    if (item[timeKey] > unix_time_millis(selectedDate)):
                        timeOK = False

                if (timeOK):

                    for timeKey in ["P_modified_time", "D_modified_time"]:
                        if (maxItem and (item[timeKey] < maxItem[timeKey])):
                            isNewer = False
                        else:
                            itemScore = itemScore + 1

                        if (isNewer and (itemScore >= maxScore) and creatorMatch and dicMatch):
                            maxItem = item
                            maxScore = itemScore
            if maxItem:
                for deletedFlagKey in ["D_deleted", "P_deleted"]:
                    if (maxItem[deletedFlagKey]):
                        deleted = True

                if not deleted:
                    if not maxItem["D_name"] in completeGraph:
                        completeGraph.add_node(maxItem["D_name"], creator=maxItem["C_id"])
                    if not maxItem["P_name"] in completeGraph:
                        completeGraph.add_node(maxItem["P_name"], type="square", creator=maxItem["C_id"])
                    if maxItem["in_or_out"] == "I":
                        completeGraph.add_edge(maxItem["D_name"], maxItem["P_name"], creator=maxItem["C_id"])
                    else:
                        completeGraph.add_edge(maxItem["P_name"], maxItem["D_name"], creator=maxItem["C_id"])

    return completeGraph

def addSearchNeighborhood(fromGraph, toGraph, search_terms, andOrField, degree):
    fromGraphUndirected = fromGraph.to_undirected()
    for nodeName in fromGraph.nodes():
        if andOrField == "or":
            termIncluded = any([word in nodeName for word in search_terms])
        else:
            termIncluded = all([word in nodeName for word in search_terms])
        if termIncluded and "type" in fromGraph.node[nodeName]:
            for distance in range(degree + 1):
                neighbor_nodes = neighborhood(fromGraphUndirected, nodeName, distance)
                add_nodes_from(fromGraph, toGraph, neighbor_nodes)
    add_edges_from(fromGraph, toGraph)

def makeSearchTermNetwork(fileName, search_terms, andOrField, NstepSelect, selectedDate, dicNames, creator_ids):
    data = extractGraphData(getGraphData())["pred_desc_id_map"]

    completeGraph = makeCompleteGraph(data, creator_ids, dicNames, selectedDate)

    if not search_terms:
        search_terms = [""]

    newSearchTermGraph = nx.DiGraph()
    degree = int(NstepSelect)

    addSearchNeighborhood(completeGraph, newSearchTermGraph, search_terms, andOrField, degree)

    if len(newSearchTermGraph.node) != 0:
        writeGraph(newSearchTermGraph, fileName)

    return len(newSearchTermGraph.node)

def makeStartEndNetwork(fileName, start, middle, end, longPathsFirst, maxDepth, maxDepthEnd, maxCount, maxCountEnd, selectedDate, dicNames, creator_ids):
    data = extractGraphData(getGraphData())["pred_desc_id_map"]

    completeGraph = makeCompleteGraph(data, creator_ids, dicNames, selectedDate)

    # check if start, middle and end are in the graph
    nodeNotPresent = "Nodes not in graph: {0}"
    if not any(startName in completeGraph for startName in start):
        raise nx.NetworkXException(nodeNotPresent.format(start))
    if not any(endName in completeGraph for endName in end):
        raise nx.NetworkXException(nodeNotPresent.format(end))
    if middle and not any(middleName in completeGraph for middleName in middle):
        raise nx.NetworkXException(nodeNotPresent.format(middle))

    startEndPathPairs = []
    startMiddlePathPairs = []
    middleEndPathPairs = []
    if not middle:
        for startName in start:
            for endName in end:
                startEndPathPairs.append([startName, endName])
    else:
        for startName in start:
            for middleName in middle:
                startMiddlePathPairs.append([startName, middleName])
        for middleName in middle:
            for endName in end:
                middleEndPathPairs.append([middleName, endName])

    # make a network of only the paths
    startEndGraph = nx.DiGraph()

    def addPathPairs(fromGraph, toGraph, pathPairs, maxDepth, maxCount):
        counter = 1
        for pathPair in pathPairs:
            pathList = list(nx.all_simple_paths(fromGraph, pathPair[0], pathPair[1], maxDepth))
            pathList.sort(key=len)
            if longPathsFirst:
                pathList.reverse()
            for path in pathList:
                if counter > maxCount: return
                print("Path length: ", len(path) - 1)
                toGraph.add_path(path)
                counter = counter + 1

    addPathPairs(completeGraph, startEndGraph, startEndPathPairs, maxDepth, maxCount)
    addPathPairs(completeGraph, startEndGraph, startMiddlePathPairs, maxDepth, maxCount)
    addPathPairs(completeGraph, startEndGraph, middleEndPathPairs, maxDepthEnd, maxCountEnd)

    # add any nodes that were not present in the paths
    for startName in start:
        if not startName in startEndGraph.node:
            add_node_from(completeGraph, startEndGraph, startName)
    for middleName in middle:
        if not middleName in startEndGraph.node:
            add_node_from(completeGraph, startEndGraph, middleName)
    for endName in end:
        if not endName in startEndGraph.node:
            add_node_from(completeGraph, startEndGraph, endName)

    # node data isn't preserved when building the new graph
    for newNode in startEndGraph.node:
        startEndGraph.node[newNode] = completeGraph.node[newNode]
    for startNode in startEndGraph.edge:
        for endNode in startEndGraph.edge[startNode]:
            startEndGraph.edge[startNode][endNode] = completeGraph.edge[startNode][endNode]

    # change start, middle and end node colors
    if len(startEndGraph.node) > 0:
        for startName in start:
            if startName in startEndGraph.node:
                startEndGraph.node[startName]["start"] = True;
        for endName in end:
            if endName in startEndGraph.node:
                startEndGraph.node[endName]["end"] = True;
        for middleName in middle:
            if middleName in startEndGraph.node:
                startEndGraph.node[middleName]["middle"] = True;
    else:
        raise nx.NetworkXNoPath("No paths between these nodes exists")

    # output graph as JSON file
    writeGraph(startEndGraph, fileName)
