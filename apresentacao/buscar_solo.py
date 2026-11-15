#!/usr/bin/env python
"""Busca o solo (SoilGrids 2.0, WCS do ISRIC; publico, sem credenciais) para cada local de premissas.yaml
e grava soilgrids_<chave>.json. Cobertura do WCS e parcial: se houver poucos pixels com dado, amplia a bbox."""
import os, sys, json, yaml
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import soilgrids_wcs as W
P = yaml.safe_load(open(f"{HERE}/premissas.yaml"))
alvo = sys.argv[1:] or list(P["locais"])
for k in alvo:
    L = P["locais"][k]
    for side in (3162.0, 6324.0, 9486.0):
        r = W.run(L["lat"], L["lon"], side)
        nmin = min(n for d in r["pixels"].values() for n in d.values())
        if nmin >= 5:
            break
    r["chave"], r["nome"], r["pixels_validos_min"] = k, L["nome"], nmin
    json.dump(r, open(f"{HERE}/soilgrids_{k}.json", "w"), indent=1)
    b = r["bruto"]
    print(f"{L['nome']:14} lado={r['bbox_lado_m']:.0f} m  pix_min={nmin:3d}  soc0-5={b['soc']['0-5cm']/10:5.1f} g/kg  N0-5={b['nitrogen']['0-5cm']/100:4.2f} g/kg  argila={b['clay']['0-5cm']/10:4.1f}%  Ds={b['bdod']['0-5cm']/100:4.2f}", flush=True)
