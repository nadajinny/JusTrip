function openDatePicker() {
  const button = document.getElementById("dateButton");
  const input = document.createElement("input");

  input.type = "date";
  input.id = "dateInput";
  input.className = "input-button";
  input.style.width = "220px";

  input.addEventListener("change", () => {
    const selectedDate = input.value;
    document.getElementById("hiddenDate").value = selectedDate;

    const newButton = document.createElement("button");
    newButton.innerText = selectedDate;
    newButton.className = "input-button";
    newButton.id = "dateButton";
    newButton.onclick = openDatePicker;

    input.parentNode.replaceChild(newButton, input);
  });

  button.parentNode.replaceChild(input, button);
  input.focus();
}

function openPlaceInput() {
  const button = document.getElementById("placeButton");
  const input = document.createElement("input");

  input.type = "text";
  input.id = "placeInput";
  input.placeholder = "Enter place";
  input.className = "input-button";
  input.style.width = "220px";

  input.addEventListener("blur", () => {
    const placeValue = input.value.trim();
    document.getElementById("hiddenPlace").value = placeValue;

    const newButton = document.createElement("button");
    newButton.innerText = placeValue || "Select place";
    newButton.className = "input-button";
    newButton.id = "placeButton";
    newButton.onclick = openPlaceInput;

    input.parentNode.replaceChild(newButton, input);
  });

  button.parentNode.replaceChild(input, button);
  input.focus();
}

function openInterestInput() {
  const button = document.getElementById("interestButton");
  const input = document.createElement("input");

  input.type = "text";
  input.id = "interestInput";
  input.placeholder = "Enter interest";
  input.className = "input-button";
  input.style.width = "220px";

  input.addEventListener("blur", () => {
    const interestValue = input.value.trim();
    document.getElementById("hiddenInterest").value = interestValue;

    const newButton = document.createElement("button");
    newButton.innerText = interestValue || "Select interest";
    newButton.className = "input-button";
    newButton.id = "interestButton";
    newButton.onclick = openInterestInput;

    input.parentNode.replaceChild(newButton, input);
  });

  button.parentNode.replaceChild(input, button);
  input.focus();
}

function goToSection2() {
  const date = document.getElementById("hiddenDate").value;
  const place = document.getElementById("hiddenPlace").value;
  const interest = document.getElementById("hiddenInterest").value;

  if (!date || !place || !interest) {
    alert("Please select date, place, and interest.");
    return;
  }

  document.getElementById("section1").classList.remove("active");
  document.getElementById("section2").classList.add("active");
}

function backToSection1() {
  document.getElementById("section2").classList.remove("active");
  document.getElementById("section1").classList.add("active");

  document.getElementById("hiddenDate").value = "";
  document.getElementById("hiddenPlace").value = "";
  document.getElementById("hiddenInterest").value = "";

  const dateButton = document.createElement("button");
  dateButton.className = "input-button";
  dateButton.id = "dateButton";
  dateButton.innerText = "Select date";
  dateButton.onclick = openDatePicker;
  const dateParent = document.getElementById("dateButton").parentNode;
  dateParent.replaceChild(dateButton, document.getElementById("dateButton"));

  const placeButton = document.createElement("button");
  placeButton.className = "input-button";
  placeButton.id = "placeButton";
  placeButton.innerText = "Select place";
  placeButton.onclick = openPlaceInput;
  const placeParent = document.getElementById("placeButton").parentNode;
  placeParent.replaceChild(placeButton, document.getElementById("placeButton"));

  const interestButton = document.createElement("button");
  interestButton.className = "input-button";
  interestButton.id = "interestButton";
  interestButton.innerText = "Select interest";
  interestButton.onclick = openInterestInput;
  const interestParent = document.getElementById("interestButton").parentNode;
  interestParent.replaceChild(interestButton, document.getElementById("interestButton"));
}