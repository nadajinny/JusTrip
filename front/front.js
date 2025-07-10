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

async function goToSection2() {
  const place = document.getElementById("placeInput").value.trim();
  if (!place) {
    alert("Please enter a place.");
    return;
  }

  const encodedPlace = encodeURIComponent(place);

  try {
    const response = await fetch(`/weather/places?loc=${encodedPlace}`);
    const data = await response.json();

    if (!data.places || data.places.length === 0) {
      alert("추천 장소가 없습니다.");
      return;
    }

    const container = document.getElementById("recommendationContainer");
    container.innerHTML = "";

    data.places.forEach((name) => {
      const div = document.createElement("div");
      div.classList.add("card");
      div.innerText = "📍 " + name.replace(/\*\*/g, ""); // ** 마크다운 제거
      container.appendChild(div);
    });

    // 섹션 전환
    document.getElementById("section1").classList.remove("active");
    document.getElementById("section2").classList.add("active");
  } catch (error) {
    console.error("Error:", error);
    alert("장소 추천을 불러오지 못했습니다.");
  }
}

function backToSection1() {
  // Section2 숨기고 Section1 다시 보여주기
  document.getElementById("section2").classList.remove("active");
  document.getElementById("section1").classList.add("active");

  // 👉 선택사항: 입력 초기화 (필요하면 사용)
  document.getElementById("hiddenDate").value = "";
  document.getElementById("hiddenPlace").value = "";

  // 날짜 버튼 초기화
  const dateButton = document.createElement("button");
  dateButton.className = "input-button";
  dateButton.id = "dateButton";
  dateButton.innerText = "Select date";
  dateButton.onclick = openDatePicker;
  const dateParent = document.getElementById("dateButton").parentNode;
  dateParent.replaceChild(dateButton, document.getElementById("dateButton"));

  // 장소 버튼 초기화
  const placeButton = document.createElement("button");
  placeButton.className = "input-button";
  placeButton.id = "placeButton";
  placeButton.innerText = "Select place";
  placeButton.onclick = openPlaceInput;
  const placeParent = document.getElementById("placeButton").parentNode;
  placeParent.replaceChild(placeButton, document.getElementById("placeButton"));
}
