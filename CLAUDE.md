# SABC (South Austin Bass Club) Development Rules

## Tournament Event Rules

### Upcoming Events
- **IMPORTANT**: Upcoming tournaments only have a **date** - nothing else is determined yet
- No location (`lake` field should be null)
- No AoY Points determination
- No Team Tournament designation
- No specific tournament names/titles
- No start/end times
- Display as "Location TBD" with appropriate tags
- Show poll results as bar chart where location map would normally be

### Completed Events  
- Have all details: location, times, tournament type, results
- Should have Google Maps integration for location
- Display actual tournament names and details

### Invalid States to Avoid
- ❌ Upcoming tournaments WITH locations assigned
- ❌ Upcoming tournaments with specific names/titles determined
- ❌ Upcoming tournaments with AoY/Team designations

### Valid Tournament Workflow
1. **Event Created** → Date only, everything else TBD
2. **Club Votes** → Location, times, tournament type determined
3. **Tournament Held** → Results added, marked complete

## UI/UX Guidelines

### Tournament Display
- Use GitHub-style issue cards for tournament listings
- "Location TBD" as title for upcoming events
- Poll results shown as bar chart for upcoming tournaments
- Google Maps integration for completed tournaments
- Pagination: 5 events per page

### Labels/Tags
- Upcoming: Blue label
- Completed: Green label
- Location TBD: Yellow/orange warning label
- AoY Points: Only for completed tournaments
- Team Tournament: Only for completed tournaments

## Database Integrity
- Clean up any tournaments in invalid states
- Upcoming tournaments should have `lake=null`, `complete=false`
- Completed tournaments should have `lake` assigned, `complete=true`