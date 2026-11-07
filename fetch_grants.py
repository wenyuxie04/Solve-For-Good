import html
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests


BASE_URL = "https://api.grants.gov/v1/api"


def api_call(endpoint, payload):
    response = requests.post(
        f"{BASE_URL}/{endpoint}",
        json=payload,
        timeout=30,
    )
    response.raise_for_status()
    result = response.json()

    if str(result.get("errorcode")) != "0":
        raise ValueError(f"Grants.gov reported an error: {endpoint}")

    data = result.get("data")
    if not isinstance(data, dict):
        raise ValueError("Unexpected Grants.gov response")

    return data


def clean_text(value):
    text = re.sub(r"<[^>]+>", " ", str(value or ""))
    return " ".join(html.unescape(text).split())


def amount(value):
    try:
        return float(str(value).replace(",", "").replace("$", ""))
    except (ValueError, TypeError):
        return None


def fetch_grants(keyword="water", limit=10):
    search = api_call(
        "search2",
        {
            "keyword": keyword,
            "oppStatuses": "posted",
            "rows": limit,
            "startRecordNum": 0,
        },
    )

    hits = search.get("oppHits")
    if not isinstance(hits, list):
        raise ValueError("Search response did not contain oppHits")

    records = []
    fetched_at = datetime.now(timezone.utc).isoformat()

    for hit in hits:
        opportunity_id = str(hit["id"])
        synopsis = {}
        detail_status = "unavailable"

        # Retrieve details because search results alone lack
        # descriptions, award amounts, and applicant types.
        time.sleep(1)

        try:
            detail = api_call(
                "fetchOpportunity",
                {"opportunityId": int(opportunity_id)},
            )
            synopsis = detail.get("synopsis") or {}
            detail_status = "retrieved"
        except (requests.RequestException, ValueError):
            print(
                f"Details unavailable for {opportunity_id}; "
                "keeping the search record."
            )

        applicant_types = synopsis.get("applicantTypes") or []
        eligibility_text = "; ".join(
            item.get("description", "")
            for item in applicant_types
            if item.get("description")
        )

        # Leave normalized eligibility unknown until we map
        # the complete Grants.gov applicant-type vocabulary.
        records.append({
            "id": f"grants-gov-{opportunity_id}",
            "opportunity_number": hit.get("number") or None,
            "is_demo": False,
            "title": hit.get("title") or "Untitled opportunity",
            "funder": hit.get("agencyName") or "Not stated",
            "description": clean_text(synopsis.get("synopsisDesc")),
            "deadline": hit.get("closeDate") or None,
            "award_min": amount(synopsis.get("awardFloor")),
            "award_max": amount(synopsis.get("awardCeiling")),
            "eligible_applicant_types": None,
            "eligibility_text": eligibility_text or "Not stated",
            "applicant_types_raw": applicant_types,
            "requirements": None,
            "source_url": (
                "https://www.grants.gov/search-results-detail/"
                + opportunity_id
            ),
            "source": "Grants.gov",
            "source_status": hit.get("oppStatus"),
            "detail_status": detail_status,
            "fetched_at": fetched_at,
        })

    return records


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--keyword", default="water")
    args = parser.parse_args()

    records = fetch_grants(keyword=args.keyword)

    if not records:
        raise SystemExit(
            "No results. Existing data was not changed. "
            "Try another keyword."
        )

    output = Path(__file__).parent / "data" / "grants-live.json"
    temporary = output.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(records, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    temporary.replace(output)

    print(f"Saved {len(records)} real opportunities to {output.name}")
