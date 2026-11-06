"""Prevent a successful HTML deployment with missing CDN dependencies."""
from html.parser import HTMLParser
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]


def test_rendered_assets_are_available_to_vercel_cdn(dashboard):
    class AssetReferences(HTMLParser):
        def __init__(self):
            super().__init__()
            self.paths = set()

        def handle_starttag(self, tag, attrs):
            for key, value in attrs:
                if key in {"src", "href", "data-src"} and value:
                    path = unquote(urlsplit(value).path)
                    if path.startswith("/static/"):
                        self.paths.add(path)

    page = dashboard.app.test_client().get("/")
    assert page.status_code == 200
    assets = AssetReferences()
    assets.feed(page.get_data(as_text=True))
    assert "/static/dashboard.css" in assets.paths
    for path in assets.paths:
        published = ROOT / "public" / path.lstrip("/")
        source = ROOT / path.lstrip("/")
        assert published.is_file(), f"Missing CDN asset: {path}"
        assert published.read_bytes() == source.read_bytes(), f"Stale CDN asset: {path}"
    stylesheet = ROOT / "public/static/dashboard.css"
    for dependency in re.findall(r'url\([\'\"]?([^\)\'\"]+)', stylesheet.read_text()):
        assert (stylesheet.parent / dependency).is_file(), f"Missing CSS dependency: {dependency}"
