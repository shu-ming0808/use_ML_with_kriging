# Notebook Workflow

這個資料夾用來放報告式實驗。每個 notebook 都會在 code cell 前加入 Markdown 說明，方便直接用在期末報告或 GitHub 文件中。

## Notebooks

1. `01_weather_data_diagnosis_and_training.ipynb`
   - 從 MySQL 讀取最近 7 天的小時天氣 observation。
   - 判斷資料比較接近 Gaussian、trend、non-stationary，或 skewed/lognormal behavior。
   - 執行 paper-aligned training/backtesting workflow，比較 Ordinary Kriging、Super Learner、Optimized Fusion model 與 AutoAR-style temporal forecasting。

2. `02_paper_reproduction_simulation.ipynb`
   - 依照前一份 notebook 診斷出的 data type 產生一種 synthetic spatial case。
   - 復現 paper 中 Ordinary Kriging、ML 與 weighted Fusion model 的比較方式。
   - 繪製類似 Figure 3(a) 的 weight optimization surface，並標示 minimum。

## VS Code Setup

安裝 notebook 支援套件：

```powershell
pip install -r requirements.txt
```

接著在 VS Code 開啟 `.ipynb`，並選擇 project Python kernel。

## Boundary GeoJSON

如果要使用正式 Taiwan boundary，可以先用 `geopandas` 在 `main/` 轉檔，再輸出給 frontend：

```powershell
python main\export_boundary_geojson.py path\to\official_boundary.shp
```

輸出位置：

```text
frontend/assets/taiwan.geojson
```
