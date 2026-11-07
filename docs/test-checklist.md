# Federal Funds Matchmaker — Interface Testing Checklist

## Purpose

This checklist evaluates whether the Federal Funds Matchmaker is functional, understandable, and practical for agency staff.

Testing focuses on three main areas:

1. Search and navigation
2. Personal saving and agency collaboration
3. Data accuracy, persistence, and usability

Tests will be performed once the application is available. Any features that are not yet implemented should be marked as Blocked rather than Passed.

## Test Status Guide

- **Pass:** The feature works as expected.
- **Fail:** The feature was tested but did not work correctly.
- **Blocked:** The feature is unavailable or cannot currently be tested.
- **Not Tested:** Testing has not started.

---

## Required Functional Tests

### Test 1: Open a Grant and Return to Results

**Steps:**
1. Open the Search & Results dashboard.
2. Select an agency.
3. Apply a keyword or deadline filter.
4. Click View Details on a grant.
5. Return to the results screen.

**Expected Result:** The correct grant details open, and returning to results preserves the previous search and filter selections.

**Status:** Not Tested

### Test 2: Save a Personal Bookmark

**Steps:**
1. Open a grant.
2. Click Save Personally.
3. Navigate away from the grant.
4. Return to the user's saved grants.

**Expected Result:** The grant appears in the user's personal bookmarks.

**Status:** Not Tested

### Test 3: Share a Grant to the Agency Workspace

**Steps:**
1. Open a grant.
2. Click Share to Agency Workspace.
3. Navigate to the Agency Workspace.

**Expected Result:** The selected grant appears in the agency's shared grants list.

**Status:** Not Tested

### Test 4: Assign a Reviewer

**Steps:**
1. Open a grant in the Agency Workspace.
2. Select Assign Reviewer.
3. Choose an available reviewer.
4. Save the assignment.

**Expected Result:** The assigned reviewer's name appears on the shared grant and remains saved.

**Status:** Not Tested

### Test 5: Add a Comment and Change Status

**Steps:**
1. Open a shared grant.
2. Enter a comment.
3. Save the comment.
4. Change the review status from Not Reviewed to Under Review.

**Expected Result:** The comment appears in the grant's shared discussion, and the updated review status is displayed.

**Status:** Not Tested

### Test 6: Confirm Progress Persists After Refresh

**Steps:**
1. Assign a reviewer to a shared grant.
2. Add a comment and update the status.
3. Refresh the browser.
4. Reopen the same grant.

**Expected Result:** The reviewer assignment, comment, and status remain unchanged after refreshing.

**Status:** Not Tested

### Test 7: Confirm a Second User Sees Shared Updates

**Steps:**
1. Open the application as simulated User A.
2. Share a grant and update its review status.
3. Open a separate session as simulated User B in the same agency.
4. Navigate to the Agency Workspace.

**Expected Result:** User B can see the grant and updates made by User A.

**Status:** Not Tested

**Note:** If the prototype does not support real user accounts, this should be labeled as a simulated-user demonstration rather than proof of production-ready multi-user access.

### Test 8: Confirm Personal Bookmarks Remain Private

**Steps:**
1. Open the application as simulated User A.
2. Save a grant personally without sharing it.
3. Open the application as simulated User B.
4. Check User B's personal bookmarks and the shared agency workspace.

**Expected Result:** User A's personal bookmark does not automatically appear in User B's bookmarks or the shared workspace.

**Status:** Not Tested

**Note:** Simulated-user testing does not establish real authentication or data security.

### Test 9: Confirm Missing Information Displays Correctly

**Steps:**
1. Identify a grant record with missing funding or deadline information.
2. Open its grant card.
3. Open the Grant Details screen.

**Expected Result:** Missing information displays "Not stated" rather than an empty value, an invented amount, or an assumed deadline.

**Status:** Not Tested

---

## Additional Usability Checks

### Search & Results

- [ ] Agency selection updates the relevant results.
- [ ] Keyword search returns appropriate opportunities.
- [ ] Deadline slider correctly filters results.
- [ ] Sorting by funding changes the order correctly.
- [ ] Sorting by match prioritizes the highest-scoring grants.
- [ ] Eligibility information is visible on grant cards.
- [ ] Grant requirements are visible or clearly marked "Not stated."
- [ ] Grant cards are readable without excessive scrolling.

### Grant Details

- [ ] Full grant information is organized into understandable sections.
- [ ] The official source link opens the correct grant announcement.
- [ ] The match explanation references relevant agency priorities.
- [ ] Missing information is clearly labeled.
- [ ] Save Personally and Share to Agency Workspace are distinguishable.

### Agency Workspace

- [ ] Shared grants are visible in the correct workspace.
- [ ] Reviewer assignment is easy to find and update.
- [ ] Review statuses are understandable.
- [ ] Comments are visible to collaborators.
- [ ] Updates persist after refresh.
- [ ] Personal and shared grant lists remain separate.

---

## User Testing Scenarios

### Scenario A: Finding a Relevant Grant

A staff member working for an NC agency wants to find federal grants aligned with the agency's priorities and closing within the next 60 days.

**Success Criteria:**
The user can select the agency, filter by deadline, compare grant opportunities, and identify a promising match without assistance.

### Scenario B: Coordinating a Grant Review

A staff member finds an opportunity and wants a colleague to review it.

**Success Criteria:**
The user can share the grant, assign a reviewer, add a note, and confirm that the colleague can see the shared information.

### Scenario C: Handling Missing Information

A staff member opens a grant that does not include an award amount or application deadline in the available data.

**Success Criteria:**
The interface clearly marks missing information as "Not stated" rather than presenting unreliable information.

---

## Bug Reporting Template

When a test fails, record the following:

**Test Number:**

**Feature:**

**Test Environment:** Browser, app URL, and simulated user identity if applicable.

**Steps to Reproduce:**
1.
2.
3.

**Expected Result:**

**Actual Result:**

**Severity:** Low / Medium / High

**Screenshot or Evidence:**

**Status:** Open / Fixed / Retested

---

## Testing Summary

To be completed after testing.

| Metric | Result |
|---|---|
| Total required tests | 9 |
| Passed | 0 |
| Failed | 0 |
| Blocked | 0 |
| Not tested | 9 |

## Known Limitations

To be completed based on actual test results.

Potential areas to examine include:

- Incomplete grant data from external sources
- Missing eligibility or application requirements
- Incorrect or unclear matching explanations
- Shared updates not persisting across sessions
- Differences between simulated and real multi-user behavior
- Usability issues caused by excessive information on grant cards

## Final Testing Notes

Testing should determine whether an agency staff member can discover, assess, save, and collaborate on federal funding opportunities without extensive technical knowledge.

Any failed test should include exact reproduction steps so the development team can identify and address the problem.
