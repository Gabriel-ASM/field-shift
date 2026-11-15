"""SoilGrids 2.0 via WCS do ISRIC (publico, sem credenciais), CRS nativo Homolosine. Media na bbox quadrada."""
import io, math, json, sys, requests, rasterio, numpy as np
from pyproj import Transformer
IGH = "+proj=igh +lat_0=0 +lon_0=0 +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs"
TR = Transformer.from_crs("EPSG:4326", IGH, always_xy=True)
PROPS = ["soc", "nitrogen", "clay", "sand", "bdod", "phh2o", "cec"]
LAYERS = ["0-5cm", "5-15cm", "15-30cm"]

def fetch(prop, layer, lat, lon, side):
    dlat = (side / 2) / 111320; dlon = (side / 2) / (111320 * math.cos(math.radians(lat)))
    xs, ys = zip(*[TR.transform(lo, la) for lo in (lon - dlon, lon + dlon) for la in (lat - dlat, lat + dlat)])
    q = [("map", f"/map/{prop}.map"), ("SERVICE", "WCS"), ("VERSION", "2.0.1"), ("REQUEST", "GetCoverage"),
         ("COVERAGEID", f"{prop}_{layer}_mean"), ("FORMAT", "image/tiff"),
         ("SUBSET", f"X({min(xs):.0f},{max(xs):.0f})"), ("SUBSET", f"Y({min(ys):.0f},{max(ys):.0f})"),
         ("SUBSETTINGCRS", "http://www.opengis.net/def/crs/EPSG/0/152160")]
    for t in range(3):
        r = requests.get("https://maps.isric.org/mapserv", params=q, timeout=120)
        if r.status_code == 200 and "tif" in r.headers.get("content-type", ""):
            break
    else:
        raise RuntimeError(f"WCS {prop}_{layer}: HTTP {r.status_code} {r.text[:120]}")
    with rasterio.open(io.BytesIO(r.content)) as ds:
        a = ds.read(1).astype(float)
        if ds.nodata is not None: a = a[a != ds.nodata]
        else: a = a.ravel()
    a = a[(a > -30000) & (a != 0)]   # o WCS devolve 0 onde nao ha dado; cobertura parcial
    return (float(a.mean()) if a.size else None), int(a.size)

def run(lat, lon, side=3162.0):
    out, npx = {}, {}
    for p in PROPS:
        out[p], npx[p] = {}, {}
        for l in LAYERS:
            out[p][l], npx[p][l] = fetch(p, l, lat, lon, side)
    return dict(lat=lat, lon=lon, bbox_lado_m=side, fonte="SoilGrids 2.0 via WCS ISRIC", bruto=out, pixels=npx)

if __name__ == "__main__":
    lat, lon = float(sys.argv[1]), float(sys.argv[2])
    props = sys.argv[3].split(",") if len(sys.argv) > 3 else PROPS
    PROPS[:] = props
    print(json.dumps(run(lat, lon), indent=1))
