sessionStorage.setItem("currentGraph", makeParameterString(document.forms));

var saveButton = document.getElementById("saveButton");
if (saveButton) {
  saveButton.addEventListener("click", (event)=>{
    sendParameters(sessionStorage.getItem("currentGraph"));
    saveButton.disabled = true;
  });
}

function sendParameters(parameterString) {

  var headers = new Headers();
  // will only work as long as there's only one cookie
  var token = document.cookie.split("=")[1]
  headers.append("X-CSRFToken", token);
  headers.append("Content-Type", "application/json")

  var graphSaveData = {
    graphs: JSON.stringify(GLOBALS.graphs),
    parameters: parameterString
  };

  var request = new Request(GLOBALS.save_url, {
    method: "POST",
    headers: headers,
    // not sure if this will need to change when client is on a different computer
    credentials: "same-origin",
    body: JSON.stringify(graphSaveData)
  });

  fetch(request).then((response)=>{console.dir(response)});

}
