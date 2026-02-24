import io
import os
import base64

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Bank Statement Converter", layout="wide")

# load and show logos at the top center of the page depending on theme
# a media query ensures the correct image appears for light/dark mode


# helper functions for logo handling (covered by tests)
def _logo_path(name: str) -> str:
    """Return absolute path to a logo file in ``files/Logos``.

    The tests import :mod:`streamlit_app` so we compute the path relative to
    this file rather than the current working directory.
    """
    return os.path.join(os.path.dirname(__file__), "files", "Logos", name)


def _load_logo(name: str) -> str:
    """Read a logo file and return a base64-encoded string.

    The returned string can be embedded directly in an ``<img>`` tag.
    """
    path = _logo_path(name)
    if not os.path.exists(path):
        raise FileNotFoundError(f"logo not found: {path}")
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def _make_logo_html(theme: str | None) -> str:
    """Return HTML/CSS string showing the correct logo for ``theme``.

    ``theme`` comes from ``st.get_option('theme.base')`` and may be
    ``'light'``, ``'dark'`` or ``None`` (when Streamlit hasn't yet initialized
    its configuration).  ``None`` is treated as light mode.

    The returned HTML includes a fixed container centred at the top of the
    viewport and an ``<img>`` whose source is a base64 data URI.  A
    semi-transparent background (light or dark depending on theme) ensures the
    logo remains readable.  We add padding on ``.stApp`` so the logo doesn't
    overlap the main title.
    """
    light_b64 = _load_logo("light.png")
    dark_b64 = _load_logo("Dark.png")

    use_dark = theme == "dark"
    logo_data = dark_b64 if use_dark else light_b64
    bg = "rgba(0,0,0,0.6)" if use_dark else "rgba(255,255,255,0.6)"

    return f"""
    <style>
    .logo-container {{
        position: fixed;
        top: 10px;
        left: 50%;
        transform: translateX(-50%);
        z-index: 9999;
        text-align: center;
        background: {bg};
        padding: 4px 8px;
        border-radius: 8px;
    }}
    .logo-img {{ height: 48px; }}
    .stApp {{ padding-top: 80px; }}
    </style>
    <div class="logo-container">
        <img src="data:image/png;base64,{logo_data}" class="logo-img" />
    </div>
    """


def _inject_logos() -> None:
    """Insert theme‑aware logo HTML into the page.

    Unlike the previous implementation we do *not* rely on the
    ``prefers-color-scheme`` media query, since that follows the *browser's*
    color preference rather than the Streamlit theme chosen by the user.
    Instead we look up the current theme via ``st.get_option`` and regenerate
    the logo markup on every run.  Because Streamlit reruns the script when the
    theme changes, the correct logo will be shown automatically.
    """
    try:
        theme = st.get_option("theme.base")
    except Exception:
        theme = None
    st.markdown(_make_logo_html(theme), unsafe_allow_html=True)


# always inject logos when the module is loaded; Streamlit ignores the call
# outside of the server process and the tests only rely on ``_load_logo``
_inject_logos()


def _render_title() -> None:
    """Render the page title with a small logo in front of the text.

    The logo chosen matches the current theme (light/dark).  We purposely
    avoid calling ``st.title`` because it doesn't support inline images; instead
    we write HTML via ``st.markdown``.  The image height is kept low so the
    heading text remains the visual focus.
    """
    try:
        theme = st.get_option("theme.base")
    except Exception:
        theme = None
    logo = _load_logo("Dark.png" if theme == "dark" else "light.png")
    # choose a larger height for better visibility (approx 50% larger)
    img_height = 60
    st.markdown(
        f"<h1><img src=\"data:image/png;base64,{logo}\" "
        f"style=\"height:{img_height}px;vertical-align:middle;margin-right:8px;\"/> "
        "Bank Statement Converter</h1>",
        unsafe_allow_html=True,
    )


# title + description
_render_title()
st.write(
    "Upload your original bank statement (Excel) and transform it into the Odoo format."
)

# file uploader
uploaded_file = st.file_uploader(
    "Original bank statement (Excel)", type=["xlsx", "xls"], key="uploader"
)


def convert_statement(df: pd.DataFrame) -> pd.DataFrame:
    """Map original columns to Odoo columns and compute Amount.

    Original columns:
      - Operation DT
      - Detailed description
      - Reference
      - Debit (stored as text, will be converted to numeric)
      - Credit (stored as text, will be converted to numeric)

    Output columns:
      - Date (formatted as yyyy-mm-dd)
      - Label
      - Reference
      - Amount (integer: negative for debit, positive for credit)
    """
    # ensure required columns exist
    required = [
        "Operation DT",
        "Detailed description",
        "Reference",
        "Debit",
        "Credit",
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in original file: {missing}")

    out = pd.DataFrame()
    
    # Format date as yyyy-mm-dd
    out["Date"] = pd.to_datetime(df["Operation DT"]).dt.strftime("%Y-%m-%d")
    out["Label"] = df["Detailed description"]
    out["Reference"] = df["Reference"]

    # Helper to parse amounts that may be text with commas or spaces
    def parse_amount(val):
        """Return a float parsed from various text formats.

        Accepts things like:
          - 1234
          - "1234.56"
          - "1 234,56" (space as thousands sep, comma as decimal)
          - "665,00"  (comma decimal)
          - None/NaN -> 0.0
        """
        if pd.isna(val):
            return 0.0
        if isinstance(val, (int, float)):
            return float(val)
        s = str(val).strip()
        # remove spaces (non-breaking too)
        s = s.replace(" ", "").replace("\xa0", "")
        # replace comma decimal with dot
        s = s.replace(",", ".")
        # drop any non-digit/dot/minus characters
        import re
        s = re.sub(r"[^0-9.\-]", "", s)
        try:
            return float(s)
        except Exception:
            return 0.0

    # Convert Debit and Credit columns handling text formats
    debit_numeric = df["Debit"].apply(parse_amount)
    credit_numeric = df["Credit"].apply(parse_amount)

    # compute amount; debit becomes negative
    def compute_amount(d, c):
        if d != 0.0:
            return -d
        return c

    # Convert amount to float, preserving centimes (two decimal places)
    out["Amount"] = [
        round(compute_amount(d, c), 2) for d, c in zip(debit_numeric, credit_numeric)
    ]
    return out


if uploaded_file is not None:
    try:
        # read the excel file (support .xls and .xlsx)
        df = pd.read_excel(uploaded_file)
    except ImportError as ie:
        # this typically happens if xlrd is missing for .xls files
        st.error(
            "Error reading spreadsheet: xlrd is required for .xls files. "
            "Install it with `pip install xlrd` and try again."
        )
        df = None
    except Exception as e:
        st.error(f"Error reading spreadsheet: {e}")
        df = None

    if df is not None:
        st.write("### Preview of original file")
        st.dataframe(df.head())

        try:
            converted = convert_statement(df)
            st.write("### Converted (Odoo) format")
            st.dataframe(converted.head())

            # provide download
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                converted.to_excel(writer, index=False, sheet_name="OdooStatement")
                
                # Apply Odoo-style formatting using openpyxl
                from openpyxl.styles import numbers
                worksheet = writer.sheets["OdooStatement"]
                
                # Format Date column (column A) as yyyy-mm-dd
                for row in worksheet.iter_rows(min_row=2, max_row=len(converted)+1, min_col=1, max_col=1):
                    for cell in row:
                        cell.number_format = 'yyyy-mm-dd'
                
# Format Amount column (column D) with two decimal places
            for row in worksheet.iter_rows(min_row=2, max_row=len(converted)+1, min_col=4, max_col=4):
                for cell in row:
                    cell.number_format = '0.00'  # two decimals
            
            buffer.seek(0)
            st.download_button(
                label="Download Odoo bank statement",
                data=buffer,
                file_name="Odoo_bank_statement.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        except Exception as e:
            st.error(f"Error processing file: {e}")
