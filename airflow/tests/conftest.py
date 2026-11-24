import sys
from pathlib import Path

# Make DAG packages (common, answer_recommendation, ...) importable like in Airflow
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dags"))
