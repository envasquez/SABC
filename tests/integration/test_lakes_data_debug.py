"""Debug test for lakes data attribute rendering."""

import html
import json
import re

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from core.db_schema import Lake, Ramp


def test_lakes_exist_in_database(db_session: Session):
    """Verify lakes and ramps exist in the test database."""
    lakes = db_session.query(Lake).all()
    print(f"\n=== Lakes in test DB: {len(lakes)} ===")
    for lake in lakes:
        ramps = db_session.query(Ramp).filter(Ramp.lake_id == lake.id).all()
        print(f"  - {lake.display_name}: {len(ramps)} ramps")


def test_lakes_data_attribute_renders_correctly(
    member_client: TestClient,
    test_lake: Lake,
    test_ramp: Ramp,
):
    """Test that the lakes-data div contains properly encoded JSON."""
    response = member_client.get("/polls?tab=tournament")

    assert response.status_code == 200
    html_content = response.text

    # First, find the lakes-data div and print context
    lakes_div_idx = html_content.find('id="lakes-data"')
    if lakes_div_idx != -1:
        print("\n=== Raw HTML around lakes-data (500 chars): ===")
        print(html_content[lakes_div_idx - 20 : lakes_div_idx + 500])

    # Find lakes-data div with double-quoted attribute
    match = re.search(r'<div id="lakes-data" data-lakes="([^"]*)"', html_content)

    assert match is not None, "lakes-data div with data-lakes attribute not found"

    data_attr = match.group(1)
    print(f"\n=== data-lakes attribute length: {len(data_attr)} ===")
    print(f"First 200 chars: {data_attr[:200]}")

    # Decode HTML entities (browser does this automatically)
    decoded = html.unescape(data_attr)
    print("\n=== After HTML unescape (first 200 chars): ===")
    print(decoded[:200])

    # Parse as JSON
    lakes = json.loads(decoded)
    print(f"\n=== SUCCESS! Parsed {len(lakes)} lakes ===")

    # With test fixtures, we should have at least test_lake
    assert len(lakes) > 0, f"Lakes data should not be empty (test_lake={test_lake.display_name})"

    # Verify structure
    first_lake = lakes[0]
    assert "id" in first_lake, "Lake should have id"
    assert "name" in first_lake, "Lake should have name"
    assert "ramps" in first_lake, "Lake should have ramps"

    print(f"First lake: {first_lake['name']}")
    print(f"First lake has {len(first_lake['ramps'])} ramps")

    # Check for the problematic ramp with single quote
    for lake in lakes:
        for ramp in lake.get("ramps", []):
            if "'" in ramp.get("name", ""):
                print(f"Found ramp with single quote: {ramp['name']} in lake {lake['name']}")
