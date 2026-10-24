import streamlit as st
import sqlite3
import pandas as pd

# ==========================================
# ⚙️ CONFIGURATION
# ==========================================
DB_FILE = "data/scholarships.db"

st.set_page_config(page_title="Scholarship Portal", page_icon="🎓", layout="wide")

# ==========================================
# 🗄️ DATABASE FUNCTIONS
# ==========================================
@st.cache_data
def load_data():
    """Loads all data dynamically."""
    conn = sqlite3.connect(DB_FILE)
    query = "SELECT * FROM scholarships WHERE name IS NOT NULL"
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    df = df.fillna("Not Specified")
    return df

def get_eligibility(scholarship_id):
    """Fetches the eligibility list for a specific scholarship."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT criteria FROM eligibility WHERE scholarship_id = ?", (scholarship_id,))
    results = [row[0] for row in cursor.fetchall()]
    conn.close()
    return results

def get_documents(scholarship_id):
    """Fetches the required documents list for a specific scholarship."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT document_name FROM documents WHERE scholarship_id = ?", (scholarship_id,))
    results = [row[0] for row in cursor.fetchall()]
    conn.close()
    return results

# ==========================================
# 🖥️ UI LOGIC
# ==========================================
st.title("🎓 Scholarship Search Portal")
st.write("Search and filter through available scholarships.")

# 1. Load Data
df = load_data()

# 2. Search Bar
search_query = st.text_input("🔍 Search by Scholarship Name or Provider", placeholder="Type here...")

# 3. Dynamic Filters
st.markdown("### 🎯 Filter Options")
columns_to_filter = [col for col in df.columns if col not in ['id', 'name', 'specs_url', 'faq_url', 'source_url', 'provider']]

cols = st.columns(4)
filter_dict = {}

for i, col_name in enumerate(columns_to_filter):
    with cols[i % 4]:
        unique_values = ["All"] + sorted(df[col_name].unique().tolist())
        selected_val = st.selectbox(
            f"Filter by {col_name.replace('_', ' ').title()}", 
            unique_values,
            key=f"filter_{col_name}"
        )
        filter_dict[col_name] = selected_val

st.write("---")

# 4. Apply All Filters
filtered_df = df.copy()

if search_query:
    filtered_df = filtered_df[
        filtered_df['name'].str.contains(search_query, case=False, na=False) | 
        filtered_df['provider'].str.contains(search_query, case=False, na=False)
    ]

for col_name, selected_val in filter_dict.items():
    if selected_val != "All":
        filtered_df = filtered_df[filtered_df[col_name] == selected_val]

# 5. Display Results
st.subheader(f"Showing {len(filtered_df)} Scholarships")

if filtered_df.empty:
    st.warning("No scholarships found matching your filters. Try adjusting your search.")
else:
    for index, row in filtered_df.iterrows():
        with st.container():
            st.markdown(f"#### {row['name']}")
            
            # Display main details
            for col in df.columns:
                if col not in ['id', 'name', 'specs_url', 'faq_url', 'source_url']:
                    if row[col] != "Not Specified" and row[col] != "":
                        st.markdown(f"**{col.replace('_', ' ').title()}:** {row[col]}")
            
            # --- NEW: DROPDOWNS FOR LISTS ---
            col1, col2 = st.columns(2)
            
            with col1:
                with st.expander("🎯 View Eligibility Criteria"):
                    elig_list = get_eligibility(row['id'])
                    if elig_list:
                        for item in elig_list:
                            st.markdown(f"- {item}")
                    else:
                        st.write("No specific eligibility criteria listed.")

            with col2:
                with st.expander("📄 View Required Documents"):
                    doc_list = get_documents(row['id'])
                    if doc_list:
                        for item in doc_list:
                            st.markdown(f"- {item}")
                    else:
                        st.write("No required documents listed.")
            # ---------------------------------
            
            # Link to PDF
            if row.get('specs_url') and row['specs_url'] != "Not Specified":
                st.markdown(f"👉 [📄 Download Official PDF]({row['specs_url']})")
            
            st.divider()