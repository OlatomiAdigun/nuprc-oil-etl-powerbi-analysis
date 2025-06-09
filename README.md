# 🛢️ NUPRC Oil Production ETL & Power BI Dashboard

This project automates the end-to-end ETL pipeline for Nigerian upstream oil production data, sourced from the [Nigerian Upstream Petroleum Regulatory Commission (NUPRC)](https://www.nuprc.gov.ng/), cleans it, and makes it available for business intelligence analysis in Power BI.

---

## 🚀 Project Overview

**Goal**: Automate extraction, transformation, and loading (ETL) of oil and condensate production reports, and enable monthly updates into a Power BI dashboard for visualization and analysis.

---

## 🔁 Workflow Summary

| Step        | Description |
|-------------|-------------|
| **Extract** | Scrapes all available `.xls`, `.xlsx`, `.csv` production files from the [NUPRC website](https://www.nuprc.gov.ng/oil-production-status-report/) |
| **Transform** | Cleans headers, unifies structure, melts monthly production data, and parses stream names, years, and months |
| **Load** | Uploads the cleaned, combined CSV file to a fixed Google Drive location |
| **Visualize** | Power BI connects to the Google Drive CSV for automated refresh and analytics |

---

## 📁 Folder Structure

nuprc_etl_clean/
│
├── raw_data/ # Raw NUPRC files downloaded monthly
├── processed/ # Cleaned and combined output file (final_combined.csv)
├── run_pipeline.py # Main ETL script with GDrive upload
├── nuprc_report.pbix # Power BI dashboard file
└── README.md # This documentation


---

## 📊 Power BI Dashboard Highlights

- 📈 **Trend Analysis**: Monthly oil vs condensate production volumes  
- 🔁 **Month-over-Month**: Uses *average daily production* to remove month-length bias  
- 🗃️ **Stream-level Insights**: Terminal/Stream performance over time  
- 🛢️ **Oil-Condensate Ratio**: Visualized to track blend variation  

---

## 🛠️ Tech Stack

- **Python**: `requests`, `pandas`, `bs4`, `google-api-python-client`
- **Google Drive API**: Authenticated upload of final CSV
- **Power BI**: Data transformation and dashboarding
- **Windows Task Scheduler**: For monthly automation

---

## 🧠 Automation Flow

1. `run_pipeline.py` is executed monthly (via Task Scheduler)
2. New files are downloaded and cleaned
3. A single CSV is generated and **overwritten** on Google Drive
4. Power BI reads the Google Drive CSV and updates visuals

---

## 🔐 Security

> 🔒 Sensitive files such as `credentials.json` and `token.json` were excluded from GitHub using `.gitignore` to prevent credential leaks.

---

## 🧪 Future Improvements

- Add email notifications after successful pipeline runs
- Integrate with Google Sheets or BigQuery for advanced querying
- Deploy on a cloud-based scheduler (e.g., GitHub Actions or Google Cloud Functions)

---

## 🙋‍♂️ Author

**Olatomi Adigun**  
[GitHub Profile](https://github.com/OlatomiAdigun)  
Calgary, Alberta | Data Engineer | [LinkedIn](https://www.linkedin.com/in/olatomiadigun)

---

## 📝 License

This project is for educational and demonstration purposes only.

