def get_tournaments_query():
    return """
        SELECT t.id, e.date, e.name, e.description,
               l.display_name as lake_display_name, l.yaml_key as lake_name,
               ra.name as ramp_name, ra.google_maps_iframe as ramp_google_maps,
               l.google_maps_iframe as lake_google_maps,
               t.start_time, t.end_time, t.entry_fee, t.fish_limit, t.limit_type,
               t.is_team, t.is_paper, t.complete, t.poll_id,
               COUNT(DISTINCT r.angler_id) as total_anglers,
               SUM(r.num_fish) as total_fish,
               SUM(r.total_weight - r.dead_fish_penalty) as total_weight,
               t.aoy_points
        FROM tournaments t
        JOIN events e ON t.event_id = e.id
        LEFT JOIN lakes l ON t.lake_id = l.id
        LEFT JOIN ramps ra ON t.ramp_id = ra.id
        LEFT JOIN results r ON t.id = r.tournament_id AND r.disqualified = FALSE
        LEFT JOIN anglers a ON r.angler_id = a.id AND a.name != 'Admin User'
        GROUP BY t.id, e.date, e.name, e.description,
                 l.display_name, l.yaml_key, ra.name, ra.google_maps_iframe, l.google_maps_iframe,
                 t.start_time, t.end_time, t.entry_fee, t.fish_limit, t.limit_type,
                 t.is_team, t.is_paper, t.complete, t.poll_id, t.aoy_points
        ORDER BY e.date DESC
        LIMIT :limit OFFSET :offset
    """


def get_top_results_query():
    return """
        SELECT
            tr.place_finish,
            a1.name as angler1_name,
            a2.name as angler2_name,
            tr.total_weight,
            CASE WHEN tr.angler2_id IS NULL THEN 1 ELSE 2 END as team_size
        FROM team_results tr
        JOIN anglers a1 ON tr.angler1_id = a1.id
        LEFT JOIN anglers a2 ON tr.angler2_id = a2.id
        WHERE tr.tournament_id = :tournament_id
        AND a1.name != 'Admin User'
        AND (a2.name != 'Admin User' OR a2.name IS NULL)
        ORDER BY tr.place_finish ASC
        LIMIT 3
    """
