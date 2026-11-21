"""Estilo común de las figuras del documento."""
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from comun import FIG

# ---------- estilo ----------
_fuentes = {f.name for f in font_manager.fontManager.ttflist}
FUENTE = next((f for f in ("TeX Gyre Pagella", "Palatino", "Palatino Linotype", "Book Antiqua") if f in _fuentes), "DejaVu Serif")
TINTA, SUAVE, REJILLA = "#222222", "#6b6b6b", "#e6e6e6"
ACENTO, OSCURO, CLARO = "#b4532a", "#4d5a66", "#b9c0c7"
ANCHO = 5.6  # pulgadas: ancho del texto en el documento
plt.rcParams.update({
    "font.family": FUENTE, "font.size": 9, "axes.titlesize": 9, "axes.titleweight": "normal", "axes.titlelocation": "left",
    "axes.labelsize": 9, "xtick.labelsize": 8, "ytick.labelsize": 8, "legend.fontsize": 8, "legend.frameon": False,
    "axes.edgecolor": SUAVE, "axes.linewidth": .6, "axes.labelcolor": TINTA, "xtick.color": SUAVE, "ytick.color": SUAVE,
    "xtick.major.width": .6, "ytick.major.width": .6, "xtick.major.size": 2.5, "ytick.major.size": 2.5,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": REJILLA, "grid.linewidth": .6,
    "axes.axisbelow": True, "axes.formatter.use_locale": False, "pdf.fonttype": 3, "savefig.bbox": "tight", "savefig.pad_inches": .02,
})


def coma(x, d=1):
    return f"{x:.{d}f}".replace(".", ",")


def eje_coma(ax, eje="x", d=1):
    f = matplotlib.ticker.FuncFormatter(lambda v, _: coma(v, d))
    (ax.xaxis if eje == "x" else ax.yaxis).set_major_formatter(f)


def guardar(fig, nombre):
    fig.savefig(FIG / f"{nombre}.pdf"); fig.savefig(FIG / f"{nombre}.png", dpi=200); plt.close(fig)


