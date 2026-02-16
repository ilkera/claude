from __future__ import annotations

from taxonomy import ECONOMIC_CATEGORIES, NON_ECONOMIC_CATEGORIES, get_taxonomy_text


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
