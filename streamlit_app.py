import io

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Bank Statement Converter", layout="wide")

st.title("📄 Bank Statement Converter")
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
