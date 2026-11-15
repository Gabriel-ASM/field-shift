#!/usr/bin/env python
"""Field Shift - evolucao de C (RothC) e N (balanco simples) numa rotacao sequencial de 14 culturas.

Tudo que nao esta em [ref] na base_tecnica.md e HIPOTESE (ver premissas.yaml). O resultado e cenario, nao previsao.
Roda no conda 'nasa'. Nao usa credenciais (POWER e publico; SoilGrids vem de soilgrids_bruto.json).
"""
import os, json, math, argparse
import numpy as np, pandas as pd, requests, yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser()
ap.add_argument("--premissas", default=f"{HERE}/premissas.yaml")
ap.add_argument("--out", default=f"{HERE}/resultados.json")
args = ap.parse_args()
P = yaml.safe_load(open(args.premissas))


# ------------------------------------------------------------------ solo (SoilGrids)
def solo(chave):
    sg = json.load(open(f"{HERE}/soilgrids_{chave}.json"))
    raw = sg["bruto"]
    esp = P["solo"]["camadas_cm"]
    tot = sum(esp.values())
    f = P["solo"]["fator"]

    def media(v):  # media ponderada pela espessura, valor ja convertido
        return sum(raw[v][l] / f[v] * e for l, e in esp.items()) / tot

    soc, n, clay, bd = media("soc"), media("nitrogen"), media("clay"), media("bdod")
    d = P["solo"]["profundidade_total_cm"]
    toc = soc * bd * d * 0.1      # t C/ha  = g/kg x kg/dm3 x cm x 0,1
    ntot = n * bd * d * 0.1       # t N/ha
    return dict(fonte=sg["fonte"], pixels_min=sg["pixels_validos_min"], lado_m=sg["bbox_lado_m"], soc_gkg=soc, n_gkg=n, argila_pct=clay, ds=bd, toc=toc, n_estoque=ntot, cn=toc / ntot,
                camadas={v: {l: raw[v][l] / f[v] for l in esp} for v in ("soc", "nitrogen", "clay", "bdod")})


# ------------------------------------------------------------------ clima (NASA POWER) + ETo FAO-56
def clima(loc):
    LAT, LON, Z = loc["lat"], loc["lon"], loc["altitude_m"]
    cache = f"{HERE}/clima_{loc['chave']}.csv"
    if not os.path.exists(cache):
        a, b = P["clima_anos"]
        r = requests.get("https://power.larc.nasa.gov/api/temporal/daily/point", timeout=180, params=dict(
            parameters="T2M_MAX,T2M_MIN,RH2M,WS2M,ALLSKY_SFC_SW_DWN,PRECTOTCORR", community="AG",
            longitude=LON, latitude=LAT, start=f"{a}0101", end=f"{b}1231", format="JSON"))
        r.raise_for_status()
        pd.DataFrame(r.json()["properties"]["parameter"]).to_csv(cache, index_label="data")
    df = pd.read_csv(cache, index_col="data", parse_dates=False).replace(-999, np.nan)
    df.index = pd.to_datetime(df.index.astype(str), format="%Y%m%d")
    tmax, tmin, rh, u2, rs = df.T2M_MAX, df.T2M_MIN, df.RH2M, df.WS2M, df.ALLSKY_SFC_SW_DWN
    tm = (tmax + tmin) / 2
    e0 = lambda t: 0.6108 * np.exp(17.27 * t / (t + 237.3))
    es, ea = (e0(tmax) + e0(tmin)) / 2, rh / 100 * e0(tm)
    delta = 4098 * e0(tm) / (tm + 237.3) ** 2
    pres = 101.3 * ((293 - 0.0065 * Z) / 293) ** 5.26
    gam = 0.000665 * pres
    J = df.index.day_of_year.values
    phi = math.radians(LAT)
    dr = 1 + 0.033 * np.cos(2 * np.pi * J / 365)
    dec = 0.409 * np.sin(2 * np.pi * J / 365 - 1.39)
    ws = np.arccos(-math.tan(phi) * np.tan(dec))
    ra = (24 * 60 / np.pi) * 0.0820 * dr * (ws * math.sin(phi) * np.sin(dec) + math.cos(phi) * np.cos(dec) * np.sin(ws))
    rso = (0.75 + 2e-5 * Z) * ra
    sig = 4.903e-9
    rnl = sig * (((tmax + 273.16) ** 4 + (tmin + 273.16) ** 4) / 2) * (0.34 - 0.14 * np.sqrt(ea)) * (
        1.35 * np.minimum(rs / rso, 1.0) - 0.35)
    rn = 0.77 * rs - rnl
    eto = (0.408 * delta * rn + gam * 900 / (tm + 273) * u2 * (es - ea)) / (delta + gam * (1 + 0.34 * u2))
    d = pd.DataFrame({"tmean": tm, "chuva": df.PRECTOTCORR, "eto": eto, "rs": rs})
    d["ano"], d["mes"] = d.index.year, d.index.month
    m = d.groupby(["ano", "mes"]).agg(tmean=("tmean", "mean"), chuva=("chuva", "sum"), eto=("eto", "sum"))
    clim = m.groupby("mes").mean()
    return dict(tmean=clim.tmean.tolist(), chuva=clim.chuva.tolist(), eto=clim.eto.tolist(),
                rs_medio=float(d.rs.mean()), anos=P["clima_anos"])


# ------------------------------------------------------------------ RothC mensal
K = {k: v / 12 for k, v in P["rothc"]["k_ano"].items()}
RR = P["rothc"]["razao_dpm_rpm_residuo"]
F_DPM = RR / (1 + RR)


class RothC:
    def __init__(self, clim, clay, depth):
        self.t, self.rain, self.eto = clim["tmean"], clim["chuva"], clim["eto"]
        self.clay = clay
        self.maxtsmd = -(20 + 1.3 * clay - 0.01 * clay ** 2) * (depth / 23)
        x = 1.67 * (1.85 + 1.60 * math.exp(-0.0786 * clay))
        self.f_co2, self.f_bio, self.f_hum = x / (x + 1), P["rothc"]["bio_hum"][0] / (x + 1), P["rothc"]["bio_hum"][1] / (x + 1)
        self.c = P["rothc"]["cobertura_c"]

    def modifiers(self, acc, m):
        t = self.t[m % 12]
        a = 0.0 if t < -5 else 47.9 / (1 + math.exp(106 / (t + 18.3)))
        acc = max(self.maxtsmd, min(0.0, acc + self.rain[m % 12] - P["rothc"]["eto_para_evap"] * self.eto[m % 12]))
        lim = 0.444 * self.maxtsmd
        b = 1.0 if acc > lim else 0.2 + 0.8 * (self.maxtsmd - acc) / (self.maxtsmd - lim)
        return a * b * self.c, acc

    def step(self, pools, acc, m, c_in):
        rate, acc = self.modifiers(acc, m)
        dec = {k: pools[k] * (1 - math.exp(-K[k] * rate)) for k in K}
        tot = sum(dec.values())
        new = {k: pools[k] - dec[k] for k in K}
        new["DPM"] += c_in * F_DPM
        new["RPM"] += c_in * (1 - F_DPM)
        new["BIO"] += tot * self.f_bio
        new["HUM"] += tot * self.f_hum
        return new, acc, tot * self.f_co2


def spinup(rc, toc, iom):
    """Equilibrio com 1 t C/ha/ano; o modelo e linear no aporte, entao basta escalar."""
    pools, acc = {k: 0.0 for k in K}, 0.0
    prev = 0.0
    for m in range(12 * 1500):
        pools, acc, _ = rc.step(pools, acc, m, 1 / 12)
        if m % 12 == 11:
            s = sum(pools.values())
            if abs(s - prev) < 1e-9:
                break
            prev = s
    unit = sum(pools.values())
    esc = (toc - iom) / unit
    return {k: v * esc for k, v in pools.items()}, acc, esc, m // 12 + 1   # esc = aporte de equilibrio (t C/ha/ano)


def rotacao(rc, pools0, acc0, iom, N0, fator):
    pools, acc = dict(pools0), acc0
    toc0 = sum(pools.values()) + iom
    serie, slots = [], []
    cum_in = cum_co2 = 0.0
    bal_n = res_n = 0.0
    m = 0
    for cult in P["culturas"]:
        toc_ini, n_ini, bal_ini = sum(pools.values()) + iom, None, bal_n
        c_slot, fbn, ex = cult["c_residuo"] * fator, cult["fbn"] * fator, cult["export_n"]
        rn = c_slot * 1000 / cult["cn_residuo"]   # kg N/ha reciclados pelos residuos
        for i in range(cult["meses"]):
            c_in = c_slot / cult["meses"]
            pools, acc, co2 = rc.step(pools, acc, m, c_in)
            cum_in += c_in
            cum_co2 += co2
            bal_n += (fbn - ex) / cult["meses"]
            res_n += rn / cult["meses"]
            toc = sum(pools.values()) + iom
            m += 1
            serie.append(dict(mes=m, cultura=cult["nome"], toc=toc, n_som=N0 * toc / toc0, bal_n=bal_n, res_n=res_n,
                              **{k: pools[k] for k in K}))
        toc_fim = sum(pools.values()) + iom
        slots.append(dict(cultura=cult["nome"], tipo=cult["tipo"], meses=cult["meses"], mes_ini=m - cult["meses"] + 1,
                          mes_fim=m, c_entrada=c_slot, delta_c=toc_fim - toc_ini,
                          delta_n_som=N0 * (toc_fim - toc_ini) / toc0,
                          fbn=fbn, export_n=ex, n_residuo=rn, balanco_n=fbn - ex))
    fecha = (sum(pools.values()) + iom - toc0) - (cum_in - cum_co2)
    return serie, slots, dict(entrada_c=cum_in, co2=cum_co2, erro_balanco=fecha, toc0=toc0, toc_fim=sum(pools.values()) + iom)


def simular(chave):
    loc = dict(P["locais"][chave], chave=chave)
    LAT, LON = loc["lat"], loc["lon"]
    S = solo(chave)
    C = clima(loc)
    rc = RothC(C, S["argila_pct"], P["solo"]["profundidade_total_cm"])
    iom = P["rothc"]["iom_a"] * S["toc"] ** P["rothc"]["iom_b"]
    pools0, acc0, aporte_eq, anos_spin = spinup(rc, S["toc"], iom)
    out = dict(meta=dict(local=loc["nome"], chave=chave, lat=LAT, lon=LON, altitude_m=loc["altitude_m"], rotulo="CENARIO [hip]/[mod], nao e previsao",
                         solo=S, iom=iom, aporte_equilibrio_t_c_ha_ano=aporte_eq, anos_spinup=anos_spin,
                         max_tsmd=rc.maxtsmd, clima=C, premissas=P["culturas"], cenarios=P["cenarios"],
                         rothc_const=P["rothc"]), cenarios={})
    meses_tot = sum(c["meses"] for c in P["culturas"])
    out["meta"]["meses_total"] = meses_tot
    for nome, f in P["cenarios"].items():
        serie, slots, chk = rotacao(rc, pools0, acc0, iom, S["n_estoque"], f)
        chk["aporte_medio_ano"] = chk["entrada_c"] / (meses_tot / 12)
        out["cenarios"][nome] = dict(fator=f, serie=serie, slots=slots, checagem=chk)
    # verificacao: com aporte medio = aporte de equilibrio, o COS tem que ficar ~estavel
    f_eq = aporte_eq / out["cenarios"]["base"]["checagem"]["aporte_medio_ano"]
    _, _, ceq = rotacao(rc, pools0, acc0, iom, S["n_estoque"], f_eq)
    out["verificacao_equilibrio"] = dict(fator=f_eq, toc0=ceq["toc0"], toc_fim=ceq["toc_fim"],
                                         deriva_pct=100 * (ceq["toc_fim"] - ceq["toc0"]) / ceq["toc0"],
                                         aporte_medio_ano=ceq["entrada_c"] / (meses_tot / 12))
    json.dump(out, open(f"{HERE}/resultados_{chave}.json", "w"), ensure_ascii=False)
    b = out["cenarios"]["base"]
    print(f"=== {loc['nome']} ===")
    print(f"COS0={S['toc']:.1f} t C/ha  N0={S['n_estoque']:.2f} t N/ha  C:N={S['cn']:.1f}  IOM={iom:.1f}  aporte_eq={aporte_eq:.2f} t C/ha/ano  spin-up={anos_spin} anos")
    print(f"Rs medio={C['rs_medio']:.1f} MJ/m2/dia | ETo anual={sum(C['eto']):.0f} mm | chuva anual={sum(C['chuva']):.0f} mm | T media={np.mean(C['tmean']):.1f} C")
    for n, c in out["cenarios"].items():
        k = c["checagem"]
        print(f"[{n}] COS {k['toc0']:.1f} -> {k['toc_fim']:.1f} (d={k['toc_fim']-k['toc0']:+.2f}) | aporte medio {k['aporte_medio_ano']:.2f} t C/ha/ano | erro balanco={k['erro_balanco']:.2e}")
    v = out["verificacao_equilibrio"]
    print(f"[verificacao] aporte=equilibrio (x{v['fator']:.2f}): COS {v['toc0']:.1f} -> {v['toc_fim']:.1f} (deriva {v['deriva_pct']:+.2f}%)")
    for s in b["slots"]:
        print(f"  {s['cultura']:<16} dC={s['delta_c']:+.2f}  dN_som={s['delta_n_som']*1000:+.0f} kg  FBN-exp={s['balanco_n']:+.0f}")


if __name__ == "__main__":
    for k in P["locais"]:
        simular(k)
