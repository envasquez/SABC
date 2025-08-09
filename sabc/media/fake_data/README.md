# SABC Fake Data Documentation

This directory contains comprehensive fake data for populating the South Austin Bass Club (SABC) application with realistic test data.

## Overview

The fake data includes:
- **300+ Anglers** with realistic names, contact info, and membership types
- **20 Texas Lakes** with accurate details, locations, and boat ramps
- **12 Tournaments** across 2024 season with complete results and statistics
- **6 Polls** for lake selection with realistic voting patterns
- **Penalties and Variations** to test calculation logic

## File Structure

```
fake_data/
├── README.md                 # This documentation
├── lakes.yaml               # 20 real Texas lakes with details
├── anglers.yaml            # First 50 anglers (officers + members)
├── more_anglers.yaml       # Additional 250+ anglers to reach 300 total
├── tournaments.yaml        # 12 tournaments with complete results
└── polls.yaml              # 6 lake selection polls with voting data
```

## Data Details

### Anglers (300 total)
- **4 Officers**: President, VP, Treasurer, Secretary
- **291 Members**: Regular club members with fishing experience
- **5 Guests**: Trial members or visitors
- **Realistic Details**: Phone numbers (512 area code), email addresses, varied names
- **Gender Diversity**: Mix of male and female anglers

### Lakes (20 locations)
- **Focus on Central Texas**: Lakes within 1-2 hours of Austin
- **Famous Bass Waters**: Lake Fork, Sam Rayburn, Toledo Bend
- **Local Favorites**: Lake Travis, Canyon Lake, Lake LBJ
- **Accurate Data**: Real GPS coordinates, acreage, depth, ramp information
- **Variety**: Small urban lakes to massive tournament destinations

### Tournaments (12 events)
- **2024 Season**: January through December
- **Mixed Formats**: Individual and team tournaments
- **Realistic Results**: Weight distributions based on lake quality
- **Penalties Included**: Dead fish penalties (0.5lb per fish) for testing
- **Seasonal Patterns**: Heavier weights in spring, lighter in summer heat
- **Complete vs Upcoming**: 8 completed tournaments with full results, 4 upcoming

#### Tournament Features:
- **Entry Fees**: Standard $25 per angler
- **Points System**: 100 points for 1st place, decreasing by 5
- **Big Bass Tracking**: Individual big bass weights recorded
- **Team Tournaments**: Combined weights and team names
- **Penalties**: Realistic dead fish penalties applied to test calculations

### Polls (6 total)
- **4 Completed Polls**: Historical lake selections for 2024
- **2 Active Polls**: Current voting for 2025 season
- **Realistic Voting**: Varied participation levels (60-100 voters)
- **Popular Lakes Win**: More desirable lakes receive more votes
- **Officer Created**: Different officers create different polls

## Key Features for Testing

### Penalties and Edge Cases
1. **Dead Fish Penalties**: Multiple tournaments include 0.5lb and 1.0lb penalties
2. **Incomplete Limits**: Some anglers caught only 4 fish instead of 5
3. **Zero Weights**: Some anglers blanked (caught no fish)
4. **Tie Breaking**: Similar weights to test tie-breaking logic

### Weight Distributions
- **Trophy Tournaments**: Lake Fork and Sam Rayburn have higher average weights
- **Seasonal Variation**: Spring tournaments (March-May) have heaviest weights
- **Summer Adjustment**: July-August tournaments show heat impact
- **Big Bass Range**: 2.89lb to 6.23lb spread for variety

### Voting Patterns
- **Realistic Turnout**: 60-100 votes per poll (about 20-35% participation)
- **Lake Preferences**: Popular lakes (Fork, Rayburn, Toledo Bend) get more votes
- **Seasonal Consideration**: Warm-water lakes win winter polls

## Loading the Data

The YAML files are structured for easy import into Django. Each file contains:
- Clear field mappings to Django model fields
- Proper data types (strings, numbers, dates, booleans)
- Realistic relationships between entities
- No duplicate usernames or emails

### Usage Notes
- Phone numbers use 512 area code (Austin area)
- Email addresses follow firstname.lastname@email.com pattern
- Tournament dates span full 2024 calendar year
- All lakes are real Texas locations with accurate GPS coordinates
- Weights are in pounds with realistic bass fishing distributions

## Calculation Testing

The data includes specific scenarios to test:
1. **Points Calculations**: Verify AoY points are calculated correctly
2. **Penalty Applications**: Ensure dead fish penalties reduce total weight
3. **Team Standings**: Test combined team weight calculations
4. **Big Bass Tracking**: Verify largest fish identification across tournaments
5. **Poll Results**: Test vote counting and winner determination

## Data Integrity

- **No Conflicts**: All usernames, emails, and IDs are unique
- **Realistic Ranges**: All weights, dates, and numbers within believable ranges
- **Proper References**: All poll voters and tournament participants exist in angler data
- **Consistent Formatting**: Standardized phone numbers, email formats, naming conventions

This fake data provides a comprehensive foundation for testing all aspects of the SABC tournament tracking system while maintaining realism and covering edge cases.