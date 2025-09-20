#!/usr/bin/env python3
"""
Tournament results ingestion script for SABC.

This script scrapes tournament data from the reference site (http://167.71.20.3)
and imports it into the SABC PostgreSQL database following the established schema.

Features:
- Type-safe implementation following SABC coding standards
- Dry-run mode for testing without database changes
- Automatic angler creation for new participants
- Support for both individual and team results
- Comprehensive error handling and logging
- Year-based data import with validation

Database Schema Dependencies:
- anglers: Stores angler information (name, email, member status)
- events: Tournament event details (date, name, location)
- tournaments: Tournament-specific settings (lake, ramp, rules)
- results: Individual angler results (weight, fish count, points)
- team_results: Team-based results (if applicable)

Usage:
    python ingest_results.py 2022 --dry-run    # Preview import
    python ingest_results.py 2023              # Import to database
    python ingest_results.py 2024 -v           # Import with verbose logging

Requirements:
- requests>=2.25.0
- beautifulsoup4>=4.9.0
- SQLAlchemy (as used by core.database)
- PostgreSQL database with SABC schema initialized

Environment:
- DATABASE_URL: PostgreSQL connection string (default: localhost)
"""

import argparse
import json
import logging
import re
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import requests  # type: ignore
from bs4 import BeautifulSoup
from sqlalchemy import text

from core.db_schema import engine

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Reference site configuration
REFERENCE_SITE = "http://167.71.20.3"


class TournamentResult:
    """Represents a tournament result."""

    def __init__(
        self,
        angler_name: str,
        total_weight: float,
        num_fish: int = 0,
        big_bass_weight: float = 0.0,
        place_finish: Optional[int] = None,
        points: int = 0,
        disqualified: bool = False,
        buy_in: bool = False,
        dead_fish_penalty: float = 0.0,
    ):
        self.angler_name = angler_name
        self.total_weight = total_weight
        self.num_fish = num_fish
        self.big_bass_weight = big_bass_weight
        self.place_finish = place_finish
        self.points = points
        self.disqualified = disqualified
        self.buy_in = buy_in
        self.dead_fish_penalty = dead_fish_penalty


class TeamResult:
    """Represents a team tournament result."""

    def __init__(
        self,
        angler1_name: str,
        angler2_name: str,
        total_weight: float,
        place_finish: Optional[int] = None,
    ):
        self.angler1_name = angler1_name
        self.angler2_name = angler2_name
        self.total_weight = total_weight
        self.place_finish = place_finish


class Tournament:
    """Represents a tournament."""

    def __init__(
        self,
        name: str,
        date: datetime,
        year: int,
        lake_name: Optional[str] = None,
        ramp_name: Optional[str] = None,
        is_team: bool = True,
        entry_fee: float = 25.00,
        fish_limit: int = 5,
        start_time: Optional[str] = None,
        weigh_in_time: Optional[str] = None,
        google_maps_iframe: Optional[str] = None,
    ):
        self.name = name
        self.date = date
        self.year = year
        self.lake_name = lake_name
        self.ramp_name = ramp_name
        self.is_team = is_team
        self.entry_fee = entry_fee
        self.fish_limit = fish_limit
        self.start_time = start_time
        self.weigh_in_time = weigh_in_time
        self.google_maps_iframe = google_maps_iframe
        self.results: List[TournamentResult] = []
        self.team_results: List[TeamResult] = []


class TournamentScraper:
    """Scrapes tournament data from reference site."""

    def __init__(self, base_url: str = REFERENCE_SITE):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0 (SABC Tournament Importer)"})

    def get_tournaments_for_year(self, year: int) -> List[Tournament]:
        """
        Extract tournament data for a specific year by scraping all paginated pages.
        """
        tournaments: List[Tournament] = []
        tournament_ids: set[int] = set()  # Track IDs to avoid duplicates

        # Scrape all pages (1-15) to find tournaments
        for page in range(1, 16):
            try:
                page_url = f"{self.base_url}/?page={page}"
                logger.debug(f"Scraping page {page}: {page_url}")
                response = self.session.get(page_url)
                response.raise_for_status()

                soup = BeautifulSoup(response.content, "html.parser")

                # Find all tournament links on the page
                for link in soup.find_all("a", class_="article-title"):
                    href = link.get("href", "")
                    text = link.get_text(strip=True)

                    # Look for tournament links (format: /tournament/ID/)
                    match = re.match(r"/tournament/(\d+)/", href)
                    if match and "Event #" in text and str(year) in text:
                        tournament_id = int(match.group(1))

                        # Skip if we've already processed this tournament
                        if tournament_id in tournament_ids:
                            continue

                        tournament_ids.add(tournament_id)

                        # Scrape the individual tournament page
                        tournament = self._scrape_tournament_page(tournament_id, text, year)
                        if tournament:
                            tournaments.append(tournament)
                            logger.info(
                                f"Found tournament: {tournament.name} on {tournament.date.date()}"
                            )

            except requests.RequestException as e:
                logger.warning(f"Could not fetch page {page}: {e}")
                continue

        # Sort tournaments by date
        tournaments.sort(key=lambda t: t.date)

        logger.info(f"Found {len(tournaments)} tournaments for {year}")
        return tournaments

    def _scrape_tournament_page(
        self, tournament_id: int, title: str, year: int
    ) -> Optional[Tournament]:
        """Scrape details from a specific tournament page."""
        try:
            url = f"{self.base_url}/tournament/{tournament_id}/"
            logger.debug(f"Scraping tournament page: {url}")
            response = self.session.get(url)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")

            # Parse tournament details from the page
            tournament_data = self._parse_tournament_details(soup, title)

            # Extract the date from the title (e.g., "January Event #1 2022 on Jan. 23, 2022")
            date_match = re.search(r"on\s+([A-Za-z]+\.?\s+\d+,\s+\d{4})", title)
            if date_match:
                date_str = date_match.group(1)
                try:
                    # Parse date like "Jan. 23, 2022"
                    tournament_data["date"] = datetime.strptime(date_str, "%b. %d, %Y")
                except ValueError:
                    try:
                        # Try without the period
                        tournament_data["date"] = datetime.strptime(date_str, "%b %d, %Y")
                    except ValueError:
                        # Fallback to extracting just month and setting to 15th
                        month_match = re.search(
                            r"(January|February|March|April|May|June|July|August|September|October|November|December)",
                            title,
                        )
                        if month_match:
                            month_name = month_match.group(1)
                            month_num = {
                                "January": 1,
                                "February": 2,
                                "March": 3,
                                "April": 4,
                                "May": 5,
                                "June": 6,
                                "July": 7,
                                "August": 8,
                                "September": 9,
                                "October": 10,
                                "November": 11,
                                "December": 12,
                            }[month_name]
                            tournament_data["date"] = datetime(year, month_num, 15)

            # Extract event name (e.g., "January Event #1 2022")
            name_match = re.match(r"([^o]+)(?:\s+on\s+)?", title)
            tournament_name = name_match.group(1).strip() if name_match else title

            # Create tournament object
            tournament = Tournament(
                name=tournament_name,
                date=tournament_data.get("date", datetime(year, 1, 1)),
                year=year,
                lake_name=tournament_data.get("lake_name", "Unknown Lake"),
                ramp_name=tournament_data.get("ramp_name", "Unknown Ramp"),
                is_team=tournament_data.get("is_team", False),
                entry_fee=tournament_data.get("entry_fee", 25.00),
                fish_limit=tournament_data.get("fish_limit", 5),
                start_time=tournament_data.get("start_time"),
                weigh_in_time=tournament_data.get("weigh_in_time"),
                google_maps_iframe=tournament_data.get("google_maps_iframe"),
            )

            # Scrape results from the tournament page
            tournament.results = self._scrape_tournament_results(soup)
            tournament.team_results = self._scrape_team_results(soup)

            # Get buy-in anglers and mark them in results
            buy_in_anglers = self._scrape_buy_in_anglers(soup)
            self._mark_buy_in_anglers(tournament.results, buy_in_anglers)

            # Add buy-in-only anglers (those who bought in but didn't appear in main results)
            self._add_buy_in_only_anglers(tournament.results, buy_in_anglers)

            return tournament

        except Exception as e:
            logger.warning(f"Failed to scrape tournament {tournament_id}: {e}")
            return None

    def _parse_tournament_details(self, soup: BeautifulSoup, title: str) -> Dict[str, Any]:
        """Parse tournament details from the tournament page."""
        details: Dict[str, Any] = {}

        # Extract lake name from h2 headers
        for h2 in soup.find_all("h2"):
            lake_text = h2.get_text(strip=True)
            if "LAKE" in lake_text.upper():
                # Remove '- RESULTS' and similar suffixes
                lake_name = lake_text
                for suffix in [" - RESULTS", "-RESULTS", " -RESULTS", "- RESULTS", " RESULTS"]:
                    lake_name = lake_name.replace(suffix, "")
                lake_name = lake_name.strip()
                details["lake_name"] = lake_name
                break

        # Extract Google Maps iframe
        iframe = soup.find("iframe")
        if iframe and iframe.get("src"):
            details["google_maps_iframe"] = str(iframe)

            # Try to extract ramp name from iframe title or nearby text
            iframe_title = iframe.get("title", "")
            if iframe_title:
                details["ramp_name"] = iframe_title

        # Parse tournament info from the details table
        for table in soup.find_all("table", class_="table"):
            for row in table.find_all("tr"):
                cells = row.find_all("td")
                # Process all cells in the row, not just first 2
                for i in range(0, len(cells), 2):
                    if i + 1 < len(cells):
                        label = cells[i].get_text(strip=True).lower()
                        value = cells[i + 1].get_text(strip=True)

                        if "date:" in label:
                            # Already handled in main method
                            pass
                        elif "start time" in label:
                            # Parse start time (e.g., "7 a.m." or "06:30")
                            details["start_time"] = value
                        elif "weigh-in" in label or "weigh in" in label:
                            # Parse weigh-in time (e.g., "3 p.m." or "15:00")
                            details["weigh_in_time"] = value
                        elif "entry fee" in label:
                            # Parse entry fee (e.g., "$25.00/angler" -> 25.00)
                            fee_match = re.search(r"\$(\d+(?:\.\d+)?)", value)
                            if fee_match:
                                details["entry_fee"] = float(fee_match.group(1))
                        elif "limit" in label and "fish" in value.lower():
                            # Parse fish limit (e.g., "5 fish/angler" -> 5)
                            limit_match = re.search(r"(\d+)\s*fish", value)
                            if limit_match:
                                details["fish_limit"] = int(limit_match.group(1))
                        elif "team payout" in label:
                            details["is_team"] = value.lower() == "yes"
                        elif "aoy points" in label:
                            details["aoy_points"] = value.lower() == "yes"

        return details

    def _scrape_tournament_results(self, soup: BeautifulSoup) -> List[TournamentResult]:
        """Scrape individual tournament results from the page."""
        results: List[TournamentResult] = []

        # Find the results table (has headers like "Place finish", "First name", "Last name")
        for table in soup.find_all("table", class_="table"):
            headers = [th.get_text(strip=True).lower() for th in table.find_all("th")]

            # Check if this is the individual results table
            if "place finish" in headers and "first name" in headers:
                for row in table.find_all("tr")[1:]:  # Skip header row
                    cells = row.find_all("td")
                    if len(cells) >= 4:
                        try:
                            # Extract data based on column positions (ignore place from reference site)
                            place = None  # Will be calculated after import
                            first_name = cells[1].get_text(strip=True)
                            last_name = cells[2].get_text(strip=True)

                            # Skip empty rows
                            if not first_name and not last_name:
                                continue

                            angler_name = f"{first_name} {last_name}".strip()

                            # Find data in remaining columns
                            num_fish = 0
                            total_weight = 0.0
                            points = 0
                            big_bass = 0.0

                            for i, cell in enumerate(cells[3:], 3):
                                cell_text = cell.get_text(strip=True)

                                # Try to identify what this column contains
                                if i < len(headers) + 1:
                                    header = headers[i] if i < len(headers) else ""

                                    if "fish" in header and cell_text.isdigit():
                                        num_fish = int(cell_text)
                                    elif "weight" in header and "bass" not in header:
                                        try:
                                            total_weight = float(cell_text)
                                        except ValueError:
                                            pass
                                    elif "points" in header and cell_text.isdigit():
                                        points = int(cell_text)
                                    elif "bass" in header:
                                        try:
                                            big_bass = float(cell_text)
                                        except ValueError:
                                            pass

                            # Points will be calculated after import
                            points = 0

                            result = TournamentResult(
                                angler_name=angler_name,
                                total_weight=total_weight,
                                num_fish=num_fish,
                                big_bass_weight=big_bass,
                                place_finish=place,
                                points=points,
                            )
                            results.append(result)

                        except Exception as e:
                            logger.debug(f"Failed to parse result row: {e}")
                            continue

                break  # Found the results table, no need to check others

        return results

    def _scrape_team_results(self, soup: BeautifulSoup) -> List[TeamResult]:
        """Scrape team tournament results from the page."""
        team_results: List[TeamResult] = []

        # Find the team results table (has headers like "Place finish", "Team name")
        for table in soup.find_all("table", class_="table"):
            headers = [th.get_text(strip=True).lower() for th in table.find_all("th")]

            # Check if this is the team results table
            if "team" in " ".join(headers) and "place" in " ".join(headers):
                for row in table.find_all("tr")[1:]:  # Skip header row
                    cells = row.find_all("td")
                    if len(cells) >= 2:
                        try:
                            place_text = cells[0].get_text(strip=True)
                            team_name = cells[1].get_text(strip=True)

                            # Skip empty rows
                            if not team_name:
                                continue

                            place = int(place_text) if place_text.isdigit() else None

                            # Extract weight if available
                            total_weight = 0.0
                            for cell in cells[2:]:
                                try:
                                    weight_text = cell.get_text(strip=True)
                                    if (
                                        weight_text and not weight_text.isdigit()
                                    ):  # Avoid fish count
                                        total_weight = float(weight_text)
                                        break
                                except ValueError:
                                    continue

                            # Try to parse team members from name (e.g., "Smith/Jones")
                            if "/" in team_name:
                                members = team_name.split("/")
                                if len(members) == 2:
                                    team_result = TeamResult(
                                        angler1_name=members[0].strip(),
                                        angler2_name=members[1].strip(),
                                        total_weight=total_weight,
                                        place_finish=place,
                                    )
                                    team_results.append(team_result)

                        except Exception as e:
                            logger.debug(f"Failed to parse team result row: {e}")
                            continue

                break  # Found the team results table

        return team_results

    def _scrape_buy_in_anglers(self, soup: BeautifulSoup) -> Dict[str, Tuple[int, int]]:
        """Scrape buy-in angler names and their place/points from the buy-in table."""
        buy_in_anglers: Dict[str, Tuple[int, int]] = {}

        # Find the buy-in table (has headers: Place finish, First name, Last name, Points)
        for table in soup.find_all("table", class_="table"):
            headers = [th.get_text(strip=True) for th in table.find_all("th")]

            # Check if this is the buy-in table
            if headers == ["Place finish", "First name", "Last name", "Points"]:
                for row in table.find_all("tr")[1:]:  # Skip header row
                    cells = row.find_all("td")
                    if len(cells) >= 3:
                        try:
                            first_name = cells[1].get_text(strip=True)
                            last_name = cells[2].get_text(strip=True)
                            cells[3].get_text(strip=True) if len(cells) >= 4 else "0"

                            # Skip empty rows
                            if not first_name and not last_name:
                                continue

                            angler_name = f"{first_name} {last_name}".strip()
                            # Place and points will be calculated after import
                            buy_in_anglers[angler_name] = (0, 0)  # Placeholder values

                        except Exception as e:
                            logger.debug(f"Failed to parse buy-in row: {e}")
                            continue

                break  # Found the buy-in table, no need to check others

        return buy_in_anglers

    def _mark_buy_in_anglers(
        self, results: List[TournamentResult], buy_in_anglers: Dict[str, Tuple[int, int]]
    ) -> None:
        """Mark anglers who bought in."""
        for result in results:
            if result.angler_name in buy_in_anglers:
                result.buy_in = True
                logger.debug(f"Marked {result.angler_name} as buy-in")

    def _add_buy_in_only_anglers(
        self, results: List[TournamentResult], buy_in_anglers: Dict[str, Tuple[int, int]]
    ) -> None:
        """Add result records for buy-in anglers who don't appear in main results."""
        existing_anglers = {result.angler_name for result in results}

        for buy_in_angler, (place, points) in buy_in_anglers.items():
            if buy_in_angler not in existing_anglers:
                # Create a result record for buy-in-only angler
                buy_in_result = TournamentResult(
                    angler_name=buy_in_angler,
                    total_weight=0.0,  # No weight recorded
                    num_fish=0,  # No fish recorded
                    big_bass_weight=0.0,
                    place_finish=None,  # Will be calculated after import
                    points=0,  # Will be calculated after import
                    disqualified=False,
                    buy_in=True,  # This is a buy-in angler
                    dead_fish_penalty=0.0,
                )
                results.append(buy_in_result)
                logger.debug(f"Added buy-in-only angler: {buy_in_angler}")


class DatabaseImporter:
    """Handles database operations for tournament import."""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.import_data: Dict[str, Any] = {
            "anglers": [],
            "lakes": [],
            "ramps": [],
            "events": [],
            "tournaments": [],
            "results": [],
            "team_results": [],
        }
        self.lake_cache: Dict[str, int] = {}  # Cache lake name -> id
        self.ramp_cache: Dict[Tuple[str, str], int] = {}  # Cache (lake_name, ramp_name) -> id

    def import_tournaments(self, tournaments: List[Tournament]) -> None:
        """Import tournaments and all related data."""
        with engine.connect() as conn:
            for tournament in tournaments:
                self._import_single_tournament(conn, tournament)

        if self.dry_run:
            print(json.dumps(self.import_data, indent=4, default=str))

    def _import_single_tournament(self, conn, tournament: Tournament) -> None:
        """Import a single tournament with all its data."""
        # Ensure lake and ramp exist
        lake_id = self._ensure_lake_exists(
            conn, tournament.lake_name, tournament.google_maps_iframe
        )
        ramp_id = self._ensure_ramp_exists(
            conn, lake_id, tournament.ramp_name, tournament.google_maps_iframe
        )

        # Create event
        event_id = self._create_event(conn, tournament)

        # Create tournament with lake and ramp IDs
        tournament_id = self._create_tournament(conn, tournament, event_id, lake_id, ramp_id)

        # Import results
        for result in tournament.results:
            angler_id = self._ensure_angler_exists(conn, result.angler_name)
            self._create_result(conn, tournament_id, angler_id, result)

        # Import team results
        for team_result in tournament.team_results:
            angler1_id = self._ensure_angler_exists(conn, team_result.angler1_name)
            angler2_id = self._ensure_angler_exists(conn, team_result.angler2_name)
            self._create_team_result(conn, tournament_id, angler1_id, angler2_id, team_result)

    def _create_event(self, conn, tournament: Tournament) -> int:
        """Create event record."""
        # Parse time strings to time objects if provided
        start_time = None
        weigh_in_time = None

        if tournament.start_time:
            try:
                # Try parsing formats like "7 a.m." or "7:00 a.m." or "06:30"
                time_str = tournament.start_time.replace(".", "").strip()
                if "am" in time_str.lower() or "pm" in time_str.lower():
                    # Handle AM/PM format - normalize the string
                    time_str = (
                        time_str.lower()
                        .replace("am", " am")
                        .replace("pm", " pm")
                        .replace("  ", " ")
                        .strip()
                    )
                    from datetime import datetime as dt

                    # Try different formats
                    for fmt in ["%I:%M %p", "%I %p", "%I:%M%p", "%I%p"]:
                        try:
                            parsed = dt.strptime(time_str, fmt)
                            start_time = parsed.strftime("%H:%M:00")
                            break
                        except ValueError:
                            continue
                elif ":" in time_str:
                    # Already in 24-hour format
                    parts = time_str.split(":")
                    if len(parts) == 2:
                        start_time = f"{parts[0].zfill(2)}:{parts[1].zfill(2)}:00"
            except Exception as e:
                logger.debug(f"Could not parse start time '{tournament.start_time}': {e}")

        if tournament.weigh_in_time:
            try:
                time_str = tournament.weigh_in_time.replace(".", "").strip()
                if "am" in time_str.lower() or "pm" in time_str.lower():
                    time_str = (
                        time_str.lower()
                        .replace("am", " am")
                        .replace("pm", " pm")
                        .replace("  ", " ")
                        .strip()
                    )
                    from datetime import datetime as dt

                    for fmt in ["%I:%M %p", "%I %p", "%I:%M%p", "%I%p"]:
                        try:
                            parsed = dt.strptime(time_str, fmt)
                            weigh_in_time = parsed.strftime("%H:%M:00")
                            break
                        except ValueError:
                            continue
                elif ":" in time_str:
                    parts = time_str.split(":")
                    if len(parts) == 2:
                        weigh_in_time = f"{parts[0].zfill(2)}:{parts[1].zfill(2)}:00"
            except Exception as e:
                logger.debug(f"Could not parse weigh-in time '{tournament.weigh_in_time}': {e}")

        event_data = {
            "date": tournament.date.date(),
            "year": tournament.year,
            "name": tournament.name,
            "event_type": "sabc_tournament",
            "lake_name": tournament.lake_name,
            "ramp_name": tournament.ramp_name,
            "entry_fee": tournament.entry_fee,
            "start_time": start_time,
            "weigh_in_time": weigh_in_time,
        }

        if self.dry_run:
            self.import_data["events"].append(event_data)
            return len(self.import_data["events"])

        # Check if event already exists
        existing = conn.execute(
            text("SELECT id FROM events WHERE date = :date"), {"date": event_data["date"]}
        ).fetchone()

        if existing:
            return existing[0]

        result = conn.execute(
            text("""
                INSERT INTO events (date, year, name, event_type, lake_name, ramp_name, entry_fee, start_time, weigh_in_time)
                VALUES (:date, :year, :name, :event_type, :lake_name, :ramp_name, :entry_fee, :start_time, :weigh_in_time)
                RETURNING id
            """),
            event_data,
        )
        conn.commit()
        return result.scalar()

    def _ensure_lake_exists(self, conn, lake_name: str, google_maps_iframe: Optional[str]) -> int:
        """Ensure lake exists in database, create if needed."""
        if not lake_name or lake_name == "Unknown Lake":
            return 1  # Return default lake ID

        # Check cache first
        if lake_name in self.lake_cache:
            return self.lake_cache[lake_name]

        if self.dry_run:
            # Check if we already have this lake in dry-run data
            for i, lake in enumerate(self.import_data["lakes"]):
                if lake["display_name"] == lake_name:
                    return i + 1

            # Add new lake to dry-run data
            lake_data = {
                "yaml_key": lake_name.lower().replace(" ", "_"),
                "display_name": lake_name,
                "google_maps_iframe": google_maps_iframe,
            }
            self.import_data["lakes"].append(lake_data)
            lake_id = len(self.import_data["lakes"])
            self.lake_cache[lake_name] = lake_id
            return lake_id

        # Check if lake exists in database
        existing = conn.execute(
            text("SELECT id FROM lakes WHERE yaml_key = :yaml_key OR display_name = :display_name"),
            {"yaml_key": lake_name.lower().replace(" ", "_"), "display_name": lake_name},
        ).fetchone()

        if existing:
            lake_id = existing[0]
            self.lake_cache[lake_name] = lake_id

            # Update google_maps_iframe if we have one and it's not set
            if google_maps_iframe:
                conn.execute(
                    text(
                        "UPDATE lakes SET google_maps_iframe = :iframe WHERE id = :id AND google_maps_iframe IS NULL"
                    ),
                    {"iframe": google_maps_iframe, "id": lake_id},
                )
                conn.commit()

            return lake_id

        # Create new lake
        lake_data = {
            "yaml_key": lake_name.lower().replace(" ", "_"),
            "display_name": lake_name,
            "google_maps_iframe": google_maps_iframe,
        }

        result = conn.execute(
            text("""
                INSERT INTO lakes (yaml_key, display_name, google_maps_iframe)
                VALUES (:yaml_key, :display_name, :google_maps_iframe)
                RETURNING id
            """),
            lake_data,
        )
        conn.commit()
        lake_id = result.scalar()
        self.lake_cache[lake_name] = lake_id
        return lake_id

    def _ensure_ramp_exists(
        self, conn, lake_id: int, ramp_name: Optional[str], google_maps_iframe: Optional[str]
    ) -> int:
        """Ensure ramp exists in database, create if needed."""
        if not ramp_name or ramp_name == "Unknown Ramp":
            return 1  # Return default ramp ID

        # Check cache first
        cache_key = (str(lake_id), ramp_name)
        if cache_key in self.ramp_cache:
            return self.ramp_cache[cache_key]

        if self.dry_run:
            # Check if we already have this ramp in dry-run data
            for i, ramp in enumerate(self.import_data["ramps"]):
                if ramp["lake_id"] == lake_id and ramp["name"] == ramp_name:
                    return i + 1

            # Add new ramp to dry-run data
            ramp_data = {
                "lake_id": lake_id,
                "name": ramp_name,
                "google_maps_iframe": google_maps_iframe,
            }
            self.import_data["ramps"].append(ramp_data)
            ramp_id = len(self.import_data["ramps"])
            self.ramp_cache[cache_key] = ramp_id
            return ramp_id

        # Check if ramp exists in database
        existing = conn.execute(
            text("SELECT id FROM ramps WHERE lake_id = :lake_id AND name = :name"),
            {"lake_id": lake_id, "name": ramp_name},
        ).fetchone()

        if existing:
            ramp_id = existing[0]
            self.ramp_cache[cache_key] = ramp_id

            # Update google_maps_iframe if we have one and it's not set
            if google_maps_iframe:
                conn.execute(
                    text(
                        "UPDATE ramps SET google_maps_iframe = :iframe WHERE id = :id AND google_maps_iframe IS NULL"
                    ),
                    {"iframe": google_maps_iframe, "id": ramp_id},
                )
                conn.commit()

            return ramp_id

        # Create new ramp
        ramp_data = {
            "lake_id": lake_id,
            "name": ramp_name,
            "google_maps_iframe": google_maps_iframe,
        }

        result = conn.execute(
            text("""
                INSERT INTO ramps (lake_id, name, google_maps_iframe)
                VALUES (:lake_id, :name, :google_maps_iframe)
                RETURNING id
            """),
            ramp_data,
        )
        conn.commit()
        ramp_id = result.scalar()
        self.ramp_cache[cache_key] = ramp_id
        return ramp_id

    def _create_tournament(
        self, conn, tournament: Tournament, event_id: int, lake_id: int, ramp_id: int
    ) -> int:
        """Create tournament record."""
        # Parse time strings for tournament table
        start_time = None
        end_time = None

        if tournament.start_time:
            try:
                time_str = tournament.start_time.replace(".", "").strip()
                if "am" in time_str.lower() or "pm" in time_str.lower():
                    time_str = (
                        time_str.lower()
                        .replace("am", " am")
                        .replace("pm", " pm")
                        .replace("  ", " ")
                        .strip()
                    )
                    from datetime import datetime as dt

                    for fmt in ["%I:%M %p", "%I %p", "%I:%M%p", "%I%p"]:
                        try:
                            parsed = dt.strptime(time_str, fmt)
                            start_time = parsed.strftime("%H:%M:00")
                            break
                        except ValueError:
                            continue
                elif ":" in time_str:
                    parts = time_str.split(":")
                    if len(parts) == 2:
                        start_time = f"{parts[0].zfill(2)}:{parts[1].zfill(2)}:00"
            except Exception:
                pass

        if tournament.weigh_in_time:
            try:
                time_str = tournament.weigh_in_time.replace(".", "").strip()
                if "am" in time_str.lower() or "pm" in time_str.lower():
                    time_str = (
                        time_str.lower()
                        .replace("am", " am")
                        .replace("pm", " pm")
                        .replace("  ", " ")
                        .strip()
                    )
                    from datetime import datetime as dt

                    for fmt in ["%I:%M %p", "%I %p", "%I:%M%p", "%I%p"]:
                        try:
                            parsed = dt.strptime(time_str, fmt)
                            end_time = parsed.strftime("%H:%M:00")
                            break
                        except ValueError:
                            continue
                elif ":" in time_str:
                    parts = time_str.split(":")
                    if len(parts) == 2:
                        end_time = f"{parts[0].zfill(2)}:{parts[1].zfill(2)}:00"
            except Exception:
                pass

        tournament_data = {
            "event_id": event_id,
            "name": tournament.name,
            "lake_id": lake_id,
            "ramp_id": ramp_id,
            "lake_name": tournament.lake_name,
            "ramp_name": tournament.ramp_name,
            "fish_limit": tournament.fish_limit,
            "entry_fee": tournament.entry_fee,
            "is_team": tournament.is_team,
            "complete": True,
            "start_time": start_time,
            "end_time": end_time,
        }

        if self.dry_run:
            self.import_data["tournaments"].append(tournament_data)
            return len(self.import_data["tournaments"])

        # Check if tournament already exists
        existing = conn.execute(
            text("SELECT id FROM tournaments WHERE event_id = :event_id"), {"event_id": event_id}
        ).fetchone()

        if existing:
            return existing[0]

        result = conn.execute(
            text("""
                INSERT INTO tournaments (event_id, name, lake_id, ramp_id, lake_name, ramp_name, fish_limit, entry_fee, is_team, complete, start_time, end_time)
                VALUES (:event_id, :name, :lake_id, :ramp_id, :lake_name, :ramp_name, :fish_limit, :entry_fee, :is_team, :complete, :start_time, :end_time)
                RETURNING id
            """),
            tournament_data,
        )
        conn.commit()
        return result.scalar()

    def _ensure_angler_exists(self, conn, angler_name: str) -> int:
        """Ensure angler exists in database, create if needed."""
        if self.dry_run:
            # In dry-run mode, check if angler is already in our dry-run data
            for i, angler in enumerate(self.import_data["anglers"]):
                if angler["name"] == angler_name:
                    return i + 1

            # Add new angler to dry-run data
            angler_data = {
                "name": angler_name,
                "member": True,  # Assume all imported anglers are members
                "email": f"{angler_name.lower().replace(' ', '.')}@example.com",
            }
            self.import_data["anglers"].append(angler_data)
            return len(self.import_data["anglers"])

        # Check if angler exists in database
        existing = conn.execute(
            text("SELECT id FROM anglers WHERE name = :name"), {"name": angler_name}
        ).fetchone()

        if existing:
            return existing[0]

        # Create new angler
        angler_data = {
            "name": angler_name,
            "member": True,  # Assume all imported anglers are members
            "email": f"{angler_name.lower().replace(' ', '.')}@example.com",
        }

        result = conn.execute(
            text("""
                INSERT INTO anglers (name, member, email)
                VALUES (:name, :member, :email)
                RETURNING id
            """),
            angler_data,
        )
        conn.commit()
        return result.scalar()

    def _create_result(
        self, conn, tournament_id: int, angler_id: int, result: TournamentResult
    ) -> None:
        """Create result record."""
        result_data = {
            "tournament_id": tournament_id,
            "angler_id": angler_id,
            "num_fish": result.num_fish,
            "total_weight": result.total_weight,
            "big_bass_weight": result.big_bass_weight,
            "dead_fish_penalty": result.dead_fish_penalty,
            "disqualified": result.disqualified,
            "buy_in": result.buy_in,
            "place_finish": None,  # Will be calculated after all results are imported
            "points": 0,  # Will be calculated after all results are imported
        }

        if self.dry_run:
            result_data["angler_name"] = result.angler_name
            self.import_data["results"].append(result_data)
            return

        # Check if result already exists
        existing = conn.execute(
            text(
                "SELECT id FROM results WHERE tournament_id = :tournament_id AND angler_id = :angler_id"
            ),
            {"tournament_id": tournament_id, "angler_id": angler_id},
        ).fetchone()

        if existing:
            # Update existing result
            conn.execute(
                text("""
                    UPDATE results SET
                        num_fish = :num_fish,
                        total_weight = :total_weight,
                        big_bass_weight = :big_bass_weight,
                        dead_fish_penalty = :dead_fish_penalty,
                        disqualified = :disqualified,
                        buy_in = :buy_in,
                        place_finish = :place_finish,
                        points = :points
                    WHERE tournament_id = :tournament_id AND angler_id = :angler_id
                """),
                result_data,
            )
        else:
            # Insert new result
            conn.execute(
                text("""
                    INSERT INTO results (tournament_id, angler_id, num_fish, total_weight, big_bass_weight,
                                       dead_fish_penalty, disqualified, buy_in, place_finish, points)
                    VALUES (:tournament_id, :angler_id, :num_fish, :total_weight, :big_bass_weight,
                           :dead_fish_penalty, :disqualified, :buy_in, :place_finish, :points)
                """),
                result_data,
            )
        conn.commit()

    def _create_team_result(
        self, conn, tournament_id: int, angler1_id: int, angler2_id: int, team_result: TeamResult
    ) -> None:
        """Create team result record."""
        team_data = {
            "tournament_id": tournament_id,
            "angler1_id": angler1_id,
            "angler2_id": angler2_id,
            "total_weight": team_result.total_weight,
            "place_finish": team_result.place_finish,
        }

        if self.dry_run:
            team_data["angler1_name"] = team_result.angler1_name
            team_data["angler2_name"] = team_result.angler2_name
            self.import_data["team_results"].append(team_data)
            return

        # Check if team result already exists
        existing = conn.execute(
            text("""
                SELECT id FROM team_results
                WHERE tournament_id = :tournament_id
                AND ((angler1_id = :angler1_id AND angler2_id = :angler2_id)
                     OR (angler1_id = :angler2_id AND angler2_id = :angler1_id))
            """),
            {"tournament_id": tournament_id, "angler1_id": angler1_id, "angler2_id": angler2_id},
        ).fetchone()

        if not existing:
            conn.execute(
                text("""
                    INSERT INTO team_results (tournament_id, angler1_id, angler2_id, total_weight, place_finish)
                    VALUES (:tournament_id, :angler1_id, :angler2_id, :total_weight, :place_finish)
                """),
                team_data,
            )
            conn.commit()


def main() -> None:
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Import tournament results from reference site",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python ingest_results.py 2022 --dry-run    # Show what would be imported for 2022
  python ingest_results.py 2023              # Import 2023 tournaments to database
  python ingest_results.py 2024 -v           # Import 2024 with verbose logging

This script will:
1. Scrape tournament data from the reference site for the specified year
2. Create angler records for any new participants
3. Create event and tournament records
4. Import individual and team results with proper scoring

The script follows the SABC database schema and type safety requirements.
        """,
    )
    parser.add_argument(
        "year", type=int, help="Year to import tournaments for (e.g., 2022, 2023, 2024)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print results as JSON instead of importing to database",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Validate year
    current_year = datetime.now().year
    if args.year < 2020 or args.year > current_year:
        logger.error(f"Year must be between 2020 and {current_year}")
        sys.exit(1)

    logger.info(f"Starting tournament import for year {args.year}")

    try:
        # Initialize scraper and importer
        scraper = TournamentScraper()
        importer = DatabaseImporter(dry_run=args.dry_run)

        # Scrape tournaments for the year
        logger.info(f"Scraping tournaments for {args.year}")
        tournaments = scraper.get_tournaments_for_year(args.year)

        if not tournaments:
            logger.warning(f"No tournaments found for {args.year}")
            sys.exit(0)

        logger.info(f"Found {len(tournaments)} tournaments")

        # Import tournaments
        if args.dry_run:
            logger.info("Running in dry-run mode - outputting JSON")
        else:
            logger.info("Importing tournaments to database")
            # Test database connection before proceeding
            try:
                with engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
            except Exception as db_error:
                logger.error(f"Database connection failed: {db_error}")
                logger.error("Please check your DATABASE_URL environment variable")
                sys.exit(1)

        importer.import_tournaments(tournaments)

        if not args.dry_run:
            logger.info(f"Successfully imported {len(tournaments)} tournaments for {args.year}")

    except KeyboardInterrupt:
        logger.info("Import cancelled by user")
        sys.exit(1)
    except requests.RequestException as e:
        logger.error(f"Network error while scraping: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Import failed: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
