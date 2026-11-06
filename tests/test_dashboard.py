import importlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import modeling


def test_home_filters_and_empty_results(dashboard):
    client = dashboard.app.test_client()
    for query in ({}, {"airline": "Indigo", "class": "Economy"}, {"source_city": "Delhi", "destination_city": "Delhi"}):
        response = client.get("/", query_string=query)
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert 'id="prediction-form"' in html
        assert "Generalization Checks" in html
        assert "Prediction history" in html
        if query.get("source_city"):
            assert "No flights match these filters" in html
    assert client.get("/static/dashboard.js").status_code == 200


@pytest.mark.parametrize("view", ["dashboard", "analytics", "history", "invalid"])
def test_tab_routing_and_clean_product_ui(dashboard, view):
    from html.parser import HTMLParser

    class Panels(HTMLParser):
        def __init__(self):
            super().__init__()
            self.visible = []
        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            if attrs.get("role") == "tabpanel" and "hidden" not in attrs:
                self.visible.append(attrs["id"])

    html = dashboard.app.test_client().get("/", query_string={"view": view}).get_data(as_text=True)
    parser = Panels()
    parser.feed(html)
    assert parser.visible == [f"panel-{view if view != 'invalid' else 'dashboard'}"]
    analytics = html.split('id="panel-analytics"')[1].split('id="panel-history"')[0]
    assert "Model Comparison" in analytics
    assert "Generalization Checks" in analytics
    assert "Interview walkthrough" not in html
    assert 'id="panel-summary"' not in html
    assert 'name="view" value="analytics"' in html


