# Environment Snapshot

Captured from the `31011` conda environment used by VS Code.

## Python

```text
Python 3.10.11
```

## Installed Packages

```text
Flask==3.1.3
mysql-connector-python==9.6.0
PyMySQL==1.1.2
pandas==2.3.3
numpy==2.2.6
scikit-learn==1.7.2
scipy==1.15.3
python-dotenv==1.2.2
matplotlib==3.10.8
ipykernel==6.29.5
statsmodels==0.14.6
PyKrige==1.7.3
```

## Required But Not Installed In 31011 Yet

```text
seaborn==0.13.2
```

`PyKrige` is installed in `31011` and is used for Ordinary Kriging. The code keeps an IDW fallback so the notebooks and backend still run if another environment does not have `PyKrige` installed.

Frontend visualization uses Plotly from a browser CDN, so no Node package is required for the current static frontend.
