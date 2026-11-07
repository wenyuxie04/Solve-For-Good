import json
from pathlib import Path

import streamlit as st
from azure.core.exceptions import AzureError

from storage import (
    share_grant,
    list_shared_grants,
    update_review_status,
)


st.set_page_config(
    page_title="Federal Funds Matchmaker",
    layout="wide",
)

st.markdown(
    """
    <style>
    .block-container {
        max-width: 1150px;
        padding-top: 2rem;
    }
    h1 {
        font-size: 2rem !important;
        letter-spacing: -0.04em;
    }
    h2, h3 {
        letter-spacing: -0.02em;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 14px;
    }
    .brand-line {
        height: 5px;
        width: 64px;
        background: #7BAFD4;
        border-radius: 4px;
        margin-bottom: 16px;
    }
    </style>
    <div class="brand-line"></div>
    """,
    unsafe_allow_html=True,
)

st.title("Federal Funds Matchmaker")
st.caption("Federal grant discovery & agency collaboration")

data_path = Path(__file__).parent / "data" / "grants.json"

with data_path.open(encoding="utf-8") as file:
    grants = json.load(file)

st.session_state.setdefault("page", "Search")
st.session_state.setdefault("selected_grant", None)
st.session_state.setdefault("search_text", "")


def navigate(page, grant=None):
    st.session_state.page = page
    if grant is not None:
        st.session_state.selected_grant = grant
    st.rerun()


def remember_search():
    st.session_state.search_text = st.session_state.search_input


def share_button(grant, key):
    if st.button("Share to workspace", key=key):
        try:
            created = share_grant(grant)
            if created:
                st.success("Added to agency workspace.")
            else:
                st.info("Already in the agency workspace.")
        except (AzureError, KeyError, ValueError):
            st.error("Could not save. Check the Azure connection.")


def show_source(grant):
    if grant.get("source_url"):
        st.link_button("Official posting ↗", grant["source_url"])


# Left sidebar navigation
with st.sidebar:
    st.markdown("### Federal Funds Matchmaker")
    st.caption("Agency funding workspace")
    st.divider()

    for page in ["Search", "Grant Details", "Workspace"]:
        if st.button(
            page,
            key=f"navigation-{page}",
            type=(
                "primary"
                if st.session_state.page == page
                else "secondary"
            ),
            use_container_width=True,
        ):
            navigate(page)

    st.divider()
    st.caption("Demo · Login not connected")


# SEARCH
if st.session_state.page == "Search":
    st.header("Find funding opportunities")
    st.write("Explore grants and share opportunities with your agency.")

    st.session_state.setdefault(
        "search_input",
        st.session_state.search_text,
    )

    keyword = st.text_input(
        "Keywords",
        placeholder="Search by topic, program, or project...",
        key="search_input",
        on_change=remember_search,
    )

    sort_by = st.selectbox(
        "Sort results",
        ["Original order", "Title A–Z"],
    )

    query = keyword.strip().lower()

    results = [
        grant
        for grant in grants
        if query in (
            f"{grant.get('title', '')} "
            f"{grant.get('description', '')}"
        ).lower()
    ]

    if sort_by == "Title A–Z":
        results = sorted(
            results,
            key=lambda grant: grant.get("title", "").lower(),
        )

    st.subheader("Grant opportunities")
    st.caption(f"{len(results)} results")

    if not results:
        st.info("No matches. Try another keyword.")

    for grant in results:
        with st.container(border=True):
            main, relevance = st.columns([4, 1])

            with main:
                st.subheader(grant["title"])
                st.caption(
                    grant.get("funder") or "Funder not stated"
                )

            with relevance:
                st.caption("Relevance")
                st.write("Not calculated")

            st.write(
                f"**Deadline:** "
                f"{grant.get('deadline') or 'Not stated'}"
            )
            st.write(
                f"**Eligibility:** "
                f"{grant.get('eligibility_text') or 'Not stated'}"
            )
            st.write(
                grant.get("description") or "Not stated"
            )

            share_column, detail_column = st.columns(2)

            with share_column:
                share_button(
                    grant,
                    f"search-share-{grant['id']}",
                )

            with detail_column:
                if st.button(
                    "View details →",
                    key=f"search-details-{grant['id']}",
                    type="primary",
                    use_container_width=True,
                ):
                    navigate("Grant Details", grant)


# GRANT DETAILS
elif st.session_state.page == "Grant Details":
    grant = st.session_state.selected_grant

    if grant is None:
        st.info("Open a grant from Search or Workspace.")
    else:
        if st.button("← Back to search"):
            navigate("Search")

        st.header(grant["title"])

        facts, content = st.columns([1, 2])

        with facts:
            with st.container(border=True):
                st.subheader("Key information")

                st.write("**Funder**")
                st.write(grant.get("funder") or "Not stated")

                st.write("**Deadline**")
                st.write(grant.get("deadline") or "Not stated")

                st.write("**Eligibility**")
                st.write(
                    grant.get("eligibility_text") or "Not stated"
                )
                st.caption("Verify against the official notice.")

                show_source(grant)
                share_button(grant, "detail-share")

        with content:
            with st.container(border=True):
                st.subheader("Overview")
                st.write(
                    grant.get("description") or "Not stated"
                )

                st.subheader("Application requirements")
                st.write(
                    grant.get("requirements") or "Not stated"
                )

                st.subheader("Why this matches")
                st.write(
                    "Agency matching has not been calculated yet."
                )


# WORKSPACE
elif st.session_state.page == "Workspace":
    st.header("Agency workspace")
    st.caption(
        "One shared demo agency · login not connected yet"
    )

    st.button("Refresh workspace")

    try:
        records = list_shared_grants()
    except (AzureError, KeyError, ValueError):
        st.error("Could not load the workspace from Azure.")
        records = None

    if records is not None:
        if not records:
            st.info(
                "No shared grants yet. Share an opportunity from Search."
            )
        else:
            st.dataframe(
                [
                    {
                        "Grant": record["grant"]["title"],
                        "Funder": (
                            record["grant"].get("funder")
                            or "Not stated"
                        ),
                        "Deadline": (
                            record["grant"].get("deadline")
                            or "Not stated"
                        ),
                        "Status": (
                            record.get("status") or "Not Reviewed"
                        ),
                        "Reviewer": (
                            record.get("assigned_reviewer")
                            or "Unassigned"
                        ),
                    }
                    for record in records
                ],
                hide_index=True,
                use_container_width=True,
            )
            st.subheader("Review shared grants")

            statuses = [
                "Not Reviewed",
                "Under Review",
                "Pursue",
                "Pass",
            ]

            for record in records:
                grant = record["grant"]

                with st.expander(grant["title"]):
                    st.write(
                        grant.get("description") or "Not stated"
                    )

                    current_status = record.get(
                        "status", "Not Reviewed"
                    )
                    if current_status not in statuses:
                        current_status = "Not Reviewed"

                    # Include the version so changed records reload
                    # with the latest saved status.
                    version_key = (
                        f"{grant['id']}-{record['_etag']}"
                    )

                    with st.form(f"review-{version_key}"):
                        selected_status = st.selectbox(
                            "Review status",
                            statuses,
                            index=statuses.index(current_status),
                        )
                        assigned_reviewer = st.text_input(
                            "Assigned reviewer",
                            value=record.get("assigned_reviewer", ""),
                            placeholder="Enter a teammate's name",
                        )

                        submitted = st.form_submit_button(
                            "Save review"
                        )

                    if submitted:
                        try:
                            saved = update_review_status(
                                record,
                                selected_status,
                                assigned_reviewer,
                            )

                            if saved:
                                st.success(
                                    "Saved to Azure. Click Refresh "
                                    "workspace to update the table."
                                )
                            else:
                                st.warning(
                                    "Someone updated this grant. "
                                    "Refresh the workspace before "
                                    "trying again."
                                )
                        except (AzureError, KeyError, ValueError):
                            st.error(
                                "Could not save the status. "
                                "Please try again."
                            )

                    if st.button(
                        "View full details",
                        key=f"workspace-details-{grant['id']}",
                    ):
                        navigate("Grant Details", grant)
