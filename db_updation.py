import sqlite3

conn = sqlite3.connect("data/scholarships.db")
cursor = conn.cursor()

# Add the 'state' column if it doesn't exist
try:
    cursor.execute("ALTER TABLE scholarships ADD COLUMN state TEXT DEFAULT 'All India'")
    conn.commit()
    print("✅ Added 'state' column to database.")
except sqlite3.OperationalError:
    print("⚠️ 'state' column already exists.")

conn.close()