CREATE TABLE IF NOT EXISTS stations (
    station_id VARCHAR(20) PRIMARY KEY,
    station_name VARCHAR(100),
    lat DOUBLE NOT NULL,
    lon DOUBLE NOT NULL
);

CREATE TABLE IF NOT EXISTS observations_hourly (
    id INT AUTO_INCREMENT PRIMARY KEY,
    station_id VARCHAR(20) NOT NULL,
    datetime DATETIME NOT NULL,
    temperature FLOAT,
    humidity FLOAT,
    wind_speed FLOAT,
    wind_direction FLOAT,
    pressure FLOAT,
    UNIQUE KEY uq_station_time (station_id, datetime),
    INDEX idx_observations_datetime (datetime),
    CONSTRAINT fk_observations_station
        FOREIGN KEY (station_id)
        REFERENCES stations(station_id)
);

CREATE TABLE IF NOT EXISTS predictions_hourly (
    id INT AUTO_INCREMENT PRIMARY KEY,
    target_datetime DATETIME NOT NULL,
    lat DOUBLE NOT NULL,
    lon DOUBLE NOT NULL,
    variable_name VARCHAR(50) NOT NULL,
    kriging_pred FLOAT,
    ml_pred FLOAT,
    fusion_pred FLOAT,
    ar_pred FLOAT,
    kriging_variance FLOAT,
    model_name VARCHAR(100),
    model_info TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_prediction_point_time (target_datetime, lat, lon, variable_name),
    INDEX idx_predictions_time_variable (target_datetime, variable_name)
);
