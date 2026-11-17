import os
import csv
from typing import Dict, List, Tuple, Any, Iterable
from meal_planner.config import SOLVER_EXE, CNF_DIR, RESULTS_DIR, MEALS_CSV



# ----------------------------
# 1) Dataset loading
# ----------------------------

def load_meals(csv_path: str) -> List[Dict[str, Any]]:
    """
    Učitava jela iz CSV datoteke i vraća ih u strukturiranom obliku.

    Input:
        csv_path (str): Putanja do CSV datoteke s popisom jela.

        Očekivani format jednog retka u CSV datoteci:
            id,name,meal_type,calories,protein_g,fat_g,carbs_g,diets
            1001,Greek Yogurt,breakfast,180,12,5,22,Vegetarian

    Output:
        List[Dict[str, Any]]: Lista rječnika, gdje svaki rječnik opisuje jedno jelo.

        Primjer jednog elementa izlazne liste:
            {
                "id": 1001,
                "name": "Greek Yogurt",
                "meal_type": "breakfast",
                "calories": 180.0,
                "protein_g": 12.0,
                "fat_g": 5.0,
                "carbs_g": 22.0,
                "diets": ["Vegetarian"]
            }

    Primjer korištenja:
        meals = load_meals("meals_test.csv")
        meals[0]["name"]  # "Greek Yogurt"
    """
    meals: List[Dict[str, Any]] = []

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            diets_raw = row.get("diets") or ""
            diets_list = [d.strip() for d in diets_raw.split(";") if d.strip()]

            dish_raw = row.get("dishTypes") or ""
            dish_list = [d.strip() for d in dish_raw.split(";") if d.strip()]

            meals.append({
                "id": int(row["id"]),
                "name": row.get("name", ""),
                "meal_type": (row.get("meal_type") or "").strip(),   # npr. "main course"
                "calories": float(row["calories"]),
                "protein_g": float(row["protein_g"]),
                "fat_g": float(row["fat_g"]),
                "carbs_g": float(row["carbs_g"]),
                "diets": diets_list,          # npr. ["Dairy Free", "Gluten Free"]
                "dishTypes": dish_list,       # npr. ["dinner", "lunch", "main course", ...]
            })

    return meals


def index_meals(meals: List[Dict[str, Any]], meal_types: List[str]) -> Tuple[Dict[str, List[Dict[str, Any]]], Dict[int, Dict[str, Any]]]:
    """
    Izrađuje pomoćne indeksne strukture nad skupom jela radi bržeg i
    čitljivijeg pristupa podacima u daljnjem modeliranju.

    Input:
        meals (List[Dict[str, Any]]):
            Lista jela učitana iz CSV datoteke.

            Primjer elementa ulazne liste:
                {
                    "id": 1001,
                    "name": "Greek Yogurt",
                    "meal_type": "breakfast",
                    "calories": 180.0,
                    "protein_g": 12.0,
                    "fat_g": 5.0,
                    "carbs_g": 22.0,
                    "diets": ["Vegetarian"]
                }

        meal_types (List[str]):
            Popis dozvoljenih tipova obroka.
            Primjer:
                ["breakfast", "main course", "dinner"]

    Output:
        Tuple[
            Dict[str, List[Dict[str, Any]]],
            Dict[int, Dict[str, Any]]
        ]:

        1) meals_by_type:
            Rječnik koji grupira jela prema tipu obroka.

            Primjer:
                {
                    "breakfast": [
                        {"id": 1001, "name": "Greek Yogurt", ...},
                        {"id": 1002, "name": "Omelette", ...}
                    ],
                    "main course": [
                        {"id": 2001, "name": "Chicken Rice", ...}
                    ],
                    "dinner": []
                }

        2) meal_by_id:
            Rječnik koji omogućuje izravan pristup jelu prema njegovom ID-u.

            Primjer:
                {
                    1001: {"id": 1001, "name": "Greek Yogurt", ...},
                    1002: {"id": 1002, "name": "Omelette", ...}
                }

    Napomena:
        Ova funkcija ne mijenja podatke o jelima, već samo stvara indeksne
        strukture koje omogućuju učinkovitije i čitljivije SAT modeliranje.
    """

    meals_by_type: Dict[str, List[Dict[str, Any]]] = {t: [] for t in meal_types}
    meal_by_id: Dict[int, Dict[str, Any]] = {}

    for m in meals:
        meal_by_id[m["id"]] = m

        for t in meal_types:
            if t in ("breakfast", "lunch", "dinner"):
                # slotovi dana dolaze iz dishTypes (jer u datasetu dinner/lunch nisu meal_type)
                if t in m.get("dishTypes", []):
                    meals_by_type[t].append(m)
            else:
                # ostali tipovi (npr. "main course") dolaze iz meal_type
                if m.get("meal_type") == t:
                    meals_by_type[t].append(m)

    return meals_by_type, meal_by_id


# ----------------------------
# 2) SAT variable mapping
# ----------------------------

Key = Tuple[int, str, int]  # (day, meal_type, meal_id)

def build_var_mapping(
    days: List[int],
    meal_types: List[str],
    meals_by_type: Dict[str, List[Dict[str, Any]]],
) -> Tuple[Dict[Key, int], Dict[int, Key]]:
    
    """
    Generira SAT varijable za sve kombinacije (dan, tip obroka, jelo).

    Svaka SAT varijabla predstavlja odluku:
        "Je li određeno jelo odabrano za određeni tip obroka na određenom danu?"

    Input:
        days (List[int]):
            Popis dana za koje se planiraju obroci.
            Primjer:
                [1, 2, 3]

        meal_types (List[str]):
            Popis tipova obroka.
            Primjer:
                ["breakfast", "main course", "dinner"]

        meals_by_type (Dict[str, List[Dict[str, Any]]]):
            Rječnik koji sadrži jela grupirana po tipu obroka.

            Primjer:
                {
                    "breakfast": [
                        {"id": 1001, "name": "Greek Yogurt", ...},
                        {"id": 1002, "name": "Omelette", ...}
                    ],
                    "dinner": [
                        {"id": 3001, "name": "Salad", ...}
                    ]
                }

    Output:
        Tuple[Dict[Key, int], Dict[int, Key]]:

        1) var_for:
            Rječnik koji mapira trojac (dan, tip obroka, ID jela)
            u jedinstvenu SAT varijablu (pozitivni cijeli broj).

            Primjer:
                {
                    (1, "breakfast", 1001): 1,
                    (1, "breakfast", 1002): 2,
                    (2, "dinner", 3001): 3
                }

        2) key_for_var:
            Obrnuto mapiranje koje omogućuje tumačenje rješenja SAT solvera.

            Primjer:
                {
                    1: (1, "breakfast", 1001),
                    2: (1, "breakfast", 1002),
                    3: (2, "dinner", 3001)
                }

    Napomena:
        SAT varijable započinju od 1, u skladu s DIMACS CNF standardom.
    """

    var_for: Dict[Key, int] = {}
    key_for_var: Dict[int, Key] = {}
    next_var = 1

    for day in days:
        for t in meal_types:
            for m in meals_by_type.get(t, []):
                key = (day, t, m["id"])  # (1, "breakfast", 1001)
                var_for[key] = next_var
                key_for_var[next_var] = key
                next_var += 1

    return var_for, key_for_var


# ----------------------------
# 3) CNF helper constraints
# ----------------------------

"""
    Pomoćne funkcije za generiranje CNF ograničenja.

    Clause:
        CNF klauzula je lista cijelih brojeva (List[int]).
        Pozitivan broj označava varijablu, negativan njezinu negaciju.

    ------------------------------------------------------------

    at_least_one:
        Baremm jedna varijabla mora biti istinita.
        Logički: v₁ ∨ v₂ ∨ ... ∨ vₙ
        Primjer: [5, 6, 7] → [5, 6, 7]

    ------------------------------------------------------------

    at_most_one_pairwise:
        Najviše jedna varijabla smije biti istinita.
        Logički (za svaki par): ¬vᵢ ∨ ¬vⱼ
        Primjer: [5, 6, 7] → [-5, -6], [-5, -7], [-6, -7]
        (ne možeš i 5 i 6, ne možeš i 5 i 7, ne možeš i 6 i 7)

    ------------------------------------------------------------

    exactly_one_pairwise:
        Točno jedna varijabla mora biti istinita.
        Logički: (v₁ ∨ ... ∨ vₙ) ∧ ∧(¬vᵢ ∨ ¬vⱼ), ∀ i < j
"""


Clause = List[int]

def at_least_one(clauses: List[Clause], vars_: List[int]) -> None:
    # PRAVILO: "bar nesto"
    #
    # ako imamo varijable [5, 6, 7]:
    # → ili 5, ili 6, ili 7 mora biti True
    #
    # → ne moze se dogoditi da su 5, 6 i 7 svi False
    if vars_:
        clauses.append(vars_)  # npr. [5, 6, 7]


def at_most_one_pairwise(clauses: List[Clause], vars_: List[int]) -> None:
    # PRAVILO: "ne 2 odjednom"
    #
    # Za svaku kombinaciju dviju varijabli dodajemo zabranu:
    #
    #   [-5, -6] → ne moze i 5 i 6
    #   [-5, -7] → ne moze i 5 i 7
    #   [-6, -7] → ne moze i 6 i 7
    #
    # najvise 1 varijabla je true
    for i in range(len(vars_)):
        for j in range(i + 1, len(vars_)):
            clauses.append([-vars_[i], -vars_[j]])


def exactly_one_pairwise(clauses: List[Clause], vars_: List[int]) -> None:
    # PRAVILO: "tocno 1"
    #
    # Kombiniramo oba pravila:
    # 1) at_least_one  → barem jedno
    # 2) at_most_one   → ne vise od jednog
    #
    # Rezultat:
    # → tocno jedna varijabla iz liste mora biti True
    # clauses = [
    # [5, 6, 7],      # moraš nešto uzeti
    # [-5, -6],       # ne možeš 5 i 6
    # [-5, -7],       # ne možeš 5 i 7
    # [-6, -7]        # ne možeš 6 i 7
    # ]
    #
    at_least_one(clauses, vars_)
    at_most_one_pairwise(clauses, vars_)


# ----------------------------
# 4) Problem-specific constraints
# ----------------------------

def add_basic_constraints(
    clauses,
    days,
    meal_types,
    meals_by_type,
    var_for
):
    """
    add_basic_constraints:

        → za svaki (dan, obrok) mora biti odabrano točno jedno jelo.

    Primjer (dan 1, doručak):
        Moguće varijable: [5, 6, 7]

        Pravila koja se dodaju:
            [5, 6, 7]        → moraš uzeti barem jedno
            [-5, -6]         → ne možeš i 5 i 6
            [-5, -7]         → ne možeš i 5 i 7
            [-6, -7]         → ne možeš i 6 i 7

    Ova funkcija definira osnovni okvir plana
    (neovisno o dijetama i drugim ograničenjima).
    """

    # prolazimo kroz sve dane
    for d in days:

        # prolazimo kroz sve tipove obroka
        for t in meal_types:

            slot_vars = []

            # prolazimo kroz sva jela tog tipa
            slot_meals = meals_by_type.get(t, [])
            if not slot_meals:
                raise ValueError(f"No meals available for meal_type='{t}'")
            for meal in slot_meals:
                var = var_for[(d, t, meal["id"])]
                slot_vars.append(var)

            # za taj dan i taj obrok:
            # moraš izabrati jedno jelo i ne smiješ dva
            exactly_one_pairwise(clauses, slot_vars)


def add_diet_constraints(
    clauses,
    required_diets,
    var_for,
    meal_by_id
):
    """
    add_diet_constraints:

    Primjenjuje ograničenja vezana uz dijetu.

    Ako je zadana dijeta (npr. "Gluten Free"):
        - svako jelo koje NE zadovoljava sve tražene dijete
        mora biti zabranjeno

    Zabrana:
        [-var]  → to jelo ne smije biti odabrano

    Primjer:
        Tražena dijeta: ["Gluten Free"]

        Jelo A: diets = ["Vegetarian"]
            → nema "Gluten Free"
            → dodaje se: [-var_A]
            → ne možeš izabrati to jelo

        Jelo B: diets = ["Gluten Free", "Vegetarian"]
            → zadovoljava dijetu
            → nema zabrane

    Ako lista `required_diets` nije zadana:
        → ne dodaju se nikakva dijetetska ograničenja.
    """

    # ako nema dijeta, nema ograničenja
    if len(required_diets) == 0:
        return

    # prolazimo kroz sve SAT varijable
    for key in var_for:
        var = var_for[key]
        meal_id = key[2]   # (day, meal_type, meal_id)

        meal = meal_by_id[meal_id]

        # provjeravamo ima li jelo sve tražene dijete
        ok = True
        for diet in required_diets:
            if diet not in meal["diets"]:
                ok = False

        # ako nema sve dijete → zabrani jelo
        if not ok:
            clauses.append([-var])


# ----------------------------
# 5) DIMACS writer
# ----------------------------

def write_dimacs(path: str, clauses: List[Clause], num_vars: int, meta: Dict[str, Any]) -> None:
    """
    write_dimacs:

    Zapisuje SAT instancu u DIMACS CNF format.

    DIMACS format sastoji se od:
        - komentara (linije koje počinju s 'c')
        - problem line: p cnf <broj_varijabli> <broj_klauzula>
        - popisa CNF klauzula, gdje svaka završava s 0

    Ulaz:
        path (str):
            Putanja do izlazne .cnf datoteke.

        clauses (List[Clause]):
            Lista CNF klauzula.
            Svaka klauzula je lista cijelih brojeva (literala).

        num_vars (int):
            Ukupan broj SAT varijabli.

        meta (Dict[str, Any]):
            Dodatne informacije o instanci (npr. dani, tipovi obroka,
            dijete), koje se zapisuju kao komentari.

    Izlaz:
        None

    Primjer zapisa klauzule:
        [5, -6, 7]  →  "5 -6 7 0"

    Napomena:
        Komentari služe samo za čitljivost i ignoriraju se od strane
        SAT solvera, dok su problem line i klauzule obavezni dijelovi
        DIMACS CNF formata.
    """

    # ako dir ne postoji, stvori ga
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        # komentari
        f.write("c Weekly meal planning SAT instance\n")
        for k, v in meta.items():
            f.write(f"c {k}: {v}\n")
        f.write(f"c variables: {num_vars}\n")
        f.write(f"c clauses: {len(clauses)}\n\n")

        # problem line
        f.write(f"p cnf {num_vars} {len(clauses)}\n")  # p cnf <broj_varijabli> <broj_klauzula>

        # klauzule - literali odvojeni razmakom, zavrsava s 0
        for cl in clauses:
            f.write(" ".join(str(lit) for lit in cl) + " 0\n")


# ----------------------------
# 6) Orchestration / demo run
# ----------------------------

def build_cnf_instance(
    meals: List[Dict[str, Any]],
    days: List[int],
    meal_types: List[str],
    required_diets: List[str],
) -> Tuple[int, List[Clause], Dict[Key, int], Dict[int, Key]]:
    """
    build_cnf_instance:

    Gradi kompletnu SAT/CNF instancu za planiranje obroka:
        1) priprema indekse nad jelima (brži dohvat po tipu i po ID-u)
        2) generira SAT varijable za svaku kombinaciju (dan, obrok, jelo)
        3) generira CNF klauzule (pravila) za:
            - osnovna ograničenja: moraš izabrati točno jedno jelo po obroku
            - dijetetska ograničenja: jela koja ne zadovoljavaju dijetu se zabranjuju

    Input:
        meals (List[Dict[str, Any]]):
            Lista jela (rezultat load_meals), npr.:
                [{"id": 1001, "meal_type": "breakfast", "diets": ["Vegetarian"], ...}, ...]

        days (List[int]):
            Popis dana, npr. [1, 2, 3]

        meal_types (List[str]):
            Tipovi obroka, npr. ["breakfast", "main course", "dinner"]

        required_diets (List[str]):
            Tražene dijete, npr. ["Gluten Free"] ili [] (bez dijete)

    Output:
        Tuple[int, List[Clause], Dict[Key, int], Dict[int, Key]] gdje:

        1) num_vars (int):
            Broj SAT varijabli (DIMACS traži broj varijabli).

        2) clauses (List[Clause]):
            Lista svih CNF klauzula (pravila).
            Primjer klauzule: [5, 6, 7] ili [-5, -6]

        3) var_for (Dict[Key, int]):
            Mapiranje odluke u SAT broj:
                (day, meal_type, meal_id) -> var_id
            Primjer:
                (1, "breakfast", 1001) -> 1

        4) key_for_var (Dict[int, Key]):
            Obrnuto mapiranje za tumačenje rješenja:
                var_id -> (day, meal_type, meal_id)
            Primjer:
                1 -> (1, "breakfast", 1001)

    Primjer poziva:
        num_vars, clauses, var_for, key_for_var = build_cnf_instance(
            meals=meals,
            days=[1, 2],
            meal_types=["breakfast"],
            required_diets=["Gluten Free"]
        )
    """

    meals_by_type, meal_by_id = index_meals(meals, meal_types)
    var_for, key_for_var = build_var_mapping(days, meal_types, meals_by_type)

    clauses: List[Clause] = []
    add_basic_constraints(clauses, days, meal_types, meals_by_type, var_for)
    add_diet_constraints(clauses, required_diets, var_for, meal_by_id)

    return len(var_for), clauses, var_for, key_for_var


def main() -> None:

    # odredivanje putanje
    # (OVO sad uzimamo iz config.py da radi iz bilo kojeg direktorija)
    csv_path = str(MEALS_CSV)

    # privremeni problem
    days = [1, 2, 3]
    meal_types = ["breakfast", "main course", "dinner"]
    required_diets = ["Gluten Free"]

    # ucitavanje podataka - comma-separated values
    meals = load_meals(csv_path)

    # pozivanje glavne funkcije build_cnf_instance -> vraća broj SAT varijabli, CNF klauzule i mape
    num_vars, clauses, _var_for, _key_for_var = build_cnf_instance(
        meals=meals,
        days=days,
        meal_types=meal_types,
        required_diets=required_diets,
    )

    # write DIMACS
    # (OVO sad pišemo u CNF_DIR iz config.py)
    out_path = str(CNF_DIR / "weekly_plan.cnf")
    meta = {"days": days, "meal_types": meal_types, "required_diets": required_diets}  # sluzi za c komentare

    # funkcija koja pretvara cnf u standard -> stvara .cnf datoteku
    write_dimacs(out_path, clauses, num_vars, meta)

    # minimal console info (useful while developing)
    print("[OK] CNF generated")
    print("  vars:", num_vars)
    print("  clauses:", len(clauses))
    print("  file:", out_path)


if __name__ == "__main__":
    main()
