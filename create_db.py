import json
import sqlite3
import os

# Paths
JSON_FILE = "data/all_scholarships_enriched.json"
DB_FILE = "data/scholarships.db"

def init_db(cursor):
    """Creates the tables if they don't exist."""
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS scholarships (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        provider TEXT,
        award_amount TEXT,
        open_date TEXT,
        student_deadline TEXT,
        defective_deadline TEXT,
        institute_deadline TEXT,
        officer_deadline TEXT,
        specs_url TEXT,
        faq_url TEXT,
        source_url TEXT
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS eligibility (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        scholarship_id INTEGER,
        criteria TEXT,
        FOREIGN KEY (scholarship_id) REFERENCES scholarships (id) ON DELETE CASCADE
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        scholarship_id INTEGER,
        document_name TEXT,
        FOREIGN KEY (scholarship_id) REFERENCES scholarships (id) ON DELETE CASCADE
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS renewal_rules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        scholarship_id INTEGER,
        rule TEXT,
        FOREIGN KEY (scholarship_id) REFERENCES scholarships (id) ON DELETE CASCADE
    )
    ''')

def insert_all_data():
    if not os.path.exists(JSON_FILE):
        print(f"❌ File not found: {JSON_FILE}")
        return

    # Load JSON data
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"📚 Found {len(data)} items in JSON.")

    # Connect to DB
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    init_db(cursor)

    success_count = 0
    skipped_count = 0

    for item in data:
        # Skip items that failed during Groq extraction
        if item.get("extraction_status") != "ok":
            skipped_count += 1
            continue

        name = item.get("scholarship_name")
        if not name:
            skipped_count += 1
            continue

        try:
            # 1. Insert Main Scholarship Data
            cursor.execute('''
            INSERT OR REPLACE INTO scholarships 
            (name, provider, award_amount, open_date, student_deadline, defective_deadline, 
             institute_deadline, officer_deadline, specs_url, faq_url, source_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                name,
                item.get("provider"),
                str(item.get("award_amount")) if item.get("award_amount") else None,
                item.get("scheme_open_date"),
                item.get("student_application_deadline"),
                item.get("defective_application_deadline"),
                item.get("institute_verification_deadline"),
                item.get("officer_verification_deadline"),
                item.get("specifications_url"),
                item.get("faq_url"),
                item.get("source_url")
            ))

            # If INSERT OR REPLACE replaces an existing row, lastrowid might be 0. 
            # So we fetch the ID by name to be safe.
            cursor.execute("SELECT id FROM scholarships WHERE name = ?", (name,))
            scholarship_id = cursor.fetchone()[0]

            # 2. Clear old lists for this ID (in case we are re-running the script)
            cursor.execute("DELETE FROM eligibility WHERE scholarship_id = ?", (scholarship_id,))
            cursor.execute("DELETE FROM documents WHERE scholarship_id = ?", (scholarship_id,))
            cursor.execute("DELETE FROM renewal_rules WHERE scholarship_id = ?", (scholarship_id,))

            # 3. Insert Eligibility
            for criteria in item.get("eligibility", []):
                if criteria:
                    cursor.execute("INSERT INTO eligibility (scholarship_id, criteria) VALUES (?, ?)", (scholarship_id, criteria))

            # 4. Insert Documents
            for doc in item.get("required_documents", []):
                if doc:
                    cursor.execute("INSERT INTO documents (scholarship_id, document_name) VALUES (?, ?)", (scholarship_id, doc))

            # 5. Insert Renewal Rules
            for rule in item.get("renewal_requirements", []):
                if rule:
                    cursor.execute("INSERT INTO renewal_rules (scholarship_id, rule) VALUES (?, ?)", (scholarship_id, rule))

            success_count += 1
            print(f"✅ Inserted: {name[:50]}...")

        except Exception as e:
            print(f"❌ Error inserting {name}: {e}")

    conn.commit()
    conn.close()

    print("\n" + "="*40)
    print(f"🎉 Finished!")
    print(f"✅ Successfully inserted: {success_count}")
    print(f"⚠️ Skipped (failed extraction): {skipped_count}")
    print(f"💾 Database saved at: {DB_FILE}")

if __name__ == "__main__":
    insert_all_data()