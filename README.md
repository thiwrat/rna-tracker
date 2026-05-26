# RNA Development Tracker

Automated daily tracking of RNA research advances from PubMed, arXiv, 
and Semantic Scholar.

## Features

- 🔍 Searches multiple sources daily
- 📂 Categorizes by RNA type
- 📊 Archives all data (CSV, JSON, Markdown)
- ⏰ Runs automatically on GitHub Actions
- ✅ Secure - no email credentials needed
- 💾 All reports stored in this repo

## How to Use

1. Clone this repo
2. Go to Actions tab
3. Click "Daily RNA Research Search"
4. Reports appear in /reports/ folder daily
5. GitHub sends you email notifications

## Reports Location

All reports saved in `/reports/` folder:

- `rna_update_YYYY-MM-DD.md` - Readable summary
- `rna_data_YYYY-MM-DD.json` - Structured data
- `rna_data_YYYY-MM-DD.csv` - Excel format

## Customization

Edit `search_rna.py` to:
- Change search keywords
- Modify categories
- Adjust results count

Edit `.github/workflows/rna-daily-search.yml` to:
- Change schedule time
- Modify frequency
