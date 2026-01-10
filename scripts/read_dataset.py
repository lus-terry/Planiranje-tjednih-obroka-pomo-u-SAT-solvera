import os
import pandas as pd

# BASE_DIR = .../meal-planner
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

# putanja do meals_test.csv -> .../meal-planner/data/raw/meals_test.csv
CSV_PATH = os.path.join(BASE_DIR, "data", "raw", "meals_test.csv")

print("CSV path:", CSV_PATH)

# ucitavanje CSV-a
df = pd.read_csv(CSV_PATH)

print("\nKolone u datasetu:")
print(df.columns.tolist())

print("\nPrvih nekoliko redova:")
print(df.head())
