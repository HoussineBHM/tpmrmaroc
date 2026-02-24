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


def test_logo_loading():
    """The light and dark logos must exist and be encodable.

    We also exercise the helper functions directly since they are used when
    the Streamlit app starts.
    """
    from streamlit_app import _load_logo, _logo_path

    for name in ("light.png", "Dark.png"):
        path = _logo_path(name)
        assert os.path.exists(path), f"logo file missing: {path}"
        data = _load_logo(name)
        assert isinstance(data, str) and len(data) > 50
        assert all(c.isalnum() or c in "+/=\n" for c in data)


def test_make_logo_html_respects_theme(monkeypatch):
    """The generated HTML should contain the correct logo and background.

    We check both light and dark themes by monkey-patching
    ``st.get_option`` since ``_inject_logos`` calls it internally.
    """
    from streamlit_app import _make_logo_html, _inject_logos, _load_logo
    import streamlit as st

    # force light theme
    monkeypatch.setattr(st, "get_option", lambda key: "light")
    html_light = _make_logo_html("light")
    assert "background: rgba(255,255,255" in html_light
    assert "logo-img" in html_light
    # it should include the light.png encoded data
    light_b64 = _load_logo("light.png")
    assert light_b64 in html_light

    # force dark theme
    monkeypatch.setattr(st, "get_option", lambda key: "dark")
    html_dark = _make_logo_html("dark")
    assert "background: rgba(0,0,0" in html_dark
    dark_b64 = _load_logo("Dark.png")
    assert dark_b64 in html_dark

    # calling _inject_logos shouldn't raise even though it tries to render
    _inject_logos()


def test_render_title(monkeypatch):
    """The title helper should emit an <h1> with the appropriate logo.

    We verify both light and dark themes by patching ``st.get_option``.
    """
    from streamlit_app import _render_title, _load_logo
    import streamlit as st

    # light theme
    monkeypatch.setattr(st, "get_option", lambda key: "light")
    # capture markdown by monkeypatching st.markdown
    captured = {}
    def fake_md(html, unsafe_allow_html=False):
        captured['html'] = html
    monkeypatch.setattr(st, "markdown", fake_md)
    _render_title()
    assert "<h1>" in captured['html']
    assert _load_logo("light.png") in captured['html']
    # logo height should be the adjusted larger size
    assert "height:60px" in captured['html']

    # dark theme
    monkeypatch.setattr(st, "get_option", lambda key: "dark")
    _render_title()
    assert _load_logo("Dark.png") in captured['html']
    assert "height:60px" in captured['html']
