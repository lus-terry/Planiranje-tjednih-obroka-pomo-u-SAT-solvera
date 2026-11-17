# Planiranje tjednih obroka pomoću SAT solvera

Web aplikacija koja generira plan obroka kao SAT problem: backend (FastAPI) gradi
CNF instancu u DIMACS formatu, rješava je solverom Glucose i vraća plan, a frontend
(React + Vite) služi za unos parametara i prikaz plana.

## Pokretanje

Sve naredbe pokreću se iz korijena repozitorija (mapa u kojoj je ovaj README).

### 1. Terminal: backend (FastAPI)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install -r backend/requirements.txt

# pokretanje (obavezno iz src foldera)
cd backend/src
uvicorn meal_planner.api:app --reload
```

- API: http://127.0.0.1:8000
- Swagger dokumentacija: http://127.0.0.1:8000/docs

### 2. Terminal: frontend (Vite + React)

```powershell
cd frontend
npm install
npm run dev
```

- Sučelje: http://localhost:5173 (zahtjevi na `/api` prosljeđuju se backendu na portu 8000)

## Važne napomene o putanjama

Putanje se određuju u `backend/src/meal_planner/config.py`, relativno prema korijenu repozitorija:

- solver: `backend/solver/glucose.exe` (Windows build)
- dataset: `data/raw/meals_spoonacular.csv`
- generirane datoteke: `outputs/cnf/` i `outputs/results/` (ne commitaju se)

## Preuzimanje recepata (opcionalno)

Dataset je već uključen. Za ponovno preuzimanje sa Spoonacular API-ja treba vlastiti ključ:

```powershell
$env:SPOONACULAR_API_KEY = "tvoj_kljuc"
python backend/src/meal_planner/download_melas.py
```
