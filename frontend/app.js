const state = {
  times: [],
  points: [],
  selectedIndex: 0,
};

const statusEl = document.querySelector("#status");
const mapEl = document.querySelector("#map");
const summaryEl = document.querySelector("#summary");
const selectedTimeEl = document.querySelector("#selected-time");
const sliderEl = document.querySelector("#time-slider");
const timeReadoutEl = document.querySelector("#time-readout");
const labelsEl = document.querySelector("#time-labels");
const variableEl = document.querySelector("#variable");
const runEl = document.querySelector("#run");

function selectedPoints() {
  const time = state.times[state.selectedIndex];
  return state.points.filter((point) => point.target_datetime === time);
}

function renderPlot(points) {
  if (!window.Plotly) {
    mapEl.innerHTML = '<div class="plotly-missing">Plotly 載入失敗，請確認網路或改用本機 Plotly 檔案。</div>';
    return;
  }

  const values = points.map((point) => Number(point.ar_pred));
  const trace = {
    type: "scatter",
    mode: "markers+text",
    x: points.map((point) => Number(point.lon)),
    y: points.map((point) => Number(point.lat)),
    text: values.map((value) => value.toFixed(1)),
    textposition: "top center",
    hovertemplate:
      "lon=%{x:.4f}<br>lat=%{y:.4f}<br>" +
      `${variableEl.value}=%{marker.color:.2f}<br>` +
      "<extra></extra>",
    marker: {
      size: 18,
      color: values,
      colorscale: "RdYlBu",
      reversescale: true,
      showscale: true,
      colorbar: {
        title: variableEl.value,
      },
      line: {
        color: "#ffffff",
        width: 1.5,
      },
    },
  };

  const layout = {
    margin: { l: 56, r: 24, t: 24, b: 52 },
    paper_bgcolor: "#ffffff",
    plot_bgcolor: "#f8fafc",
    dragmode: "pan",
    xaxis: {
      title: "Longitude",
      zeroline: false,
      gridcolor: "#dfe5eb",
    },
    yaxis: {
      title: "Latitude",
      zeroline: false,
      gridcolor: "#dfe5eb",
      scaleanchor: "x",
      scaleratio: 1,
    },
  };

  const config = {
    responsive: true,
    displaylogo: false,
    modeBarButtonsToRemove: ["lasso2d", "select2d"],
  };

  Plotly.react(mapEl, [trace], layout, config);
}

function render() {
  const points = selectedPoints();
  summaryEl.innerHTML = "";

  if (!state.times.length) {
    mapEl.innerHTML = "";
    selectedTimeEl.textContent = "No time selected";
    statusEl.textContent = "目前沒有預測資料，請先 Run Forecast。";
    timeReadoutEl.textContent = "--";
    return;
  }

  const time = state.times[state.selectedIndex];
  selectedTimeEl.textContent = time;
  timeReadoutEl.textContent = time;
  statusEl.textContent = `${variableEl.value}，共 ${state.times.length} 個小時預測`;

  if (!points.length) {
    mapEl.innerHTML = "";
    summaryEl.textContent = "這個時間點沒有預測資料。";
    return;
  }

  const values = points.map((point) => Number(point.ar_pred));
  const minValue = Math.min(...values);
  const maxValue = Math.max(...values);

  renderPlot(points);

  const avg = values.reduce((sum, value) => sum + value, 0) / Math.max(values.length, 1);
  const metrics = [
    ["Stations", points.length],
    ["Average", avg.toFixed(2)],
    ["Minimum", minValue.toFixed(2)],
    ["Maximum", maxValue.toFixed(2)],
  ];

  metrics.forEach(([label, value]) => {
    const row = document.createElement("div");
    row.className = "metric";
    row.innerHTML = `<span>${label}</span><strong>${value}</strong>`;
    summaryEl.appendChild(row);
  });
}

async function loadPredictions() {
  const variable = variableEl.value;
  const response = await fetch(`/api/predictions?variable=${encodeURIComponent(variable)}`);
  const data = await response.json();
  state.times = data.times;
  state.points = data.points;
  state.selectedIndex = 0;
  sliderEl.max = Math.max(state.times.length - 1, 0);
  sliderEl.value = 0;
  labelsEl.innerHTML = state.times.length
    ? `<span>${state.times[0]}</span><span>${state.times[state.times.length - 1]}</span>`
    : "";
  render();
}

async function runForecast() {
  runEl.disabled = true;
  statusEl.textContent = "正在產生預測...";
  const response = await fetch("/api/forecast/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ variable: variableEl.value, hours: 24, training_hours: 168 }),
  });
  const data = await response.json();
  statusEl.textContent = `完成，寫入 ${data.rows} 筆預測資料。`;
  runEl.disabled = false;
  await loadPredictions();
}

sliderEl.addEventListener("input", () => {
  state.selectedIndex = Number(sliderEl.value);
  render();
});

variableEl.addEventListener("change", loadPredictions);
runEl.addEventListener("click", runForecast);

loadPredictions().catch((error) => {
  statusEl.textContent = `載入失敗：${error.message}`;
});
