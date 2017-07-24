for (var graphObject of GLOBALS.graphs) {
  initializeGraph(
    GLOBALS.networkdata + graphObject.fileName + ".json",
    graphObject.creatorIds,
    graphObject.displayString,
    graphObject.timestamp,
    graphObject.parameterString
  );
}

/**
 * Create a graph from data put in the HTML by Django.
 * @param {string} graphPath 
 * @param {string} title 
 * @param {string} displayString 
 * @param {string} timestamp 
 * @param {string} parameterString 
 */
function initializeGraph(graphPath, title, displayString, timestamp, parameterString) {

  var w = window.innerWidth;
  var h = window.innerHeight;

  var focus_node = null, highlight_node = null;

  var text_center = false;
  var outline = false;

  var min_score = 0;
  var max_score = 1;

  var highlight_color = "blue";
  var highlight_trans = 0.1;

  var force = d3.layout.force()
    .linkDistance(60)
    .charge(-300)
    .size([w,h]);

  var default_node_color = "lime";
  var default_link_color = "#888";
  var nominal_base_node_size = 8;
  var nominal_text_size = 10;
  var max_text_size = 24;
  var nominal_stroke = 1.5;
  var max_stroke = 4.5;
  var max_base_node_size = 36;
  var min_zoom = 0.1;
  var max_zoom = 7;
  var clickstart;

  var graphContainerDiv = document.getElementById("graph");
  var graphDiv = document.createElement("div");
  var graphDetails = document.createElement("div");
  graphDetails.className = "graphDetails";

  if (displayString) {
    graphDetails.appendChild(document.createTextNode("Saved date: " + timestamp));
    graphDetails.appendChild(document.createElement("br"));
    graphDetails.innerHTML += displayString;

    graphDetails.appendChild(document.createElement("br"));

    var parameterRestoreButton = document.createElement("button");
    parameterRestoreButton.type = "button";
    parameterRestoreButton.innerHTML = "Restore Parameters";
    parameterRestoreButton.addEventListener("click", ()=>{
      console.dir(parameterString)
      loadFormData(document.forms, JSON.parse(parameterString));
    });
    graphDetails.appendChild(parameterRestoreButton);

  }
  var linkDiv = document.createElement("div");
  linkDiv.id = "linkDiv";

  graphDetails.appendChild(linkDiv);

  graphDiv.appendChild(graphDetails);

  var colors = ["red", "orange", "yellow", "green", "teal", "blue", "purple", "gray", "brown", "black"];
  /**
   * Color the creator id numbers in the graph title to match their corresponding edges
   * @param {number[]} numbers 
   * @param {string[]} colors 
   * @returns {HTMLSpanElement}
   */
  function addColor(numbers, colors) {
    var container = document.createElement("span");
    for (number of numbers) {
      var span = document.createElement("span");
      span.style = "color: " + colors[number] + ";";
      span.appendChild(document.createTextNode(number + " "));
      container.appendChild(span);
    }
    return container;
  }

  if (title.length > 0) {
    var header = document.createElement("span");
    header.style = "font-weight: bold;";
    var titleText = document.createTextNode("Creator Ids: ");
    var coloredNumbers = addColor(title, colors);
    header.appendChild(titleText);
    header.appendChild(coloredNumbers);
    graphDiv.appendChild(header);
  }
  var svg = d3.select(graphDiv).append("svg");
  graphContainerDiv.appendChild(graphDiv);


  svg.append("svg:defs").append("svg:marker")
    .attr("id", "triangle")
    .attr("refX", 18)
    .attr("refY", 6)
    .attr("markerWidth", 30)
    .attr("markerHeight", 30)
    .attr("orient", "auto")
    .append("path")
    .attr("d", "M 0 0 12 6 0 12 3 6 0 0")
    .style("stroke", "gray")
    .style("fill", "white");


  var zoom = d3.behavior.zoom().scaleExtent([min_zoom,max_zoom]);
  var textOpacity;
  var g = svg.append("g");
  var linkedByIndex = {};
  var tocolor;
  var towhite;
  var jsonGraph;
  var offset;
  svg.style("cursor","move");

  /**
   * 
   * @param {object} d
   * @returns {string}
   */
  var linkColorFunction = (d)=>{
    return colors[d.creator] ? colors[d.creator % colors.length] : default_link_color;
  };

  //  GLOBALS contains Django template variables, defined in graph.html
  d3.json(graphPath, function(error, graph) {
    jsonGraph = graph;
    update(graph);
    zoomToScale(Math.min(3000, graph.nodes.length), svg.node());
  });

  // functions contained in initializeGraph for access to variables

  /**
   * Run every tick of the graph to adjust appearance and position of nodes and edges.
   * @param {object} graph 
   */
  function update(graph) {

    if (graph.links) {
      graph.links.forEach((d)=>{linkedByIndex[d.source + "," + d.target] = true;});
    }

    force.nodes(graph.nodes)
    if (graph.links) {
      force.links(graph.links)
    }
    force.start();

    if (graph.links) {
      var link = g.selectAll(".link").data(graph.links);
      link.exit().remove();
      link
        .enter().append("line")
        .attr("class", "link")
        .attr("marker-end", "url(#triangle)")
      	.style("stroke-width", nominal_stroke)
      	.style("stroke", linkColorFunction)
        // uncomment for dotted lines
        // .style("stroke-dasharray", "4,4")
    }
    else {
      /**
       * Prevents edge-related styling from causing errors when there are no edges in the graph.
       * @returns {object}
       */
      function fakeAttr() {return {attr:fakeAttr};}
      var link = {
        style:()=>{},
        transition:()=>{
          return {
            duration:()=>{
              return {style:()=>{}};
            }
          };
        },
        attr:fakeAttr,
      };
    }

    var node = g.selectAll(".node").data(graph.nodes);
    node.exit().remove();
    node
      .enter().append("g")
      .attr("class", "node")
      .call(force.drag)

    tocolor = "fill";
    towhite = "stroke";
    if (outline) {
    	tocolor = "stroke"
    	towhite = "fill"
    }

    var circle = node.append("path")
      .attr("d", d3.svg.symbol()
        .size((d)=>{return Math.PI * Math.pow(nominal_base_node_size, 2);})
        .type((d)=>{return d.type;})
      )
    	.style(tocolor, nodeColor)
    	.style("stroke-width", nominal_stroke)
    	.style(towhite, "white");


    var text = g.selectAll(".text")
      .data(graph.nodes)
      .enter().append("text")
      .attr("dy", ".35em")
      .style("font-size", nominal_text_size + "px")

    if (text_center) {
      text.text(function(d) { return d.id; })
        .style("text-anchor", "middle");
    }
    else {
    	text.attr("dx", function(d) {return nominal_base_node_size;})
        .text(function(d) { return '\u2002'+d.id; });
    }

    node.on("mouseover", (d)=>{set_highlight(d, circle, text, link);})
      .on("mouseout", (d)=>{exit_highlight(circle, text, link);})
      .on("mousedown", (d)=>{
        if (d3.event.button == 0) {nodeMousedown(d, circle, text, link);}
      })

    svg.node().addEventListener("mousedown", (e)=>{
      clickstart = e;
    });

    /**
     * Used to tell how far the mouse was dragged.
     * @param {number} x1 
     * @param {number} x2 
     * @param {number} y1 
     * @param {number} y2 
     * @returns {number}
     */
    function distance(x1, x2, y1, y2) {
      var a = x1 - x2;
      var b = y1 - y2;
      var c = Math.sqrt( a*a + b*b );
      return c;
    }

    svg.node().addEventListener("mouseup", (e)=>{
      if (clickstart && distance(clickstart.clientX, e.clientX, clickstart.clientY, e.clientY) < 5) {
        removeFocus(circle, text, link);
        clickstart = undefined;
        document.getElementById("linkDiv").innerHTML = "";
      }
    });

    zoom.on("zoom", ()=>{onZoom(circle, text, link)});

    svg.call(zoom);

    resize();
    d3.select(window).on("resize", resize);

    force.on("tick", ()=>{forceTick(node, text, link)});

  }

  /**
   * Adds a link for the clicked node to the interface.
   * @param {object} d 
   */
  function goToNodeLink(d) {
    var nodeID = d.id.match(/\(id : (\d+)\)/);
    if (nodeID && nodeID.length > 1) {
      var urlPart = (d.type == "square" ? "prediction-models" : "descriptors") + "/";
      var nodeNameMatch = d.id.match(/(.*?)\(id : (\d+)\)/)
      var nodeName = nodeNameMatch[1];
      var nodeIDNumber = nodeNameMatch[2];
      var outsideURL = "http://ebi.nims.go.jp/inventory/reference/" + urlPart + nodeIDNumber;

      var linkDiv = document.getElementById("linkDiv");
      document.getElementById("linkDiv").innerHTML = "";

      linkDiv.appendChild(document.createTextNode(nodeName));
      linkDiv.appendChild(document.createElement("br"));

      var nodeLink = document.createElement("a");
      nodeLink.href = outsideURL;
      nodeLink.innerHTML = nodeIDNumber;
      linkDiv.appendChild(nodeLink);
    }
  }

  /**
   * Used to convert the number of nodes in a graph into how far we should zoom out.
   * @param {number} x 
   * @param {number} xMin 
   * @param {number} xMax 
   * @param {number} yMin 
   * @param {number} yMax 
   * @returns {number}
   */
  function rescale(x, xMin, xMax, yMin, yMax) {
    var ratio = (x - xMin) / (xMax - xMin);
    var y = (ratio * (yMax - yMin)) + yMin;
    return y;
  }

  // svg.node() is always the element passed in currently
  /**
   * Used to change the starting zoom level of graphs.
   * @param {number} distance 
   * @param {HTMLElement} elem 
   */
  function wheelScroll(distance, elem) {
    var rect = elem.getBoundingClientRect();
    evt = new WheelEvent("wheel", {
      "deltaY": distance,
      "clientX": rect.left + (rect.width / 2),
      "clientY": rect.top + (rect.height / 2),
    });
    elem.dispatchEvent(evt);
  }

  /**
   * Zooms a graph such that most of the nodes fit inside the display area.
   * @param {number} nodeCount 
   * @param {HTMLElement} elem 
   */
  function zoomToScale(nodeCount, elem) {
    var scrollMax = 1500;
    var scrollMid = 500;
    var scrollMin = 0;
    var nodeMax = 3000;
    var nodeMid = 300;
    var nodeMin = 0;
    if (nodeCount < 500) {
      wheelScroll(rescale(nodeCount,
        nodeMin, nodeMid,
        scrollMin, scrollMid), elem);
    }
    else {
      wheelScroll(rescale(nodeCount,
        nodeMid, nodeMax,
        scrollMid, scrollMax), elem);
    }
  }

  /**
   * Used to color start, end, and middle nodes of path searches,
   * as well as to make squares and circles be different colors.
   * @param {object} d 
   * @returns {string}
   */
  function nodeColor(d) {
    var color;
    if (d.start) {
      color = "red";
    }
    else if (d.middle) {
      color = "yellow";
    }
    else if (d.end) {
      color = "blue";
    }
    else if (d.type) {
      color = "#00d3d0";
    }
    else {
      color = default_node_color;
    }
    return color;
  }

  var prevScale = zoom.scale();

  /**
   * Changes the styling of the graph to fit the new zoom level. Font size, opacity, etc.
   * @param {object} circle 
   * @param {object} text 
   * @param {object} link 
   */
  function onZoom(circle, text, link) {

    var transitionTime = prevScale == zoom.scale() ? 0 : 500;

    textOpacity = rescale(zoom.scale(), .3, .7, 0, 1);

    var stroke = nominal_stroke;
    if (nominal_stroke*zoom.scale()>max_stroke) {stroke = max_stroke/zoom.scale();}
    link.transition().duration(transitionTime)
      .style("stroke-width", stroke);
    circle.transition().duration(transitionTime)
      .style("stroke-width", stroke);

    var base_radius = nominal_base_node_size;
    if (nominal_base_node_size*zoom.scale()>max_base_node_size) {base_radius = max_base_node_size/zoom.scale();}
    circle.transition().duration(transitionTime)
      .attr("d", d3.svg.symbol()
        .size(function(d) { return Math.PI*Math.pow(base_radius,2); })
        .type(function(d) { return d.type; })
      )

    if (!text_center) {
      text.transition().duration(transitionTime)
        .attr("dx", function(d) { return base_radius; });
    }

    var text_size = nominal_text_size;
    if (nominal_text_size*zoom.scale()>max_text_size) {text_size = max_text_size/zoom.scale();}
    text.transition().duration(transitionTime)
      .style("font-size", text_size + "px")
    if (focus_node === null) {
      text.transition().duration(transitionTime)
        .style("opacity", textOpacity);
    }

    g.transition().duration(transitionTime)
      .attr("transform", "translate(" + d3.event.translate + ")scale(" + d3.event.scale + ")")

    prevScale = zoom.scale();
  }

  /**
   * Calculates how the nodes are pulled together and pushed apart.
   * @param {object} node 
   * @param {object} text 
   * @param {object} link 
   */
  function forceTick(node, text, link) {
    node.attr("transform", function(d) { return "translate(" + d.x + "," + d.y + ")"; });
    text.attr("transform", function(d) { return "translate(" + d.x + "," + d.y + ")"; });

    link.attr("x1", function(d) { return d.source.x; })
      .attr("y1", function(d) { return d.source.y; })
      .attr("x2", function(d) { return d.target.x; })
      .attr("y2", function(d) { return d.target.y; });

    node.attr("cx", function(d) { return d.x; })
      .attr("cy", function(d) { return d.y; });
  }

  /**
   * Used to determine which nodes should be highlighted when one is clicked on.
   * @param {object} a 
   * @param {object} b 
   * @returns {boolean}
   */
  function isConnected(a, b) {
    return linkedByIndex[a.index + "," + b.index] || linkedByIndex[b.index + "," + a.index] || a.index == b.index;
  }

  /**
   * Returns styling back to normal once highlighting is removed.
   * @param {object} circle 
   * @param {object} text 
   * @param {object} link 
   */
  function exit_highlight(circle, text, link) {
    highlight_node = null;
    if (focus_node===null) {
      svg.style("cursor","move");
      text.style("opacity", textOpacity);
      if (highlight_color!="white") {
        circle.style(towhite, "white");
        text.style("font-weight", "normal");
        link.style("stroke", linkColorFunction);
      }
    }
  }

  /**
   * Used to find adjacent nodes for highlighting.
   * @param {object} d 
   * @param {object} circle 
   * @returns {object[]}
   */
  function connectedTo(d, circle) {
    var results = [];
    circle.data().forEach((node)=>{
      if (isConnected(d, node) && results.indexOf(node) == -1) {
        results.push(node);
      }
    });
    return results;
  }

  /**
   * Used to find adjacent nodes for highlighting.
   * @param {object} d 
   * @param {object} circle
   * @returns {object[]}
   */
  function getNeighborhood2(d, circle) {
    var neighborhood1 = connectedTo(d, circle);
    var neighborhood2 = [];
    for (neighborhood1Node of neighborhood1) {
      var neighborhood2Nodes = connectedTo(neighborhood1Node, circle);
      for (neighborhood2Node of neighborhood2Nodes) {
        if (neighborhood2.indexOf(neighborhood2Node) == -1) {
          neighborhood2.push(neighborhood2Node);
        }
      }
    }
    return neighborhood2;
  }

  /**
   * Change styling for nodes when highlighting is active
   * @param {object} d 
   * @param {object} circle 
   * @param {object} text 
   * @param {object} link
   * @returns {number}
   */
  function set_focus(d, circle, text, link) {
    if (highlight_trans<1) {

      var neighborhood2 = getNeighborhood2(d, circle);

      circle.style("opacity", function(o) {
        return neighborhood2.indexOf(o) != -1 ? 1 : highlight_trans;
      });

      text.style("opacity", function(o) {
        return neighborhood2.indexOf(o) != -1 ? 1 : 0;
      });

      link.style("opacity", function(o) {
        var sourceIncluded = neighborhood2.indexOf(o.source) != -1;
        var targetIncluded = neighborhood2.indexOf(o.target) != -1;
        return sourceIncluded && targetIncluded ? 1 : highlight_trans;
      });
    }
  }

  /**
   * Change styling for nodes when highlighting is active
   * @param {object} d 
   * @param {object} circle 
   * @param {object} text 
   * @param {object} link 
   */
  function set_highlight(d, circle, text, link) {
    svg.style("cursor","pointer");
    if (focus_node !== null) {d = focus_node;}
    highlight_node = d;

    if (highlight_color!="white")
    {
      var neighborhood2 = getNeighborhood2(d, circle);
      circle.style(towhite, function(o) {
        return neighborhood2.indexOf(o) != -1 ? highlight_color : "white";
      });
      text.style("font-weight", function(o) {
        return neighborhood2.indexOf(o) != -1 ? "bold" : "normal";
      });
      link.style("stroke", linkColorFunction);
    }
  }

  /**
   * Triggers highlighting style changes.
   * @param {object} d 
   * @param {object} circle 
   * @param {object} text 
   * @param {object} link 
   */
  function nodeMousedown(d, circle, text, link) {
    d3.event.stopPropagation();
    focus_node = d;
    set_focus(d, circle, text, link);
    if (highlight_node === null) {set_highlight(d, circle, text, link);}
    // uncomment to show links
    // goToNodeLink(d);
  }

  /**
   * Returns the graph to normal styling when highlights are removed.
   * @param {object} circle 
   * @param {object} text 
   * @param {object} link 
   */
  function removeFocus(circle, text, link) {
    if (focus_node !== null) {
      focus_node = null;
      if (highlight_trans < 1) {
        circle.style("opacity", 1);
        text.style("opacity", textOpacity);
        link.style("opacity", 1);
      }
    }

    if (highlight_node === null) {exit_highlight(circle, text, link);}
  }

  /**
   * Used to adjust graph size when the window size changes.
   */
  function resize() {
    var width = window.innerWidth, height = window.innerHeight;
    svg.attr("width", width).attr("height", height);

    force.size([force.size()[0]+(width-w)/zoom.scale(),force.size()[1]+(height-h)/zoom.scale()]).resume();
    w = width;
    h = height;
  }

}
