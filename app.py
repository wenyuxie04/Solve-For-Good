import json
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="Grant Finder", layout="wide")

st.title("Grant Finder")
st.caption("Prototype · Fictional demo grants")

data_path = Path(__file__).parent / "data" / "grants.json"

with data_path.open(encoding="utf-8") as file:
    grants = json.load(file)

keyword = st.text_input("Search grants", placeholder="Try water")

results = [
    grant
    for grant in grants
    if keyword.lower()
    in f"{grant['title']} {grant['description']}".lower()
]

st.write(f"{len(results)} opportunities found")

if not results:
    st.info("No matches. Try another keyword.")
    st.stop()

selected_id = st.selectbox(
    "Select a grant",
    options=[grant["id"] for grant in results],
    format_func=lambda grant_id: next(
        grant["title"] for grant in results
        if grant["id"] == grant_id
    ),
)

grant = next(g for g in results if g["id"] == selected_id)

st.subheader(grant["title"])
st.write(f"**Funder:** {grant['funder']}")
st.write(f"**Deadline:** {grant.get('deadline') or 'Not stated'}")
st.write(grant["description"])
st.write(f"**Eligibility:** {grant['eligibility_text']}")

if grant.get("source_url"):
    st.link_button("View original posting", grant["source_url"])
