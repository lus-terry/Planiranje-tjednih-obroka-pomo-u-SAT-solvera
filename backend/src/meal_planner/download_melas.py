import os
import time
import random
import requests
import pandas as pd

# SPOONACULAR API KEY - čita se iz varijable okruženja, ne sprema se u kod
# PowerShell:  $env:SPOONACULAR_API_KEY = "tvoj_kljuc"
API_KEY = os.environ.get("SPOONACULAR_API_KEY", "")

BASE_URL = "https://api.spoonacular.com/recipes/complexSearch"

TOTAL_RECIPES = 5000      
PAGE_SIZE = 100            # max 100 po requestu
CUISINE = "European"     


MEAL_TYPES_PRIORITY = [
    "main course",
    "side dish",
    "dessert",
    "appetizer",
    "salad",
    "bread",
    "breakfast",
    "soup",
    "beverage",
    "fingerfood",
    "snack",
    "drink",
]

SLEEP_SEC = 1.0
MAX_RETRIES = 6


OUTPUT_PATH = "data/raw/meals_spoonacular.csv"


def infer_meal_type(recipe: dict) -> str:
    """
    Odredi meal_type na temelju dishTypes i službene liste meal types.
    Vraća jedan od navedenih tipova ili 'unknown' ako ne pronađe ništa.
    """
    dish_types = recipe.get("dishTypes", []) or []
    dish_types_lower = [d.lower() for d in dish_types]

    for mt in MEAL_TYPES_PRIORITY:
        if mt in dish_types_lower:
            return mt  # canonical ime iz dokumentacije

    return "unknown"


def extract_nutrients(recipe: dict):
    """
    Izvuci kcal, protein, fat, carbs iz nutrition.nutrients.
    """
    calories = protein = fat = carbs = None
    nutrition = recipe.get("nutrition", {})
    nutrients = nutrition.get("nutrients", []) or []

    for n in nutrients:
        name = (n.get("name") or "").lower()
        amount = n.get("amount")
        if amount is None:
            continue
        if name == "calories":
            calories = amount
        elif name == "protein":
            protein = amount
        elif name == "fat":
            fat = amount
        elif name == "carbohydrates":
            carbs = amount

    return calories, protein, fat, carbs


def normalize_diet_name(name: str) -> str:
    """
    Spoonacular diet string -> canonical oblik (npr. 'gluten free' -> 'Gluten Free').
    """
    if not isinstance(name, str):
        return ""
    return " ".join(w.capitalize() for w in name.strip().split())


def extract_diets(recipe: dict) -> str:
    """
    Vrati sve dijete (normalizirane), spojene u jedan string odvojen ';'.
    """
    diets_raw = recipe.get("diets", []) or []
    diets_norm = [normalize_diet_name(d) for d in diets_raw if d]
    return ";".join(sorted(set(diets_norm)))


def request_with_retry(url: str, params: dict) -> dict:
    """
    Retry/backoff za 402/429/5xx.
    """
    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, params=params, timeout=60)

            if resp.status_code in (402, 429) or 500 <= resp.status_code <= 599:
                wait = (2 ** (attempt - 1)) + random.random()
                print(f"[WARN] HTTP {resp.status_code}. Retry {attempt}/{MAX_RETRIES} za {wait:.1f}s")
                time.sleep(wait)
                continue

            resp.raise_for_status()
            return resp.json()

        except Exception as e:
            last_err = e
            wait = (2 ** (attempt - 1)) + random.random()
            print(f"[WARN] Exception: {e}. Retry {attempt}/{MAX_RETRIES} za {wait:.1f}s")
            time.sleep(wait)

    raise RuntimeError(f"API request failed after {MAX_RETRIES} retries: {last_err}")


def load_existing_ids(path: str) -> set[int]:
    """
    Ako CSV već postoji, učitaj postojeće ID-eve da možemo nastaviti bez duplikata.
    """
    if not os.path.exists(path):
        return set()
    try:
        df = pd.read_csv(path)
        if "id" in df.columns:
            return set(df["id"].dropna().astype(int).tolist())
    except Exception:
        pass
    return set()


def append_to_csv(path: str, rows: list[dict]) -> None:
    df = pd.DataFrame(rows)
    file_exists = os.path.exists(path)
    df.to_csv(path, mode="a", header=not file_exists, index=False, encoding="utf-8")
    print(f"[OK] Appended {len(df)} rows -> {path}")


def fetch_recipes(total: int = TOTAL_RECIPES, page_size: int = PAGE_SIZE):
    """
    Dohvati 'total' recepata u više stranica.
    Spremamo:
      id, name, meal_type (raw), calories, protein_g, fat_g, carbs_g, diets, dishTypes
    """
    existing_ids = load_existing_ids(OUTPUT_PATH)
    if existing_ids:
        print(f"[INFO] Postoji dataset. Existing IDs: {len(existing_ids)}")

    batch = []
    offset = 0
    total_results_known = None
    collected = 0  # koliko smo NOVIH dodali (bez duplikata)

    while collected < total:
        remaining = total - collected
        number = page_size if remaining > page_size else remaining

        params = {
            "apiKey": API_KEY,
            "number": number,
            "offset": offset,
            "addRecipeNutrition": "true",
            "addRecipeInformation": "true",
        }
        if CUISINE:
            params["cuisine"] = CUISINE

        print(f"[INFO] Fetch {number} recepata od offseta {offset} (novo {collected}/{total})")

        data = request_with_retry(BASE_URL, params)

        if total_results_known is None:
            tr = data.get("totalResults")
            if isinstance(tr, int):
                total_results_known = tr
                print(f"[INFO] totalResults from API: {total_results_known}")

        results = data.get("results", []) or []
        if not results:
            print("[WARN] Nema više rezultata od API-ja, prekid.")
            break

        added_this_page = 0

        for r in results:
            recipe_id = r.get("id")
            if recipe_id is None:
                continue

            try:
                recipe_id = int(recipe_id)
            except Exception:
                continue

            if recipe_id in existing_ids:
                continue

            title = (r.get("title") or "").strip()

            meal_type = infer_meal_type(r)  # <-- NEMA mapiranja, ostaje Spoonacular tip
            calories, protein, fat, carbs = extract_nutrients(r)
            diets = extract_diets(r)

            dish_types = r.get("dishTypes", []) or []
            dish_types_str = ";".join(sorted({str(x).strip() for x in dish_types if x}))

            # izbaci recepte bez kalorija (češće se dogodi)
            if calories is None:
                continue

            row = {
                "id": recipe_id,
                "name": title,
                "meal_type": meal_type,      # spoonacular tip (npr. side dish)
                "calories": calories,
                "protein_g": protein,
                "fat_g": fat,
                "carbs_g": carbs,
                "diets": diets,              # "Vegan;Gluten Free"
                "dishTypes": dish_types_str, # svi dishTypes za UI kasnije
            }

            batch.append(row)
            existing_ids.add(recipe_id)
            collected += 1
            added_this_page += 1

            if collected >= total:
                break

        offset += number

        # checkpoint svakih 200 novih
        if len(batch) >= 200:
            append_to_csv(OUTPUT_PATH, batch)
            batch = []

        # delay
        time.sleep(SLEEP_SEC + random.random() * 0.25)

        if isinstance(total_results_known, int) and offset >= total_results_known:
            print("[INFO] Offset >= totalResults, prekid.")
            break

        if added_this_page == 0:
            print("[WARN] Stranica nije dodala ništa (duplikati/no calories). Nastavljam dalje...")

    if batch:
        append_to_csv(OUTPUT_PATH, batch)

    print(f"[OK] Gotovo. Novi recepti spremljeni u: {OUTPUT_PATH}")


def main():
    if not API_KEY:
        raise SystemExit("Postavi varijablu okruženja SPOONACULAR_API_KEY prije pokretanja.")

    fetch_recipes(total=TOTAL_RECIPES, page_size=PAGE_SIZE)

    # quick preview
    df = pd.read_csv(OUTPUT_PATH)
    print(df.head(5))
    print("[INFO] Rows:", len(df))


if __name__ == "__main__":
    main()
