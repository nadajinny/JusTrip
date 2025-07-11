let recommendationData = [];  // 추천 장소 3개를 담는 전역 변수

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

function goToSection2() {
  const date = document.getElementById("hiddenDate").value;
  const place = document.getElementById("hiddenPlace").value;

  if (!date || !place) {
    alert("Please select both date and place.");
    return;
  }

  setDummyRecommendations();  // 카드 세팅

  document.getElementById("section1").classList.remove("active");
  document.getElementById("section2").classList.add("active");
}



function setDummyRecommendations() {
  recommendationData = [
    {
      "Name of Place": "1913 Songjeong Market",
      "Location": "13, Songjeong-ro, Gwangju",
      "Estimated Time to Travel": "10 minutes by taxi",
      "Description": "Market with youth and food.",
      "Cost": "15,000 - 25,000 KRW",
      "Website": "(http://1913songjung.com/)"
    },
    {
      "Name of Place": "Asia Culture Center",
      "Location": "38, Munhwajeondang-ro, Gwangju",
      "Estimated Time to Travel": "30 minutes by metro",
      "Description": "Arts and culture complex.",
      "Cost": "20,000 KRW",
      "Website": "(https://www.acc.go.kr/en/)"
    },
    {
      "Name of Place": "May 18th Liberty Park",
      "Location": "120, Sangmubyungsan-ro, Gwangju",
      "Estimated Time to Travel": "20 minutes by taxi",
      "Description": "Historical memorial site.",
      "Cost": "Free",
      "Website": "-"
    }
  ];

  const cards = document.querySelectorAll(".card");
  cards.forEach((card, index) => {
    card.innerText = `📍 ${recommendationData[index]["Name of Place"]}`;
    card.onclick = () => showPlaceDetail(index);  // 💡 이 부분이 핵심
  });
}


function backToSection1() {
  // Section2 숨기고 Section1 다시 보여주기
  document.getElementById("section2").classList.remove("active");   
  document.getElementById("section3").classList.remove("active");
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


function showPlaceDetail(index) {
  console.log("📍 카드 클릭됨! index =", index);
  const place = recommendationData[index];

  document.getElementById("placeName").innerText = place["Name of Place"] || "-";
  document.getElementById("placeLink").href = extractLink(place.Website);
  document.getElementById("placeLink").innerText = "Visit Website";

  document.getElementById("locationInfo").innerText = place.Location || "-";
  document.getElementById("timeInfo").innerText = place["Estimated Time to Travel"] || "-";
  document.getElementById("reasonInfo").innerText = place.Description || "-";
  document.getElementById("websiteInfo").innerText = extractLink(place.Website) || "-";

  // 하단 추가 정보 (간단히 파싱하거나 직접 설정)
  document.getElementById("costInfo").innerText = `Cost: ${place.Cost || "-"}`;
  document.getElementById("krwInfo").innerText = `KRW: 추출 필요`;
  document.getElementById("usdInfo").innerText = `USD: 추출 필요`;
  document.getElementById("clothesInfo").innerText = `Clothes: e.g. light & casual`;
  document.getElementById("itemsInfo").innerText = `Essentials: sunscreen, water`;

  document.getElementById("section2").classList.remove("active");
  document.getElementById("section3").classList.add("active");

}

// 링크만 추출하는 도우미 함수
function extractLink(text) {
  if (!text) return "#";
  const match = text.match(/\((https?:\/\/[^\s)]+)\)/);
  return match ? match[1] : text;
}
