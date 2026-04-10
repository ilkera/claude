from __future__ import annotations

ECONOMIC_CATEGORIES: dict[str, list[str]] = {
    "Trade & Tariffs": [
        "Tariff Announcements/Threats",
        "Trade Deals/Negotiations",
        "Sanctions",
        "Import/Export Restrictions",
        "Country-Specific Trade (China, EU, etc.)",
    ],
    "Monetary Policy & The Fed": [
        "Interest Rate Commentary",
        "Fed Chair Criticism/Praise",
        "Inflation",
        "Dollar Strength/Weakness",
        "Quantitative Easing/Tightening",
    ],
    "Tax Policy": [
        "Corporate Tax",
        "Individual Tax Cuts/Hikes",
        "Capital Gains",
        "Tax Incentives/Credits",
        "Estate Tax",
    ],
    "Stock Market & Equities": [
        "General Market Commentary",
        "Specific Company Callouts",
        "Sector Remarks (Tech, Energy, Defense, Pharma)",
        "IPO/Listing Commentary",
    ],
    "Housing & Real Estate": [
        "Mortgage Rates",
        "Housing Affordability",
        "Construction/Development Policy",
        "Fannie Mae/Freddie Mac",
        "Rent Control",
    ],
    "Government Spending & Fiscal Policy": [
        "Budget Proposals",
        "Debt Ceiling",
        "Deficit Commentary",
        "Infrastructure Spending",
        "DOGE/Cost-Cutting Initiatives",
        "Government Shutdowns",
    ],
    "Industry & Sector Regulation": [
        "Energy/Oil & Gas",
        "Banking/Financial Regulation",
        "Tech/Antitrust",
        "Pharma/Drug Pricing",
        "Auto Industry",
        "Crypto/Digital Assets",
    ],
    "Jobs & Labor": [
        "Employment Numbers",
        "Wage Commentary",
        "Immigration Impact on Labor",
        "Manufacturing Jobs",
        "Union-Related",
    ],
    "International Economic Relations": [
        "BRICS/De-dollarization",
        "Foreign Investment",
        "Bilateral Economic Relationships",
        "NATO Spending/Burden-Sharing",
    ],
    "Crypto & Digital Assets": [
        "Bitcoin/Crypto Endorsements",
        "Regulatory Stance",
        "CBDCs",
        "Specific Token Mentions",
    ],
}

NON_ECONOMIC_CATEGORIES: list[str] = [
    "Immigration & Border",
    "Foreign Policy & Military",
    "Legal & Judicial",
    "Elections & Politics",
    "Culture War & Social Issues",
    "Personal & Self-Promotion",
    "Law Enforcement & Crime",
    "Healthcare",
    "Energy & Environment (Non-Economic)",
]


def validate_classification(
    is_economic: bool,
    primary_category: str,
    subcategory: str | None,
    market_sentiment: str | None,
    confidence: float,
    relevance_score: float,
) -> tuple[bool, dict, list[str]]:
    """Validate and correct LLM classification output.

    Returns:
        Tuple of (is_valid, corrected_dict, corrections_list)
        - is_valid: True if no corrections were needed
        - corrected_dict: Dict with validated values
        - corrections_list: List of human-readable correction descriptions
    """
    corrections = []
    corrected = {}

    # Normalize "and" to "&" for category matching (case-insensitive)
    def normalize_category(cat: str) -> str:
        return cat.replace(" and ", " & ").replace(" And ", " & ")

    # Validate primary category
    normalized_primary = normalize_category(primary_category or "")
    matched_category = None

    if is_economic:
        # Try case-insensitive match against economic categories
        for cat in ECONOMIC_CATEGORIES.keys():
            if normalize_category(cat).lower() == normalized_primary.lower():
                matched_category = cat
                break
        if not matched_category:
            # Fall back to first economic category
            matched_category = list(ECONOMIC_CATEGORIES.keys())[0]
            corrections.append(
                f"Invalid economic category '{primary_category}', using '{matched_category}'"
            )
    else:
        # Try case-insensitive match against non-economic categories
        for cat in NON_ECONOMIC_CATEGORIES:
            if cat.lower() == (primary_category or "").lower():
                matched_category = cat
                break
        if not matched_category:
            # Fall back to first non-economic category
            matched_category = NON_ECONOMIC_CATEGORIES[0]
            corrections.append(
                f"Invalid non-economic category '{primary_category}', using '{matched_category}'"
            )

    corrected["is_economic"] = bool(is_economic)
    corrected["primary_category"] = matched_category

    # Validate subcategory
    if is_economic:
        valid_subs = ECONOMIC_CATEGORIES.get(matched_category, [])
        matched_sub = None
        if subcategory:
            # Try case-insensitive match
            for sub in valid_subs:
                if sub.lower() == subcategory.lower():
                    matched_sub = sub
                    break
        if not matched_sub and valid_subs:
            matched_sub = valid_subs[0]
            if subcategory:
                corrections.append(
                    f"Invalid subcategory '{subcategory}' for '{matched_category}', using '{matched_sub}'"
                )
            else:
                corrections.append(
                    f"Missing subcategory for '{matched_category}', using '{matched_sub}'"
                )
        corrected["subcategory"] = matched_sub
    else:
        # Non-economic posts should have None for subcategory
        if subcategory is not None:
            corrections.append("Cleared subcategory for non-economic post")
        corrected["subcategory"] = None

    # Validate market sentiment
    if is_economic:
        valid_sentiments = {"bullish", "bearish", "neutral"}
        if market_sentiment and market_sentiment.lower() in valid_sentiments:
            corrected["market_sentiment"] = market_sentiment.lower()
        else:
            if market_sentiment is not None and market_sentiment.lower() not in valid_sentiments:
                corrections.append(
                    f"Invalid market sentiment '{market_sentiment}', using 'neutral'"
                )
            corrected["market_sentiment"] = "neutral"
    else:
        # Non-economic posts should have None for market_sentiment
        if market_sentiment is not None:
            corrections.append("Cleared market_sentiment for non-economic post")
        corrected["market_sentiment"] = None

    # Validate confidence
    try:
        conf = float(confidence)
        if conf < 0.0:
            corrections.append(f"Confidence {conf} below 0.0, clamped to 0.0")
            conf = 0.0
        elif conf > 1.0:
            corrections.append(f"Confidence {conf} above 1.0, clamped to 1.0")
            conf = 1.0
        corrected["confidence"] = conf
    except (TypeError, ValueError):
        corrections.append(f"Invalid confidence '{confidence}', using 0.5")
        corrected["confidence"] = 0.5

    # Validate relevance_score
    try:
        rel = float(relevance_score)
        if rel < 0.0:
            corrections.append(f"Relevance {rel} below 0.0, clamped to 0.0")
            rel = 0.0
        elif rel > 1.0:
            corrections.append(f"Relevance {rel} above 1.0, clamped to 1.0")
            rel = 1.0
        corrected["relevance_score"] = rel
    except (TypeError, ValueError):
        corrections.append(f"Invalid relevance_score '{relevance_score}', using 0.5")
        corrected["relevance_score"] = 0.5

    is_valid = len(corrections) == 0
    return is_valid, corrected, corrections


def get_taxonomy_text() -> str:
    """Format the full taxonomy as human-readable text for prompt injection."""
    lines = ["ECONOMIC CATEGORIES:"]
    for category, subcategories in ECONOMIC_CATEGORIES.items():
        lines.append(f"  {category}:")
        for sub in subcategories:
            lines.append(f"    - {sub}")
    lines.append("")
    lines.append("NON-ECONOMIC CATEGORIES:")
    for category in NON_ECONOMIC_CATEGORIES:
        lines.append(f"  - {category}")
    return "\n".join(lines)
