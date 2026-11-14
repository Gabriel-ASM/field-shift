"""Freeze Yahoo Finance crop futures for the selected harvest date."""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parent.parent
YAHOO_SYMBOLS = {
    "soybean": {"symbol": "ZSK27.CBT", "pounds_per_bushel": 60},
    "maize": {"symbol": "ZCK27.CBT", "pounds_per_bushel": 56},
}
POUNDS_PER_METRIC_TON = 2204.62262185


def fetch_json(url: str) -> dict:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0 Field-Shift-MVP"})
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def freeze(as_of: date) -> dict:
    raw_yahoo = ROOT / "data" / "raw" / "yahoo-finance"
    raw_bacen = ROOT / "data" / "raw" / "bacen"
    raw_yahoo.mkdir(parents=True, exist_ok=True)
    raw_bacen.mkdir(parents=True, exist_ok=True)

    start = datetime.combine(as_of - timedelta(days=4), datetime.min.time(), timezone.utc)
    end = datetime.combine(as_of + timedelta(days=2), datetime.min.time(), timezone.utc)
    quotes = []
    for crop, contract in YAHOO_SYMBOLS.items():
        params = urlencode(
            {
                "period1": int(start.timestamp()),
                "period2": int(end.timestamp()),
                "interval": "1d",
                "events": "history",
            }
        )
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{contract['symbol']}?{params}"
        raw = fetch_json(url)
        results = raw.get("chart", {}).get("result") or []
        if not results:
            raise RuntimeError(f"Yahoo Finance did not return data for {contract['symbol']}: {raw}")
        result = results[0]
        exchange_zone = ZoneInfo(result["meta"].get("exchangeTimezoneName", "America/Chicago"))
        quote_rows = result["indicators"]["quote"][0]
        matching = [
            index
            for index, stamp in enumerate(result.get("timestamp", []))
            if datetime.fromtimestamp(stamp, exchange_zone).date() == as_of
        ]
        if not matching:
            raise RuntimeError(f"No Yahoo Finance candle for {contract['symbol']} on {as_of}")
        index = matching[-1]
        raw_yahoo.joinpath(f"{contract['symbol']}-{as_of.isoformat()}.json").write_text(
            json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        close = quote_rows["close"][index]
        quotes.append(
            {
                "crop": crop,
                "symbol": contract["symbol"],
                "contract_name": result["meta"].get("longName"),
                "exchange": result["meta"].get("fullExchangeName", "CBOT"),
                "currency_code_yahoo": result["meta"].get("currency"),
                "quote_date": as_of.isoformat(),
                "close_yahoo": close,
                "quote_unit": "US cents per bushel",
                "pounds_per_bushel": contract["pounds_per_bushel"],
                "price_usd_per_metric_ton": close
                / 100
                * POUNDS_PER_METRIC_TON
                / contract["pounds_per_bushel"],
                "source_url": f"https://finance.yahoo.com/quote/{contract['symbol']}/history/",
                "raw_response": f"data/raw/yahoo-finance/{contract['symbol']}-{as_of.isoformat()}.json",
            }
        )

    bcb_date = as_of.strftime("%m-%d-%Y")
    bcb_url = (
        "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/"
        f"CotacaoDolarDia(dataCotacao=@dataCotacao)?@dataCotacao='{bcb_date}'&%24format=json"
    )
    bcb_raw = fetch_json(bcb_url)
    if not bcb_raw.get("value"):
        raise RuntimeError(f"BCB PTAX returned no quote for {as_of}: {bcb_raw}")
    raw_bacen.joinpath(f"PTAX-USD-BRL-{as_of.isoformat()}.json").write_text(
        json.dumps(bcb_raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    fx = bcb_raw["value"][-1]
    exchange_rate = fx["cotacaoVenda"]
    for quote in quotes:
        quote["exchange_rate_brl_per_usd"] = exchange_rate
        quote["price_brl_per_metric_ton"] = quote["price_usd_per_metric_ton"] * exchange_rate
        quote["bcb_quote_time"] = fx["dataHoraCotacao"]
        quote["bcb_source_url"] = bcb_url

    return {
        "schema_version": "1.0.0",
        "purpose": "Frozen harvest price references for the interactive crop rotation demonstration.",
        "as_of_date": as_of.isoformat(),
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "price_semantics": "Yahoo Finance daily close for a May 2027 CBOT futures contract, converted to BRL per metric tonne using the same date's BCB PTAX selling rate. This is an exchange reference, not a local cash price or farm-gate offer.",
        "conversion": {
            "futures_quote_unit": "US cents per bushel",
            "formula": "(Yahoo close / 100) * (2204.62262185 lb per metric tonne / commodity lb per bushel) * BCB PTAX BRL/USD selling rate",
            "pounds_per_bushel_source": "USDA NASS 2024 Oklahoma Agricultural Statistics, Conversion Factors",
        },
        "fx": {
            "currency_pair": "USD/BRL",
            "rate": exchange_rate,
            "kind": "PTAX selling rate",
            "quote_time": fx["dataHoraCotacao"],
            "source_url": bcb_url,
            "raw_response": f"data/raw/bacen/PTAX-USD-BRL-{as_of.isoformat()}.json",
        },
        "quotes": quotes,
        "limitations": [
            "May 2027 CBOT contracts are price references for 2027 harvest scenarios; they do not establish a Brazilian local basis, quality premium, freight, tax, hedge result, or net revenue.",
            "Yahoo Finance is the market-data display source; unit conversion follows CME contract specifications and USDA bushel weights.",
            "No comparable Yahoo peanut or sorghum futures quote is included.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", type=date.fromisoformat, default=date(2026, 11, 13))
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "data" / "reference" / "yahoo-harvest-futures.json",
    )
    options = parser.parse_args()
    snapshot = freeze(options.date)
    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.output.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
