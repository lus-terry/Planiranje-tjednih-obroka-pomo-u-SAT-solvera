from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]  # .../meal-planner

MEALS_CSV = PROJECT_ROOT / "data" / "raw" / "meals_spoonacular.csv"

OUTPUTS_DIR = PROJECT_ROOT / "outputs"
CNF_DIR = OUTPUTS_DIR / "cnf"
RESULTS_DIR = OUTPUTS_DIR / "results"

SOLVER_EXE = PROJECT_ROOT / "backend" / "solver" / "glucose.exe"

CNF_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
