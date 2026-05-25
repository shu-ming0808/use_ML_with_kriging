const state = {
  times: [],
  points: [],
  frames: [],
  frameValueColumn: "",
  frameViewer: null,
  frameImages: [],
  activeFrameImage: 0,
  activeFrameSrc: "",
  frameRenderToken: 0,
  selectedIndex: 0,
  timer: null,
  hasFrames: false,
};

const statusEl = document.querySelector("#status");
const mapEl = document.querySelector("#map");
const summaryEl = document.querySelector("#summary");
const selectedTimeEl = document.querySelector("#selected-time");
const selectedLayerEl = document.querySelector("#selected-layer");
const sliderEl = document.querySelector("#time-slider");
const timeSelectEl = document.querySelector("#time-select");
const timeReadoutEl = document.querySelector("#time-readout");
const labelsEl = document.querySelector("#time-labels");
const variableEl = document.querySelector("#variable");
const modelValueEl = document.querySelector("#model-value");
const runEl = document.querySelector("#run");
const playEl = document.querySelector("#play");
const pauseEl = document.querySelector("#pause");
const loopEl = document.querySelector("#loop");
const speedEl = document.querySelector("#speed");
const speedLabelEl = document.querySelector("#speed-label");

const COLORSCALE = [
  [0.0, "#2c7bb6"],
  [0.22, "#00a6ca"],
  [0.4, "#abd9e9"],
  [0.56, "#ffffbf"],
  [0.72, "#fdae61"],
  [0.88, "#f46d43"],
  [1.0, "#d7191c"],
];

const MAP_BOUNDS = {
  lonMin: 116.25,
  lonMax: 122.82,
  latMin: 21.55,
  latMax: 25.47,
};

function numericValue(point) {
  const key = modelValueEl.value;
  const candidates =
    key === "auto"
      ? ["fusion_pred", "fixed_half_pred", "ml_pred", "kriging_pred", "ar_pred"]
      : [key, "fusion_pred", "fixed_half_pred", "ml_pred", "kriging_pred"];

  for (const candidate of candidates) {
    if (point[candidate] === null || point[candidate] === undefined || point[candidate] === "") {
      continue;
    }
    const value = Number(point[candidate]);
    if (Number.isFinite(value)) {
      return value;
    }
  }
  return NaN;
}

function selectedPoints() {
  const time = state.times[state.selectedIndex];
  return state.points
    .filter((point) => point.target_datetime === time)
    .map((point) => ({ ...point, display_value: numericValue(point) }))
    .filter((point) => Number.isFinite(point.display_value));
}

function linspace(min, max, count) {
  if (count <= 1) return [min];
  const step = (max - min) / (count - 1);
  return Array.from({ length: count }, (_, index) => min + step * index);
}

function buildSurface(points, gridSize = 80) {
  const lons = points.map((point) => Number(point.lon));
  const lats = points.map((point) => Number(point.lat));
  const values = points.map((point) => Number(point.display_value));
  const xs = linspace(MAP_BOUNDS.lonMin, MAP_BOUNDS.lonMax, gridSize);
  const ys = linspace(MAP_BOUNDS.latMin, MAP_BOUNDS.latMax, gridSize);
  const z = ys.map((lat) =>
    xs.map((lon) => {
      let numerator = 0;
      let denominator = 0;
      for (let i = 0; i < points.length; i += 1) {
        const dx = lon - lons[i];
        const dy = lat - lats[i];
        const distanceSquared = dx * dx + dy * dy;
        if (distanceSquared < 1e-10) {
          return values[i];
        }
        const weight = 1 / distanceSquared;
        numerator += weight * values[i];
        denominator += weight;
      }
      return numerator / denominator;
    }),
  );
  return { xs, ys, z, values };
}

async function loadFrameManifest(variable) {
  try {
    const response = await fetch(`/assets/frames/${variable}/manifest.json`, { cache: "no-store" });
    if (!response.ok) {
      state.frames = [];
      state.hasFrames = false;
      return false;
    }
    const manifest = await response.json();
    state.frames = Array.isArray(manifest.frames) ? manifest.frames : [];
    state.frameValueColumn = manifest.value_column || "";
    state.hasFrames = state.frames.length > 0;
    return state.hasFrames;
  } catch {
    state.frames = [];
    state.frameValueColumn = "";
    state.hasFrames = false;
    return false;
  }
}

function ensureFrameViewer() {
  if (state.frameViewer && mapEl.contains(state.frameViewer)) {
    return;
  }

  mapEl.innerHTML = "";
  const viewer = document.createElement("div");
  viewer.className = "frame-viewer";

  state.frameImages = [0, 1].map((index) => {
    const image = document.createElement("img");
    image.className = "surface-frame";
    image.alt = "";
    image.draggable = false;
    image.dataset.buffer = String(index);
    viewer.appendChild(image);
    return image;
  });

  state.frameViewer = viewer;
  state.activeFrameImage = 0;
  state.activeFrameSrc = "";
  mapEl.appendChild(viewer);
}

function preloadNearbyFrames(index) {
  [index + 1, index + 2].forEach((nextIndex) => {
    const frame = state.frames[nextIndex];
    if (!frame) return;
    const image = new Image();
    image.src = frame.src;
  });
}

function renderFrame() {
  const frame = state.frames[state.selectedIndex];
  if (!frame) {
    mapEl.innerHTML = "";
    summaryEl.textContent = "這個時間點沒有可顯示的 frame。";
    return;
  }

  ensureFrameViewer();
  preloadNearbyFrames(state.selectedIndex);

  if (state.activeFrameSrc !== frame.src) {
    const token = (state.frameRenderToken += 1);
    const nextImageIndex = 1 - state.activeFrameImage;
    const nextImage = state.frameImages[nextImageIndex];
    const currentImage = state.frameImages[state.activeFrameImage];

    nextImage.alt = `${variableEl.value} prediction surface ${frame.time}`;
    nextImage.onload = () => {
      if (token !== state.frameRenderToken) return;
      currentImage.classList.remove("is-active");
      nextImage.classList.add("is-active");
      state.activeFrameImage = nextImageIndex;
      state.activeFrameSrc = frame.src;
    };

    if (nextImage.getAttribute("src") === frame.src) {
      nextImage.onload();
    } else {
      nextImage.src = frame.src;
    }
  }

  summaryEl.innerHTML = "";
  const metrics = [
    ["Frame", `${state.selectedIndex + 1} / ${state.frames.length}`],
    ["Source", "GeoPandas"],
    ["Layer", state.frameValueColumn || modelValueEl.value],
    ["Variable", variableEl.value],
  ];
  metrics.forEach(([label, value]) => {
    const row = document.createElement("div");
    row.className = "metric";
    row.innerHTML = `<span>${label}</span><strong>${value}</strong>`;
    summaryEl.appendChild(row);
  });
}

function renderPlot(points) {
  if (!window.Plotly) {
    mapEl.innerHTML = '<div class="plotly-missing">Plotly 載入失敗，請確認網路或改用本機 Plotly 檔案。</div>';
    return;
  }

  const surface = buildSurface(points);
  const minValue = Math.min(...surface.values);
  const maxValue = Math.max(...surface.values);

  const heatmap = {
    type: "heatmap",
    name: "surface",
    x: surface.xs,
    y: surface.ys,
    z: surface.z,
    colorscale: COLORSCALE,
    zmin: minValue,
    zmax: maxValue,
    opacity: 0.86,
    colorbar: {
      title: variableEl.value,
      thickness: 14,
      len: 0.74,
    },
    hoverinfo: "skip",
  };

  const stations = {
    type: "scatter",
    name: "stations",
    mode: "markers",
    x: points.map((point) => Number(point.lon)),
    y: points.map((point) => Number(point.lat)),
    text: points.map((point) => `${point.variable_name}<br>${point.display_value.toFixed(2)}`),
    marker: {
      size: 4,
      color: "#111827",
      opacity: 0.62,
    },
    showlegend: false,
    hoverinfo: "skip",
  };

  const layout = {
    margin: { l: 54, r: 44, t: 18, b: 44 },
    paper_bgcolor: "#ffffff",
    plot_bgcolor: "#f6f8fa",
    dragmode: "pan",
    hovermode: false,
    xaxis: {
      title: "Longitude",
      zeroline: false,
      gridcolor: "rgba(70, 82, 95, 0.32)",
      showgrid: true,
      range: [MAP_BOUNDS.lonMin, MAP_BOUNDS.lonMax],
      fixedrange: false,
    },
    yaxis: {
      title: "Latitude",
      zeroline: false,
      gridcolor: "rgba(70, 82, 95, 0.32)",
      showgrid: true,
      scaleanchor: "x",
      scaleratio: 1,
      range: [MAP_BOUNDS.latMin, MAP_BOUNDS.latMax],
      fixedrange: false,
    },
    annotations: [
      {
        xref: "paper",
        yref: "paper",
        x: 0.02,
        y: 0.98,
        text: selectedTimeEl.textContent,
        showarrow: false,
        font: { size: 26, color: "rgba(23, 32, 42, 0.62)" },
        align: "left",
      },
      {
        xref: "paper",
        yref: "paper",
        x: 0.98,
        y: 0.98,
        text: "Model Surface",
        showarrow: false,
        font: { size: 20, color: "rgba(23, 32, 42, 0.48)" },
        align: "right",
      },
    ],
  };

  const config = {
    responsive: true,
    displaylogo: false,
    staticPlot: false,
    modeBarButtonsToRemove: ["lasso2d", "select2d"],
  };

  Plotly.react(mapEl, [heatmap, stations], layout, config);
}

function renderSummary(points) {
  const values = points.map((point) => point.display_value);
  const avg = values.reduce((sum, value) => sum + value, 0) / Math.max(values.length, 1);
  const metrics = [
    ["Stations", points.length],
    ["Average", avg.toFixed(2)],
    ["Minimum", Math.min(...values).toFixed(2)],
    ["Maximum", Math.max(...values).toFixed(2)],
  ];

  summaryEl.innerHTML = "";
  metrics.forEach(([label, value]) => {
    const row = document.createElement("div");
    row.className = "metric";
    row.innerHTML = `<span>${label}</span><strong>${value}</strong>`;
    summaryEl.appendChild(row);
  });
}

function render() {
  if (!state.times.length) {
    mapEl.innerHTML = "";
    summaryEl.innerHTML = "";
    selectedTimeEl.textContent = "No time selected";
    statusEl.textContent = "目前沒有預測資料，請先 Run Forecast 或執行 notebook rolling prediction。";
    timeReadoutEl.textContent = "--";
    return;
  }

  const time = state.times[state.selectedIndex];
  selectedTimeEl.textContent = time;
  timeReadoutEl.textContent = time;
  timeSelectEl.value = String(state.selectedIndex);
  selectedLayerEl.textContent = state.hasFrames && state.frameValueColumn ? state.frameValueColumn : modelValueEl.value;
  statusEl.textContent = `${variableEl.value}，共 ${state.times.length} 個小時 surface`;

  if (state.hasFrames) {
    renderFrame();
    return;
  }

  const points = selectedPoints();

  if (!points.length) {
    mapEl.innerHTML = "";
    summaryEl.textContent = "這個時間點沒有可顯示的預測資料。";
    return;
  }

  renderPlot(points);
  renderSummary(points);
}

function syncTimeControls() {
  sliderEl.max = Math.max(state.times.length - 1, 0);
  sliderEl.value = state.selectedIndex;
  timeSelectEl.innerHTML = "";
  state.times.forEach((time, index) => {
    const option = document.createElement("option");
    option.value = String(index);
    option.textContent = time;
    timeSelectEl.appendChild(option);
  });
  labelsEl.innerHTML = state.times.length
    ? `<span>${state.times[0]}</span><span>${state.times[state.times.length - 1]}</span>`
    : "";
}

async function loadPredictions() {
  stopAnimation();
  state.frameViewer = null;
  state.frameImages = [];
  state.activeFrameSrc = "";
  state.frameRenderToken += 1;
  const variable = variableEl.value;
  const hasFrames = await loadFrameManifest(variable);
  if (hasFrames) {
    state.points = [];
    state.times = state.frames.map((frame) => frame.time);
    state.selectedIndex = 0;
    syncTimeControls();
    render();
    return;
  }

  const response = await fetch(`/api/predictions?variable=${encodeURIComponent(variable)}`);
  const data = await response.json();
  state.times = data.times;
  state.points = data.points;
  state.frames = [];
  state.frameValueColumn = "";
  state.hasFrames = false;
  state.selectedIndex = 0;
  syncTimeControls();
  render();
}

async function runForecast() {
  stopAnimation();
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

function setIndex(index) {
  state.selectedIndex = Math.min(Math.max(index, 0), Math.max(state.times.length - 1, 0));
  sliderEl.value = state.selectedIndex;
  timeSelectEl.value = String(state.selectedIndex);
  render();
}

function stopAnimation() {
  if (state.timer) {
    clearInterval(state.timer);
    state.timer = null;
  }
}

function startAnimation() {
  if (!state.times.length) return;
  stopAnimation();
  const interval = Number(speedEl.value) * 1000;
  state.timer = setInterval(() => {
    if (state.selectedIndex >= state.times.length - 1) {
      if (!loopEl.checked) {
        stopAnimation();
        return;
      }
      setIndex(0);
      return;
    }
    setIndex(state.selectedIndex + 1);
  }, interval);
}

sliderEl.addEventListener("input", () => {
  stopAnimation();
  setIndex(Number(sliderEl.value));
});

timeSelectEl.addEventListener("change", () => {
  stopAnimation();
  setIndex(Number(timeSelectEl.value));
});

variableEl.addEventListener("change", loadPredictions);
modelValueEl.addEventListener("change", render);
runEl.addEventListener("click", runForecast);
playEl.addEventListener("click", startAnimation);
pauseEl.addEventListener("click", stopAnimation);
speedEl.addEventListener("input", () => {
  speedLabelEl.textContent = `${Number(speedEl.value).toFixed(1)}s`;
  if (state.timer) startAnimation();
});

loadPredictions().catch((error) => {
  statusEl.textContent = `載入失敗：${error.message}`;
});
