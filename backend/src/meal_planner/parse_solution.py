import os
from typing import Any, Dict, List, Tuple, Set, Optional
from meal_planner.build_cnf import load_meals, index_meals, build_var_mapping
from meal_planner.run_solver import parse_true_vars_from_output
from meal_planner.config import MEALS_CSV, RESULTS_DIR



# Key je isti kao u build_cnf.py: (day, meal_type, meal_id)
Key = Tuple[int, str, int]


def build_plan_from_true_vars(
    true_vars: Set[int],
    key_for_var: Dict[int, Key],
) -> Dict[int, Dict[str, int]]:
    """
    Pretvara skup true varijabli u plan:

    true_vars: npr. {4, 5, 12, 16, ...}
    key_for_var: mapa var_id -> (day, meal_type, meal_id)

    Returns:
        plan: dict[day][meal_type] = meal_id
        npr. plan[1]["breakfast"] = 1001
    """
    plan: Dict[int, Dict[str, int]] = {}

    for var in true_vars:
        if var not in key_for_var:
            # može se dogoditi ako solver ispiše i neke varijable izvan mappinga (rijetko)
            continue

        day, meal_type, meal_id = key_for_var[var]

        if day not in plan:
            plan[day] = {}

        # ako se dogodi da ima dva true za isti (day, meal_type),
        # to je znak da nešto nije u redu u CNF-u (ali kod exactly_one_pairwise ne bi smjelo)
        plan[day][meal_type] = meal_id

    return plan


def pretty_print_plan(
    plan: Dict[int, Dict[str, int]],
    meal_by_id: Dict[int, Dict[str, Any]],
    meal_types: List[str],
) -> None:
    """
    Lijep ispis plana u terminal.

    plan: dict[day][meal_type] = meal_id
    meal_by_id: id -> meal dict (name, calories, diets...)
    meal_types: redoslijed ispisa (npr. ["breakfast", "main course", "dinner"])
    """
    if not plan:
        print("[WARN] Plan is empty (no true vars or mapping mismatch).")
        return

    days_sorted = sorted(plan.keys())

    print("\n================ WEEKLY PLAN ================\n")
    for d in days_sorted:
        print(f"DAY {d}")
        print("-" * 40)

        for t in meal_types:
            meal_id = plan.get(d, {}).get(t)
            if meal_id is None:
                print(f"  {t:12s}: (missing)")
                continue

            meal = meal_by_id.get(meal_id, {})
            name = meal.get("name", f"(unknown meal id={meal_id})")
            calories = meal.get("calories", "?")
            diets = meal.get("diets", [])

            diets_str = ", ".join(diets) if diets else "-"
            print(f"  {t:12s}: {name}  | kcal={calories} | diets={diets_str}")

        print("")  # prazna linija između dana


def main() -> None:
    """
    Demo runner:
    - učita meals
    - izgradi CNF mapping (key_for_var, meal_by_id)
    - učita true vars iz results/weekly_plan.out
    - složi i ispiše plan
    """

    # umjesto ručnog računanja base_dir, uzimamo iz config.py
    csv_path = str(MEALS_CSV)
    out_path = str(RESULTS_DIR / "weekly_plan.out")

    # isti parametri kao u build_cnf.py (mora biti dosljedno!)
    days = [1, 2, 3]
    meal_types = ["breakfast", "main course", "dinner"]
    meals = load_meals(csv_path)
    meals_by_type, meal_by_id = index_meals(meals, meal_types)

    # mapping var_id <-> (day, meal_type, meal_id)
    var_for, key_for_var = build_var_mapping(days, meal_types, meals_by_type)

    # true vars iz solver output-a (tvoj Glucose format)
    true_vars = parse_true_vars_from_output(out_path)
    if not true_vars:
        print("[INFO] No true vars found (maybe UNSAT or output file empty).")
        return

    plan = build_plan_from_true_vars(true_vars, key_for_var)
    pretty_print_plan(plan, meal_by_id, meal_types)


if __name__ == "__main__":
    main()
