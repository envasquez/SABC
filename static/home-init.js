/**
 * Home page initialization JavaScript
 * Initializes the home page polls with data from data attributes
 */

(function() {
    'use strict';

/**
 * Record that a cancelled-tournament alert was dismissed.
 */
function dismissCancelledAlert(eventId) {
    const dismissed = safeParseJSON(localStorage.getItem('dismissedCancelledAlerts'), []);
    if (dismissed.indexOf(eventId) === -1) {
        dismissed.push(eventId);
        localStorage.setItem('dismissedCancelledAlerts', JSON.stringify(dismissed));
    }
}

/**
 * Client-side pagination for the Club News sidebar list.
 */
function initNewsPagination() {
    const NEWS_PER_PAGE = 3;
    let currentPage = 1;
    const items = document.querySelectorAll('.news-item');
    const totalItems = items.length;
    const totalPages = Math.ceil(totalItems / NEWS_PER_PAGE);
    const pagination = document.getElementById('news-pagination');
    const pageInfo = document.getElementById('news-page-info');
    const prevBtn = document.getElementById('news-prev');
    const nextBtn = document.getElementById('news-next');
    if (totalItems <= NEWS_PER_PAGE) return;
    if (pagination) pagination.style.display = 'flex';
    function showPage(page) {
        currentPage = page;
        const start = (page - 1) * NEWS_PER_PAGE;
        const end = Math.min(start + NEWS_PER_PAGE, totalItems);
        items.forEach(function(item, i) { item.style.display = (i >= start && i < end) ? 'block' : 'none'; });
        if (pageInfo) pageInfo.textContent = 'Showing ' + (start + 1) + '-' + end + ' of ' + totalItems;
        if (prevBtn) prevBtn.disabled = (page === 1);
        if (nextBtn) nextBtn.disabled = (page === totalPages);
    }
    if (prevBtn) prevBtn.addEventListener('click', function() { if (currentPage > 1) showPage(currentPage - 1); });
    if (nextBtn) nextBtn.addEventListener('click', function() { if (currentPage < totalPages) showPage(currentPage + 1); });
    showPage(1);
}

document.addEventListener('DOMContentLoaded', function() {
    // Get lakes data from data attribute
    const homeDataElement = document.getElementById('home-data');
    const lakesData = homeDataElement ? safeParseJSON(homeDataElement.dataset.lakes, []) : [];

    // Initialize home polls with the data
    initializeHomePolls({
        lakesData: lakesData
    });

    // Client-side news pagination
    initNewsPagination();

    // Cancelled-tournament alert dismissal
    document.querySelectorAll('.js-dismiss-cancelled-alert').forEach(function(btn) {
        btn.addEventListener('click', function() {
            const id = parseInt(btn.dataset.eventId, 10);
            if (!isNaN(id)) dismissCancelledAlert(id);
        });
    });
});
})();
