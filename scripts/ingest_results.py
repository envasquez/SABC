#!/usr/bin/env python3
"""
Tournament results ingestion script for SABC.

This script scrapes tournament data from http://167.71.20.3 and imports essential data:
- Angler names
- Tournament info (name, date, lake)
- Results (weight, big bass, penalties)

Clears existing tournament data for the specified year before importing.
"""

import argparse
import logging
import re
import sys
from datetime import datetime
from typing import Dict, List, Optional

import requests  # type: ignore
from bs4 import BeautifulSoup  # type: ignore
from sqlalchemy import text

from core.db_schema import engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

REFERENCE_SITE = "http://167.71.20.3"


class TournamentResult:
    def __init__(
        self,
        angler_name: str,
        total_weight: float,
        big_bass_weight: float = 0.0,
        dead_fish_penalty: float = 0.0,
        place_finish: Optional[int] = None,
    ):
        self.angler_name = angler_name
        self.total_weight = total_weight
        self.big_bass_weight = big_bass_weight
        self.dead_fish_penalty = dead_fish_penalty
        self.place_finish = place_finish


class TeamResult:
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
    def __init__(self, name: str, date: datetime, lake_name: str):
        self.name = name
        self.date = date
        self.lake_name = lake_name
        self.results: List[TournamentResult] = []
        self.team_results: List[TeamResult] = []
        # Additional tournament metadata
        self.ramp_name: Optional[str] = None
        self.start_time: Optional[str] = None
        self.weigh_in_time: Optional[str] = None
        self.google_maps_iframe: Optional[str] = None
        self.description: Optional[str] = None
        self.entry_fee: float = 25.00
        self.fish_limit: int = 5
        self.is_team: bool = True


class TournamentScraper:
    def __init__(self, base_url: str = REFERENCE_SITE):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0 (SABC Tournament Importer)"})

    def get_tournaments_for_year(self, year: int) -> List[Tournament]:
        tournaments: List[Tournament] = []
        tournament_ids: set[int] = set()

        # Scrape all pages to find tournaments
        for page in range(1, 16):
            try:
                page_url = f"{self.base_url}/?page={page}"
                logger.debug(f"Scraping page {page}: {page_url}")
                response = self.session.get(page_url)
                response.raise_for_status()

                soup = BeautifulSoup(response.content, "html.parser")

                # Find tournament links
                for link in soup.find_all("a", class_="article-title"):
                    href = link.get("href", "")
                    text = link.get_text(strip=True)

                    # Look for tournament links with year
                    match = re.match(r"/tournament/(\d+)/", href)
                    if match and "Event #" in text and str(year) in text:
                        tournament_id = int(match.group(1))

                        if tournament_id in tournament_ids:
                            continue

                        tournament_ids.add(tournament_id)

                        tournament = self._scrape_tournament_page(tournament_id, text, year)
                        if tournament:
                            tournaments.append(tournament)
                            logger.info(
                                f"Found tournament: {tournament.name} on {tournament.date.date()}"
                            )

            except requests.RequestException as e:
                logger.warning(f"Could not fetch page {page}: {e}")
                continue

        tournaments.sort(key=lambda t: t.date)
        logger.info(f"Found {len(tournaments)} tournaments for {year}")
        return tournaments

    def _scrape_tournament_page(
        self, tournament_id: int, title: str, year: int
    ) -> Optional[Tournament]:
        try:
            url = f"{self.base_url}/tournament/{tournament_id}/"
            logger.debug(f"Scraping tournament page: {url}")
            response = self.session.get(url)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")

            # Extract date from title
            date_match = re.search(r"on\s+([A-Za-z]+\.?\s+\d+,\s+\d{4})", title)
            tournament_date = datetime(year, 1, 1)

            if date_match:
                date_str = date_match.group(1)
                try:
                    tournament_date = datetime.strptime(date_str, "%b. %d, %Y")
                except ValueError:
                    try:
                        tournament_date = datetime.strptime(date_str, "%b %d, %Y")
                    except ValueError:
                        # If date parsing fails, use a unique fallback based on tournament_id
                        import calendar

                        month_name = title.split()[0].lower()
                        month_num = 1
                        for i, name in enumerate(calendar.month_name[1:], 1):
                            if name.lower().startswith(month_name):
                                month_num = i
                                break
                        tournament_date = datetime(year, month_num, min(tournament_id, 28))
            else:
                # Use month from title and tournament_id as day
                import calendar

                month_name = title.split()[0].lower()
                month_num = 1
                for i, name in enumerate(calendar.month_name[1:], 1):
                    if name.lower().startswith(month_name):
                        month_num = i
                        break
                tournament_date = datetime(year, month_num, min(tournament_id, 28))

            # Extract tournament name and lake
            tournament_name = (
                re.match(r"([^o]+)(?:\s+on\s+)?", title).group(1).strip()
                if re.match(r"([^o]+)(?:\s+on\s+)?", title)
                else title
            )

            lake_name = "Unknown Lake"
            for h2 in soup.find_all("h2"):
                h2_text = h2.get_text(strip=True)
                if "LAKE" in h2_text.upper():
                    lake_name = h2_text.replace(" - RESULTS", "").replace("-RESULTS", "").strip()
                    break

            tournament = Tournament(
                name=tournament_name,
                date=tournament_date,
                lake_name=lake_name,
            )

            # Extract additional tournament metadata
            self._extract_tournament_metadata(soup, tournament)

            # Scrape individual results
            tournament.results = self._scrape_individual_results(soup)

            # Scrape team results
            tournament.team_results = self._scrape_team_results(soup)

            return tournament

        except Exception as e:
            logger.warning(f"Failed to scrape tournament {tournament_id}: {e}")
            return None

    def _scrape_individual_results(self, soup: BeautifulSoup) -> List[TournamentResult]:
        results: List[TournamentResult] = []

        # Find the individual results table
        for table in soup.find_all("table", class_="table"):
            headers = [th.get_text(strip=True).lower() for th in table.find_all("th")]

            # Check if this is the individual results table
            if "place finish" in headers and "first name" in headers and "last name" in headers:
                header_indices = {header: i for i, header in enumerate(headers)}

                for row in table.find_all("tr")[1:]:  # Skip header row
                    cells = row.find_all("td")
                    if len(cells) < 3:
                        continue

                    try:
                        # Extract place
                        place_text = cells[header_indices.get("place finish", 0)].get_text(
                            strip=True
                        )
                        place = int(place_text) if place_text.isdigit() else None

                        # Extract name
                        first_name = cells[header_indices.get("first name", 1)].get_text(strip=True)
                        last_name = cells[header_indices.get("last name", 2)].get_text(strip=True)

                        if not first_name and not last_name:
                            continue

                        angler_name = f"{first_name} {last_name}".strip()

                        # Extract weight data
                        total_weight = 0.0
                        big_bass = 0.0
                        penalty = 0.0

                        # Look for weight columns
                        for key in ["total weight", "total wt", "weight", "wt"]:
                            if key in header_indices and "bass" not in key:
                                cell_text = cells[header_indices[key]].get_text(strip=True)
                                try:
                                    total_weight = float(cell_text)
                                    break
                                except ValueError:
                                    pass

                        # Look for big bass columns
                        for key in ["big bass", "big bass weight", "big bass wt", "bb"]:
                            if key in header_indices:
                                cell_text = cells[header_indices[key]].get_text(strip=True)
                                try:
                                    big_bass = float(cell_text)
                                    break
                                except ValueError:
                                    pass

                        # Look for penalty columns
                        for key in ["penalty", "dead fish", "dead fish penalty"]:
                            if key in header_indices:
                                cell_text = cells[header_indices[key]].get_text(strip=True)
                                try:
                                    penalty = float(cell_text)
                                    break
                                except ValueError:
                                    pass

                        result = TournamentResult(
                            angler_name=angler_name,
                            total_weight=total_weight,
                            big_bass_weight=big_bass,
                            dead_fish_penalty=penalty,
                            place_finish=place,
                        )
                        results.append(result)

                    except Exception as e:
                        logger.debug(f"Failed to parse result row: {e}")
                        continue

                break

        return results

    def _scrape_team_results(self, soup: BeautifulSoup) -> List[TeamResult]:
        """Scrape team results from tournament page."""
        team_results: List[TeamResult] = []

        # Find the team results table
        for table in soup.find_all("table", class_="table"):
            headers = [th.get_text(strip=True).lower() for th in table.find_all("th")]

            # Check if this is the team results table
            # Look for team-specific headers like "team place", "partner", or multiple angler columns
            is_team_table = (
                "team place" in headers
                or "team" in " ".join(headers)
                or ("angler 1" in headers and "angler 2" in headers)
                or ("partner" in headers)
            )

            if is_team_table:
                logger.debug(f"Found team results table with headers: {headers}")
                header_indices = {header: i for i, header in enumerate(headers)}

                for row_idx, row in enumerate(table.find_all("tr")[1:]):  # Skip header row
                    cells = row.find_all("td")
                    if len(cells) < 3:
                        continue

                    # Debug: Log first few rows
                    if row_idx < 3:
                        cell_texts = [cell.get_text(strip=True) for cell in cells]
                        logger.debug(f"Team table row {row_idx}: {cell_texts}")

                    try:
                        # Extract team place
                        place = None
                        for place_key in ["team place", "place", "team finish", "finish"]:
                            if place_key in header_indices:
                                place_text = cells[header_indices[place_key]].get_text(strip=True)
                                if place_text.isdigit():
                                    place = int(place_text)
                                    break

                        # Extract angler names
                        angler1_name = ""
                        angler2_name = ""

                        # Method 1: Separate angler columns
                        if "angler 1" in header_indices and "angler 2" in header_indices:
                            angler1_name = cells[header_indices["angler 1"]].get_text(strip=True)
                            angler2_name = cells[header_indices["angler 2"]].get_text(strip=True)
                        # Method 2: Combined name column with separator
                        elif "team" in header_indices or "team name" in header_indices:
                            team_key = "team name" if "team name" in header_indices else "team"
                            team_text = cells[header_indices[team_key]].get_text(strip=True)
                            logger.debug(f"Processing team text: '{team_text}'")
                            # Try various separators
                            for sep in [" / ", " & ", " and ", " - ", "/", "&", " + "]:
                                if sep in team_text:
                                    parts = team_text.split(sep, 1)
                                    angler1_name = parts[0].strip()
                                    angler2_name = parts[1].strip() if len(parts) > 1 else ""
                                    logger.debug(
                                        f"Split team '{team_text}' with '{sep}' into: '{angler1_name}' and '{angler2_name}'"
                                    )
                                    break
                            else:
                                # If no separator found, try looking for common patterns
                                # Like "FirstName LastName SecondFirstName SecondLastName"
                                parts = team_text.split()
                                if len(parts) >= 4:
                                    # Assume first two words are first angler, last two are second
                                    angler1_name = f"{parts[0]} {parts[1]}"
                                    angler2_name = f"{parts[-2]} {parts[-1]}"
                                    logger.debug(
                                        f"Split team '{team_text}' by word count into: '{angler1_name}' and '{angler2_name}'"
                                    )
                        # Method 3: First/Last name pairs
                        elif "first name" in header_indices and "last name" in header_indices:
                            # This might be individual results, not team - skip
                            continue
                        # Method 4: Partner column approach
                        elif "partner" in header_indices:
                            # Look for angler name in another column
                            for name_key in ["angler", "name", "first name"]:
                                if name_key in header_indices:
                                    angler1_name = cells[header_indices[name_key]].get_text(
                                        strip=True
                                    )
                                    break
                            angler2_name = cells[header_indices["partner"]].get_text(strip=True)

                        # Skip if we don't have both anglers
                        if not angler1_name or not angler2_name:
                            continue

                        # Extract team weight
                        total_weight = 0.0
                        for weight_key in [
                            "total weight",
                            "team weight",
                            "weight",
                            "total",
                            "team total",
                        ]:
                            if weight_key in header_indices:
                                weight_text = cells[header_indices[weight_key]].get_text(strip=True)
                                try:
                                    total_weight = float(weight_text)
                                    break
                                except ValueError:
                                    pass

                        team_result = TeamResult(
                            angler1_name=angler1_name,
                            angler2_name=angler2_name,
                            total_weight=total_weight,
                            place_finish=place,
                        )
                        team_results.append(team_result)
                        logger.debug(
                            f"Found team: {angler1_name} & {angler2_name} - {total_weight}lbs"
                        )

                    except Exception as e:
                        logger.debug(f"Failed to parse team result row: {e}")
                        continue

                # If we found team results in this table, break
                if team_results:
                    break

        logger.info(f"Found {len(team_results)} team results")
        return team_results

    def _extract_tournament_metadata(self, soup: BeautifulSoup, tournament: Tournament) -> None:
        """Extract additional tournament metadata from the page."""

        # Extract Google Maps iframe
        iframe = soup.find("iframe", src=re.compile(r"google\.com/maps"))
        if iframe:
            tournament.google_maps_iframe = iframe.get("src", "")
            logger.debug(f"Found Google Maps iframe: {tournament.google_maps_iframe[:100]}...")

        # Extract timing information from the tournament details table
        for table in soup.find_all("table", class_="table"):
            rows = table.find_all("tr")
            for row in rows:
                cells = row.find_all("td")
                if len(cells) >= 6:  # Table with Date, Start time, Weigh-in format
                    cell_texts = [cell.get_text(strip=True) for cell in cells]

                    # Look for start time and weigh-in time
                    for i, cell_text in enumerate(cell_texts):
                        if "start time" in cell_text.lower() and i + 1 < len(cell_texts):
                            start_time_text = cell_texts[i + 1]
                            tournament.start_time = self._parse_time(start_time_text)
                            logger.debug(
                                f"Found start time: {start_time_text} -> {tournament.start_time}"
                            )

                        elif "weigh-in" in cell_text.lower() and i + 1 < len(cell_texts):
                            weigh_in_text = cell_texts[i + 1]
                            tournament.weigh_in_time = self._parse_time(weigh_in_text)
                            logger.debug(
                                f"Found weigh-in time: {weigh_in_text} -> {tournament.weigh_in_time}"
                            )

        # Try to extract ramp name from Google Maps iframe URL or page content
        if tournament.google_maps_iframe:
            tournament.ramp_name = self._extract_ramp_name_from_iframe(
                tournament.google_maps_iframe
            )

        # Set defaults based on tournament characteristics
        tournament.is_team = len(tournament.team_results) > 0 or "team" in tournament.name.lower()

        logger.debug(
            f"Tournament metadata: ramp={tournament.ramp_name}, start={tournament.start_time}, weigh_in={tournament.weigh_in_time}"
        )

    def _parse_time(self, time_text: str) -> Optional[str]:
        """Parse time text into HH:MM format."""
        if not time_text:
            return None

        # Clean up common time formats
        time_text = time_text.lower().strip()

        # Handle formats like "6 a.m.", "3 p.m.", "6:00 AM", etc.
        time_patterns = [
            r"(\d{1,2}):(\d{2})\s*([ap])\.?m\.?",  # 6:00 a.m.
            r"(\d{1,2})\s*([ap])\.?m\.?",  # 6 a.m.
        ]

        for pattern in time_patterns:
            match = re.search(pattern, time_text)
            if match:
                if len(match.groups()) == 3:  # Has minutes
                    hour, minute, ampm = match.groups()
                    hour = int(hour)
                    minute = int(minute)
                else:  # No minutes
                    hour = int(match.group(1))
                    minute = 0
                    ampm = match.group(2)

                # Convert to 24-hour format
                if ampm == "p" and hour != 12:
                    hour += 12
                elif ampm == "a" and hour == 12:
                    hour = 0

                return f"{hour:02d}:{minute:02d}"

        return None

    def _extract_ramp_name_from_iframe(self, iframe_url: str) -> Optional[str]:
        """Extract ramp name from Google Maps iframe URL."""
        try:
            # Try to decode the ramp name from the iframe URL
            # Google Maps URLs often contain the place name
            if "!1s" in iframe_url:
                # Format: !1s0x865b34da5ad510af%3A0xc87465991d57c4da!2sLoop%20360%20Boat%20Ramp
                parts = iframe_url.split("!2s")
                if len(parts) > 1:
                    ramp_part = parts[1].split("!")[0]
                    # URL decode
                    import urllib.parse

                    ramp_name = urllib.parse.unquote(ramp_part)
                    logger.debug(f"Extracted ramp name from iframe: {ramp_name}")
                    return ramp_name

        except Exception as e:
            logger.debug(f"Failed to extract ramp name from iframe: {e}")

        return None


class DatabaseImporter:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self._lake_cache: Optional[Dict[str, int]] = None
        self._ramp_cache: Optional[Dict[str, int]] = None

    def clear_existing_data(self, year: Optional[int] = None) -> None:
        """Clear existing tournament data for a specific year or all data."""
        if self.dry_run:
            if year:
                logger.info(f"DRY RUN: Would clear existing tournament data for year {year}")
            else:
                logger.info("DRY RUN: Would clear ALL existing tournament and angler data")
            return

        if year:
            logger.info(f"Clearing existing tournament data for year {year}...")

            with engine.connect() as conn:
                # Get event IDs for the specified year
                event_ids = conn.execute(
                    text("SELECT id FROM events WHERE year = :year"), {"year": year}
                ).fetchall()

                if event_ids:
                    event_id_list = [e[0] for e in event_ids]

                    # Get tournament IDs for these events
                    tournament_ids = conn.execute(
                        text("SELECT id FROM tournaments WHERE event_id = ANY(:event_ids)"),
                        {"event_ids": event_id_list},
                    ).fetchall()

                    if tournament_ids:
                        tournament_id_list = [t[0] for t in tournament_ids]

                        # Delete results for these tournaments
                        conn.execute(
                            text("DELETE FROM results WHERE tournament_id = ANY(:tournament_ids)"),
                            {"tournament_ids": tournament_id_list},
                        )
                        conn.execute(
                            text(
                                "DELETE FROM team_results WHERE tournament_id = ANY(:tournament_ids)"
                            ),
                            {"tournament_ids": tournament_id_list},
                        )

                    # Delete tournaments and events for this year
                    conn.execute(
                        text("DELETE FROM tournaments WHERE event_id = ANY(:event_ids)"),
                        {"event_ids": event_id_list},
                    )
                    conn.execute(text("DELETE FROM events WHERE year = :year"), {"year": year})

                    conn.commit()
                    logger.info(f"Cleared {len(event_ids)} events and related data for year {year}")
                else:
                    logger.info(f"No events found for year {year}")
        else:
            logger.info("Clearing ALL existing tournament and angler data...")

            with engine.connect() as conn:
                # Clear in proper order due to foreign keys
                conn.execute(text("DELETE FROM results"))
                conn.execute(text("DELETE FROM team_results"))
                conn.execute(text("DELETE FROM tournaments"))
                conn.execute(text("DELETE FROM events"))
                conn.execute(text("DELETE FROM anglers"))
                conn.commit()

            logger.info("All existing data cleared")

    def import_tournaments(self, tournaments: List[Tournament]) -> None:
        """Import tournaments and all related data."""
        if self.dry_run:
            logger.info("DRY RUN: Tournament import preview:")
            for tournament in tournaments:
                print(
                    f"Tournament: {tournament.name} ({tournament.date.date()}) at {tournament.lake_name}"
                )
                print("  Metadata:")
                print(f"    Ramp: {tournament.ramp_name or 'Unknown'}")
                print(f"    Start time: {tournament.start_time or 'Unknown'}")
                print(f"    Weigh-in time: {tournament.weigh_in_time or 'Unknown'}")
                print(f"    Entry fee: ${tournament.entry_fee}")
                print(f"    Is team tournament: {tournament.is_team}")
                print(f"    Google Maps: {'Yes' if tournament.google_maps_iframe else 'No'}")
                print(f"  Individual Results ({len(tournament.results)}):")
                for result in tournament.results[:3]:  # Show first 3
                    print(
                        f"    {result.angler_name}: {result.total_weight}lbs, BB: {result.big_bass_weight}lbs"
                    )
                if len(tournament.results) > 3:
                    print(f"    ... and {len(tournament.results) - 3} more")
                print(f"  Team Results ({len(tournament.team_results)}):")
                for team_result in tournament.team_results[:3]:  # Show first 3
                    print(
                        f"    {team_result.angler1_name} & {team_result.angler2_name}: {team_result.total_weight}lbs"
                    )
                if len(tournament.team_results) > 3:
                    print(f"    ... and {len(tournament.team_results) - 3} more")
                print()
            return

        with engine.connect() as conn:
            for tournament in tournaments:
                self._import_single_tournament(conn, tournament)

    def _import_single_tournament(self, conn, tournament: Tournament) -> None:
        """Import a single tournament with all its data."""
        # Create event (handle date conflicts by adding tournament name to make unique)
        base_date = tournament.date.date()
        event_date = base_date

        # If date conflicts, find next available date
        attempt = 0
        while attempt < 30:  # Max 30 attempts
            existing = conn.execute(
                text("SELECT id FROM events WHERE date = :date"), {"date": event_date}
            ).fetchone()

            if not existing:
                break

            attempt += 1
            event_date = base_date.replace(day=min(base_date.day + attempt, 28))

        event_data = {
            "date": event_date,
            "year": tournament.date.year,
            "name": tournament.name,
            "event_type": "sabc_tournament",
            "lake_name": tournament.lake_name,
            "ramp_name": tournament.ramp_name,
            "start_time": tournament.start_time,
            "weigh_in_time": tournament.weigh_in_time,
            "entry_fee": tournament.entry_fee,
        }

        result = conn.execute(
            text("""
                INSERT INTO events (date, year, name, event_type, lake_name, ramp_name, start_time, weigh_in_time, entry_fee)
                VALUES (:date, :year, :name, :event_type, :lake_name, :ramp_name, :start_time, :weigh_in_time, :entry_fee)
                RETURNING id
            """),
            event_data,
        )
        event_id = result.scalar()

        # Look up lake and ramp IDs
        lake_id = self._find_lake_id(conn, tournament.lake_name)
        ramp_id = (
            self._find_ramp_id(conn, tournament.ramp_name, tournament.lake_name)
            if tournament.ramp_name
            else None
        )

        # Create tournament
        tournament_data = {
            "event_id": event_id,
            "name": tournament.name,
            "lake_id": lake_id,
            "ramp_id": ramp_id,
            "lake_name": tournament.lake_name,
            "ramp_name": tournament.ramp_name,
            "start_time": tournament.start_time,
            "end_time": tournament.weigh_in_time,  # Use weigh-in as end time
            "fish_limit": tournament.fish_limit,
            "entry_fee": tournament.entry_fee,
            "is_team": tournament.is_team,
            "complete": True,
        }

        result = conn.execute(
            text("""
                INSERT INTO tournaments (event_id, name, lake_id, ramp_id, lake_name, ramp_name,
                                       start_time, end_time, fish_limit, entry_fee, is_team, complete)
                VALUES (:event_id, :name, :lake_id, :ramp_id, :lake_name, :ramp_name,
                       :start_time, :end_time, :fish_limit, :entry_fee, :is_team, :complete)
                RETURNING id
            """),
            tournament_data,
        )
        tournament_id = result.scalar()

        # Import individual results
        for result_data in tournament.results:
            angler_id = self._ensure_angler_exists(conn, result_data.angler_name)
            self._create_result(conn, tournament_id, angler_id, result_data)

        # Import team results
        for team_result in tournament.team_results:
            angler1_id = self._ensure_angler_exists(conn, team_result.angler1_name)
            angler2_id = self._ensure_angler_exists(conn, team_result.angler2_name)
            self._create_team_result(conn, tournament_id, angler1_id, angler2_id, team_result)

        conn.commit()

    def _ensure_angler_exists(self, conn, angler_name: str) -> int:
        """Ensure angler exists in database, create if needed."""
        # Check if angler exists
        existing = conn.execute(
            text("SELECT id FROM anglers WHERE name = :name"), {"name": angler_name}
        ).fetchone()

        if existing:
            return existing[0]

        # Create new angler
        angler_data = {
            "name": angler_name,
            "member": True,
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
        return result.scalar()

    def _create_result(
        self, conn, tournament_id: int, angler_id: int, result: TournamentResult
    ) -> None:
        """Create result record."""
        result_data = {
            "tournament_id": tournament_id,
            "angler_id": angler_id,
            "total_weight": result.total_weight,
            "big_bass_weight": result.big_bass_weight,
            "dead_fish_penalty": result.dead_fish_penalty,
            "place_finish": result.place_finish,
        }

        conn.execute(
            text("""
                INSERT INTO results (tournament_id, angler_id, total_weight, big_bass_weight,
                                   dead_fish_penalty, place_finish)
                VALUES (:tournament_id, :angler_id, :total_weight, :big_bass_weight,
                       :dead_fish_penalty, :place_finish)
            """),
            result_data,
        )

    def _get_lake_cache(self, conn) -> Dict[str, int]:
        """Get cached lake name to ID mapping."""
        if self._lake_cache is None:
            self._lake_cache = {}
            lakes = conn.execute(text("SELECT id, yaml_key, display_name FROM lakes")).fetchall()
            for lake in lakes:
                lake_id, yaml_key, display_name = lake
                # Add both yaml_key and display_name as lookup keys
                self._lake_cache[yaml_key.lower()] = lake_id
                self._lake_cache[display_name.lower()] = lake_id
        return self._lake_cache

    def _get_ramp_cache(self, conn) -> Dict[str, int]:
        """Get cached ramp name to ID mapping."""
        if self._ramp_cache is None:
            self._ramp_cache = {}
            ramps = conn.execute(
                text(
                    "SELECT r.id, r.name, l.display_name FROM ramps r JOIN lakes l ON r.lake_id = l.id"
                )
            ).fetchall()
            for ramp in ramps:
                ramp_id, ramp_name, lake_name = ramp
                # Create composite key with lake name for uniqueness
                key = f"{ramp_name.lower()}@{lake_name.lower()}"
                self._ramp_cache[key] = ramp_id
                # Also add just the ramp name for fallback
                self._ramp_cache[ramp_name.lower()] = ramp_id
        return self._ramp_cache

    def _find_lake_id(self, conn, lake_name: str) -> Optional[int]:
        """Find lake ID by name with fuzzy matching."""
        if not lake_name:
            return None

        lake_cache = self._get_lake_cache(conn)
        lake_key = lake_name.lower().strip()

        # Direct match first
        if lake_key in lake_cache:
            return lake_cache[lake_key]

        # Try without common prefixes/suffixes
        cleaned_name = lake_key.replace("lake ", "").replace(" lake", "").strip()
        if cleaned_name in lake_cache:
            return lake_cache[cleaned_name]

        # Try fuzzy matching for common variations
        for db_name, db_id in lake_cache.items():
            if cleaned_name in db_name or db_name in cleaned_name:
                logger.debug(f"Fuzzy matched lake '{lake_name}' to '{db_name}' (ID: {db_id})")
                return db_id

        logger.warning(f"Could not find lake ID for: {lake_name}")
        return None

    def _find_ramp_id(self, conn, ramp_name: str, lake_name: str) -> Optional[int]:
        """Find ramp ID by name and lake with fuzzy matching."""
        if not ramp_name:
            return None

        ramp_cache = self._get_ramp_cache(conn)

        # Try with lake context first
        if lake_name:
            composite_key = f"{ramp_name.lower()}@{lake_name.lower()}"
            if composite_key in ramp_cache:
                return ramp_cache[composite_key]

        # Try just ramp name
        ramp_key = ramp_name.lower().strip()
        if ramp_key in ramp_cache:
            return ramp_cache[ramp_key]

        # Try fuzzy matching
        for db_key, db_id in ramp_cache.items():
            if "@" not in db_key:  # Skip composite keys for this check
                if ramp_key in db_key or db_key in ramp_key:
                    logger.debug(f"Fuzzy matched ramp '{ramp_name}' to '{db_key}' (ID: {db_id})")
                    return db_id

        logger.warning(f"Could not find ramp ID for: {ramp_name} at {lake_name}")
        return None

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

        conn.execute(
            text("""
                INSERT INTO team_results (tournament_id, angler1_id, angler2_id, total_weight, place_finish)
                VALUES (:tournament_id, :angler1_id, :angler2_id, :total_weight, :place_finish)
            """),
            team_data,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Import tournament results from reference site")
    parser.add_argument("year", type=int, help="Year to import tournaments for (e.g., 2023, 2024)")
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview import without writing to database"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument(
        "--clear-all",
        action="store_true",
        help="Clear ALL existing data before import (default: only clear specified year)",
    )

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
        scraper = TournamentScraper()
        importer = DatabaseImporter(dry_run=args.dry_run)

        # Clear existing data (unless dry run)
        if not args.dry_run:
            if args.clear_all:
                importer.clear_existing_data()  # Clear all data
            else:
                importer.clear_existing_data(year=args.year)  # Clear only this year's data

        # Scrape tournaments
        tournaments = scraper.get_tournaments_for_year(args.year)

        if not tournaments:
            logger.warning(f"No tournaments found for {args.year}")
            sys.exit(0)

        logger.info(f"Found {len(tournaments)} tournaments")

        # Import tournaments
        if args.dry_run:
            logger.info("Running in dry-run mode")
        else:
            logger.info("Importing tournaments to database")

        importer.import_tournaments(tournaments)

        if not args.dry_run:
            logger.info(f"Successfully imported {len(tournaments)} tournaments for {args.year}")

    except KeyboardInterrupt:
        logger.info("Import cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Import failed: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
