from __future__ import annotations

from taxonomy import ECONOMIC_CATEGORIES, NON_ECONOMIC_CATEGORIES, get_taxonomy_text


# === pass_to_pass tests (exist at base_commit) ===


def test_economic_categories_have_subcategories():
    for category, subs in ECONOMIC_CATEGORIES.items():
        assert len(subs) > 0, f"{category} has no subcategories"


def test_no_duplicate_category_names():
    economic_names = set(ECONOMIC_CATEGORIES.keys())
    non_economic_names = set(NON_ECONOMIC_CATEGORIES)
    overlap = economic_names & non_economic_names
    assert not overlap, f"Duplicate category names: {overlap}"


def test_get_taxonomy_text_includes_all_categories():
    text = get_taxonomy_text()
    for category in ECONOMIC_CATEGORIES:
        assert category in text
    for category in NON_ECONOMIC_CATEGORIES:
        assert category in text


def test_get_taxonomy_text_includes_subcategories():
    text = get_taxonomy_text()
    for subs in ECONOMIC_CATEGORIES.values():
        for sub in subs:
            assert sub in text


def test_category_counts():
    assert len(ECONOMIC_CATEGORIES) == 10
    assert len(NON_ECONOMIC_CATEGORIES) == 9


# === fail_to_pass tests (added in gold_commit) ===


def test_validate_classification_economic_valid():
    from taxonomy import validate_classification

    is_valid, corrected, corrections = validate_classification(
        is_economic=True,
        primary_category="Trade & Tariffs",
        subcategory="Tariff Announcements/Threats",
        market_sentiment="bearish",
        confidence=0.92,
        relevance_score=0.8,
    )
    assert corrected["is_economic"] is True
    assert corrected["primary_category"] == "Trade & Tariffs"
    assert corrected["subcategory"] == "Tariff Announcements/Threats"
    assert corrected["market_sentiment"] in ("bullish", "bearish", "neutral", None)
    assert 0.0 <= corrected["confidence"] <= 1.0
    assert 0.0 <= corrected["relevance_score"] <= 1.0


def test_validate_classification_normalizes_and_to_ampersand():
    from taxonomy import validate_classification

    is_valid, corrected, corrections = validate_classification(
        is_economic=True,
        primary_category="Trade and Tariffs",
        subcategory="Tariff Announcements/Threats",
        market_sentiment="neutral",
        confidence=0.85,
        relevance_score=0.7,
    )
    assert corrected["primary_category"] in ECONOMIC_CATEGORIES


def test_validate_classification_invalid_category_fallback():
    from taxonomy import validate_classification

    is_valid, corrected, corrections = validate_classification(
        is_economic=True,
        primary_category="Totally Fake Category",
        subcategory="Also Fake",
        market_sentiment="bullish",
        confidence=0.5,
        relevance_score=0.6,
    )
    all_valid = set(ECONOMIC_CATEGORIES.keys()) | set(NON_ECONOMIC_CATEGORIES)
    assert corrected["primary_category"] in all_valid
    assert len(corrections) > 0


def test_validate_classification_invalid_subcategory_fallback():
    from taxonomy import validate_classification

    is_valid, corrected, corrections = validate_classification(
        is_economic=True,
        primary_category="Trade & Tariffs",
        subcategory="This Subcategory Does Not Exist",
        market_sentiment="neutral",
        confidence=0.7,
        relevance_score=0.5,
    )
    valid_subs = ECONOMIC_CATEGORIES["Trade & Tariffs"]
    assert corrected["subcategory"] in valid_subs or corrected["subcategory"] is None


def test_validate_classification_non_economic_clears_fields():
    from taxonomy import validate_classification

    is_valid, corrected, corrections = validate_classification(
        is_economic=False,
        primary_category="Immigration & Border",
        subcategory="Some Subcategory",
        market_sentiment="bullish",
        confidence=0.8,
        relevance_score=0.6,
    )
    assert corrected["is_economic"] is False
    assert corrected["subcategory"] is None
    assert corrected["market_sentiment"] is None


def test_validate_classification_clamps_scores():
    from taxonomy import validate_classification

    # Test high values clamped
    _, corrected, _ = validate_classification(
        is_economic=True,
        primary_category="Tax Policy",
        subcategory="Corporate Tax",
        market_sentiment="neutral",
        confidence=999.9,
        relevance_score=5.0,
    )
    assert 0.0 <= corrected["confidence"] <= 1.0
    assert 0.0 <= corrected["relevance_score"] <= 1.0

    # Test low values clamped
    _, corrected, _ = validate_classification(
        is_economic=True,
        primary_category="Tax Policy",
        subcategory="Corporate Tax",
        market_sentiment="neutral",
        confidence=-50.0,
        relevance_score=-2.0,
    )
    assert 0.0 <= corrected["confidence"] <= 1.0
    assert 0.0 <= corrected["relevance_score"] <= 1.0

    # Test non-numeric defaults to 0.5
    _, corrected, _ = validate_classification(
        is_economic=True,
        primary_category="Tax Policy",
        subcategory="Corporate Tax",
        market_sentiment="neutral",
        confidence="not_a_number",
        relevance_score=0.5,
    )
    assert 0.0 <= corrected["confidence"] <= 1.0


def test_validate_classification_invalid_sentiment_defaults():
    from taxonomy import validate_classification

    is_valid, corrected, corrections = validate_classification(
        is_economic=True,
        primary_category="Tax Policy",
        subcategory="Corporate Tax",
        market_sentiment="totally_invalid",
        confidence=0.5,
        relevance_score=0.5,
    )
    assert corrected["market_sentiment"] in ("bullish", "bearish", "neutral", None)


def test_validate_classification_case_insensitive():
    from taxonomy import validate_classification

    is_valid, corrected, corrections = validate_classification(
        is_economic=True,
        primary_category="trade & tariffs",
        subcategory="Tariff Announcements/Threats",
        market_sentiment="neutral",
        confidence=0.8,
        relevance_score=0.7,
    )
    assert corrected["primary_category"] in ECONOMIC_CATEGORIES
