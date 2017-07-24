/**
 * Used to make sure the form data you submitted is re-loaded when your results arrive.
 */
function main() {
  var allFormData = JSON.parse(sessionStorage.getItem("forms"))
  var forms = Array.from(document.forms);
  loadFormData(forms, allFormData);
  for (form of forms) {
    form.addEventListener("submit", ()=>{saveFormData(forms)});
  }
}
main();

function removeDeletedGraphIDs(displayDivName) {
  identifierList = GLOBALS.graphIdentifiers;
  var displayDiv = document.getElementById(displayDivName);
  for (input of Array.from(displayDiv.children)) {
    if (identifierList.indexOf(parseInt(input.firstChild.value)) == -1) {
      input.remove();
    }
  }
}

function getAllMultiformData(formIDs) {
  var allMultiformData = {};
  for (formID of formIDs) {
    var multiformData = getMultiformData(formID);
    if (Object.keys(multiformData).length > 0) {
      Object.assign(allMultiformData, multiformData);
    }
  }
  return allMultiformData;
}

function getMultiformData(formID) {
  var formData = {};
  var inputs = document.getElementById(formID.displayDiv).children;
  var displayDiv = document.getElementById(formID.displayDiv);
  if (inputs.length > 0) {formData[formID.displayDiv] = displayDiv.innerHTML;}
  return formData;
}

function setMultiformData(allMultiformData) {
  for (displayDivName in allMultiformData) {
    var excluded = ["deleteGraphsDisplayDiv"];
    if (excluded.indexOf(displayDivName) == -1) {
      var displayDiv = document.getElementById(displayDivName);
      displayDiv.innerHTML = allMultiformData[displayDivName];
      var multiformEvent = new Event("multiformChange");
      displayDiv.dispatchEvent(multiformEvent);
    }
  }
}

/* these radio buttons aren't inside a form because
   css doesn't have parent selectors yet */
function getSelectedRadioButton() {
  var buttons = document.querySelectorAll("[name=search]");
  for (button of buttons) {
    if (button.checked) {
      return button.value;
    }
  }
}

function setSelectedRadioButton(buttonValue) {
  var button = document.querySelector("[value=" + buttonValue + "]");
  button.checked = true;
}

function getDateTimeFields() {
  var fieldList = {
    "creatorDateTimePicker": undefined,
    "pathDateTimePicker": undefined
  };
  for (name in fieldList) {
    var field = document.getElementById(name);
    fieldList[name] = field.children[0].value;
  }
  return fieldList;
}

function setDateTimeFields(fieldList) {
  for (name in fieldList) {
    var field = document.getElementById(name);
    field.children[0].value = fieldList[name];
  }
}

function saveFormData(forms) {
  formDataString = makeParameterString(forms);
  sessionStorage.setItem("forms", formDataString);
}

function makeParameterString(forms) {
  var parsedForms = [];
  for (form of Array.from(forms)) {
    var data = new FormData(form);
    // safari support for restoring parameters in saved graphs
    if (!Array.from(data).length) {
      data = [];
      for (input of Array.from(form)) {
        if (input.name) {
          if (input.type == "checkbox") {
            if (input.checked) {
              data.push([input.name, input.value]);
            }
          }
          else {
            data.push([input.name, input.value]);
          }
        }
      }
    }
    var parsedForm = parseFormData(data);
    parsedForms.push(parsedForm);
  }
  var allFormData = {};
  allFormData["parameters"] = parsedForms;
  allFormData["radioDisplay"] = getSelectedRadioButton();
  var multiformData = getAllMultiformData(getMultiformIDs());
  var pathMultiformData = getAllMultiformData(getPathMultiformIDs());
  allFormData["multiforms"] = {};
  Object.assign(allFormData["multiforms"], multiformData);
  Object.assign(allFormData["multiforms"], pathMultiformData);
  allFormData["dateTimeFields"] = getDateTimeFields();
  return JSON.stringify(allFormData);
}

function parseFormData(formData) {
  var parsedFormData = {};
  for (data of Array.from(formData)) {
    if (data[0] !== "csrfmiddlewaretoken") {
      if (Array.isArray(parsedFormData[data[0]])) {
        parsedFormData[data[0]].push(data[1]);
      }
      else if (parsedFormData[data[0]]) {
          parsedFormData[data[0]] = [parsedFormData[data[0]]];
          parsedFormData[data[0]].push(data[1]);
      }
      else {
        parsedFormData[data[0]] = data[1];
      }
    }
  }
  return parsedFormData;
}

function loadFormData(forms, allFormData) {
  if (!allFormData) {return;}
  var savedData = allFormData["parameters"];
  if (savedData.length === 5) {
    savedData.shift();
  }
  if (forms.length !== savedData.length) {
    throw "Error: Saved form data differs from number of forms";
  }
  for (var i = 0; i < savedData.length; i++) {
    for (field of Array.from(forms[i])) {
      if (field.name in savedData[i]) {
        if (["text", "number", "hidden"].indexOf(field.type) != -1 ||
            ["SELECT"].indexOf(field.tagName) != -1) {
          field.value = savedData[i][field.name];
        }
        if (["checkbox", "radio"].indexOf(field.type) != -1) {
          console.log(savedData[i][field.name], field.value);
          if (savedData[i][field.name].indexOf(field.value) !== -1) {
            field.checked = true;
          }
        }
      }
    }
  }
  setSelectedRadioButton(allFormData["radioDisplay"]);
  setMultiformData(allFormData["multiforms"]);
  setDateTimeFields(allFormData["dateTimeFields"]);
  removeDeletedGraphIDs("savedGraphsDisplayDiv");
}
