/**
 * Home page initialization JavaScript
 * Initializes the home page polls with data from data attributes
 */

document.addEventListener('DOMContentLoaded', function() {
    // Get lakes data from data attribute
    const homeDataElement = document.getElementById('home-data');
    const lakesData = homeDataElement ? JSON.parse(homeDataElement.dataset.lakes || '[]') : [];

    // Initialize home polls with the data
    initializeHomePolls({
        lakesData: lakesData
    });
});
