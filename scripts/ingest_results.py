#!/usr/bin/env python3
"""
Tournament results ingestion script for SABC.

This script scrapes tournament data from http://167.71.20.3 and imports essential data:
- Angler names
- Tournament info (name, date, lake)
- Results (weight, big bass, penalties)

Clears all existing tournament/angler data before importing.
"""

import argparse
import logging
import re
import sys
from datetime import datetime
from typing import List, Optional

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


class Tournament:
    def __init__(self, name: str, date: datetime, lake_name: str):
        self.name = name
        self.date = date
        self.lake_name = lake_name
        self.results: List[TournamentResult] = []


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

            # Scrape individual results
            tournament.results = self._scrape_individual_results(soup)

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


class DatabaseImporter:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run

    def clear_existing_data(self) -> None:
        """Clear all existing tournament and angler data."""
        if self.dry_run:
            logger.info("DRY RUN: Would clear existing tournament and angler data")
            return

        logger.info("Clearing existing tournament and angler data...")

        with engine.connect() as conn:
            # Clear in proper order due to foreign keys
            conn.execute(text("DELETE FROM results"))
            conn.execute(text("DELETE FROM team_results"))
            conn.execute(text("DELETE FROM tournaments"))
            conn.execute(text("DELETE FROM events"))
            conn.execute(text("DELETE FROM anglers"))
            conn.commit()

        logger.info("Existing data cleared")

    def import_tournaments(self, tournaments: List[Tournament]) -> None:
        """Import tournaments and all related data."""
        if self.dry_run:
            logger.info("DRY RUN: Tournament import preview:")
            for tournament in tournaments:
                print(
                    f"Tournament: {tournament.name} ({tournament.date.date()}) at {tournament.lake_name}"
                )
                for result in tournament.results:
                    print(
                        f"  {result.angler_name}: {result.total_weight}lbs, BB: {result.big_bass_weight}lbs"
                    )
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
        }

        result = conn.execute(
            text("""
                INSERT INTO events (date, year, name, event_type, lake_name)
                VALUES (:date, :year, :name, :event_type, :lake_name)
                RETURNING id
            """),
            event_data,
        )
        event_id = result.scalar()

        # Create tournament
        tournament_data = {
            "event_id": event_id,
            "name": tournament.name,
            "lake_name": tournament.lake_name,
            "complete": True,
        }

        result = conn.execute(
            text("""
                INSERT INTO tournaments (event_id, name, lake_name, complete)
                VALUES (:event_id, :name, :lake_name, :complete)
                RETURNING id
            """),
            tournament_data,
        )
        tournament_id = result.scalar()

        # Import results
        for result_data in tournament.results:
            angler_id = self._ensure_angler_exists(conn, result_data.angler_name)
            self._create_result(conn, tournament_id, angler_id, result_data)

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


def main() -> None:
    parser = argparse.ArgumentParser(description="Import tournament results from reference site")
    parser.add_argument("year", type=int, help="Year to import tournaments for (e.g., 2023, 2024)")
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview import without writing to database"
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
        scraper = TournamentScraper()
        importer = DatabaseImporter(dry_run=args.dry_run)

        # Clear existing data (unless dry run)
        if not args.dry_run:
            importer.clear_existing_data()

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
