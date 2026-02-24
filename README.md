# tpmrmaroc

This repository contains a **Streamlit** application that converts a bank
statement from an "Original bank statement" Excel file into the format
expected by Odoo.

## Features

1. Upload an Excel file containing the following columns:
   - `Operation DT`
   - `Detailed description`
   - `Reference`
   - `Debit`
   - `Credit`
2. The app transforms the data to match Odoo's bank statement format:
   - `Date` → formatted as `yyyy-mm-dd` (from `Operation DT`)
   - `Label` → `Detailed description`
   - `Reference` → `Reference`
   - `Amount` → numeric format with two decimals (negative for debit, positive for credit)
3. Preview the original and converted data and download the result as an
   Excel file named `Odoo_bank_statement.xlsx` with proper Odoo formatting.

## Quick start

1. **Install dependencies** (preferably in a virtual environment):

   ```bash
   pip install -r requirements.txt
   ```

2. **Run the Streamlit app**:

   ```bash
   streamlit run streamlit_app.py
   ```

3. Open the URL shown in the terminal (usually `http://localhost:8501`).

> **Note:** reading `.xls` files requires the `xlrd` package.
> It is included in `requirements.txt`, but if you install dependencies
> manually make sure `pip install xlrd` is run.

## Development

Tests live in `tests/test_conversion.py` and can be executed with:

```bash
pytest -q
```

Feel free to extend the converter with additional formats or validation logic.
