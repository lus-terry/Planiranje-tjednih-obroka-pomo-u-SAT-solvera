// Ova datoteka sadrži tipove i funkciju za komunikaciju s backend API-jem za planiranje obroka.
// Tipovi opisuju strukturu zahtjeva i odgovora, a funkcija generatePlan šalje zahtjev backendu i vraća rezultat plana.


//request od usera
export type PlanRequest = {
  days: number;
  mealsPerDay: number;
  requiredDiets: string[];
};

export type MealSlot = {
  // ID jela iz baze
  meal_id: number;
  // Naziv jela (može biti null ako nije pronađeno)
  name: string | null;
  // Broj kalorija (može biti null ako nije poznato)
  calories: number | null;
  // Popis dijeta koje jelo zadovoljava
  diets: string[];
};

export type PlanResponse = {
  // Jedinstveni identifikator pokretanja plana
  run_id: string;
  request: PlanRequest;
  // Je li pronađeno rješenje (SAT = moguće, UNSAT = nije moguće)
  sat: boolean;
  meal_types?: string[];
  // Plan: za svaki dan i tip obroka daje podatke o jelu ili null ako nije moguće
  plan: Record<string, Record<string, MealSlot>> | null;
  // Poruka s dodatnim informacijama ili greškom (nije obavezno)
  message?: string;
};

/**
 * Funkcija za slanje zahtjeva backendu za generiranje plana obroka.
 *
 * @param payload - Objekt s parametrima plana (broj dana, obroka, dijete)
 * @returns Promise s odgovorom backend API-ja (PlanResponse)
 * @throws Error ako API vrati grešku
 */
export async function generatePlan(payload: PlanRequest): Promise<PlanResponse> {
  // Šalje POST zahtjev na /api/plan s podacima iz payload-a
  const res = await fetch("/api/plan", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API error ${res.status}: ${text}`);
  }

  // Vraća JSON odgovor kao PlanResponse
  return res.json();
}
