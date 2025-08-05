// Main JavaScript file for Assignment Assistant Dashboard
// This file will contain client-side functionality as the application grows

document.addEventListener('DOMContentLoaded', function() {
    console.log('Assignment Assistant Dashboard loaded');
    
    // Add any initialization code here
    initializeDashboard();
});

function initializeDashboard() {
    // Dashboard initialization logic will be added here
    console.log('Dashboard initialized');
    
    // Load statistics on page load
    loadStatistics();
    
    // Add event listeners for future functionality
    setupEventListeners();
}

function setupEventListeners() {
    // Event listeners for interactive elements will be added here
    console.log('Event listeners set up');
    
    // Refresh statistics every 30 seconds
    setInterval(loadStatistics, 30000);
}

// Function to load statistics from API endpoints
async function loadStatistics() {
    console.log('Loading statistics...');
    
    // Load total users
    try {
        const usersResponse = await fetch('/api/total_users');
        const usersData = await usersResponse.json();
        updateStatDisplay('total-users', usersData.total_users);
    } catch (error) {
        console.error('Error loading users count:', error);
        updateStatDisplay('total-users', 'Error');
    }
    
    // Load total conversations
    try {
        const conversationsResponse = await fetch('/api/total_conversations');
        const conversationsData = await conversationsResponse.json();
        updateStatDisplay('total-conversations', conversationsData.total_conversations);
    } catch (error) {
        console.error('Error loading conversations count:', error);
        updateStatDisplay('total-conversations', 'Error');
    }
    
    // Load total messages
    try {
        const messagesResponse = await fetch('/api/total_messages');
        const messagesData = await messagesResponse.json();
        updateStatDisplay('total-messages', messagesData.total_messages);
    } catch (error) {
        console.error('Error loading messages count:', error);
        updateStatDisplay('total-messages', 'Error');
    }
}

// Function to update statistic display
function updateStatDisplay(elementId, value) {
    const element = document.getElementById(elementId);
    if (element) {
        if (value === 'Error') {
            element.innerHTML = '<span class="text-danger">Error</span>';
        } else {
            // Format number with commas for better readability
            const formatted = typeof value === 'number' ? value.toLocaleString() : value;
            element.innerHTML = formatted;
            
            // Add animation effect
            element.classList.add('fade-in');
            setTimeout(() => element.classList.remove('fade-in'), 500);
        }
    }
}

// Utility functions for future API interactions
function showNotification(message, type = 'info') {
    // Function to show notifications to users
    console.log(`${type.toUpperCase()}: ${message}`);
}

function handleApiError(error) {
    // Function to handle API errors gracefully
    console.error('API Error:', error);
    showNotification('An error occurred while connecting to the API', 'error');
}

// Export functions for potential use in other scripts
window.AssignmentDashboard = {
    showNotification,
    handleApiError
};
