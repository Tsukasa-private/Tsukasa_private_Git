main(GLOBALS.creatorIDToDicNames, GLOBALS.pred_desc_id_map, GLOBALS.dic_id_map);

function main(creatorIDToDicNames, pred_desc_id_map, dic_id_map) {

  var dateKeys = ["P_modified_time", "D_modified_time", "Dic_creation_time"];
  var deletedKeys = ["P_deleted", "D_deleted", "Dic_deleted"];
  var pNamesAndDescriptionsLimiter = makeLimiter(["P_name", "P_description"]);
  var allNamesLimiter = makeLimiter(["D_name", "P_name"]);
  var dicNamesLimiter = makeLimiter(["Dic_name"]);

  var formIDs = [
    {
      search: "creatorText",
      select: "creatorSelect",
      restrictionData: pred_desc_id_map,
      limiter: pNamesAndDescriptionsLimiter,
      timeKeys: ["P_modified_time", "D_modified_time"],
      deletedFlagKeys: ["P_deleted", "D_deleted"],
      dateTimePicker: "creatorDateTimePicker",
      nameKey: ["P_name"]
    },
    {
      search: "pathText",
      select: "pathSelect",
      restrictionData: pred_desc_id_map,
      limiter: allNamesLimiter,
      timeKeys: ["P_modified_time", "D_modified_time"],
      deletedFlagKeys: ["P_deleted", "D_deleted"],
      dateTimePicker: "pathDateTimePicker",
      nameKey: ["P_name", "D_name"]
    },
  ];

  for (formID of formIDs) {
    var search = document.getElementById(formID.search);
    var select = document.getElementById(formID.select);
    initSearchSelect(
      search,
      formID.dateTimePicker,
      formID.restrictionData,
      formID.limiter,
      formID.timeKeys,
      formID.deletedFlagKeys,
      formID.nameKey,
      select
    );
  }

  var creatorDicIDs = [
    {
      creatorDisplayDivID: "creatorIDDisplayDiv",
      dicSelectID: "creatorDictionarySelect",
      dateTimePicker: "creatorDateTimePicker",
      nameKey: ["Dic_name"]
    },
    {
      creatorDisplayDivID: "pathIDDisplayDiv",
      dicSelectID: "pathDictionarySelect",
      dateTimePicker: "pathDateTimePicker",
      nameKey: ["Dic_name"]
    },
  ];
  for (formID of creatorDicIDs) {
    var creatorDisplayDiv = document.getElementById(formID.creatorDisplayDivID);
    var dicSelect = document.getElementById(formID.dicSelectID);
    initCreatorDictionarySelect(
      creatorDisplayDiv,
      dicSelect,
      formID.dateTimePicker,
      creatorIDToDicNames,
      dic_id_map,
      dicNamesLimiter,
      ["Dic_modified_time"],
      ["Dic_deleted"], 
      formID.nameKey
    );
  }

}

function makeLimiter(keysToKeep) {
  return function(selectRestrictData) {
    return limitRestrictionData(keysToKeep, selectRestrictData);
  }
}

function limitRestrictionData(keysToKeep, selectRestrictData) {
  var limitedRestrictionData = [];
  for (item of selectRestrictData) {
    limitedRestrictionData.push(shrinkObject(keysToKeep, item));
  }
  return limitedRestrictionData;
}

function shrinkObject(keysToKeep, originalObject) {
  var shrunkenObject = {};
  for (key in originalObject) {
    if (keysToKeep.indexOf(key) !== -1) {
      shrunkenObject[key] = originalObject[key];
    }
  }
  return shrunkenObject;
}

function extractNewestRestrictionData(selectedDate, fastRestrictData, timeKeys, deletedFlagKeys) {
  var newRestrictionData = [];

  for (pmid in fastRestrictData) {
    for (did in fastRestrictData[pmid]) {      

      var comparableItems = fastRestrictData[pmid][did];

      var maxItem = false;
      var maxScore = 0;
      var deleted = false;
      for (item of comparableItems) {
        
        var timeOK = true;
        var isNewer = true;
        var itemScore = 0;
        for (timeKey of timeKeys) {
          if (timeKeys.indexOf("Dic_modified_time") != -1) {
            var timeConditional = item["Dic_creation_time"] > selectedDate;
          }
          else {
            var timeConditional = item[timeKey] > selectedDate;
          }
          if (timeConditional) {
            timeOK = false;
          }
        }
        if (timeOK) {

          for (timeKey of timeKeys) {
            if (maxItem && (item[timeKey] < maxItem[timeKey])) {
              isNewer = false;
            }
            else {
              itemScore++;
            }
            
          }

          if (isNewer && (itemScore >= maxScore)) {
            maxItem = item;
            maxScore = itemScore;
          }
        }
      }
      if (maxItem) {

        for (deletedFlagKey of deletedFlagKeys) {
          // hardcoding when instead this needs to be two functions
          // i don't have time, i'm sorry
          if (timeKeys.indexOf("Dic_modified_time") != -1) {
            var dateBetweenTimes = (maxItem["Dic_modified_time"] > selectedDate) && (maxItem["Dic_creation_time"] < selectedDate);
            var deleteConditional = maxItem[deletedFlagKey] && !dateBetweenTimes;
          }
          else {
            var deleteConditional = maxItem[deletedFlagKey];
          }
          if (deleteConditional) {
            deleted = true;
          }
        }
        if (!deleted) {
          newRestrictionData.push(maxItem);
        }

      }
      
    }

  }

  return newRestrictionData;
}

function addOption(select, optionName) {
  var option = document.createElement("option");
  option.text = optionName;
  option.value = optionName;
  select.add(option);
}

// add only options from names which contain text, and one default option
function addMatchingOptions(text, dateTimePickerID, selectRestrictData, limiter, timeKeys, deletedFlagKeys, nameKey, select) {

  addOption(select, "");
  var textx = text.split(" ");

  matches = getMatches(textx, dateTimePickerID, selectRestrictData, limiter, timeKeys, deletedFlagKeys);

  var usedNames = {};
  for (match of matches) {
    for (name of nameKey) {
      var optionName = match[name];
      if (!usedNames[optionName] && (nameKey.length == 1 || textx.every(word=>optionName.indexOf(word)!=-1))) {
        addOption(select, optionName);
        usedNames[optionName] = true;
      }
    }
  }

}

function getMatches(words, dateTimePickerID, selectRestrictData, limiter, timeKeys, deletedFlagKeys) {
  matchingItems = [];

  var formDate = $("#" + dateTimePickerID).datetimepicker(GLOBALS.dateTimeSettings).data("DateTimePicker").date();
  var date = formDate ? new Date(formDate) : new Date();

  var textKeys = ["D_name", "P_name", "Dic_name", "P_description"];

  for (item of limiter(extractNewestRestrictionData(date, selectRestrictData, timeKeys, deletedFlagKeys))) {

    var wordMatches = [];
    for (word of words) {
      wordObj = {"word": word, "value": false};
      wordMatches.push(wordObj);
    }
    
    for (key in item) {
      var isTextKey = textKeys.indexOf(key) !== -1;
      if (isTextKey) {
        for (word of words) {
          if (item[key]) {
            if (item[key].indexOf(word)!=-1) {
              wordMatches.find(item=>item.word == word).value = true;
            }
          }
        }
      }
    }
    var debug = words.filter(word=>["frac{1}", "2814"].indexOf(word)!=-1).length == words.length && item.P_name=="Coffin則 (id : 2814)";
    if (debug) {
      console.log(words);
      console.dir(wordMatches);
    }
    if (!wordMatches.filter(item=>!item.value).length) {
      if (debug) {console.log("added to results!");}
      matchingItems.push(item);
    }

  }

  return matchingItems;
}

function removeAllOptions(select) {
  select.options.length = 0;
}

function initSearchSelect(search, dateTimePickerID, selectRestrictData, limiter, timeKeys, deletedFlagKeys, nameKey, select) {

  // limit visible selections based on search
  function updateSelect() {
    removeAllOptions(select);
    addMatchingOptions(search.value, dateTimePickerID, selectRestrictData, limiter, timeKeys, deletedFlagKeys, nameKey, select);
  }

  search.addEventListener("keyup", updateSelect);

  removeAllOptions(select);
  addMatchingOptions(search.value, dateTimePickerID, selectRestrictData, limiter, timeKeys, deletedFlagKeys, nameKey, select);

  $("#" + dateTimePickerID).datetimepicker(GLOBALS.dateTimeSettings).on("dp.change", updateSelect);

  // on select, set search bar value
  select.addEventListener("change", function(e) {
    search.value = e.target.value;
  });

}

function initCreatorDictionarySelect(creatorDisplayDiv, dicSelect, dateTimePickerID, creatorIDToDicNames, selectRestrictData, limiter, timeKeys, deletedFlagKeys,  nameKey) {
  function updateSelect() {
    var choiceList = getMultiformChoices(creatorDisplayDiv.id)
    if (choiceList.length > 0) {
      removeAllOptions(dicSelect);
      var namesList = [];
      for (choice of choiceList) {
        namesList = namesList.concat(creatorIDToDicNames[choice]);
      }
      var choiceRestricted = {"mock": {}};
      for (dic_id in selectRestrictData["mock"]) {
        choiceRestricted["mock"][dic_id] = selectRestrictData["mock"][dic_id].filter((item)=>{return namesList.indexOf(item["Dic_name"]) !== -1});
      }
      console.dir(selectRestrictData);
      console.dir(choiceRestricted);
      addMatchingOptions("", dateTimePickerID, choiceRestricted, limiter, timeKeys, deletedFlagKeys, nameKey, dicSelect);
    }
    else {
      removeAllOptions(dicSelect);
      addMatchingOptions("", dateTimePickerID, selectRestrictData, limiter, timeKeys, deletedFlagKeys, nameKey, dicSelect);
    }
  }
  
  creatorDisplayDiv.addEventListener("multiformChange", updateSelect);
  $("#" + dateTimePickerID).datetimepicker(GLOBALS.dateTimeSettings).on("dp.change", updateSelect);
  
  var multiformEvent = new Event("multiformChange");
  creatorDisplayDiv.dispatchEvent(multiformEvent);
}

function getMultiformChoices(displayDivID) {
  var choices = [];
  var inputs = document.getElementById(displayDivID).children;
  for (input of Array.from(inputs)) {choices.push(input.firstChild.value);}
  return choices;
}
