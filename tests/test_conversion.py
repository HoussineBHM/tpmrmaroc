import os
import sys
import pandas as pd
import pytest

# ensure workspace root is on path so we can import streamlit_app
root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root not in sys.path:
    sys.path.insert(0, root)

from streamlit_app import convert_statement


def make_row(op, desc, ref, debit, credit):
    return {
        "Operation DT": op,
        "Detailed description": desc,
        "Reference": ref,
        "Debit": debit,
        "Credit": credit,
    }


def test_basic_conversion():
    rows = [
        make_row("2026-02-24", "Foo", "R1", 50, None),
        make_row("2026-02-25", "Bar", "R2", None, 75.5),
        make_row("2026-02-26", "Baz", "R3", 0, 0),
        # comma-decimal values stored as text
        make_row("2026-02-27", "Comma debit", "R4", "665,00", None),
        make_row("2026-02-28", "Comma credit", "R5", None, "1 234,50"),
        make_row("2026-03-01", "Text suffix", "R6", "665,00 credit", None),
        make_row("2026-03-02", "Precision", "R7", None, "4631,36"),
    ]
    df = pd.DataFrame(rows)
    out = convert_statement(df)
    assert list(out.columns) == ["Date", "Label", "Reference", "Amount"]
    # Check date format is yyyy-mm-dd string
    assert out.loc[0, "Date"] == "2026-02-24"
    assert out.loc[1, "Date"] == "2026-02-25"
    # Check amounts preserve two decimals
    assert out.loc[0, "Amount"] == -50.0
    assert out.loc[1, "Amount"] == 75.5
    assert out.loc[2, "Amount"] == 0.0
    # verify comma‑formatted values parsed correctly
    assert out.loc[3, "Amount"] == -665.0
    assert out.loc[4, "Amount"] == 1234.5
    # strip extraneous text
    assert out.loc[5, "Amount"] == -665.0
    # check decimal precision is preserved exactly
    assert out.loc[6, "Amount"] == 4631.36


def test_missing_column_raises():
    df = pd.DataFrame({"Operation DT": ["x"], "Debit": [10]})
    with pytest.raises(ValueError):
        convert_statement(df)
