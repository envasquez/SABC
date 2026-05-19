/**
 * Tournament Results page JavaScript functionality
 * Handles result deletion operations for individual, team, and buy-in results
 */

(function() {
    'use strict';

    /**
     * Delete a tournament result after confirmation
     * @param {string} url - DELETE endpoint URL
     * @param {string} confirmMsg - Confirmation prompt shown to the user
     * @param {string} errLabel - Label used in error messages (e.g. 'result', 'buy-in result')
     */
    async function deleteResult(url, confirmMsg, errLabel) {
        if (!confirm(confirmMsg)) return;

        try {
            const response = await deleteRequest(url);

            if (response.ok) {
                window.location.reload();
            } else {
                const text = await response.text();
                try {
                    const data = JSON.parse(text);
                    showToast(data.error || `Error deleting ${errLabel}. Please try again.`, 'error');
                } catch (e) {
                    showToast(`Error deleting ${errLabel}: ` + text, 'error');
                }
            }
        } catch (error) {
            console.error('Error:', error);
            showToast(`Error deleting ${errLabel}. Please try again.`, 'error');
        }
    }

    function deleteIndividualResult(tournamentId, resultId, anglerName) {
        deleteResult(
            `/admin/tournaments/${tournamentId}/results/${resultId}`,
            `Are you sure you want to delete the result for ${anglerName}?\n\nThis will also delete any team results that include this angler.\n\nThis action cannot be undone.`,
            'result'
        );
    }

    function deleteBuyInResult(tournamentId, resultId, anglerName) {
        deleteResult(
            `/admin/tournaments/${tournamentId}/results/${resultId}`,
            `Are you sure you want to delete the buy-in result for ${anglerName}?\n\nThis action cannot be undone.`,
            'buy-in result'
        );
    }

    function deleteTeamResult(tournamentId, teamResultId, teamName, isSolo) {
        const memberText = isSolo ? 'this angler' : 'both team members';
        deleteResult(
            `/admin/tournaments/${tournamentId}/team-results/${teamResultId}`,
            `Are you sure you want to delete the team result for ${teamName}?\n\nThis will also delete the individual results for ${memberText}.\n\nThis action cannot be undone.`,
            'team result'
        );
    }

    // Wire up delegated event listeners for delete buttons.
    // Using data-* attributes + addEventListener avoids the HTML-attribute -> JS string
    // breakout vector that inline onclick="fn('{{ name }}')" exposes.
    document.addEventListener('DOMContentLoaded', function() {
        document.querySelectorAll('.js-delete-team-result').forEach(function(btn) {
            btn.addEventListener('click', function() {
                const d = btn.dataset;
                deleteTeamResult(
                    parseInt(d.tournamentId, 10),
                    parseInt(d.teamResultId, 10),
                    d.teamName,
                    parseInt(d.isSolo, 10)
                );
            });
        });

        document.querySelectorAll('.js-delete-individual-result').forEach(function(btn) {
            btn.addEventListener('click', function() {
                const d = btn.dataset;
                deleteIndividualResult(
                    parseInt(d.tournamentId, 10),
                    parseInt(d.resultId, 10),
                    d.anglerName
                );
            });
        });

        document.querySelectorAll('.js-delete-buy-in-result').forEach(function(btn) {
            btn.addEventListener('click', function() {
                const d = btn.dataset;
                deleteBuyInResult(
                    parseInt(d.tournamentId, 10),
                    parseInt(d.resultId, 10),
                    d.anglerName
                );
            });
        });
    });
})();
