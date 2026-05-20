from __future__ import annotations

import mysql.connector
import pandas as pd

from config import db_settings


def get_connection():
    return mysql.connector.connect(
        host=db_settings["server"],
        port=db_settings["port"],
        user=db_settings["user"],
        password=db_settings["password"],
        database=db_settings["database"],
        charset=db_settings["charset"],
    )


def ensure_predictions_schema() -> None:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.columns
            WHERE table_schema = DATABASE()
              AND table_name = 'predictions_hourly'
              AND column_name = 'fixed_half_pred'
            """
        )
        exists = cursor.fetchone()[0] > 0
        if not exists:
            cursor.execute("ALTER TABLE predictions_hourly ADD COLUMN fixed_half_pred FLOAT AFTER ml_pred")
            conn.commit()


def read_observations(variable: str, limit_hours: int = 168) -> pd.DataFrame:
    allowed = {"temperature", "humidity", "wind_speed", "wind_direction", "pressure"}
    if variable not in allowed:
        raise ValueError(f"Unsupported variable: {variable}")

    query = f"""
        SELECT
            o.station_id,
            s.station_name,
            s.lat,
            s.lon,
            o.datetime,
            o.{variable} AS value
        FROM observations_hourly o
        JOIN stations s ON s.station_id = o.station_id
        WHERE o.{variable} IS NOT NULL
          AND o.datetime >= (
              SELECT DATE_SUB(MAX(datetime), INTERVAL %s HOUR)
              FROM observations_hourly
          )
        ORDER BY o.datetime, o.station_id
    """

    with get_connection() as conn:
        return pd.read_sql(query, conn, params=(limit_hours,))


def read_observations_range(variable: str, start_datetime: str, end_datetime: str) -> pd.DataFrame:
    allowed = {"temperature", "humidity", "wind_speed", "wind_direction", "pressure"}
    if variable not in allowed:
        raise ValueError(f"Unsupported variable: {variable}")

    query = f"""
        SELECT
            o.station_id,
            s.station_name,
            s.lat,
            s.lon,
            o.datetime,
            o.{variable} AS value
        FROM observations_hourly o
        JOIN stations s ON s.station_id = o.station_id
        WHERE o.{variable} IS NOT NULL
          AND o.datetime >= %s
          AND o.datetime <= %s
        ORDER BY o.datetime, o.station_id
    """

    with get_connection() as conn:
        return pd.read_sql(query, conn, params=(start_datetime, end_datetime))


def read_predictions(variable: str) -> pd.DataFrame:
    ensure_predictions_schema()
    query = """
        SELECT
            target_datetime,
            lat,
            lon,
            variable_name,
            kriging_pred,
            ml_pred,
            fixed_half_pred,
            fusion_pred,
            ar_pred,
            kriging_variance,
            model_name,
            model_info
        FROM predictions_hourly
        WHERE variable_name = %s
        ORDER BY target_datetime, lat, lon
    """

    with get_connection() as conn:
        return pd.read_sql(query, conn, params=(variable,))


def upsert_predictions(rows: list[dict]) -> int:
    if not rows:
        return 0
    ensure_predictions_schema()

    sql = """
        INSERT INTO predictions_hourly (
            target_datetime,
            lat,
            lon,
            variable_name,
            kriging_pred,
            ml_pred,
            fixed_half_pred,
            fusion_pred,
            ar_pred,
            kriging_variance,
            model_name,
            model_info
        )
        VALUES (
            %(target_datetime)s,
            %(lat)s,
            %(lon)s,
            %(variable_name)s,
            %(kriging_pred)s,
            %(ml_pred)s,
            %(fixed_half_pred)s,
            %(fusion_pred)s,
            %(ar_pred)s,
            %(kriging_variance)s,
            %(model_name)s,
            %(model_info)s
        )
        ON DUPLICATE KEY UPDATE
            kriging_pred = VALUES(kriging_pred),
            ml_pred = VALUES(ml_pred),
            fixed_half_pred = VALUES(fixed_half_pred),
            fusion_pred = VALUES(fusion_pred),
            ar_pred = VALUES(ar_pred),
            kriging_variance = VALUES(kriging_variance),
            model_name = VALUES(model_name),
            model_info = VALUES(model_info)
    """

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.executemany(sql, rows)
        conn.commit()
        return cursor.rowcount
