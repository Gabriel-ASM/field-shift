"""Regional chain from every selectable starting crop, three seeds: evidence behind the best sequence.

    uv run python tests/parity/evaluate_results.py 100000 out.json
"""
import json, sys
from field_shift.engines.run import run, options
N = int(sys.argv[1]); out = []
def repeats(crops, crop="soybean"):
    return any(a == b == crop for a, b in zip(crops, crops[1:]))
for profile in ("ariquemes-ro", "franca-sp", "varginha-mg"):
    opt = options(profile); need = opt["ranking"]["support"]["minimum_recommended"]
    for start in opt["initial_crops"]:
        row = {"profile": profile, "start": start, "seeds": []}
        for seed in (1, 2, 3):
            req = {"profile": profile, "seed": seed, "trajectories": N, "horizon_days": opt["horizon_days"],
                   "scenarios": [{"id": "region", "policy": {"kind": "markov"}, "initial_state": f"{start}:skip_stages"}]}
            res = run(req, f"{start}:skip_stages"); sc = res["scenarios"][0]; rs = sc["routes"]
            ok = [r for r in rs if r["value"] and r["value"]["count"] >= need]
            best = max(ok, key=lambda r: r["value"]["p50"]) if ok else None
            common = max(rs, key=lambda r: r["share"])
            row["seeds"].append({"seed": seed, "device": res["device"], "seconds": res["seconds"], "routes": len(rs), "supported": len(ok),
                "covered": sum(r["share"] for r in ok), "unpriced": sum(r["share"] for r in rs if not r["value"]),
                "soy_repeat_share": sum(r["share"] for r in rs if repeats(r["crops"])),
                "best": best and {"crops": best["crops"], "share": best["share"], **{k: round(best["value"][k]) for k in ("p5","p50","p95","cvar5","count")}, "carbon": best.get("final_carbon")},
                "best_repeats_soy": bool(best and repeats(best["crops"])),
                "common": {"crops": common["crops"], "share": common["share"], "p50": common["value"] and round(common["value"]["p50"])},
                "keys": sorted(sc.keys())})
        out.append(row)
json.dump(out, open(sys.argv[2], "w"), indent=1)
for row in out:
    print(row["profile"], row["start"])
    for s in row["seeds"]:
        b = s["best"]
        print(f'  seed {s["seed"]} {s["device"]} {s["seconds"]}s routes {s["routes"]} supported {s["supported"]} covered {s["covered"]:.3f} unpriced {s["unpriced"]:.4f} soy-soy {s["soy_repeat_share"]:.3f}')
        print(f'    best {"|".join(b["crops"])} share {b["share"]:.4f} p5 {b["p5"]} p50 {b["p50"]} p95 {b["p95"]} cvar {b["cvar5"]} n {b["count"]} C {b["carbon"]}' if b else "    no supported route")
        print(f'    common {"|".join(s["common"]["crops"])} share {s["common"]["share"]:.3f} p50 {s["common"]["p50"]}')
