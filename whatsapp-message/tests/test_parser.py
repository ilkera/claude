from __future__ import annotations

from parser import PostParser


def test_extraction_count(sample_raw_posts):
    posts = PostParser().parse(sample_raw_posts)
    # 4 entries, but one has empty text -> 3 valid posts
    assert len(posts) == 3


def test_content_extraction(sample_raw_posts):
    posts = PostParser().parse(sample_raw_posts)
    assert "25% tariffs" in posts[0].content
    assert "economy" in posts[1].content.lower()


def test_timestamp_parsing(sample_raw_posts):
    posts = PostParser().parse(sample_raw_posts)
    assert "2026" in posts[0].timestamp


def test_image_extraction(sample_raw_posts):
    posts = PostParser().parse(sample_raw_posts)
    assert len(posts[0].image_urls) == 1
    assert "media-cdn.factba.se" in posts[0].image_urls[0]


def test_stable_ids(sample_raw_posts):
    parser = PostParser()
    posts1 = parser.parse(sample_raw_posts)
    posts2 = parser.parse(sample_raw_posts)
    assert posts1[0].post_id == posts2[0].post_id


def test_empty_input():
    posts = PostParser().parse([])
    assert posts == []


def test_platform_detection(sample_raw_posts):
    posts = PostParser().parse(sample_raw_posts)
    # First two have truthsocial in image_url, third has twitter
    assert posts[0].platform == "truth_social"
    assert posts[2].platform == "twitter"
