# Solve-For-Good

# Federal Funds Matchmaker

Federal Funds Matchmaker is a working prototype that helps North Carolina state agency staff discover federal funding opportunities, assess alignment with agency priorities, and coordinate grant reviews.

Built for the UNC Solve-a-thon, the prototype uses the North Carolina Department of Environmental Quality (NC DEQ) as its initial agency example.

## Live Prototype

**Application:** https://ffm-team11-gbfngghph9fvgda9.eastus2-01.azurewebsites.net

The application currently uses demo identities rather than authenticated accounts. Enter a demo user name in the sidebar to explore personal favorites and reviewer-specific dashboard features.

Use public grant information and fictional discussion content when testing.

## Problem

Agency staff must identify relevant opportunities across funding programs, evaluate eligibility and deadlines, and coordinate with colleagues. Relevant opportunities can be difficult to find in time, and review progress can become scattered across individual documents and messages.

Federal Funds Matchmaker brings discovery and collaboration into one agency workspace.

## Prototype Features

### Grant Discovery

- Browse a locally stored snapshot of real Grants.gov opportunities.
- Search by keywords, title, description, funding organization, or opportunity number.
- Filter by deadline and award amount range.
- Select multiple applicant-type assessment categories.
- Review keyword-based alignment with agency priorities.
- Open official grant announcements using direct source links.
- View funding opportunity numbers, award amounts, and deadlines.
- Display unavailable information as “Not stated.”

### Agency Collaboration

- Share opportunities to an agency workspace.
- Assign a reviewer.
- Set review status:
  - Not Reviewed
  - Under Review
  - Pursue
  - Pass
- Hide passed opportunities from the default workspace view.
- Add discussion comments and replies.
- Expand a discussion to view its replies.
- Persist shared records in Azure Blob Storage.

“Pass” is a review decision, not a test result. Passed opportunities remain stored and can be displayed again.

### Personal Dashboard

- View grants assigned to the current demo identity.
- View personal favorites.
- View recently shared opportunities.
- View comments and replies from others on assigned grants.

Personal views use the entered demo name. They do not provide authenticated privacy or access control.

## Suggested Demonstration

1. Open the live application.
2. Enter a demo user name in the sidebar.
3. Select NC DEQ and search for a relevant topic.
4. Adjust deadline or award filters.
5. Open a grant’s details.
6. Review its priority alignment, eligibility information, and official posting.
7. Share the grant to the workspace.
8. Assign a reviewer and save a review status.
9. Add a comment and reply.
10. Refresh the page to verify that shared progress persists.
11. Open another browser session with a different demo name to demonstrate collaboration.
12. Open the Dashboard to review assigned work and favorites.

A second-session demonstration shows shared persistence. It does not establish production authentication or authorization.

## Technology Stack

| Component | Technology |
|---|---|
| Application interface | Streamlit |
| Application language | Python |
| Grant source | Grants.gov public API |
| Shared record storage | Azure Blob Storage |
| Hosting | Azure App Service on Linux |
| Initial agency configuration | JSON profile for NC DEQ |
| Matching | Rule-based keyword matching |

The current matching system does not use a language model.

## Architecture

The application separates grant discovery data from collaborative review records:

1. `fetch_grants.py` requests opportunities from Grants.gov and writes a local JSON snapshot.
2. `app.py` reads the snapshot and agency profile.
3. `matching.py` evaluates keyword alignment and applicant-type information.
4. `storage.py` reads and writes shared review records in Azure Blob Storage.
5. Azure App Service hosts the Streamlit application.

Searching and filtering use the existing snapshot rather than making a new Grants.gov request for every interaction.

## Repository Structure

```text
.
├── app.py
├── storage.py
├── matching.py
├── fetch_grants.py
├── requirements.txt
├── README.md
├── .gitignore
├── .streamlit/
│   └── config.toml
└── data/
    ├── agencies/
    │   └── nc-deq.json
    ├── grants.json
    └── grants-live.json
```

| File | Purpose |
|---|---|
| `app.py` | Search, details, workspace, dashboard, and interface behavior |
| `storage.py` | Azure Blob Storage operations for collaboration |
| `matching.py` | Priority matching and applicant-type assessment |
| `fetch_grants.py` | Grants.gov retrieval and snapshot generation |
| `requirements.txt` | Python dependencies |
| `.streamlit/config.toml` | Interface theme configuration |
| `data/agencies/nc-deq.json` | Agency identity, priorities, and matching configuration |
| `data/grants.json` | Fictional demonstration records |
| `data/grants-live.json` | Retrieved Grants.gov snapshot |

## Run Locally

### Prerequisites

- Python 3.12
- An Azure Storage account
- A private Blob Storage container named `ffm-data`
- A storage connection string with the permissions needed by the application

### Install Dependencies

From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

On Windows, activate the environment with:

```powershell
.venv\Scripts\Activate.ps1
```

### Configure Storage

Set this environment variable in the environment running the application:

```text
AZURE_STORAGE_CONNECTION_STRING
```

Its value must be the complete connection string for the intended Azure Storage account.

Do not commit connection strings, account keys, or other credentials to the repository.

### Start the Application

```bash
python -m streamlit run app.py
```

For GitHub Codespaces:

```bash
python -m streamlit run app.py \
  --server.address=0.0.0.0 \
  --server.port=8501
```

Open the forwarded port shown by Codespaces.

## Refresh Grant Data

Run the retrieval script from the repository root:

```bash
python fetch_grants.py
```

The default searches cover:

- Water
- PFAS
- Recycling
- Flood resilience
- Environmental infrastructure
- A supplementary state-government applicant search

To use a single topic:

```bash
python fetch_grants.py --keyword water
```

To change the maximum results requested per search:

```bash
python fetch_grants.py --rows 20
```

The supported `--rows` range is 1–50.

### Retrieval Behavior

- Requests posted opportunities from Grants.gov.
- Deduplicates results by opportunity ID.
- Retrieves additional opportunity details.
- Retries failed requests with delays.
- Retains previous details where available when an individual detail request fails.
- Preserves the existing snapshot if a search fails or all detail requests fail.
- Replaces the snapshot only after retrieval completes successfully.

The snapshot is a limited search sample, not a complete index of federal funding opportunities.

Refreshing is currently manual. Updating a snapshot in a local checkout does not automatically update the deployed application.

## Matching and Eligibility

### Agency Priority Alignment

The prototype compares grant text with configured agency-priority keywords and displays the matching evidence.

This is a transparent relevance aid. It does not measure award probability or confirm that an agency should apply.

### Applicant-Type Assessment

The prototype distinguishes between:

- An applicant-type match
- An applicant-type mismatch
- Information that needs verification

Broad categories such as “Others,” unrestricted eligibility, missing details, and program-specific conditions can require manual review.

An applicant-type match does not establish full eligibility. Staff must verify geographic restrictions, program conditions, partnerships, matching funds, and other requirements against the official announcement.

## Storage and Persistence

Shared grant records are stored as JSON blobs under workspace-specific paths.

Each shared record can contain:

- A copy of the grant information
- Review status
- Assigned reviewer
- Sharing and update timestamps
- Comments and replies

Stable grant identifiers prevent duplicate sharing of the same opportunity within a workspace.

Conditional writes using Azure Blob ETags help detect conflicting edits. If another user updates a record first, refresh the workspace before retrying.

Favorites are also stored in Azure, using the selected agency and normalized demo name.

Workspace separation and demo-name-based favorites are organizational conventions in this prototype, not enforced security boundaries.

## Azure Deployment

The prototype is hosted on Azure App Service using:

- Linux
- Python 3.12
- A Basic B1 App Service plan
- Azure Blob Storage for persistent application records

### App Settings

Configure these under the web app’s environment variables:

| Name | Value |
|---|---|
| `AZURE_STORAGE_CONNECTION_STRING` | Storage connection string |
| `SCM_DO_BUILD_DURING_DEPLOYMENT` | `true` |
| `ENABLE_ORYX_BUILD` | `true` |

### Startup Command

```bash
python -m streamlit run app.py --server.port=8000 --server.address=0.0.0.0
```

### Deployment Package

Place `app.py` and `requirements.txt` at the root of the deployment ZIP, together with the supporting Python files, agency profiles, grant snapshot, and Streamlit configuration.

Exclude credentials, local virtual environments, and Git metadata.

The current deployment process uses a manually uploaded ZIP. Repository changes require a new deployment to appear in the hosted application.

### Verify a Deployment

Check both deployment logs and application startup logs. A successful upload alone does not establish that the application started correctly.

Then verify:

- Search results load.
- Official posting links open the expected opportunities.
- Sharing to the workspace succeeds.
- Review changes and discussions persist after refresh.
- Another browser session can retrieve shared updates.

## Testing

The project’s interface testing checklist covers:

1. Opening details and returning to search
2. Personal bookmarks
3. Sharing to the agency workspace
4. Reviewer assignment
5. Comments and review statuses
6. Persistence after refresh
7. Shared updates across sessions
8. Separation of personal and shared lists
9. Display of missing information

Record actual outcomes as Pass, Fail, Blocked, or Not Tested. Do not mark an unimplemented or untested feature as passed.

For failures, include reproduction steps, expected behavior, actual behavior, browser, and supporting evidence.

## Known Limitations

- Demo identities are not real user accounts.
- Authentication, role-based access, and agency membership enforcement are not implemented.
- Favorites do not have authenticated privacy guarantees.
- Grant data refresh is manual.
- Results reflect selected searches rather than all available federal opportunities.
- Source records may omit award amounts, deadlines, requirements, or detailed eligibility conditions.
- Saved workspace records contain a grant snapshot and may differ from later source updates.
- Matching is keyword-based and can miss relevant opportunities or include weak matches.
- Comments shown on the dashboard are not a complete notification system and have no unread tracking.
- Automatic application-effort estimates and requirement extraction are not implemented.
- Sensitive-information filtering is not implemented.

## Recommended Next Steps for State Developers

### 1. Establish Identity and Access Control

Integrate an approved identity provider, such as Microsoft Entra ID. Use verified user identifiers and enforce agency membership and permissions on every storage operation.

Replace demo-name-based identity before using the application with sensitive information.

### 2. Automate Data Refresh

Move grant retrieval into a scheduled background process. Store a centrally accessible snapshot with refresh timestamps, failure monitoring, and source-change tracking.

Keep interactive search independent of slow source retrieval.

### 3. Improve Data Quality

Expand applicant-type normalization, preserve detailed eligibility conditions, validate deadlines and award amounts, and distinguish missing information from confirmed absence.

Track source provenance for extracted requirements.

### 4. Extend Agency Support

Add agency profiles with stable IDs, applicant types, documented priorities, and reviewed keywords.

Confirm that agency selection, matching, and workspace isolation work correctly for each additional profile.

### 5. Strengthen Collaboration

Add audit history, notifications, clearer conflict handling, and controls for reviewer assignment and discussion moderation.

Evaluate whether a database would better support querying, permissions, and activity history as usage grows.

### 6. Validate with Agency Staff

Observe staff completing realistic discovery and review tasks. Evaluate relevance, clarity, accessibility, response time, and the usefulness of collaboration features.

Use those findings to guide further development.

## Handoff Notes

A developer continuing this project should begin with:

1. Running the application with the existing snapshot.
2. Confirming Azure storage configuration.
3. Reviewing `matching.py` alongside the agency profile.
4. Completing the interface testing checklist.
5. Resolving authentication and access-control requirements before broader use.

The prototype demonstrates a grant discovery and collaborative review workflow. Production use requires additional security, operational, and user validation.
