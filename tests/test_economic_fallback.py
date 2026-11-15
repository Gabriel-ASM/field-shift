import pytest

pytest.importorskip("xlrd", reason="economic ingestion uses the optional XLS reader")
from data.pipeline.build_economic_benchmarks import pam_crop_values


def test_old_municipal_observation_does_not_block_recent_state_proxy():
    municipal = {"records": [{"crop": "sorgo_em_grao", "year": 1993,
                             "yield_kg_ha": 2000, "unit_value_brl_per_tonne_nominal": 6000}]}
    state = [{"uf_code": "31", "product_id": "40125", "year": 2025,
              "production_tonnes": 300, "production_value_thousand_brl_nominal": 210,
              "harvested_area_ha": 100, "yield_kg_ha": 3000}]
    value, price, source, notes = pam_crop_values(
        "varginha-mg", "sorghum_grain", municipal, state,
        {"202610": 110}, {"2025": 100})
    assert value == 3000
    assert price["scope"] == "state"
    assert price["brl_per_tonne"] == pytest.approx(770)
    assert price["history_start_year"] == 2025
    assert "proxy" in source and notes


def test_no_valid_real_history_remains_missing_instead_of_using_1993_nominal():
    municipal = {"records": [{"crop": "sorgo_em_grao", "year": 1993,
                             "yield_kg_ha": 2000, "unit_value_brl_per_tonne_nominal": 6000}]}
    value, price, _, _ = pam_crop_values("varginha-mg", "sorghum_grain", municipal, [],
                                        {"202610": 110}, {"2025": 100})
    assert value is None and price is None
