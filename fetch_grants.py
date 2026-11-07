import argparse
import html
import json
import math
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests


BASE_URL = "https://api.grants.gov/v1/api"

DEFAULT_TOPICS = [
    "water",
    "PFAS",
    "recycling",
    "flood resilience",
    "environmental infrastructure",
]


def api_call(endpoint, payload):
    for attempt in range(3):
        time.sleep(1)

        try:
            response = requests.post(
                f"{BASE_URL}/{endpoint}",
                json=payload,
                timeout=30,
            )
            response.raise_for_status()
            result = response.json()

            if str(result.get("errorcode")) != "0":
                raise ValueError(
                    f"Grants.gov reported an error: {endpoint}"
                )

            data = result.get("data")
            if not isinstance(data, dict):
                raise ValueError("Unexpected Grants.gov response")

            return data

        except (requests.RequestException, ValueError):
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)


def clean_text(value):
    text = re.sub(r"<[^>]+>", " ", str(value or ""))
    return " ".join(html.unescape(text).split())


def amount(value):
    try:
        number = float(
            str(value).replace(",", "").replace("$", "")
        )
        if math.isfinite(number) and number >= 0:
            return number
    except (ValueError, TypeError):
        pass

    return None


def collect_hits(topics, rows):
    searches = [
        {
            "label": f"Topic: {topic}",
            "keyword": topic,
            "eligibilities": "",
        }
        for topic in topics
    ]

    searches.append({
        "label": "State-government applicants",
        "keyword": "",
        "eligibilities": "00",
    })

    unique_hits = {}

    for search in searches:
        print(f"Searching: {search['label']}", flush=True)

        data = api_call(
            "search2",
            {
                "keyword": search["keyword"],
                "eligibilities": search["eligibilities"],
                "oppStatuses": "posted",
                "rows": rows,
                "startRecordNum": 0,
            },
        )

        hits = data.get("oppHits")
        if not isinstance(hits, list):
            raise ValueError("Search response missing oppHits")

        print(f"  Received {len(hits)} records", flush=True)

        for hit in hits:
            opportunity_id = str(hit["id"])

            if opportunity_id not in unique_hits:
                unique_hits[opportunity_id] = {
                    "hit": hit,
                    "discovered_by": [],
                }

            unique_hits[opportunity_id]["discovered_by"].append(
                search["label"]
            )

    return unique_hits


def fetch_grants(topics, rows=10):
    unique_hits = collect_hits(topics, rows)

    output = Path(__file__).parent / "data" / "grants-live.json"
    previous = {}

    if output.exists():
        with output.open(encoding="utf-8") as file:
            previous = {
                record["id"]: record
                for record in json.load(file)
            }

    records = []
    fetched_at = datetime.now(timezone.utc).isoformat()
    detail_failures = 0

    for index, (opportunity_id, entry) in enumerate(
        unique_hits.items(), start=1
    ):
        hit = entry["hit"]
        record_id = f"grants-gov-{opportunity_id}"
        old = previous.get(record_id, {})

        print(
            f"Details {index}/{len(unique_hits)}: "
            f"{hit.get('title')}",
            flush=True,
        )

        synopsis = {}
        details_retrieved = False

        try:
            detail = api_call(
                "fetchOpportunity",
                {"opportunityId": int(opportunity_id)},
            )
            synopsis = detail.get("synopsis")

            if not isinstance(synopsis, dict) or not synopsis:
                raise ValueError("Opportunity synopsis unavailable")

            details_retrieved = True

        except (requests.RequestException, ValueError):
            synopsis = {}
            detail_failures += 1
            print(
                "  Details unavailable; retaining prior details if any."
            )

        if details_retrieved:
            applicant_types = synopsis.get("applicantTypes") or []

            eligibility_text = "; ".join(
                item.get("description", "")
                for item in applicant_types
                if item.get("description")
            )

            additional_eligibility_text = clean_text(
                synopsis.get("applicantEligibilityDesc")
            ) or None

            description = clean_text(
                synopsis.get("synopsisDesc")
            )
            award_min = amount(synopsis.get("awardFloor"))
            award_max = amount(synopsis.get("awardCeiling"))
            detail_status = "retrieved"
            details_fetched_at = fetched_at

        else:
            applicant_types = old.get("applicant_types_raw") or []
            eligibility_text = old.get("eligibility_text")
            additional_eligibility_text = old.get(
                "additional_eligibility_text"
            )
            description = old.get("description") or ""
            award_min = old.get("award_min")
            award_max = old.get("award_max")
            details_fetched_at = old.get("details_fetched_at")
            detail_status = "stale" if old else "unavailable"

        records.append({
            "id": record_id,
            "opportunity_number": (
                hit.get("number")
                or old.get("opportunity_number")
            ),
            "is_demo": False,
            "title": hit.get("title") or "Untitled opportunity",
            "funder": (
                hit.get("agencyName")
                or synopsis.get("agencyName")
                or old.get("funder")
                or "Not stated"
            ),
            "description": description,
            "deadline": hit.get("closeDate") or None,
            "award_min": award_min,
            "award_max": award_max,
            "eligible_applicant_types": None,
            "eligibility_text": eligibility_text or "Not stated",
            "additional_eligibility_text": additional_eligibility_text,
            "applicant_types_raw": applicant_types,
            "requirements": old.get("requirements"),
            "source_url": (
                "https://www.grants.gov/search-results-detail/"
                + opportunity_id
            ),
            "source": "Grants.gov",
            "source_status": hit.get("oppStatus"),
            "detail_status": detail_status,
            "details_fetched_at": details_fetched_at,
            "discovered_by": entry["discovered_by"],
            "fetched_at": fetched_at,
        })

    if records and detail_failures == len(records):
        raise ValueError(
            "All detail requests failed. Existing snapshot preserved."
        )

    return records


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--keyword",
        help="Optional single topic instead of the default five topics.",
    )
    parser.add_argument(
        "--rows",
        type=int,
        default=10,
        help="Maximum results requested per search.",
    )
    args = parser.parse_args()

    if not 1 <= args.rows <= 50:
        raise SystemExit("--rows must be between 1 and 50")

    topics = [args.keyword] if args.keyword else DEFAULT_TOPICS

    try:
        records = fetch_grants(topics, rows=args.rows)
        if not records:
            raise ValueError("No opportunities returned")
    except (requests.RequestException, ValueError) as error:
        raise SystemExit(
            f"Refresh failed: {error}\n"
            "Existing snapshot was not changed."
        )

    output = Path(__file__).parent / "data" / "grants-live.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".tmp")

    temporary.write_text(
        json.dumps(records, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    temporary.replace(output)

    print(
        f"\nSaved {len(records)} unique opportunities "
        f"to {output.name}"
    )
