import { useState } from "react";


type DietOption = { id: string; label: string; icon: string };

const DIETS: DietOption[] = [
  { id: "Dairy Free", label: "Dairy Free", icon: "🚫🥛" }, 
  { id: "Fodmap Friendly", label: "Fodmap", icon: "🌾" },
  { id: "Gluten Free", label: "Gluten Free", icon: "🚫🍞" }, 
  { id: "Ketogenic", label: "Keto", icon: "🥩" },
  { id: "Lacto Ovo Vegetarian", label: "Veggie", icon: "🥚" },
  { id: "Paleolithic", label: "Paleo", icon: "🍖" },
  { id: "Pescatarian", label: "Pescaterian", icon: "🐟" },
  { id: "Primal", label: "Primal", icon: "🦴" },
  { id: "Vegan", label: "Vegan", icon: "🌿" },
  { id: "Whole 30", label: "Whole 30", icon: "🍱" },
];

type Meal = {
  meal_id: number;
  name: string;
  calories: number;
  diets: string[];
};

type PlanResponse = {
  run_id: string;
  sat: boolean;
  meal_types: string[]; // ["breakfast", "lunch", "dinner"]
  plan: Record<string, Record<string, Meal>> | null;
};

export default function App() {
  const [days, setDays] = useState(7);
  const [mealsPerDay, setMealsPerDay] = useState(3);
  const [requiredDiets, setRequiredDiets] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<PlanResponse | null>(null);

  const toggleDiet = (id: string) => {
    setRequiredDiets(prev => prev.includes(id) ? prev.filter(d => d !== id) : [...prev, id]);
  };

  async function generatePlan() {
    setLoading(true);
    setResult(null);
    try {
      const res = await fetch("/api/plan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ days, mealsPerDay, requiredDiets }),
      });
      const data = await res.json();
      setResult(data);
    } catch (e) {
      console.error("Greška:", e);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-emerald-50/40 text-slate-800 font-sans p-4 md:p-8">
      <div className="mx-auto max-w-7xl">
        {/* Header */}
        <header className="mb-10 text-center">
          <h1 className="text-4xl font-black tracking-tighter text-slate-900 sm:text-6xl uppercase italic leading-none">
            Meal <span className="text-emerald-600">Planner</span>
          </h1>
         
        </header>

        <div className="grid grid-cols-1 gap-8 lg:grid-cols-12">
          {/* Sidebar: Kontrole */}
          <aside className="lg:col-span-4 xl:col-span-3 space-y-6">
            <div className="bg-white rounded-[2.5rem] p-8 shadow-xl shadow-emerald-900/5 border border-emerald-100">
              <h2 className="text-xl font-bold mb-8 text-slate-800 tracking-tight">Parametri plana</h2>

              <div className="space-y-8">
                {/* Dana */}
                <div>
                  <div className="flex justify-between items-end mb-2">
                    <label className="text-xs font-black text-slate-400 uppercase tracking-widest">Trajanje</label>
                    <span className="text-lg font-bold text-emerald-600 leading-none">{days} dana</span>
                  </div>
                  <input
                    type="range" min="1" max="14" value={days}
                    onChange={(e) => setDays(parseInt(e.target.value))}
                    className="w-full h-1.5 bg-emerald-100 rounded-lg appearance-none cursor-pointer accent-emerald-600 mt-2"
                  />
                </div>

                {/* Obroka */}
                <div>
                  <label className="text-xs font-black text-slate-400 uppercase tracking-widest mb-3 block">Broj obroka po danu</label>
                  <div className="grid grid-cols-5 gap-2">
                    {[1, 2, 3, 4, 5].map(n => (
                      <button
                        key={n}
                        onClick={() => setMealsPerDay(n)}
                        className={`h-10 rounded-2xl font-bold transition-all ${mealsPerDay === n ? 'bg-emerald-600 text-white shadow-lg shadow-emerald-200' : 'bg-slate-50 text-slate-400 hover:bg-slate-100'}`}
                      >
                        {n}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Moderni Checkboxovi */}
                <div>
                  <label className="text-xs font-black text-slate-400 uppercase tracking-widest mb-4 block">Dijete / Ograničenja</label>
                  <div className="grid grid-cols-1 gap-2.5 max-h-[400px] overflow-y-auto pr-2 custom-scrollbar">
                    {DIETS.map((d) => {
                      const active = requiredDiets.includes(d.id);
                      return (
                        <label
                          key={d.id}
                          className={`flex items-center justify-between p-3.5 rounded-2xl cursor-pointer border-2 transition-all duration-200 ${
                            active ? "border-emerald-500 bg-emerald-50/50" : "border-slate-50 bg-slate-50/50 hover:border-slate-200"
                          }`}
                        >
                          <div className="flex items-center gap-3">
                            <span className="text-xl leading-none">{d.icon}</span>
                            <span className={`text-sm font-bold ${active ? "text-emerald-800" : "text-slate-600"}`}>{d.label}</span>
                          </div>
                          <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center transition-all ${
                            active ? "bg-emerald-500 border-emerald-500" : "border-slate-300"
                          }`}>
                            {active && <span className="text-white text-[10px] font-bold">✓</span>}
                          </div>
                          <input type="checkbox" className="hidden" checked={active} onChange={() => toggleDiet(d.id)} />
                        </label>
                      );
                    })}
                  </div>
                </div>
              </div>

              <button
                onClick={generatePlan}
                disabled={loading}
                className="w-full mt-10 bg-slate-900 hover:bg-emerald-700 text-white font-black py-4 rounded-2xl shadow-xl transition-all uppercase tracking-widest active:scale-[0.98] disabled:opacity-50"
              >
                {loading ? "Učitavanje..." : "Generiraj plan"}
              </button>
            </div>
          </aside>

          {/* Rezultat: Tablica */}
          <main className="lg:col-span-8 xl:col-span-9">
            {result?.sat ? (
              <div className="bg-white rounded-[2.5rem] shadow-xl shadow-emerald-900/5 border border-emerald-100 overflow-hidden animate-in fade-in slide-in-from-bottom-4 duration-500">
                <div className="p-8 border-b border-emerald-50 flex justify-between items-center bg-emerald-50/30">
                  <div>
                    <h2 className="text-2xl font-bold text-slate-800">Tvoj jelovnik</h2>
                  </div>
                  <div className="bg-white px-4 py-2 rounded-2xl border border-emerald-100 shadow-sm text-xs font-black text-slate-400 uppercase tracking-tighter">
                    {Object.keys(result.plan || {}).length} dana
                  </div>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full border-collapse">
                    <thead>
                      <tr className="bg-slate-50/50">
                        <th className="p-5 text-left text-[10px] font-black text-slate-400 uppercase tracking-[0.2em]">Obrok</th>
                        {Object.keys(result.plan || {}).map(day => (
                          <th key={day} className="p-5 text-center text-sm font-bold text-slate-700 border-l border-emerald-50">
                            Dan {day}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-emerald-50">
                      {result.meal_types.map((type) => (
                        <tr key={type} className="group hover:bg-emerald-50/30 transition-colors">
                          <td className="p-5">
                            <span className="text-xs font-black text-emerald-600 uppercase italic tracking-widest">{type}</span>
                          </td>
                          {Object.keys(result.plan || {}).map(day => {
                            const meal = result.plan![day][type];
                            return (
                              <td key={day} className="p-5 border-l border-emerald-50 min-w-[200px] align-top">
                                {meal ? (
                                  <div className="space-y-2">
                                    <div className="font-bold text-slate-800 leading-snug group-hover:text-emerald-900 transition-colors">
                                      {meal.name}
                                    </div>
                                    <div className="flex items-center justify-between">
                                      <span className="text-[11px] font-black text-emerald-500 bg-emerald-50 px-2 py-0.5 rounded-md">
                                        {meal.calories.toFixed(0)} kcal
                                      </span>
                                    </div>
                                    <div className="flex flex-wrap gap-1">
                                      {meal.diets.slice(0, 2).map(d => (
                                        <span key={d} className="text-[9px] font-bold text-slate-400 border border-slate-100 px-1.5 py-0.5 rounded-md uppercase">
                                          {d}
                                        </span>
                                      ))}
                                    </div>
                                  </div>
                                ) : (
                                  <span className="text-slate-200">—</span>
                                )}
                              </td>
                            );
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ) : (
              <div className="h-full min-h-[500px] flex flex-col items-center justify-center p-12 bg-white rounded-[2.5rem] border-2 border-dashed border-emerald-200">
                {loading ? (
                   <div className="text-center">
                    <div className="w-16 h-16 border-4 border-emerald-100 border-t-emerald-600 rounded-full animate-spin mx-auto mb-4"></div>
                    <p className="font-bold text-slate-400 uppercase tracking-widest text-sm italic">Sastavljanje savršenog plana...</p>
                   </div>
                ) : (
                  <>
                    <div className="w-24 h-24 bg-emerald-50 rounded-full flex items-center justify-center text-4xl mb-6 shadow-inner animate-bounce">🥗</div>
                    <p className="text-slate-400 text-center mt-3 max-w-sm font-medium">
                      Odaberi trajanje i prehrambene preferencije s lijeve strane i klikni generiraj.
                    </p>
                  </>
                )}
              </div>
            )}
          </main>
        </div>
      </div>
    </div>
  );
}