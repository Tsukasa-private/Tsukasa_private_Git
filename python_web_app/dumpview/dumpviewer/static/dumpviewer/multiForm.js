/**
 * Multiforms allow adding multiple values to a form through a simple interface.
 */
function main() {
  for (formID of getMultiformIDs()) {
    var field = document.getElementById(formID.field);
    var button = document.getElementById(formID.button);
    var displayDiv = document.getElementById(formID.displayDiv);
    initMultiForm(field, button, displayDiv);
  }
  for (formID of getPathMultiformIDs()) {
    var nameField = document.getElementById(formID.nameField);
    var valueField = document.getElementById(formID.valueField);
    var button = document.getElementById(formID.button);
    var displayDiv = document.getElementById(formID.displayDiv);
    initPathMultiForm(nameField, valueField, button, displayDiv);
  }
}

main();

/**
 * Used to specify which forms need to be initialized.
 * @returns {object[]}
 */
function getMultiformIDs() {
  var formIDs = [
    {
      field: "creatorText",
      button: "creatorButton",
      displayDiv: "creatorDisplayDiv"
    },
    {
      field: "creatorDictionarySelect",
      button: "creatorDictionaryButton",
      displayDiv: "creatorDictionaryDisplayDiv"
    },
    {
      field: "pathDictionarySelect",
      button: "pathDictionaryButton",
      displayDiv: "pathDictionaryDisplayDiv"
    },
    {
      field: "creatorIDSelect",
      button: "creatorIDButton",
      displayDiv: "creatorIDDisplayDiv"
    },
    {
      field: "pathIDSelect",
      button: "pathIDButton",
      displayDiv: "pathIDDisplayDiv"
    },
    {
      field: "savedGraphsField",
      button: "savedGraphsButton",
      displayDiv: "savedGraphsDisplayDiv"
    },
    {
      field: "deleteGraphsField",
      button: "deleteGraphsButton",
      displayDiv: "deleteGraphsDisplayDiv"
    },
  ];
  return formIDs;
}

/**
 * Used to specify which forms need to be initialized.
 * @returns {object[]}
 */
function getPathMultiformIDs() {
  var formIDs = [
    {
      nameField: "pathTypeSelect",
      valueField: "pathText",
      button: "pathButton",
      displayDiv: "pathDisplayDiv"
    },
  ];
  return formIDs;
}

/**
 * Initializes a multiform.
 * @param {string} field 
 * @param {string} button 
 * @param {string} displayDiv 
 */
function initMultiForm(field, button, displayDiv) {

  var inputName = field.name;
  field.name = "";

  button.addEventListener("click", (e)=>{
    if (field.value) {
      addHiddenInput(field.value, inputName, displayDiv);
      field.value = "";
      var multiformEvent = new Event("multiformChange");
      displayDiv.dispatchEvent(multiformEvent);
    }
  });

}

/**
 * Determines the order select options should be sorted in.
 * @param {string} x 
 * @param {string} y 
 * @returns {number}
 */
function sortDOM(x, y) {
  var xVal = x.firstChild.value;
  var yVal = y.firstChild.value;
  var srt = ["開始", "中間", "終了"];
  if (xVal == yVal) {return 0;}
  else if (srt.indexOf(xVal) < srt.indexOf(yVal)) {return -1;}
  else {return 1;}
}

/**
 * Makes sure path start points are displayed first, followed by middle, then end points.
 * @param {string} displayDivName 
 */
function sortPathDisplayDiv(displayDivName) {
  var p = document.getElementById('pathDisplayDiv');
  Array.prototype.slice.call(p.children)
    .map(function (x) { return p.removeChild(x); })
    .sort(sortDOM)
    .forEach(function (x) { p.appendChild(x); });
}

/**
 * Used to know when to show or hide certain input elements.
 * @param {string} displayDivName 
 * @returns {boolean}
 */
function containsMiddlePoint(displayDivName) {
  var displayDiv = document.getElementById(displayDivName);
  for (elem of Array.from(displayDiv.children)) {
    if (elem.firstChild.value == "中間") {
      return true;
    }
  }
  return false;
}

/**
 * Hooks the path multiforms up with event handlers.
 * @param {HTMLElement} nameField 
 * @param {HTMLElement} valueField 
 * @param {HTMLElement} button 
 * @param {HTMLElement} displayDiv 
 */
function initPathMultiForm(nameField, valueField, button, displayDiv) {

  button.addEventListener("click", (e)=>{
    if (valueField.value) {
      var nameText = nameField.options[nameField.selectedIndex].text;
      addHiddenInput(valueField.value, nameField.value, displayDiv, nameText);
      valueField.value = "";
      sortPathDisplayDiv(displayDiv.id);
      var multiformEvent = new Event("multiformChange");
      displayDiv.dispatchEvent(multiformEvent);
    }
  });

  displayDiv.addEventListener("multiformChange", (e)=>{
    if (containsMiddlePoint("pathDisplayDiv")) {
      for (elem of Array.from(document.querySelectorAll(".singlePath"))) {
        for (childNode of Array.from(elem.children)) {
          if (childNode.tagName == "INPUT") {
            console.dir(childNode)
            childNode.required = true;
          }
        }
        elem.className = "multiPath";
      }
    }
    else {
      for (elem of Array.from(document.querySelectorAll(".multiPath"))) {
        for (childNode of Array.from(elem.children)) {
          if (childNode.tagName == "INPUT") {
            childNode.value = childNode.defaultValue;
            childNode.required = false;
          }
        }
        elem.className = "singlePath";
      }
    }
  });

}

/**
 * 
 * @param {string} value 
 * @param {string} name 
 * @param {HTMLDivElement} parentDiv 
 * @param {string} displayInfo 
 */
function addHiddenInput(value, name, parentDiv, displayInfo) {

  var hiddenInputContainer = document.createElement("div");

  var hiddenInput = document.createElement("input");
  hiddenInput.type = "text";
  hiddenInput.name = name;
  hiddenInput.setAttribute("value", value);
  hiddenInput.readOnly = true;

  if (displayInfo) {
    var displayInfoNode = document.createElement("input");
    displayInfoNode.type = "text";
    displayInfoNode.setAttribute("value", displayInfo);
    displayInfoNode.readOnly = true;
    displayInfoNode.className = "smallText";
    hiddenInputContainer.appendChild(displayInfoNode);
  }

  hiddenInputContainer.appendChild(hiddenInput);

  var deleteButton = document.createElement("button");
  deleteButton.type = "button";
  deleteButton.innerHTML = "X";
  var buttonHandler =  (e)=>{

    var parentDisplayDiv = e.target.parentNode.parentNode;

    e.target.parentNode.remove();

    var multiformEvent = new Event("multiformChange");
    parentDisplayDiv.dispatchEvent(multiformEvent);

  };
  var codeString = "(" + buttonHandler.toString() + ")(event)";
  deleteButton.setAttribute("onclick", codeString);

  hiddenInputContainer.appendChild(deleteButton);

  parentDiv.insertBefore(hiddenInputContainer, parentDiv.firstChild);

}
