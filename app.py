import hashlib
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import streamlit as st
from azure.core.exceptions import (
    AzureError,
    ResourceExistsError,
    ResourceNotFoundError,
)
from azure.storage.blob import ContentSettings

from matching import match_grant
from storage import (
    get_container,
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
    """,
    unsafe_allow_html=True,
)


# DATA
data_directory = Path(__file__).parent / "data"
live_path = data_directory / "grants-live.json"
data_path = (
    live_path if live_path.exists()
    else data_directory / "grants.json"
)

with data_path.open(encoding="utf-8") as file:
    grants = json.load(file)

grants_by_id = {str(grant["id"]): grant for grant in grants}

agencies = {}
for profile_path in sorted(
    (data_directory / "agencies").glob("*.json")
):
    with profile_path.open(encoding="utf-8") as file:
        profile = json.load(file)
        agencies[profile["id"]] = profile

if not agencies:
    st.error("No agency profiles found in data/agencies.")
    st.stop()

st.session_state.setdefault("page", "Search")
st.session_state.setdefault("selected_grant", None)
st.session_state.setdefault("search_text", "")


# GENERAL HELPERS
def navigate(page, grant=None):
    st.session_state.page = page
    if grant is not None:
        st.session_state.selected_grant = grant
    st.rerun()


def remember_search():
    st.session_state.search_text = st.session_state.search_input


def identity_key(name):
    return " ".join(str(name or "").split()).casefold()


def stable_key(value):
    return hashlib.sha256(
        str(value).encode("utf-8")
    ).hexdigest()


def parsed_timestamp(value):
    if not value:
        return None
    try:
        result = datetime.fromisoformat(
            str(value).replace("Z", "+00:00")
        )
        if result.tzinfo is None:
            result = result.replace(tzinfo=timezone.utc)
        return result
    except (ValueError, TypeError):
        return None


def display_timestamp(value):
    parsed = parsed_timestamp(value)
    if parsed is None:
        return value or "Not stated"
    return parsed.astimezone(
        ZoneInfo("America/New_York")
    ).strftime("%b %d, %Y · %I:%M %p %Z")


def funding_label(grant):
    def number(value):
        try:
            result = float(value)
            if math.isfinite(result) and result >= 0:
                return result
        except (ValueError, TypeError):
            pass
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

    today = datetime.now(
        ZoneInfo("America/New_York")
    ).date()
    days_left = (closing_date - today).days

    if days_left < 0:
        timing = "Past closing date"
    elif days_left == 0:
        timing = "Closes today"
    else:
        timing = f"{days_left} days left"

    return f"{closing_date:%b %d, %Y} · {timing}"


def show_source(grant):
    url = grant.get("source_url")
    if url:
        st.link_button(
            "Open original grant announcement ↗", url
        )
        st.caption(url)
    else:
        st.caption("Original announcement link not available.")


def show_requirements(value):
    if isinstance(value, list):
        if not value:
            st.write("Not stated")
        for item in value:
            st.write(f"• {item}")
    else:
        st.write(value or "Not stated")


def show_data_footer():
    st.divider()
    if data_path != live_path:
        st.warning("Data source: fictional demo grants")
        return

    st.caption("Data source: Grants.gov snapshot")
    fetched_at = (
        grants[0].get("fetched_at") if grants else None
    )
    st.caption(
        f"Fetched: {display_timestamp(fetched_at)}"
        " · Refresh is currently manual"
    )


def load_workspace(workspace_id):
    try:
        return list_shared_grants(workspace_id=workspace_id)
    except (AzureError, KeyError, ValueError):
        st.error("Could not load the workspace from Azure.")
        return None


# FAVORITES
# One blob per agency, demo identity, and grant.
# This is identity-based demo organization, NOT authentication.
def favorite_prefix(workspace_id, user_name):
    user_id = stable_key(identity_key(user_name))
    return f"favorites/{workspace_id}/{user_id}/"


def save_favorite(grant, workspace_id, user_name):
    blob_name = (
        favorite_prefix(workspace_id, user_name)
        + stable_key(grant["id"])
        + ".json"
    )
    record = {
        "grant": grant,
        "saved_by": user_name,
        "saved_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        get_container().get_blob_client(blob_name).upload_blob(
            json.dumps(
                record, ensure_ascii=False
            ).encode("utf-8"),
            overwrite=False,
            content_settings=ContentSettings(
                content_type="application/json"
            ),
        )
        return True
    except ResourceExistsError:
        return False


def list_favorites(workspace_id, user_name):
    container = get_container()
    records = []

    for item in container.list_blobs(
        name_starts_with=favorite_prefix(
            workspace_id, user_name
        )
    ):
        content = container.get_blob_client(
            item.name
        ).download_blob().readall()
        record = json.loads(content)
        record["_blob_name"] = item.name
        records.append(record)

    return sorted(
        records,
        key=lambda record: record.get("saved_at", ""),
        reverse=True,
    )


def favorite_button(grant, key, workspace_id, user_name):
    if st.button("☆ Favorite", key=key):
        if not user_name:
            st.warning("Enter your demo name in the sidebar first.")
            return
        try:
            created = save_favorite(
                grant, workspace_id, user_name
            )
            if created:
                st.success("Saved to your dashboard favorites.")
            else:
                st.info("Already in your favorites.")
        except (AzureError, KeyError, ValueError):
            st.error("Could not save this favorite.")


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


def open_details_button(grant, key):
    if st.button(
        "View details →",
        key=key,
        type="primary",
        use_container_width=True,
    ):
        navigate("Grant Details", grant)


def show_review_editor(record, workspace_id, user_name):
    grant = record["grant"]
    statuses = [
        "Not Reviewed", "Under Review", "Pursue", "Pass"
    ]

    with st.expander(grant["title"]):
        st.write(
            "**Funding opportunity number:** "
            + str(grant.get("opportunity_number") or "Not stated")
        )
        st.write(f"**Deadline:** {deadline_label(grant)}")

        current_status = record.get("status") or "Not Reviewed"
        if current_status not in statuses:
            current_status = "Not Reviewed"

        version_key = (
            f"{workspace_id}-{grant['id']}-{record['_etag']}"
        )

        with st.form(f"review-{version_key}"):
            selected_status = st.selectbox(
                "Review status",
                statuses,
                index=statuses.index(current_status),
            )
            reviewer = st.text_input(
                "Assigned reviewer",
                value=record.get("assigned_reviewer") or "",
                placeholder="Use their exact demo name",
            )
            submitted = st.form_submit_button("Save review")

        if submitted:
            try:
                saved = update_review_status(
                    record, selected_status, reviewer
                )
                if saved:
                    st.rerun()
                else:
                    st.warning(
                        "This grant changed. Refresh the workspace "
                        "before trying again."
                    )
            except (AzureError, KeyError, ValueError):
                st.error("Could not save the review.")

        st.markdown("#### Comments")
        comments = record.get("comments") or []

        if not comments:
            st.caption("No comments yet.")

        for comment in comments:
            st.text(
                f"{comment.get('author') or 'Unknown'} · "
                f"{display_timestamp(comment.get('created_at'))}"
            )
            st.text(comment.get("text") or "")
            st.divider()

        with st.form(f"comment-{version_key}"):
            st.caption(
                f"Posting as: {user_name or 'No demo name selected'}"
            )
            comment_text = st.text_area("Comment")
            submitted_comment = st.form_submit_button(
                "Post comment",
                disabled=not bool(user_name),
            )

        if submitted_comment:
            if not comment_text.strip():
                st.warning("Enter a comment.")
            else:
                try:
                    saved = add_comment(
                        record, user_name, comment_text
                    )
                    if saved:
                        st.rerun()
                    else:
                        st.warning(
                            "This grant changed. Copy your comment, "
                            "refresh, and try again."
                        )
                except (AzureError, KeyError, ValueError):
                    st.error(
                        "Could not save. Copy your comment "
                        "before refreshing."
                    )

        open_details_button(
            grant, f"workspace-details-{grant['id']}"
        )


# LEFT SIDEBAR
with st.sidebar:
    st.markdown(
        '<div class="brand-line"></div>',
        unsafe_allow_html=True,
    )
    st.markdown("### Federal Funds Matchmaker")
    st.caption("Federal grant discovery & agency collaboration")
    st.divider()

    agency_id = st.selectbox(
        "Agency",
        options=list(agencies),
        format_func=lambda value: agencies[value]["short_name"],
        key="selected_agency",
    )
    agency = agencies[agency_id]

    user_name = st.text_input(
        "Demo user name",
        key="demo_user_name",
        placeholder="Enter your name",
    ).strip()
    st.caption(
        "Demo identity only—not a secure login. "
        "Reviewer assignments use this name."
    )

    st.divider()

    pages = ["Search", "Workspace", "Dashboard"]

    for index, page in enumerate(pages):
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

        if index < len(pages) - 1:
            st.divider()

    st.divider()
    st.caption("Prototype · Login not connected")


# SEARCH
if st.session_state.page == "Search":
    st.header("Find funding opportunities")
    st.write("Explore grants and share opportunities with your agency.")
    st.caption(f"Selected agency: {agency['name']}")

    st.session_state.setdefault(
        "search_input", st.session_state.search_text
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
        grant for grant in grants
        if query in (
            f"{grant.get('title') or ''} "
            f"{grant.get('description') or ''}"
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
        "Include unknown or unrecognized deadlines", value=True
    )
    hide_past = st.checkbox(
        "Hide grants past their closing date", value=True
    )

    today = datetime.now(ZoneInfo("America/New_York")).date()
    maximum_days = {
        "Next 30 days": 30,
        "Next 60 days": 60,
        "Next 90 days": 90,
    }.get(deadline_window)

    filtered = []
    for grant in results:
        closing_date = deadline_date(grant)
        if closing_date is None:
            if include_unknown:
                filtered.append(grant)
            continue

        days_left = (closing_date - today).days
        if hide_past and days_left < 0:
            continue
        if maximum_days is not None:
            if not 0 <= days_left <= maximum_days:
                continue
        filtered.append(grant)

    results = filtered

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
            grant for grant in results
            if match_grant(grant, agency)["eligibility"]["status"]
            == eligibility_filter
        ]

    st.subheader("Grant opportunities")
    st.caption(f"{len(results)} results")

    if not results:
        st.info("No matches. Adjust your keywords or filters.")

    for grant in results:
        match = match_grant(grant, agency)

        with st.container(border=True):
            main, relevance = st.columns([4, 1])

            with main:
                st.subheader(grant["title"])
                st.caption(grant.get("funder") or "Funder not stated")
                st.write(
                    "**Funding opportunity number:** "
                    + str(
                        grant.get("opportunity_number") or "Not stated"
                    )
                )
                if grant.get("source_url"):
                    st.link_button(
                        "Open original posting ↗", grant["source_url"]
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
                "**Eligibility:** "
                + (grant.get("eligibility_text") or "Not stated")
            )
            st.write(grant.get("description") or "Not stated")
            st.write("**Why this matches**")
            st.write(match["reason"])
            st.write(
                "**Applicant-type check:** "
                + match["eligibility"]["status"]
            )
            st.caption(match["eligibility"]["reason"])

            favorite_col, share_col, detail_col = st.columns(3)
            with favorite_col:
                favorite_button(
                    grant,
                    f"favorite-search-{grant['id']}",
                    agency_id,
                    user_name,
                )
            with share_col:
                share_button(
                    grant,
                    f"share-search-{grant['id']}",
                    agency_id,
                )
            with detail_col:
                open_details_button(
                    grant, f"details-search-{grant['id']}"
                )

    show_data_footer()


# GRANT DETAILS
elif st.session_state.page == "Grant Details":
    grant = st.session_state.selected_grant

    if grant is None:
        st.info("Open a grant from Search, Workspace, or Dashboard.")
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
                favorite_button(
                    grant, "favorite-detail", agency_id, user_name
                )
                share_button(grant, "share-detail", agency_id)

        with content:
            with st.container(border=True):
                st.subheader("Overview")
                st.write(grant.get("description") or "Not stated")

                if grant.get("detail_status") in {
                    "stale", "unavailable"
                }:
                    st.warning(
                        "Full details were not refreshed successfully. "
                        "Check the original announcement."
                    )

                st.subheader("Application requirements")
                show_requirements(grant.get("requirements"))

                st.subheader("Why this matches")
                match = match_grant(grant, agency)
                st.write(match["reason"])
                for evidence in match["priority_matches"]:
                    st.write(f"**{evidence['priority_title']}**")
                    st.write(
                        "Matched terms: "
                        + ", ".join(evidence["matched_keywords"])
                    )

                st.subheader("Applicant-type check")
                st.write(match["eligibility"]["status"])
                st.caption(match["eligibility"]["reason"])


# WORKSPACE
elif st.session_state.page == "Workspace":
    st.header("Agency workspace")
    st.caption(agency["name"])

    st.markdown("#### Agency priorities")
    for priority in agency["priorities"]:
        if priority.get("enabled", True):
            st.markdown(
                f"- **{priority['title']}** — "
                f"{priority['description']}"
            )

    st.divider()
    st.subheader("Shared grants")
    st.button("Refresh workspace")
    records = load_workspace(agency_id)

    if records is not None:
        show_passed = st.checkbox(
            "Show passed grants",
            value=False,
            key=f"show-passed-{agency_id}",
        )
        if not show_passed:
            records = [
                record for record in records
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
                        "Opportunity number": (
                            record["grant"].get("opportunity_number")
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
            for record in records:
                show_review_editor(
                    record, agency_id, user_name
                )


# DASHBOARD — FOURTH TAB
elif st.session_state.page == "Dashboard":
    st.header("My dashboard")
    st.caption(agency["name"])

    if not user_name:
        st.info(
            "Enter a demo user name in the sidebar to view "
            "your assignments and favorites."
        )
    else:
        st.write(f"Welcome, **{user_name}**.")
        st.caption(
            "Assignments match your demo name. "
            "This view is not protected by real authentication."
        )
        st.button("Refresh dashboard")

        records = load_workspace(agency_id)

        try:
            favorites = list_favorites(agency_id, user_name)
        except (AzureError, KeyError, ValueError):
            st.error("Could not load favorites from Azure.")
            favorites = None

        if records is not None:
            my_records = [
                record for record in records
                if identity_key(record.get("assigned_reviewer"))
                == identity_key(user_name)
            ]
            my_todos = [
                record for record in my_records
                if record.get("status") != "Pass"
            ]

            # Prioritize known deadlines, earliest first.
            my_todos.sort(
                key=lambda record: (
                    deadline_date(record["grant"]) is None,
                    deadline_date(record["grant"])
                    or datetime.max.date(),
                )
            )

            cutoff = datetime.now(timezone.utc) - timedelta(days=7)
            new_records = [
                record for record in records
                if parsed_timestamp(record.get("shared_at"))
                and parsed_timestamp(record["shared_at"]) >= cutoff
            ]
            new_records.sort(
                key=lambda record: record.get("shared_at", ""),
                reverse=True,
            )

            received_comments = []
            for record in my_records:
                for comment in record.get("comments") or []:
                    if (
                        identity_key(comment.get("author"))
                        != identity_key(user_name)
                    ):
                        received_comments.append({
                            "grant": record["grant"],
                            "comment": comment,
                        })
            received_comments.sort(
                key=lambda item: (
                    item["comment"].get("created_at", "")
                ),
                reverse=True,
            )

            metrics = st.columns(4)
            metrics[0].metric("Assigned reviews", len(my_todos))
            metrics[1].metric("Shared in last 7 days", len(new_records))
            metrics[2].metric(
                "Favorites",
                len(favorites) if favorites is not None else "—",
            )
            metrics[3].metric(
                "Comments from others", len(received_comments)
            )

            st.divider()
            st.subheader("My to-dos")
            st.caption(
                "Assigned grants you have not marked Pass. "
                "These are review assignments, not a separate task list."
            )

            if not my_todos:
                st.info(
                    "No active assignments. Assign a shared grant "
                    "to your demo name in Workspace."
                )

            for record in my_todos:
                grant = record["grant"]
                with st.container(border=True):
                    st.markdown(f"**{grant['title']}**")
                    st.write(
                        f"Status: {record.get('status') or 'Not Reviewed'}"
                    )
                    st.write(f"Deadline: {deadline_label(grant)}")

                    detail_col, workspace_col = st.columns(2)
                    with detail_col:
                        open_details_button(
                            grant, f"todo-detail-{grant['id']}"
                        )
                    with workspace_col:
                        if st.button(
                            "Manage in workspace",
                            key=f"todo-manage-{grant['id']}",
                        ):
                            navigate("Workspace")

            st.divider()
            st.subheader("Newly shared to your agency")
            st.caption(
                "Added to Workspace in the last 7 days. "
                "This is not the grant's original publication date."
            )

            if not new_records:
                st.info("No grants shared in the last 7 days.")

            for record in new_records:
                grant = record["grant"]
                with st.container(border=True):
                    st.markdown(f"**{grant['title']}**")
                    st.caption(
                        "Shared: "
                        + display_timestamp(record.get("shared_at"))
                    )
                    st.write(
                        f"Status: {record.get('status') or 'Not Reviewed'}"
                    )
                    open_details_button(
                        grant, f"new-detail-{grant['id']}"
                    )

            st.divider()
            st.subheader("Comments on grants assigned to me")
            st.caption(
                "Comments from others on your current assignments. "
                "Read/unread tracking is not implemented."
            )

            if not received_comments:
                st.info("No comments from others on your assignments.")

            for index, item in enumerate(received_comments):
                grant = item["grant"]
                comment = item["comment"]
                with st.container(border=True):
                    st.markdown(f"**{grant['title']}**")
                    st.text(
                        f"{comment.get('author') or 'Unknown'} · "
                        f"{display_timestamp(comment.get('created_at'))}"
                    )
                    st.text(comment.get("text") or "")
                    if st.button(
                        "Open workspace discussion",
                        key=f"comment-open-{index}-{grant['id']}",
                    ):
                        navigate("Workspace")

        st.divider()
        st.subheader("My favorites")
        st.caption(
            "Favorites for this agency and demo identity, saved in Azure."
        )

        if favorites is not None:
            if not favorites:
                st.info(
                    "No favorites yet. Use ☆ Favorite on a grant."
                )

            for favorite in favorites:
                saved_grant = favorite["grant"]
                grant = grants_by_id.get(
                    str(saved_grant["id"]), saved_grant
                )

                with st.container(border=True):
                    st.markdown(f"**{grant['title']}**")
                    st.write(funding_label(grant))
                    st.write(deadline_label(grant))
                    st.caption(
                        "Favorited: "
                        + display_timestamp(favorite.get("saved_at"))
                    )

                    detail_col, remove_col = st.columns(2)
                    with detail_col:
                        open_details_button(
                            grant,
                            f"favorite-detail-{grant['id']}",
                        )

                    with remove_col:
                        if st.button(
                            "Remove favorite",
                            key=f"favorite-remove-{grant['id']}",
                        ):
                            try:
                                get_container().get_blob_client(
                                    favorite["_blob_name"]
                                ).delete_blob()
                                st.rerun()
                            except ResourceNotFoundError:
                                st.rerun()
                            except AzureError:
                                st.error("Could not remove favorite.")
