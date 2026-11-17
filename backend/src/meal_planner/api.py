from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from uuid import uuid4

from meal_planner.config import MEALS_CSV, CNF_DIR, RESULTS_DIR, SOLVER_EXE

from meal_planner.build_cnf import (
    load_meals,
    index_meals,
    build_var_mapping,
    build_cnf_instance,
    write_dimacs,
)
from meal_planner.run_solver import run_solver, parse_true_vars_from_output
from meal_planner.parse_solution import build_plan_from_true_vars  


app = FastAPI(title="Meal Planner API")


@app.get("/api/health")
def health():
    return {"status": "ok"}


class PlanRequest(BaseModel):
    days: int = Field(ge=1, le=14)
    mealsPerDay: int = Field(ge=1, le=5)
    requiredDiets: list[str] = []


def meal_types_for(meals_per_day: int) -> list[str]:
    # Za sada: dataset ima 3 tipa
    if meals_per_day <= 1:
        return ["dinner"]
    if meals_per_day == 2:
        return ["breakfast", "dinner"]
    return ["breakfast", "lunch", "dinner"]


@app.post("/api/plan")
def generate_plan(req: PlanRequest):
    # 1) parametri
    days = list(range(1, req.days + 1))
    meal_types = meal_types_for(req.mealsPerDay)
    required_diets = req.requiredDiets or []

    # 2) učitaj meals + indexi
    meals = load_meals(str(MEALS_CSV))
    meals_by_type, meal_by_id = index_meals(meals, meal_types)

    # 3) build CNF instance
    num_vars, clauses, var_for, key_for_var = build_cnf_instance(
        meals=meals,
        days=days,
        meal_types=meal_types,
        required_diets=required_diets,
    )

    # 4) upiši CNF (unique run_id da se ne pregazi)
    run_id = uuid4().hex[:8]
    cnf_path = CNF_DIR / f"plan_{run_id}.cnf"
    out_path = RESULTS_DIR / f"plan_{run_id}.out"

    meta = {"days": days, "meal_types": meal_types, "required_diets": required_diets}
    write_dimacs(str(cnf_path), clauses, num_vars, meta)

    # 5) pokreni solver
    is_sat, _stdout = run_solver(str(SOLVER_EXE), str(cnf_path), str(out_path))

    if not is_sat:
        return {
            "run_id": run_id,
            "request": req.model_dump(),
            "sat": False,
            "plan": None,
            "message": "UNSAT (no solution under current constraints)",
        }

    # 6) parse true vars
    true_vars = parse_true_vars_from_output(str(out_path))
    if not true_vars:
        raise HTTPException(status_code=500, detail="SAT, but no model parsed from output file.")

    # 7) build plan (day -> meal_type -> meal_id)
    plan_ids = build_plan_from_true_vars(true_vars, key_for_var)

    # 8) obogati plan s podacima o jelima (name/kcal/diets)
    plan_full = {}
    for day, slots in plan_ids.items():
        plan_full[day] = {}
        for mtype, meal_id in slots.items():
            m = meal_by_id.get(meal_id, {})
            plan_full[day][mtype] = {
                "meal_id": meal_id,
                "name": m.get("name"),
                "calories": m.get("calories"),
                "diets": m.get("diets", []),
            }

    return {
        "run_id": run_id,
        "request": req.model_dump(),
        "sat": True,
        "meal_types": meal_types,
        "plan": plan_full,
    }
