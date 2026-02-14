from __future__ import annotations

import json
from pathlib import Path

import pytest

from models import Post

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_raw_posts() -> list[dict]:
    return json.loads((FIXTURES_DIR / "sample_api_response.json").read_text())


@pytest.fixture
def sample_posts() -> list[Post]:
    return [
        Post(
            platform="truth_social",
            content="Announced new 25% tariffs on all imports from China.",
            timestamp="2026-02-14T14:32:00-05:00",
            image_urls=["https://media-cdn.factba.se/realdonaldtrump-truthsocial/116069904214662301.jpg"],
        ),
        Post(
            platform="truth_social",
            content="The economy is doing GREAT. Best numbers ever.",
            timestamp="2026-02-14T12:15:00-05:00",
        ),
    ]
