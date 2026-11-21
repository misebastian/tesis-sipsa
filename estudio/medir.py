"""Ejecuta un paso del estudio y registra su tiempo (minutos) y memoria residente máxima (GB) en resultados/tiempos.csv.
Uso: python medir.py 04_regresion"""
import sys, time, subprocess, resource, platform, csv, os
from pathlib import Path
paso = sys.argv[1]; RES = Path(__file__).resolve().parent / "resultados"; RES.mkdir(exist_ok=True)
t0 = time.time()
with open(RES / f"log_{paso}.txt", "w") as log:
    proc = subprocess.Popen([sys.executable, "-u", f"{paso}.py"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for linea in proc.stdout:
        if "Warning" not in linea: print(linea, end="", flush=True)
        log.write(linea); log.flush()
    proc.wait()
minutos = (time.time() - t0) / 60
rss = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
gb = rss / 1024 ** 3 if platform.system() == "Darwin" else rss / 1024 ** 2      # macOS: bytes; Linux: KB
f = RES / "tiempos.csv"; filas = []
if f.exists():
    filas = [r for r in csv.DictReader(open(f)) if r["paso"] != paso]
filas.append(dict(paso=paso, minutos=round(minutos, 2), memoria_gb=round(gb, 2), equipo=f"{platform.system()} {platform.machine()}, {os.cpu_count()} núcleos"))
orden = ["01_panel", "02_eda", "03_variables", "sarima", "04_regresion", "05_clasificacion", "06_resultados", "07_complementarios", "09_verificacion"]
filas.sort(key=lambda r: orden.index(r["paso"]) if r["paso"] in orden else 99)
with open(f, "w", newline="") as h:
    w = csv.DictWriter(h, fieldnames=["paso", "minutos", "memoria_gb", "equipo"]); w.writeheader(); w.writerows(filas)
print(f"--- {paso}: {minutos:.1f} min, {gb:.2f} GB")
sys.exit(proc.returncode)
