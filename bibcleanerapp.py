import streamlit as st
import bibtexparser
import hashlib
import re
from collections import defaultdict
from io import StringIO

st.set_page_config(page_title="BibCleaner", layout="wide")
st.title("📚 BibCleaner: Detect & Fix Duplicate Citations")

# --- Helper functions ---
def normalize(s):
    return s.lower().replace('{', '').replace('}', '').strip()

def hash_entry(entry):
    fields = ['title', 'author', 'year', 'journal', 'volume', 'pages']
    return hashlib.md5('|'.join([normalize(entry.get(f, '')) for f in fields]).encode()).hexdigest()

def load_bib_entries(bib_file):
    bib_db = bibtexparser.load(bib_file)
    return bib_db.entries, bib_db

def group_duplicates(entries):
    hash_groups = defaultdict(list)
    for entry in entries:
        h = hash_entry(entry)
        hash_groups[h].append(entry)
    return hash_groups

# --- File Upload ---
st.sidebar.header("1. Upload Files")
bib_file = st.sidebar.file_uploader("Upload .bib file", type="bib")
tex_file = st.sidebar.file_uploader("(Optional) Upload .tex file", type="tex")

if bib_file:
    st.subheader("🔍 Duplicate Bibliography Entries")
    entries, bib_db = load_bib_entries(bib_file)
    dup_groups = group_duplicates(entries)

    citation_map = {}
    cleaned_entries = []

    for group in dup_groups.values():
        if len(group) > 1:
            group.sort(key=lambda e: len(e['ID']))
            default = group[0]['ID']
            options = [e['ID'] for e in group]
            chosen = st.selectbox(f"Choose preferred key for: {', '.join(options)}", options, index=0, key=default)
            for e in group:
                if e['ID'] != chosen:
                    citation_map[e['ID']] = chosen
            cleaned_entries.append([e for e in group if e['ID'] == chosen][0])
        else:
            cleaned_entries.append(group[0])

    # --- TEX Highlight ---
    if tex_file:
        tex_str = tex_file.read().decode('utf-8')

        st.subheader("📄 Side-by-side Preview of Citation Fixes")
        fixed_lines = []
        original_lines = tex_str.splitlines()

        for line in original_lines:
            updated_line = line
            for old_key, new_key in citation_map.items():
                pattern = re.compile(rf'(\\cite\w*\s*\{{[^}}]*?)\b{re.escape(old_key)}\b')
                updated_line = pattern.sub(rf'\1{new_key}', updated_line)
            if updated_line != line:
                fixed_lines.append((line, updated_line))

        if fixed_lines:
            for original, fixed in fixed_lines:
                st.markdown(f"<div style='margin-bottom:10px;'>
                <span style='color:gray;'>Original:</span><br>
                <code style='background:#f8f8f8;padding:2px;'>{original}</code><br>
                <span style='color:green;'>Fixed:</span><br>
                <code style='background:#eaffea;padding:2px;'>{fixed}</code>
                </div>", unsafe_allow_html=True)
        else:
            st.info("No citations were changed.")

        # Show full fixed .tex for download
        fixed_tex = tex_str
        for old_key, new_key in citation_map.items():
            pattern = re.compile(rf'(\\cite\w*\s*\{{[^}}]*?)\b{re.escape(old_key)}\b', re.IGNORECASE)
            fixed_tex = pattern.sub(rf'\1{new_key}', fixed_tex)

        st.text_area("📜 Full Fixed .tex content:", fixed_tex, height=400)
        st.download_button("📥 Download Fixed .tex", fixed_tex, file_name="fixed_main.tex")

    # --- Save Cleaned .bib File ---
    from bibtexparser.bwriter import BibTexWriter
    new_db = bibtexparser.bibdatabase.BibDatabase()
    new_db.entries = cleaned_entries
    writer = BibTexWriter()
    cleaned_bib = writer.write(new_db)

    st.subheader("📁 Download Cleaned .bib File")
    st.download_button("📥 Download Cleaned .bib", cleaned_bib, file_name="cleaned.bib")
else:
    st.info("Upload a .bib file to get started.")
