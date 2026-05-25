# Notebook Workflow

這個資料夾用來放報告式實驗。每個 notebook 都會在 code cell 前加入 Markdown 說明，方便直接用在期末報告或 GitHub 文件中。

## Notebooks

1. `01_temperature_main.ipynb`
   - 針對 `temperature` 做 data type diagnosis、paper-aligned model training、rolling validation 與 prediction export。

2. `02_humidity_main.ipynb`
   - 針對 `humidity` 做同一套 workflow。

3. `03_wind_speed_main.ipynb`
   - 針對 `wind_speed` 做同一套 workflow。

4. `04_pressure_main.ipynb`
   - 針對 `pressure` 做同一套 workflow。

5. `05_paper_reproduction_simulation.ipynb`
   - 依照前一份 notebook 診斷出的 data type 產生一種 synthetic spatial case。
   - 復現 paper 中 Ordinary Kriging、ML 與 weighted Fusion model 的比較方式。
   - 繪製類似 Figure 3(a) 的 weight optimization surface，並標示 minimum。

`weather_data_training.ipynb` 保留為 template；正式報告建議使用上面四個 variable-specific notebooks。

## Frontend Frames

每個 variable notebook 跑完 rolling validation 並寫入 `predictions_hourly` 後，可以輸出前端播放用的 GeoPandas frames：

```powershell
python main\render_prediction_frames.py --variable temperature
python main\render_prediction_frames.py --variable humidity
python main\render_prediction_frames.py --variable wind_speed
python main\render_prediction_frames.py --variable pressure
```

或一次輸出四個 variable：

```powershell
python main\render_all_prediction_frames.py
```

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
