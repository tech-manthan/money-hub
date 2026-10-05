"""Create static font instances from the variable Google Fonts (SIL OFL) so WeasyPrint picks exact weights."""
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

FONTS = Path(__file__).resolve().parent.parent / "assets" / "fonts"
OUT = FONTS / "static"
OUT.mkdir(exist_ok=True)

JOBS = {
    "DMSans": ("DMSans-Variable.ttf", {"opsz": 14}, [400, 500, 700]),
    "Inter": ("Inter-Variable.ttf", {"opsz": 14}, [400, 500, 600, 700]),
    "Lora": ("Lora-Variable.ttf", {}, [400, 500, 600, 700]),
    "Nunito": ("Nunito-Variable.ttf", {}, [400, 600, 700, 800]),
    "PlayfairDisplay": ("PlayfairDisplay-Variable.ttf", {}, [400, 600, 700]),
    "Fraunces": ("Fraunces-Variable.ttf", {"opsz": 48, "SOFT": 0, "WONK": 0}, [400, 600, 700]),
    "Caveat": ("Caveat-Variable.ttf", {}, [400, 700]),
}

for family, (fname, pins, weights) in JOBS.items():
    for w in weights:
        font = TTFont(FONTS / fname)
        axes = {"wght": w, **pins}
        inst = instancer.instantiateVariableFont(font, axes, inplace=False)
        inst.save(OUT / f"{family}-{w}.ttf")
        print("wrote", family, w)

for p in FONTS.glob("Poppins-*.ttf"):
    (OUT / p.name).write_bytes(p.read_bytes())
