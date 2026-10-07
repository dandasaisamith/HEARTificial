import pandas as pd
from tracefx import config, features, schema

def test_feature_matrix_identity_flag_off():
    cfg_base = config.default_config()
    cfg_base["features"]["use_since_open"] = False
    
    cfg_on = config.default_config()
    cfg_on["features"]["use_since_open"] = True

    df = schema.load("data/demo_small.csv")
    
    f_off = features.build(df, cfg_base)
    f_on = features.build(df, cfg_on)
    
    assert "since_open_hours" not in f_off.columns
    assert "since_open_hours" in f_on.columns
    
    # Exclude since_open_hours from f_on for comparison
    f_on_subset = f_on.drop(columns=["since_open_hours"])
    
    pd.testing.assert_frame_equal(f_off, f_on_subset)
