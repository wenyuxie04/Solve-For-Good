# Federal Funds Matchmaker — Interface Design

## Overview

The Federal Funds Matchmaker is designed to help North Carolina government agencies find, evaluate, and manage federal grant opportunities more efficiently.

Based on our client discovery session with OSBM, we learned that grant discovery is only one part of the problem. Agency staff also have limited time to review opportunities, may struggle to determine whether a grant fits their priorities, and often work with different levels of staffing and resources.

Our interface prioritizes simplicity, transparency, and collaboration. The goal is to allow agency staff to quickly identify promising grants, understand why they match, and coordinate next steps without requiring extensive technical training.

The application will have three main screens:

1. Search & Results
2. Grant Details
3. Agency Workspace

These screens should share a consistent design, with simple navigation, clear information, and minimal unnecessary steps.

---

## Screen 1: Search & Results

### Purpose

This is the main dashboard where users can discover and compare federal grant opportunities.

The interface should allow users to search based on their agency's strategic priorities or a specific project they are working on.

### Main Components

**Search and Filters**
- Agency selector: Users select their North Carolina agency to receive recommendations based on its strategic goals.
- Project input: Users can describe a specific project to find relevant grant opportunities.
- Keyword search: Users search for grants using words or phrases.
- Deadline filter: A slider allows users to filter grants based on how many days remain until applications close.
- Sort options: Users can organize grants by best match, funding amount, or application deadline.
- Eligibility filter: Users can filter opportunities based on applicant eligibility, such as state or local government.

**Grant Cards**

Each grant card should display:

- Grant title
- Federal funding agency
- Match score or priority indicator
- Funding amount
- Application deadline and days remaining
- Applicant eligibility
- Key application requirements
- Short explanation of why the grant matches the selected agency or project

Grant cards should prioritize the information users need to determine whether an opportunity is worth reviewing.

If funding, deadlines, eligibility, or requirements are unavailable, the interface should display "Not stated" rather than guessing or leaving the information blank.

### Buttons and Interactions

| Element | Expected Behavior |
|---|---|
| Agency selector | Updates recommendations based on the selected agency's strategic priorities. |
| Project input | Allows users to describe a project and search for grants related to that project. |
| Keyword search | Filters grant results based on the user's search terms. |
| Deadline slider | Filters results according to the number of days remaining before the grant closes. |
| Sort by best match | Orders grants according to their relevance scores. |
| Sort by funding | Orders grants by funding amount, highest to lowest. |
| Sort by deadline | Orders grants by the nearest upcoming application deadline. |
| Eligibility filter | Filters grants based on applicant eligibility, with unknown eligibility clearly identified. |
| View Details | Opens the full Grant Details screen for the selected opportunity. |
| Save | Adds the grant to the current user's personal bookmarks. |
| Share | Adds the grant to the selected agency's shared workspace. |

### Design Considerations

- Use a clean, card-based dashboard with readable text and minimal clutter.
- Make grant deadlines and match scores easy to identify.
- Display essential information directly on grant cards to reduce unnecessary clicking.
- Use simple labels rather than technical terminology.
- Make sure users understand why an opportunity is being recommended.
- Keep missing or unverified information clearly labeled.

---

## Screen 2: Grant Details

### Purpose

This screen allows users to examine a specific grant opportunity before deciding whether to save, share, or pursue it.

While the main dashboard provides a quick overview, this screen includes more detailed information.

### Main Components

**Grant Overview**
- Grant title
- Federal funding agency
- Funding amount
- Application deadline
- Eligibility requirements
- Grant status
- Link to the official federal grant announcement

**Description**
- Full grant description or a concise summary based on the official source.
- Intended purpose of the funding opportunity.
- Relevant program areas or priorities.

**Application Requirements**
- Required documents and application materials, when stated in the source.
- Cost-sharing or matching-fund requirements, when available.
- Important eligibility restrictions.
- Additional conditions that agency staff should verify before applying.

**Fit Explanation**
- Match score and explanation.
- Relevant agency strategic goals or project priorities.
- Reasons the opportunity may be a good fit.
- Potential concerns, including limited time, unclear eligibility, or application complexity.

### Buttons and Interactions

| Element | Expected Behavior |
|---|---|
| Back to Results | Returns the user to the search dashboard without losing their previous search and filters. |
| Official Grant Source | Opens the original federal grant announcement so users can verify information. |
| Save Personally | Bookmarks the grant for the current user without automatically sharing it with other agency staff. |
| Share to Agency Workspace | Adds the grant to the shared agency workspace for collaborative review. |

### Design Considerations

- Clearly separate verified grant information from generated summaries or matching explanations.
- Use section headings so users can easily locate eligibility, funding, and application requirements.
- Avoid overly long blocks of text.
- Keep the official source easily accessible.
- Personal saving and agency sharing must remain separate actions.

---

## Screen 3: Agency Workspace

### Purpose

The Agency Workspace allows multiple staff members within an agency to collaborate on grant opportunities.

During client discovery, we learned that grant discovery is not always handled by one dedicated employee. Some agencies have grant specialists, while others divide responsibilities among several staff members.

A shared workspace can reduce duplicated work and make it easier to track which opportunities are being considered.

### Main Components

**Shared Grants List**

Each shared grant should display:

- Grant title
- Funding amount
- Application deadline
- Match score or priority
- Assigned reviewer
- Current review status
- Most recent update

**Review Status**

Suggested status options:

- Not Reviewed
- Under Review
- Pursue
- Pass

**Collaboration Features**

- Assign a staff member to review a grant.
- Update the review status.
- Add comments or notes.
- Review previous comments and progress.
- View the grant's full details.

### Buttons and Interactions

| Element | Expected Behavior |
|---|---|
| Assign Reviewer | Allows a user to select the staff member responsible for reviewing a shared grant. |
| Change Status | Updates the grant's review status for everyone in the agency workspace. |
| Add Comment | Saves a comment associated with the shared grant and displays it to agency collaborators. |
| View Grant | Opens the full details of the selected grant. |
| Refresh | Displays the latest saved reviewer assignments, statuses, and comments without deleting previous progress. |

### Design Considerations

- The workspace should display only grants shared with that agency.
- Updates should remain saved after refreshing or reopening the application.
- Other authorized members of the agency should see shared updates.
- Personal bookmarks should not automatically appear in the shared workspace.
- Status labels should be straightforward and easy to understand.

---

## Features to Prioritize

### Must Have for Initial Prototype

- Agency selection
- Keyword search
- Deadline filtering
- Grant cards with relevant funding and application information
- Match explanations
- Grant details
- Official source links
- Personal bookmarking
- Sharing to agency workspace
- Reviewer assignment
- Review status updates
- Comments
- Persistent shared progress

### Can Be Postponed

- Advanced personalization and saved search preferences
- Searching additional funding platforms beyond the initial data source
- Automated recurring-grant reminders
- Email or notification alerts
- AI-generated application effort estimates
- Automated reviewer recommendations
- Advanced analytics and reporting
- Customizable dashboard layouts

These can be considered for later versions after the core workflow is functional.

---

## Main User Flow

1. The user selects an agency or enters a specific project.
2. The system displays ranked federal grant opportunities.
3. The user adjusts filters to narrow the results.
4. The user reviews funding, deadlines, eligibility, requirements, and match explanations on the grant cards.
5. The user opens a promising grant to review more details.
6. The user saves the grant personally or shares it with the agency workspace.
7. Agency staff assign reviewers, update statuses, and leave comments.
8. Shared decisions and progress remain accessible to other authorized agency staff.

## Wireframes

The three planned wireframes are:

- Search & Results — `docs/sketches/01-search-results.svg`
- Grant Details — `docs/sketches/02-grant-details.svg`
- Agency Workspace — `docs/sketches/03-agency-workspace.svg`

These sketches illustrate the intended layout and interactions. The final implementation may be adjusted based on technical constraints and usability testing.

## Design Principle

The Federal Funds Matchmaker should help agency staff make better-informed decisions without replacing their judgment.

A successful interface should make it easier to answer five questions:

1. Does this grant match our agency's priorities?
2. Are we eligible?
3. How much funding is available?
4. How much time do we have, and what does the application require?
5. What should our team do next?
