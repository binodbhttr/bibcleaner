import streamlit as st
import bibtexparser
import hashlib
import re
from collections import defaultdict

st.title("📚 BibCleaner: Fix Duplicate Citations")

# Upload files
bib_file = st.file_uploader("Upload your .bib file", type=["bib"])
tex_file = st.file_uploader("Upload your .tex file", type=["tex"])

def normalize(s):
    return s.lower().replace('{', '').replace('}', '').strip()

def hash_entry(entry):
    fields = ['title', 'author', 'year', 'journal', 'volume', 'pages']
    return hashlib.md5('|'.join([normalize(entry.get(f, '')) for f in fields]).encode()).hexdigest()

if bib_file and tex_file:
    bib_db = bibtexparser.load(bib_file)
    entries = bib_db.entries

    hash_groups = defaultdict(list)
    for e in entries:
        hash_groups[hash_entry(e)].append(e)

    citation_map = {}
    cleaned_entries = []
    for group in hash_groups.values():
        group.sort(key=lambda e: len(e['ID']))  # Shortest key wins
        keep = group[0]
        cleaned_entries.append(keep)
        for dup in group[1:]:
            citation_map[dup['ID']] = keep['ID']

    st.success(f"Found {len(citation_map)} duplicate citation keys.")
    st.write(citation_map)

    tex_content = tex_file.read().decode()

    def replace_cites(text, citation_map):
        def replacer(match):
            keys = match.group(2).split(',')
            keys = [citation_map.get(k.strip(), k.strip()) for k in keys]
            return f"{match.group(1)}{{{','.join(keys)}}}"
        return re.sub(r'(\\cite\w*\s*\{)([^}]+)\}', replacer, text)

    fixed_tex = replace_cites(tex_content, citation_map)
    cleaned_bib_str = bibtexparser.dumps(bibtexparser.bibdatabase.BibDatabase(entries=cleaned_entries))

    st.download_button("📥 Download Cleaned .bib", cleaned_bib_str, file_name="cleaned.bib")
    st.download_button("📥 Download Fixed .tex", fixed_tex, file_name="fixed_main.tex")
