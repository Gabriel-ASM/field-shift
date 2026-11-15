#!/usr/bin/env python
"""Gera index.html (autocontido) a partir de template.html + resultados_<local>.json. Roda no conda 'nasa'."""
import json, os, yaml
H = os.path.dirname(os.path.abspath(__file__))
P = yaml.safe_load(open(f"{H}/premissas.yaml"))
ordem = [k for k in P["locais"] if os.path.exists(f"{H}/resultados_{k}.json")]
all_ = {"ordem": ordem, "cidades": {k: json.load(open(f"{H}/resultados_{k}.json")) for k in ordem}}
data = json.dumps(all_, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
html = open(f"{H}/template.html", encoding="utf-8").read().replace("__DATA__", data)
open(f"{H}/index.html", "w", encoding="utf-8").write(html)
print(f"index.html gerado: {len(html)/1024:.0f} KB, areas: {', '.join(ordem)}")
