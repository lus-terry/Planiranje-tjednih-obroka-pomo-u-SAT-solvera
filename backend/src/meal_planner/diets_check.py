import pandas as pd

df = pd.read_csv("data/raw/meals_spoonacular.csv")
all_diets = set()

for x in df["diets"].fillna(""):
    for d in str(x).split(";"):
        d = d.strip()
        if d:
            all_diets.add(d)

print(sorted(all_diets))
