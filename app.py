import json
from pathlib import Path
from azure.core.exceptions import AzureError
from storage import share_grant, list_shared_grants

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

st.divider()

if st.button("Share to agency workspace"):
    try:
        created = share_grant(grant)

        if created:
            st.success("Grant shared successfully!")
        else:
            st.info("This grant is already in the workspace.")
    except (AzureError, KeyError, ValueError):
        st.error(
            "Could not save to Azure. Check the connection "
            "and try again."
        )

st.header("Agency workspace")
st.caption(
    "Demo: one shared agency workspace. Login is not connected yet."
)

st.button("Refresh workspace")

try:
    shared_records = list_shared_grants()
except (AzureError, KeyError, ValueError):
    st.error("Could not load the workspace from Azure.")
    shared_records = None

if shared_records is not None:
    if not shared_records:
        st.info("No grants shared yet.")

    for record in shared_records:
        saved_grant = record["grant"]

        with st.expander(saved_grant["title"]):
            st.write(
                f"**Funder:** {saved_grant.get('funder') or 'Not stated'}"
            )
            st.write(f"**Status:** {record['status']}")
            st.write(
                saved_grant.get("description") or "Not stated"
            )
            st.write(
                f"**Deadline:** "
                f"{saved_grant.get('deadline') or 'Not stated'}"
            )
