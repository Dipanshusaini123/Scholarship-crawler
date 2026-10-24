# 🎓 Scholarship Crawler

An AI-powered scholarship discovery and information extraction system built with Python. The project discovers scholarship-related URLs, filters pages based on their actual content, extracts structured scholarship information from official guidelines, and stores records in an SQLite database for display through a Streamlit dashboard.

## 🌐 Live Application

**[Launch Scholarship Crawler](https://scholarship-crawler.streamlit.app/)**

## 📌 Project Overview

Scholarship information is distributed across government portals and official guideline documents. Finding relevant pages and extracting accurate details manually can be time-consuming.

The Scholarship Crawler automates URL discovery, content-based filtering, PDF processing, and scholarship information extraction.

To manage LLM API usage and processing costs, the current detailed extraction pipeline focuses on one trusted official scholarship portal instead of processing every discovered website with an LLM.

The project also handles image-based, scanned PDFs using vision-based processing, enabling scholarship details to be extracted even when conventional PDF text extraction cannot read the document.

## ✨ Key Features

- **Automated URL Discovery:** Discover multiple potentially relevant URLs from configured websites.
- **Content-Based Filtering:** Identify pages containing actual scholarship details and filter out irrelevant pages.
- **Cost-Conscious AI Extraction:** Focus detailed LLM processing on a selected official scholarship portal.
- **PDF Processing:** Extract text from regular PDFs and process scanned documents using vision-based techniques.
- **Structured Information Extraction:** Organize scholarship names, eligibility criteria, award amounts, education levels, courses, required documents, and renewal requirements.
- **JSON and CSV Outputs:** Maintain structured scholarship records and URL-processing results.
- **SQLite Database:** Store and manage extracted scholarship information.
- **Streamlit Dashboard:** Provide a web interface for exploring scholarship data.

## 🛠️ Technology Stack

| Technology | Purpose |
|---|---|
| Python | Core application logic |
| Scrapy | Web crawling and URL discovery |
| Requests | Downloading web pages and PDFs |
| Beautiful Soup | HTML parsing where required |
| pypdf | PDF text extraction |
| PyMuPDF | PDF processing and page rendering |
| Groq API | AI-powered scholarship information extraction |
| Pandas | Data processing |
| SQLite | Database storage |
| Streamlit | Interactive web dashboard |

## 🔄 System Workflow

1. **URL Discovery:** Discover candidate URLs from configured websites.
2. **Content-Based Filtering:** Inspect page content and separate relevant scholarship pages from irrelevant pages.
3. **Source Selection:** Select a trusted official scholarship portal for detailed extraction.
4. **PDF Processing:** Download official guidelines and extract readable text or process scanned pages as images.
5. **AI-Powered Extraction:** Convert scholarship information into structured JSON.
6. **Database Storage:** Store scholarship records in SQLite.
7. **Dashboard:** Display scholarship information through the Streamlit application.

## 📄 OCR and Vision-Based PDF Processing

During development, a scanned, image-based scholarship PDF presented a challenge because conventional PDF text extraction could not read its contents.

To address this, the project uses a vision-based processing approach:

1. Download the official scholarship guideline PDF.
2. Convert scanned pages into images.
3. Process the images using a vision-capable model.
4. Extract scholarship information into structured fields.
5. Save the extracted details for database integration.

This approach successfully enabled the extraction of scholarship details from a scanned PDF that could not be processed through ordinary text extraction alone.

## 💰 LLM Cost Optimization

Processing every discovered website with an LLM can increase API usage and costs.

The project separates URL discovery and content filtering from detailed AI extraction. The current pipeline focuses on one selected official scholarship portal for detailed extraction, reducing unnecessary LLM processing.

## 🗄️ Database

The project uses SQLite to store structured scholarship records.

**Database location:** `data/scholarships.db`

The database supports storing and retrieving scholarship information for use in the Streamlit dashboard and subsequent processing.

## 📊 Scholarship Information

The extraction pipeline is designed to organize:

- Scholarship name
- Provider or sponsoring organization
- Eligibility criteria
- Award amount
- Education level
- Eligible courses
- Required documents
- Renewal requirements
- Source URL
- Missing fields

Original application deadlines and other source metadata can be retained separately from the extracted guideline details.

## 📁 Project Structure

```text
Scholarship-crawler/
├── 02_filter.py
├── 03_extraction.py
├── app.py
├── create_db.py
├── db_updation.py
├── requirements.txt
├── scholarship_crawler/
└── data/
    ├── all_scholarships_enriched.json
    ├── discovered_urls.csv
    ├── filtered_urls.csv
    ├── nsp_scholarship_cards.json
    ├── rejected_urls.csv
    └── scholarships.db
```

## ☁️ Deployment

The application is deployed using Streamlit Community Cloud.

**Live dashboard:** [Open Scholarship Crawler](https://scholarship-crawler.streamlit.app/)

The application uses `app.py` as its entry point and accesses scholarship records from the project database.

## 🔍 Verification Engine

A verification engine is planned as a next step to help assess scholarship record completeness, maintain supporting evidence, track verification status, and identify potentially outdated information.

## 👨‍💻 Author

**Dipanshu Saini**

- GitHub: [Dipanshusaini123](https://github.com/Dipanshusaini123)
- Repository: [Scholarship-crawler](https://github.com/Dipanshusaini123/Scholarship-crawler)

## 📄 Disclaimer

This project helps discover and organize scholarship information. Always consult official scholarship websites and guidelines for final eligibility requirements, award amounts, and application deadlines.
