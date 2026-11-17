import os
import subprocess  # pokrece vanjske programe
from typing import Optional, Set, Tuple
from meal_planner.config import SOLVER_EXE, CNF_DIR, RESULTS_DIR


# https://www.labri.fr/perso/lsimon/research/glucose/

def run_solver(
    solver_path: str,
    cnf_path: str,
    out_path: str,
    timeout_sec: int = 60,
) -> Tuple[bool, str]:
    """
    Pokreće SAT solver (Glucose/MiniSAT) kao vanjski program.

    Returns:
        (is_sat, stdout_text)

    - is_sat = True ako solver pronađe rješenje (SAT), False ako UNSAT ili greška.
    - stdout_text = stdout solvera (korisno za debug).
    """
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)

    # USAGE: glucose.exe [options] <input-file> <result-output-file>

    # Glucose: koristi -model da ispiše model (varijable) na kraj stdout-a
   
    cmd = [solver_path, cnf_path, out_path]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,  # hvata sve sto solver ispise
            text=True,
            timeout=timeout_sec,  # prekid nakon timeout_sec
        )
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(f"Solver timeout after {timeout_sec}s: {cmd}") from e

    stdout = proc.stdout or ""  # poruka
    stderr = proc.stderr or ""  # error

    debug = True

    if debug:
        print("----- SOLVER STDOUT -----")
        print(stdout)
        print("----- END SOLVER STDOUT -----")

    if stderr:
        print("----- SOLVER STDERR -----")
        print(stderr)
        print("----- END SOLVER STDERR -----")

    # SAT/UNSAT:
    # Glucose često koristi povratne kodove: 10=SAT, 20=UNSAT (najpouzdanije)
    if proc.returncode == 10:
        is_sat = True
    elif proc.returncode == 20:
        is_sat = False
    else:
        # Fallback: ako stdout nije pouzdan, provjerimo i out file

        is_sat = os.path.exists(out_path) and os.path.getsize(out_path) > 0

    return is_sat, stdout


def parse_true_vars_from_output(out_path: str) -> Optional[Set[int]]:
    """
    Parsira true varijable iz solver output file-a.

    Očekuje format (Glucose - ovaj build na Windowsu) tipa:
        -1 -2 -3 4 5 -6 ... 36 0

    (dakle: u out file-u NEMA "SAT" linije, nego samo model kao lista literala)

    Returns:
        set pozitivnih varijabli koje su True, ili None ako file ne postoji / prazan.
    """
    if not os.path.exists(out_path):
        return None

    with open(out_path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read().strip()

    if not text:
        return None

    # skupimo sve brojeve dok ne dođemo do 0 (kraj modela)
    nums = []
    for tok in text.split():
        if tok == "0":
            break
        nums.append(int(tok))

    true_vars = {n for n in nums if n > 0}  # odabire samo pozitivne
    return true_vars


def main() -> None:
    cnf_path = CNF_DIR / "weekly_plan.cnf"
    out_path = RESULTS_DIR / "weekly_plan.out"

    # sanity check
    if not SOLVER_EXE.exists():
        raise FileNotFoundError(f"Solver ne postoji: {SOLVER_EXE}")
    if not cnf_path.exists():
        raise FileNotFoundError(f"CNF ne postoji: {cnf_path}")

    is_sat, stdout = run_solver(str(SOLVER_EXE), str(cnf_path), str(out_path))

    print("[OK] Solver finished")
    print("  SAT:", is_sat)
    print("  output file:", out_path)

    if is_sat:
        true_vars = parse_true_vars_from_output(str(out_path))
        print("  true vars:", (len(true_vars) if true_vars else 0))
    else:
        print("  UNSAT (no solution under current constraints)")


if __name__ == "__main__":
    main()
