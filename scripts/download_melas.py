import requests
import time
import pandas as pd

# ➜ OVDJE STAVI SVOJ SPOONACULAR API KEY
API_KEY = "fb42636a935949f886aebfca7f829a22"

BASE_URL = "https://api.spoonacular.com/recipes/complexSearch"

TOTAL_RECIPES = 500        # koliko ukupno želimo
PAGE_SIZE = 100            # max 100 po requestu (preporuka)
CUISINE = "European"       # filtriramo samo europska jela

# službeni meal types iz Spoonacular dokumentacije
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
    "sauce",
    "marinade",
    "fingerfood",
    "snack",
    "drink",
]


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
    Spoonacular diet string -> canonical oblik (npr. 'gluten free', 'ketogenic' → 'Gluten Free', 'Ketogenic').
    """
    if not isinstance(name, str):
        return ""
    return " ".join(w.capitalize() for w in name.strip().split())


def extract_diets(recipe: dict) -> str:
    """
    Vrati sve dijete koje Spoonacular navede za recept (npr. 'gluten free', 'vegan', 'ketogenic')
    normalizirane na isti format kao u dokumentaciji (Gluten Free, Vegan, Ketogenic, ...),
    spojene u jedan string odvojen ';'.
    """
    diets_raw = recipe.get("diets", []) or []
    diets_norm = [normalize_diet_name(d) for d in diets_raw if d]
    diets_str = ";".join(sorted(set(diets_norm)))
    return diets_str


def fetch_european_recipes(total: int = TOTAL_RECIPES, page_size: int = PAGE_SIZE):
    """
    Dohvati 'total' europskih recepata (cuisine = European) u više stranica.
    Vraća listu dict-ova spremnih za DataFrame s poljima:
        id, name, meal_type, calories, protein_g, fat_g, carbs_g, diets
    """
    recipes = []
    offset = 0

    while len(recipes) < total:
        remaining = total - len(recipes)
        number = page_size if remaining > page_size else remaining

        params = {
            "apiKey": API_KEY,
            "number": number,
            "offset": offset,
            "cuisine": CUISINE,
            "addRecipeNutrition": "true",
            "addRecipeInformation": "true",
        }

        print(f"[INFO] Fetcham {number} recepata od offseta {offset} "
              f"(trenutno {len(recipes)}/{total})")

        resp = requests.get(BASE_URL, params=params)
        resp.raise_for_status()
        data = resp.json()

        results = data.get("results", []) or []
        if not results:
            print("[WARN] Nema više rezultata od API-ja, prekidam.")
            break

        for r in results:
            recipe_id = r.get("id")
            title = (r.get("title") or "").strip()

            meal_type = infer_meal_type(r)
            calories, protein, fat, carbs = extract_nutrients(r)
            diets = extract_diets(r)

            recipes.append({
                "id": recipe_id,
                "name": title,
                "meal_type": meal_type,
                "calories": calories,
                "protein_g": protein,
                "fat_g": fat,
                "carbs_g": carbs,
                "diets": diets,
            })

        offset += number
        time.sleep(1)  # mali delay da ne zaspammaš API

    print(f"[INFO] Ukupno dohvaćeno recepata: {len(recipes)}")
    return recipes


def main():
    recipes = fetch_european_recipes()

    df = pd.DataFrame(recipes)

    # izbaci recepte bez kalorija (ako ih ima)
    df = df[df["calories"].notna()].reset_index(drop=True)

    output_path = "meals_europe_500.csv"
    df.to_csv(output_path, index=False, encoding="utf-8")

    print(f"[OK] Spremio dataset u: {output_path}")
    print("Prvih 5 redova:")
    print(df.head())


if __name__ == "__main__":
    main()
