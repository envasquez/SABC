# Tournament Generation Utility

This Django management command generates realistic team tournaments with results, team pairings, and voting data for the SABC database.

## Usage

### Basic Usage

Generate tournaments for default years (2023-2024) and 7 months of 2025:
```bash
cd sabc
python manage.py generate_team_tournaments
```

### Clear and Regenerate

Clear all existing tournament data and generate fresh:
```bash
python manage.py generate_team_tournaments --clear
```

### Custom Years

Generate tournaments for specific years:
```bash
python manage.py generate_team_tournaments --years 2022 2023 2024 --months-2025 12
```

### Custom Parameters

Adjust tournament characteristics:
```bash
python manage.py generate_team_tournaments \
    --big-bass-percent 40 \        # 40% of tournaments have big bass
    --zero-catch-percent 20        # 20% of anglers catch zero fish
```

### Skip Upcoming Tournament

Generate only completed tournaments without creating an upcoming one:
```bash
python manage.py generate_team_tournaments --no-create-upcoming
```

## Features

The command generates:

1. **Team Tournaments** - Monthly tournaments for each specified year
2. **Tournament Dates** - 4th Sunday of each month (or 3rd if no 4th Sunday exists)
3. **Random Lake Selection** - Each tournament assigned a random non-paper lake from database
4. **Ramp Assignment** - Appropriate boat ramp for each lake
5. **Individual Results** - 60-80% of members participate with realistic catch data
6. **Team Pairings** - Random pairing of anglers into teams
7. **Zero Catches** - Configurable percentage of anglers catch nothing
8. **Big Bass** - Configurable percentage of tournaments have 5+ lb bass
9. **Penalties** - ~5% of results include penalty weights
10. **Team Tournaments** - All tournaments are regular team tournaments that count for points
11. **Realistic Times** - Start times calculated from sunrise (~15-45 min before) with 8-hour duration
12. **Completed Polls** - Each tournament has a completed poll showing voting that selected the lake
13. **Upcoming Tournament** - Creates next month's tournament with active location poll
14. **Voting Data** - Sample votes for both completed and upcoming tournament polls

## Options

- `--years`: List of years to generate tournaments for (default: 2023 2024)
- `--months-2025`: Number of months to generate for 2025 (default: 7)
- `--clear`: Clear all existing tournament data before generating
- `--paper-count`: Number of paper tournaments to create randomly (default: 0 - disabled)
- `--big-bass-percent`: Percentage of tournaments with big bass (default: 30)
- `--zero-catch-percent`: Percentage of anglers who catch zero fish (default: 18)
- `--create-upcoming`: Create upcoming tournament for next month (default: True)

## Data Generated

### Per Tournament
- 60-80% member participation
- Individual results with fish counts and weights
- Team results with combined weights
- Proper place assignments
- Buy-in tracking
- Disqualification tracking

### Realistic Distribution
- Fish weights: 1-4 lbs typically
- Big bass: 5-8 lbs when present
- Zero catches: ~18% of participants
- Penalties: ~5% of results
- Team count: ~50% of participant count

## Example Output

```
=== Creating 2023 Tournaments ===
Created: January 2023 Team Tournament at Lake Travis (Regular)
Created: February 2023 Team Tournament at Lake Buchanan (Regular)
...

=== Summary ===
Total tournaments created: 31
All tournaments are regular team tournaments
Upcoming tournaments: 1
Tournaments with big bass (5+ lbs): 10 (32.3%)

=== Database Statistics ===
Total tournaments: 32
Total results: 3139
Total team results: 1561
Zero catches: 575
```

## Notes

- Requires existing lakes and anglers in the database
- Tournament polls are automatically created for upcoming tournaments
- All tournaments follow CLAUDE.md rules for upcoming vs completed states
- Transactional - either all tournaments are created or none (on error)