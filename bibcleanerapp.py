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
        def highlight_citations(text, citation_map):
            def replacer(match):
                keys = match.group(2).split(',')
                updated_keys = [citation_map.get(k.strip(), k.strip()) for k in keys]
                return f"{match.group(1)}{{{' ,'.join(updated_keys)}}}"
            return re.sub(r'(\\cite\w*\s*\{)([^}]+)\}', replacer, text)

        st.subheader("📄 Fixed .tex File Preview")
        fixed_tex = tex_str
        for old_key, new_key in citation_map.items():
            pattern = re.compile(rf'(\\cite\w*\s*\{{[^}}]*?)\b{re.escape(old_key)}\b', re.IGNORECASE)
            fixed_tex = pattern.sub(rf'\1{new_key}', fixed_tex)

        st.text_area("Fixed .tex content:", fixed_tex, height=500)

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
