main();

function main() {

  var formData = [
    {"formName": "creatorSearchForm", "submitButtonName": "creatorSearchSubmit"},
    {"formName": "pathSearchForm", "submitButtonName": "pathSearchSubmit"},
  ];

  for (data of formData) {
    var submitButton = document.getElementById(data.submitButtonName);
    submitButton.addEventListener("click", makeSubmitHandler(data.formName));
  }

}

function makeSubmitHandler(formName) {
  return (event)=>{
    if (event.isTrusted) {
      event.preventDefault();
      var form = document.getElementById(formName)
      var validated = validateForm(form);
      if (validated) {
        form.dispatchEvent(new Event("submit"));
        form.querySelector("[type=submit]").click();
      }
      else {
        alert("Please enter correct date in the following format: YYYY/MM/DD hh:mm:ss");
      }
      return false;
    }
    else {
      return true;
    }
  };
}

function validateForm(form) {
  var validated = false;

  var dateTimePicker = form.getElementsByClassName("input-group date")[0];

  if (!$(dateTimePicker).data("DateTimePicker").date()) {
    $(dateTimePicker).data("DateTimePicker").date(new Date());
    form.querySelector("[name=dateWasSelected]").value = "No";
  }
  else {
    form.querySelector("[name=dateWasSelected]").value = "Yes";
  }


  var dateTimeValue = dateTimePicker.children[0].value;
  var dateTimeIsValid = !isNaN(new Date(dateTimeValue));
  validated = validated || dateTimeIsValid;

  // var requiredUnfilled = Array.from(form.querySelectorAll("[required]")).filter(item=>!item.value).length > 0

  // if (requiredUnfilled) {validated = false;}

  return validated;
}
