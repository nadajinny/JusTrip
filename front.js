let recommendationData = [];  // 전역 변수로 추천 데이터 저장

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

// ✅ 서버에서 Gemini 추천 데이터 받아오기
async function fetchRecommendationsFromServer(place, budget = 50000) {
  try {
    const res = await fetch(`http://127.0.0.1:8000/weather/json?loc=${encodeURIComponent(place)}&budget_krw=${budget}`);
    const data = await res.json();

    const aiItems = data.ai_recommendations;
    recommendationData = aiItems.map(item => ({
      "Name of Place": item["Name of Place"],
      "Location": item["Location"],
      "Estimated Time to Travel": item["Estimated Travel Time"],
      "Description": item["Description"],
      "Website": item["Website"],
      "Cost": `${item["Cost_KRW"]} KRW / ${item["Cost_USD"]} USD`
    }));

    setRecommendations();
  } catch (err) {
    alert("추천 데이터를 불러오는 데 실패했습니다.");
    console.error(err);
  }
}

// ✅ 카드 구성
function setRecommendations() {
  const container = document.querySelector(".recommendations");
  container.innerHTML = "";  // 기존 카드 모두 제거

  recommendationData.forEach((place, index) => {
    const card = document.createElement("div");
    card.className = "card";
    card.innerText = `📍 ${place["Name of Place"]}`;
    card.onclick = () => showPlaceDetail(index);  // 🔥 클릭 연결
    container.appendChild(card);
  });
}

// ✅ section1 → section2로 이동
function goToSection2() {
  const date = document.getElementById("hiddenDate").value;
  const place = document.getElementById("hiddenPlace").value;

  if (!date || !place) {
    alert("Please select both date and place.");
    return;
  }

  fetchRecommendationsFromServer(place, 50000); // 서버에서 동적 데이터 받아오기

  document.getElementById("section1").classList.remove("active");
  document.getElementById("section2").classList.add("active");
}

// ✅ section3 상세 정보 출력
function showPlaceDetail(index) {
  console.log("✅ showPlaceDetail() 호출됨. index =", index);

  const place = recommendationData[index];
  if (!place) {
    console.warn("❌ 해당 index의 데이터가 recommendationData에 없음.");
    return;
  }

  console.log("🧩 보여줄 place 정보:", place);

  // 각 요소가 존재하는지 확인
  const placeNameElem = document.getElementById("placeName");
  const section3 = document.getElementById("section3");

  if (!placeNameElem || !section3) {
    console.error("❌ DOM 요소를 찾을 수 없습니다.");
    return;
  }

  // 값 삽입
  placeNameElem.innerText = place["Name of Place"] || "-";
  document.getElementById("placeLink").href = extractLink(place.Website);
  document.getElementById("placeLink").innerText = "Visit Website";
  document.getElementById("locationInfo").innerText = place.Location || "-";
  document.getElementById("timeInfo").innerText = place["Estimated Travel Time"] || "-";
  document.getElementById("reasonInfo").innerText = place.Description || "-";
  document.getElementById("websiteInfo").innerText = extractLink(place.Website) || "-";
  const krw = place.cost_krw || 0;
  const usd = place.cost_usd || 0;

  document.getElementById("costInfo").innerText =
    `Cost: ${krw.toLocaleString()} KRW / $${usd.toFixed(2)} USD`;
  document.getElementById("krwInfo").innerText = `KRW: ${krw.toLocaleString()}원`;
  document.getElementById("usdInfo").innerText = `USD: $${usd.toFixed(2)}`;


  document.getElementById("clothesInfo").innerText = `Clothes: e.g. light & casual`;
  document.getElementById("itemsInfo").innerText = `Essentials: sunscreen, water`;

  console.log("🎯 Section2 → Section3 화면 전환 시도");

  document.getElementById("section2").classList.remove("active");
  section3.classList.add("active");

  console.log("✅ 화면 전환 완료: section3이 활성화됨");
}


// ✅ 링크 추출 헬퍼
function extractLink(text) {
  if (!text) return "#";
  const match = text.match(/\((https?:\/\/[^\s)]+)\)/);
  return match ? match[1] : text;
}

// ✅ section1으로 돌아가기
function backToSection1() {
  document.getElementById("section2").classList.remove("active");
  document.getElementById("section3").classList.remove("active");
  document.getElementById("section1").classList.add("active");

  // 입력 초기화
  document.getElementById("hiddenDate").value = "";
  document.getElementById("hiddenPlace").value = "";

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
}

function goToSection4() {
  // 섹션 전환
  document.getElementById("section2").classList.remove("active");
  document.getElementById("section4").classList.add("active");

  // 지도가 초기화되어 있지 않다면 생성
  if (!window.mapInitialized) {
    initMap(); // 지도 생성
    window.mapInitialized = true;
  }

  dropPins(); // 마커 추가
}

function backToSection2() {
  document.getElementById("section4").classList.remove("active");
  document.getElementById("section2").classList.add("active");
}

// Google Maps 초기화
async function initMap() {
  const mapsLib = await google.maps.importLibrary("maps");
  const markerLib = await google.maps.importLibrary("marker");
  AdvancedMarkerElement = markerLib.AdvancedMarkerElement;

  map = new mapsLib.Map(document.getElementById("map"), {
    center: { lat: 37.5665, lng: 126.978 }, // 서울
    zoom: 12,
    mapId: "DEMO_MAP_ID", // 선택사항
  });

  dropPins(); // 맵 초기화 시 핀 표시
}

// 핀 추가 함수
function addPinsToMap() {
  if (!Array.isArray(MARKERS)) {
    console.error("MARKERS 배열이 유효하지 않습니다.");
    return;
  }

  MARKERS.forEach((data) => {
    const marker = new AdvancedMarkerElement({
      map: map,
      position: data.position,
      title: data.title,
    });

    const infoWindow = new google.maps.InfoWindow({
      content: data.infoContent,
    });

    marker.addListener("click", () => {
      infoWindows.forEach((iw) => iw.close());
      infoWindow.open(map, marker);
    });

    markers.push(marker);
    infoWindows.push(infoWindow);
  });

  // 모든 마커 포함되도록 지도 범위 재설정
  if (markers.length > 0) {
    const bounds = new google.maps.LatLngBounds();
    markers.forEach((marker) => bounds.extend(marker.position));
    map.fitBounds(bounds);
  }
}

// 버튼 클릭 시 핀 표시
function dropPins() {
  if (!map) {
    console.error("지도가 아직 초기화되지 않았습니다.");
    return;
  }

  if (markers.length > 0) {
    console.log("이미 마커가 추가됨");
    return;
  }

  addPinsToMap();
}