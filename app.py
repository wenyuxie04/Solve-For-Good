import json
from pathlib import Path
from matching import match_grant
from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st
from azure.core.exceptions import AzureError

from storage import (
    share_grant,
    list_shared_grants,
    update_review_status,
    add_comment,
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

data_directory = Path(__file__).parent / "data"
live_path = data_directory / "grants-live.json"

if live_path.exists():
    data_path = live_path
    st.caption("Data source: Grants.gov snapshot")
else:
    data_path = data_directory / "grants.json"
    st.warning("Using fictional demo grants. Real data not loaded yet.")

with data_path.open(encoding="utf-8") as file:
    grants = json.load(file)

if data_path == live_path and grants:
    st.caption(
        f"Fetched: {grants[0].get('fetched_at', 'Unknown')} "
        "· Snapshot refresh is currently manual"
    )

agency_directory = Path(__file__).parent / "data" / "agencies"
agencies = {}

for profile_path in sorted(agency_directory.glob("*.json")):
    with profile_path.open(encoding="utf-8") as file:
        profile = json.load(file)
        agencies[profile["id"]] = profile

if not agencies:
    st.error("No agency profiles found in data/agencies.")
    st.stop()

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


def share_button(grant, key, workspace_id):
    if st.button("Share to workspace", key=key):
        try:
            created = share_grant(
                grant, workspace_id=workspace_id
            )
            if created:
                st.success("Added to agency workspace.")
            else:
                st.info("Already in the agency workspace.")
        except (AzureError, KeyError, ValueError):
            st.error("Could not save. Check the Azure connection.")


def show_source(grant):
    url = grant.get("source_url")

    if url:
        st.link_button("Open original grant announcement ↗", url)
        st.caption(url)
    else:
        st.caption("Original announcement link not available.")

def funding_label(grant):
    def number(value):
        try:
            result = float(value)
            return result if result >= 0 else None
        except (ValueError, TypeError):
            return None

    minimum = number(grant.get("award_min"))
    maximum = number(grant.get("award_max"))

    if minimum is not None and maximum is not None:
        if minimum == maximum:
            return f"${maximum:,.0f}"
        return f"${minimum:,.0f} – ${maximum:,.0f}"

    if maximum is not None:
        return f"Up to ${maximum:,.0f}"

    if minimum is not None:
        return f"From ${minimum:,.0f}"

    return "Not stated"


def deadline_date(grant):
    value = grant.get("deadline")

    if not value:
        return None

    for date_format in ("%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(
                str(value).strip(), date_format
            ).date()
        except ValueError:
            continue

    return None


def deadline_label(grant):
    closing_date = deadline_date(grant)

    if closing_date is None:
        return grant.get("deadline") or "Not stated"

    today = datetime.now(ZoneInfo("America/New_York")).date()
    days_left = (closing_date - today).days

    if days_left < 0:
        timing = "Past closing date"
    elif days_left == 0:
        timing = "Closes today"
    else:
        timing = f"{days_left} days left"

    return f"{closing_date:%b %d, %Y} · {timing}"
# Left sidebar navigation
with st.sidebar:
    agency_id = st.selectbox(
        "Agency",
        options=list(agencies),
        format_func=lambda agency_id: agencies[agency_id]["short_name"],
        key="selected_agency",
    )
    agency = agencies[agency_id]
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
    st.caption(f"Selected agency: {agency['name']}")

    with st.expander("Agency priorities"):
        for priority in agency["priorities"]:
            if priority.get("enabled", True):
                st.markdown(f"**{priority['title']}**")
                st.write(priority["description"])
                st.link_button(
                    "View priority source",
                    priority["source_url"],
                )
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
        ["Best keyword match", "Original order", "Title A–Z"],
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

    if sort_by == "Best keyword match":
        results = sorted(
            results,
            key=lambda grant: (
                -match_grant(grant, agency)["keyword_count"],
                grant["title"].lower(),
            ),
        )

    elif sort_by == "Title A–Z":
        results = sorted(
            results,
            key=lambda grant: grant.get("title", "").lower(),
        )
    deadline_window = st.selectbox(
        "Deadline",
        ["Any date", "Next 30 days", "Next 60 days", "Next 90 days"],
    )

    include_unknown = st.checkbox(
        "Include unknown or unrecognized deadlines",
        value=True,
    )

    hide_past = st.checkbox(
        "Hide grants past their closing date",
        value=True,
    )

    today = datetime.now(ZoneInfo("America/New_York")).date()
    maximum_days = {
        "Next 30 days": 30,
        "Next 60 days": 60,
        "Next 90 days": 90,
    }.get(deadline_window)

    filtered_results = []

    for grant in results:
        closing_date = deadline_date(grant)

        if closing_date is None:
            if include_unknown:
                filtered_results.append(grant)
            continue

        days_left = (closing_date - today).days

        if hide_past and days_left < 0:
            continue

        if maximum_days is not None:
            if not 0 <= days_left <= maximum_days:
                continue

        filtered_results.append(grant)

    results = filtered_results
    eligibility_filter = st.selectbox(
        "Applicant-type filter",
        [
            "Show all",
            "Applicant type matches",
            "Needs verification",
            "Applicant type does not match",
        ],
    )

    if eligibility_filter != "Show all":
        results = [
            grant
            for grant in results
            if match_grant(grant, agency)["eligibility"]["status"]
            == eligibility_filter
        ]
    st.subheader("Grant opportunities")
    st.caption(f"{len(results)} results")

    if not results:
        st.info("No matches. Try another keyword.")

    for grant in results:
        match = match_grant(grant, agency)

        with st.container(border=True):
            main, relevance = st.columns([4, 1])

            with main:
                st.subheader(grant["title"])
                st.caption(
                    grant.get("funder") or "Funder not stated"
                )
                st.write(
                    "**Funding opportunity number:** "
                    + (grant.get("opportunity_number") or "Not stated")
                )

                if grant.get("source_url"):
                    st.link_button(
                        "View on Grants.gov ↗",
                        grant["source_url"],
                    )
            with relevance:
                st.caption("Keyword matches")
                st.write(str(match["keyword_count"]))

            funding_column, deadline_column = st.columns(2)

            with funding_column:
                st.write("**Award amount**")
                st.write(funding_label(grant))

            with deadline_column:
                st.write("**Deadline**")
                st.write(deadline_label(grant))
        
            st.write(
                f"**Eligibility:** "
                f"{grant.get('eligibility_text') or 'Not stated'}"
            )
            st.write(
                grant.get("description") or "Not stated"
            )
            st.write("**Why this matches**")
            st.write(match["reason"])

            st.write(
                f"**Applicant-type check:** "
                f"{match['eligibility']['status']}"
            )
            st.caption(match["eligibility"]["reason"])
            share_column, detail_column = st.columns(2)

            with share_column:
                share_button(
                    grant,
                    f"search-share-{grant['id']}",
                    agency_id,
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
                st.write("**Funding opportunity number**")
                st.write(
                    grant.get("opportunity_number") or "Not stated"
                )
                st.write("**Funder**")
                st.write(grant.get("funder") or "Not stated")

                st.write("**Award amount**")
                st.write(funding_label(grant))

                st.write("**Deadline**")
                st.write(deadline_label(grant))

                st.write("**Eligibility**")
                st.write(
                    grant.get("eligibility_text") or "Not stated"
                )
                st.caption("Verify against the official notice.")

                show_source(grant)
                share_button(
                    grant, "detail-share", agency_id
                )

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
                match = match_grant(grant, agency)
                st.write(match["reason"])

                for evidence in match["priority_matches"]:
                    st.write(
                        f"**{evidence['priority_title']}**"
                    )
                    st.write(
                        "Matched terms: "
                        + ", ".join(evidence["matched_keywords"])
                    )
                    if evidence.get("source_url"):
                        st.link_button(
                            "Agency priority source",
                            evidence["source_url"],
                        )

                st.subheader("Applicant-type check")
                st.write(match["eligibility"]["status"])
                st.caption(match["eligibility"]["reason"])


# WORKSPACE
elif st.session_state.page == "Workspace":
    st.header("Agency workspace")
    st.caption(
        f"{agency['name']} · Demo workspace · Login not connected"
    )

    st.button("Refresh workspace")

    try:
        records = list_shared_grants(
            workspace_id=agency_id
        )
    except (AzureError, KeyError, ValueError):
        st.error("Could not load the workspace from Azure.")
        records = None

    if records is not None:
        show_passed = st.checkbox(
            "Show passed grants",
            value=False,
        )
        if not show_passed:
            records = [
                record
                for record in records
                if record.get("status") != "Pass"
            ]
        if not records:
            st.info(
                "No active shared grants. Share one from Search "
                "or enable Show passed grants."
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
                                st.rerun()
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
                    st.markdown("#### Comments")

                    for comment in record.get("comments", []):
                        st.text(
                            f"{comment['author']} · "
                            f"{comment['created_at']}"
                        )
                        st.text(comment["text"])
                        st.divider()

                    with st.form(f"comment-{version_key}"):
                        author = st.text_input(
                            "Your name",
                            placeholder="Demo identity",
                        )
                        comment_text = st.text_area("Comment")
                        post_comment = st.form_submit_button(
                            "Post comment"
                        )

                    if post_comment:
                        if not author.strip() or not comment_text.strip():
                            st.warning(
                                "Enter your name and a comment."
                            )
                        else:
                            try:
                                saved = add_comment(
                                    record, author, comment_text
                                )
                                if saved:
                                    st.rerun()
                                else:
                                    st.warning(
                                        "This grant changed. Copy your "
                                        "comment, refresh the workspace, "
                                        "and try again."
                                    )
                            except (AzureError, KeyError, ValueError):
                                st.error(
                                    "Could not save your comment. "
                                    "Copy it before refreshing."
                                )
                    if st.button(
                        "View full details",
                        key=f"workspace-details-{grant['id']}",
                    ):
                        navigate("Grant Details", grant)
