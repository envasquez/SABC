/**
 * Admin Events - Filtering Module
 * Handles event list filtering, search, and tab badge updates
 */

/**
 * Filter events in a specific tab
 */
function filterEvents(tabType) {
    const searchInput = document.getElementById(`${tabType}-search`).value.toLowerCase();
    const yearFilter = document.getElementById(`${tabType}-year-filter`)?.value;
    const statusFilter = document.getElementById(`${tabType}-status-filter`)?.value;
    const lakeFilter = document.getElementById(`${tabType}-lake-filter`)?.value.toLowerCase();
    const typeFilter = document.getElementById(`${tabType}-type-filter`)?.value;
    const resultsFilter = document.getElementById(`${tabType}-results-filter`)?.value;

    // Determine the correct table selector based on tab type
    let tableSelector;
    if (tabType === 'past') {
        tableSelector = '#past-events-tab table tbody tr';
    } else if (tabType === 'past-tournaments') {
        tableSelector = '#past-tournaments-events table tbody tr';
    } else {
        tableSelector = `#${tabType}-events table tbody tr`;
    }

    const rows = document.querySelectorAll(tableSelector);
    let visibleCount = 0;

    rows.forEach(row => {
        // Skip rows with no data cells (e.g., empty state messages)
        if (row.cells.length < 3) {
            return;
        }

        let visible = true;

        // Search filter
        if (searchInput && !row.textContent.toLowerCase().includes(searchInput)) {
            visible = false;
        }

        // Year filter
        if (yearFilter && row.dataset.year !== yearFilter) {
            visible = false;
        }

        // Status filter (for SABC tournaments)
        if (statusFilter) {
            if (statusFilter === 'has-poll' && !row.textContent.includes('\u{1F5F3}\u{FE0F}')) {
                visible = false;
            }
            if (statusFilter === 'no-poll' && row.textContent.includes('\u{1F5F3}\u{FE0F}')) {
                visible = false;
            }
            if (statusFilter === 'complete' && !row.textContent.includes('\u{2705}')) {
                visible = false;
            }
            if (statusFilter === 'incomplete' && row.textContent.includes('\u{2705}')) {
                visible = false;
            }
        }

        // Lake filter
        if (lakeFilter && row.dataset.lake && !row.dataset.lake.includes(lakeFilter)) {
            visible = false;
        }

        // Type filter
        if (typeFilter && row.dataset.eventType !== typeFilter) {
            visible = false;
        }

        // Results filter
        if (resultsFilter) {
            const hasResults = row.dataset.hasResults === 'yes';
            if (resultsFilter === 'has-results' && !hasResults) {
                visible = false;
            }
            if (resultsFilter === 'no-results' && hasResults) {
                visible = false;
            }
        }

        row.style.display = visible ? '' : 'none';
        if (visible) visibleCount++;
    });

    // Update empty state
    updateEmptyState(tabType, visibleCount);
}

function clearFilters(tabType) {
    // Clear all filter inputs for this tab
    document.getElementById(`${tabType}-search`).value = '';

    const yearFilter = document.getElementById(`${tabType}-year-filter`);
    if (yearFilter) yearFilter.value = '';

    const statusFilter = document.getElementById(`${tabType}-status-filter`);
    if (statusFilter) statusFilter.value = '';

    const lakeFilter = document.getElementById(`${tabType}-lake-filter`);
    if (lakeFilter) lakeFilter.value = '';

    const typeFilter = document.getElementById(`${tabType}-type-filter`);
    if (typeFilter) typeFilter.value = '';

    const resultsFilter = document.getElementById(`${tabType}-results-filter`);
    if (resultsFilter) resultsFilter.value = '';

    // Show all rows
    let tableSelector;
    if (tabType === 'past') {
        tableSelector = '#past-events-tab table tbody tr';
    } else if (tabType === 'past-tournaments') {
        tableSelector = '#past-tournaments-events table tbody tr';
    } else {
        tableSelector = `#${tabType}-events table tbody tr`;
    }

    const rows = document.querySelectorAll(tableSelector);
    let visibleCount = 0;

    rows.forEach(row => {
        if (row.cells.length > 2 && !row.textContent.includes('No events')) {
            row.style.display = '';
            visibleCount++;
        }
    });

    updateEmptyState(tabType, visibleCount);
}

function updateEmptyState(tabType, visibleCount) {
    // Update tab badges with filtered counts
    let badgeId;
    if (tabType === 'sabc') badgeId = 'sabc-count';
    else if (tabType === 'holidays') badgeId = 'holidays-count';
    else if (tabType === 'other') badgeId = 'other-count';
    else if (tabType === 'past-tournaments') badgeId = 'past-tournaments-count';
    else if (tabType === 'past') badgeId = 'past-count';

    const tabBadge = document.getElementById(badgeId);

    if (tabBadge && visibleCount !== undefined) {
        // Store original count if not already stored
        if (!tabBadge.dataset.originalCount) {
            tabBadge.dataset.originalCount = tabBadge.textContent;
        }

        // Show filtered count if different from original
        if (document.getElementById(`${tabType}-search`).value ||
            document.getElementById(`${tabType}-year-filter`)?.value ||
            document.getElementById(`${tabType}-status-filter`)?.value ||
            document.getElementById(`${tabType}-lake-filter`)?.value ||
            document.getElementById(`${tabType}-type-filter`)?.value ||
            document.getElementById(`${tabType}-results-filter`)?.value) {
            tabBadge.textContent = visibleCount;
            tabBadge.classList.add('bg-warning');
            tabBadge.classList.remove('bg-primary', 'bg-info', 'bg-secondary');
        } else {
            tabBadge.textContent = tabBadge.dataset.originalCount;
            tabBadge.classList.remove('bg-warning');
            // Restore original badge color based on tab
            if (tabType === 'sabc') tabBadge.classList.add('bg-primary');
            else if (tabType === 'holidays') tabBadge.classList.add('bg-info');
            else if (tabType === 'other') tabBadge.classList.add('bg-warning');
            else tabBadge.classList.add('bg-secondary');
        }
    }
}
