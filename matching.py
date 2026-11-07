import re


def normalize(text):
    """Normalize case, punctuation, and whitespace."""
    text = str(text or "").casefold()
    text = re.sub(r"[-–—/]", " ", text)
    text = re.sub(r"[^\w\s]", " ", text)
    return " ".join(text.split())


def contains_phrase(text, phrase):
    phrase = normalize(phrase)
    if not phrase:
        return False

    return f" {phrase} " in f" {text} "


def assess_eligibility(grant, agency):
    """
    Check structured applicant types only.
    This does not establish full grant eligibility.
    """
    allowed = grant.get("eligible_applicant_types")
    applicant_type = agency.get("applicant_type")

    if not allowed or not applicant_type:
        return {
            "status": "Needs verification",
            "reason": "Applicant-type eligibility is not stated.",
        }

    if applicant_type in allowed:
        return {
            "status": "Applicant type matches",
            "reason": (
                "The listed applicant types include this agency's type. "
                "Other eligibility conditions still require review."
            ),
        }

    return {
        "status": "Applicant type does not match",
        "reason": (
            "The listed applicant types do not include this agency's "
            "type. Check the official notice for exceptions."
        ),
    }


def match_grant(grant, agency):
    """
    Rank by keyword evidence in title and description.
    The count is not a probability or a calibrated percentage.
    """
    text = normalize(
        f"{grant.get('title') or ''} "
        f"{grant.get('description') or ''}"
    )

    priority_matches = []
    all_keywords = set()

    for priority in agency.get("priorities", []):
        if not priority.get("enabled", True):
            continue

        # Deduplicate normalized terms within each priority.
        terms = {}
        for keyword in priority.get("keywords", []):
            normalized = normalize(keyword)
            if normalized:
                terms.setdefault(normalized, keyword)

        matched = [
            original
            for normalized, original in terms.items()
            if contains_phrase(text, normalized)
        ]

        if matched:
            all_keywords.update(normalize(term) for term in matched)
            priority_matches.append({
                "priority_id": priority["id"],
                "priority_title": priority["title"],
                "matched_keywords": matched,
                "source_url": priority.get("source_url"),
                "source_sections": priority.get("source_sections", []),
            })

    priority_matches.sort(
        key=lambda item: (
            -len(item["matched_keywords"]),
            item["priority_title"],
        )
    )

    if priority_matches:
        strongest = priority_matches[0]
        terms = ", ".join(strongest["matched_keywords"])
        reason = (
            f"Keyword evidence for "
            f"{strongest['priority_title']}: {terms}."
        )
    else:
        reason = (
            "No configured priority keywords were found in the "
            "title or description. This does not prove irrelevance."
        )

    return {
        "keyword_count": len(all_keywords),
        "priority_matches": priority_matches,
        "reason": reason,
        "eligibility": assess_eligibility(grant, agency),
    }
