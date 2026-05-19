# Spatio-Temporal Weather Forecasting System

Final project prototype for hourly weather forecasting with database ingestion, spatial modeling, model fusion, AR-based temporal forecasting, and a browser frontend.

## Environment

- Python: `3.10.11` using the `31011` conda environment
- Main dependencies are pinned in `requirements.txt`.
- Local secrets should be placed in `.env`, using `.env.example` as the template.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Then edit `.env` with your MySQL username and password.

Default database settings are written in the same style as the notebook examples:

```python
db_settings = {
    "server": "127.0.0.1",
    "user": "sammy",
    "password": "",
    "database": "homework",
    "charset": "utf8",
}
```

If you use conda, select the existing `31011` environment in VS Code and install missing packages there:

```powershell
conda activate 31011
pip install -r requirements.txt
```

Default forecast settings:

```text
TRAINING_HOURS=168
FORECAST_HOURS=24
AR_MAX_LAG=24
```

## Database Tables

The app expects these tables in the `spatial` database:

```sql
stations(station_id, station_name, lat, lon)
observations_hourly(station_id, datetime, temperature, humidity, wind_speed, wind_direction, pressure)
predictions_hourly(target_datetime, lat, lon, variable_name, kriging_pred, ml_pred, fusion_pred, ar_pred, kriging_variance, model_name, model_info)
```

You can keep the SQL version in `database/schema.sql` under GitHub for reproducibility.

## Run

```powershell
python backend\app.py
```

Open:

```text
http://127.0.0.1:5000
```

## Current Modeling Plan

1. Read the latest 7 days of hourly station observations from MySQL.
2. Train spatial models for one variable at a time using a rolling 168-hour window.
3. Produce Kriging prediction, ML prediction, and weighted fusion prediction.
4. Select AR lag automatically using validation error or information criteria.
5. Forecast the next 24 hours and save results into `predictions_hourly`.
6. Display forecasts with an interactive Plotly chart and an hourly time slider.
