#!/usr/bin/env python
import os
import sys
import django
import random

# Setup Django
sys.path.insert(0, '/Users/env/Development/SABC_II/SABC')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sabc.settings')
django.setup()

from tournaments.models.tournaments import Tournament

# Seasonal fishing descriptions by month
SEASONAL_DESCRIPTIONS = {
    1: [  # January - Winter
        "Cold water fishing with slow presentations. Focus on deeper structures and main lake points. Bass are sluggish but can be caught with patience.",
        "Winter patterns in effect. Target deep water areas and use slow-moving baits. Dress warm and expect challenging but rewarding conditions.",
        "Pre-spawn positioning begins. Look for bass staging in deeper water near spawning areas. Cold fronts will affect fish activity.",
        "Winter bass fishing at its finest. Focus on deep ledges and points with slow-moving jigs and spoons. Quality over quantity."
    ],
    2: [  # February - Late Winter
        "Late winter patterns with bass beginning to move shallow. Target sunny protected coves and points. Pre-spawn activity increases.",
        "Fish are starting to think about spring. Focus on transition areas between deep and shallow water. Spinnerbaits and jigs work well.",
        "Pre-spawn staging areas are key. Look for bass moving from deep to shallow water. Weather patterns greatly influence fish movement.",
        "February fishing can be excellent. Target areas that warm first and focus on baitfish concentrations. Patience is essential."
    ],
    3: [  # March - Early Spring
        "Spring transition is underway! Bass are moving to spawning areas. Target shallow coves and spawning flats. Exciting fishing ahead!",
        "Pre-spawn bass are aggressive and feeding heavily. Focus on shallow water structure and spawning areas. Great tournament potential.",
        "March madness for bass fishing! Fish are moving shallow and feeding aggressively. Target spawning areas and transition zones.",
        "Spring patterns emerging. Bass are beginning their spawning migration. Focus on protected coves and shallow water structure."
    ],
    4: [  # April - Peak Spring
        "Prime spawning season! Bass are on beds and guarding fry. Sight fishing opportunities abound. Respect the spawn and practice conservation.",
        "Peak spring conditions. Bass are spawning and post-spawn fish are feeding heavily. Variety of techniques will produce.",
        "April brings prime bass fishing conditions. Spawning activity and post-spawn feeding make for exciting tournament action.",
        "Spawning season at its peak. Target shallow water and sight fish to bedding bass. Post-spawn fish provide excellent action."
    ],
    5: [  # May - Late Spring
        "Post-spawn recovery and feeding. Bass are scattered but hungry. Target both shallow and deep water. Great all-around fishing.",
        "Late spring transition with bass recovering from spawn. Focus on areas near spawning grounds and deeper adjacent water.",
        "May offers excellent fishing variety. Post-spawn bass are feeding heavily while others are still spawning. Something for everyone.",
        "Spring patterns winding down but fishing remains excellent. Target both spawning areas and deeper structure for consistent action."
    ],
    6: [  # June - Early Summer
        "Early summer patterns emerging. Bass move to summer structure. Target deeper points, humps, and ledges. Dawn and dusk bite.",
        "Summer fishing begins! Focus on deeper water during the day and shallow areas in low light. Topwater action heats up.",
        "June brings summer patterns. Bass move to deeper structure but still feed in shallows during low light periods.",
        "Early summer transition. Target main lake structure and points. Topwater fishing in the mornings and evenings is outstanding."
    ],
    7: [  # July - Peak Summer
        "Peak summer conditions! Early morning and late evening fishing is best. Target deep structure and shade. Hot weather, hot fishing!",
        "Summer heat is on! Focus on early morning topwater action and deep structure during midday. Hydrate and fish smart.",
        "July summer fishing requires adjusting to hot conditions. Dawn and dusk provide the best action on topwater and shallow cover.",
        "High summer means early starts and deep water midday. Target shaded areas and deep structure for consistent summer bass."
    ],
    8: [  # August - Late Summer
        "Late summer patterns with schooling fish. Target main lake points and humps. Early morning topwater action is outstanding.",
        "August brings schooling bass and deep water structure fishing. Early morning surface action followed by deep water presentations.",
        "Late summer fishing with bass relating to deep structure. Watch for surface feeding activity and schooling fish.",
        "Dog days of summer require patience and persistence. Focus on deep water structure and early morning surface action."
    ],
    9: [  # September - Early Fall
        "Fall transition begins! Cooling water temperatures trigger feeding. Schooling activity increases. Great fishing ahead!",
        "September brings the start of fall patterns. Bass begin feeding heavily for winter. Target baitfish schools and points.",
        "Early fall conditions with increasing fish activity. Cooling temperatures trigger feeding patterns. Excellent tournament fishing.",
        "Fall fishing begins! Bass are feeding aggressively as water temperatures cool. Target areas with baitfish concentrations."
    ],
    10: [  # October - Peak Fall
        "Peak fall fishing! Bass are feeding heavily before winter. Schooling fish and surface action. Prime tournament conditions!",
        "October offers some of the year's best fishing. Bass are feeding aggressively and schooling. Target main lake areas and points.",
        "Fall feeding frenzy is on! Bass are schooling and feeding heavily. Outstanding topwater action and schooling fish opportunities.",
        "Prime fall conditions with aggressive feeding bass. Target areas with baitfish and watch for surface feeding activity."
    ],
    11: [  # November - Late Fall
        "Late fall patterns with bass feeding heavily before winter. Target deeper areas but don't ignore shallow water on warm days.",
        "November brings excellent fishing as bass prepare for winter. Focus on main lake structure and areas with baitfish concentrations.",
        "Late fall feeding continues with bass stocking up for winter. Variable weather keeps fishing interesting and productive.",
        "Fall patterns continue with bass feeding heavily. Target both deep and shallow water depending on weather conditions."
    ],
    12: [  # December - Early Winter
        "Early winter conditions with bass moving to deeper water. Target main lake structure and points. Quality fish are the reward.",
        "December fishing requires patience but rewards with quality bass. Focus on deeper water and main lake structure areas.",
        "Early winter patterns emerging. Bass move deeper but still feed on warm days. Target structure in deeper water.",
        "Winter fishing begins with bass moving to deeper areas. Focus on main lake points and structure for quality fish."
    ]
}

def add_descriptions():
    """Add seasonal descriptions to all tournaments except August 2025."""
    print("Adding seasonal fishing descriptions to tournaments...")
    
    updated_count = 0
    
    # Get all tournaments except August 2025
    tournaments = Tournament.objects.exclude(event__year=2025, event__month=8)
    
    for tournament in tournaments:
        month = tournament.event.month
        
        # Get random description for this month
        descriptions = SEASONAL_DESCRIPTIONS.get(month, SEASONAL_DESCRIPTIONS[1])
        chosen_description = random.choice(descriptions)
        
        # Update tournament description
        tournament.description = chosen_description
        tournament.save()
        
        updated_count += 1
        print(f"Updated {tournament.name}: {chosen_description[:60]}...")
    
    print(f"\nUpdated {updated_count} tournaments with seasonal descriptions")
    
    # Verify August 2025 was skipped
    aug_2025 = Tournament.objects.filter(event__year=2025, event__month=8).first()
    if aug_2025:
        print(f"August 2025 tournament '{aug_2025.name}' was skipped (description: '{aug_2025.description or 'None'}')")

if __name__ == "__main__":
    add_descriptions()