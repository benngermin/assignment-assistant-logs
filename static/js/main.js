// Main JavaScript file for Assignment Assistant Dashboard
// This file will contain client-side functionality as the application grows

document.addEventListener('DOMContentLoaded', function() {
    console.log('Assignment Assistant Dashboard loaded');
    
    // Add any initialization code here
    initializeDashboard();
    
    // Load metrics after a short delay to prioritize main stats
    setTimeout(loadMetrics, 1000);
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

// Function to load comprehensive metrics
async function loadMetrics() {
    console.log('Loading comprehensive metrics...');
    const metricsContent = document.getElementById('metrics-content');
    
    // Show loading state
    metricsContent.innerHTML = `
        <div class="text-center py-3">
            <div class="spinner-border text-info" role="status">
                <span class="visually-hidden">Loading metrics...</span>
            </div>
            <p class="mt-2 text-muted">Loading comprehensive metrics...</p>
        </div>
    `;
    
    try {
        const response = await fetch('/api/metrics');
        const metrics = await response.json();
        
        // Build metrics display HTML
        let html = '<div class="row g-3">';
        
        // Summary cards
        html += `
            <div class="col-md-6">
                <div class="card bg-dark">
                    <div class="card-body">
                        <h6 class="card-subtitle mb-2 text-muted">Summary Statistics</h6>
                        <ul class="list-unstyled mb-0">
                            <li><strong>Total Users:</strong> ${metrics.total_users.toLocaleString()}</li>
                            <li><strong>Total Conversations:</strong> ${metrics.total_conversations.toLocaleString()}</li>
                            <li><strong>Total Messages:</strong> ${metrics.total_messages.toLocaleString()}</li>
                            <li><strong>Avg Messages per Conversation:</strong> ${metrics.avg_messages_per_conv.toFixed(2)}</li>
                            <li><strong>Data Quality:</strong> <span class="badge bg-${metrics.summary?.data_quality === 'complete' ? 'success' : 'warning'}">${metrics.summary?.data_quality || 'unknown'}</span></li>
                        </ul>
                    </div>
                </div>
            </div>
        `;
        
        // Course distribution
        html += `
            <div class="col-md-6">
                <div class="card bg-dark">
                    <div class="card-body">
                        <h6 class="card-subtitle mb-2 text-muted">Course Distribution</h6>
                        <p class="mb-2"><strong>Unique Courses:</strong> ${metrics.summary?.unique_courses || 0}</p>
        `;
        
        if (Object.keys(metrics.convs_per_course).length > 0) {
            html += '<div class="small" style="max-height: 150px; overflow-y: auto;">';
            for (const [courseId, count] of Object.entries(metrics.convs_per_course).slice(0, 10)) {
                html += `<div class="d-flex justify-content-between mb-1">
                    <span class="text-truncate" style="max-width: 200px;">Course ${courseId.substring(0, 8)}...</span>
                    <span class="badge bg-primary">${count}</span>
                </div>`;
            }
            if (Object.keys(metrics.convs_per_course).length > 10) {
                html += '<p class="text-muted small mt-2 mb-0">...and more</p>';
            }
            html += '</div>';
        } else {
            html += '<p class="text-muted">No course data available</p>';
        }
        
        html += `
                    </div>
                </div>
            </div>
        `;
        
        // Assignment distribution
        html += `
            <div class="col-12">
                <div class="card bg-dark">
                    <div class="card-body">
                        <h6 class="card-subtitle mb-2 text-muted">Assignment Distribution</h6>
                        <p class="mb-2"><strong>Unique Assignments:</strong> ${metrics.summary?.unique_assignments || 0}</p>
        `;
        
        if (Object.keys(metrics.convs_per_assignment).length > 0) {
            html += '<div class="row g-2">';
            for (const [assignmentId, count] of Object.entries(metrics.convs_per_assignment).slice(0, 12)) {
                html += `<div class="col-md-3 col-sm-6">
                    <div class="d-flex justify-content-between align-items-center p-2 bg-secondary bg-opacity-10 rounded">
                        <span class="text-truncate small" style="max-width: 120px;">Assignment ${assignmentId.substring(0, 6)}...</span>
                        <span class="badge bg-info">${count}</span>
                    </div>
                </div>`;
            }
            if (Object.keys(metrics.convs_per_assignment).length > 12) {
                html += '<div class="col-12"><p class="text-muted small mt-2 mb-0 text-center">...and more</p></div>';
            }
            html += '</div>';
        } else {
            html += '<p class="text-muted">No assignment data available</p>';
        }
        
        html += `
                    </div>
                </div>
            </div>
        `;
        
        html += '</div>';
        
        // Update the content
        metricsContent.innerHTML = html;
        
        // Add animation
        metricsContent.classList.add('fade-in');
        setTimeout(() => metricsContent.classList.remove('fade-in'), 500);
        
    } catch (error) {
        console.error('Error loading metrics:', error);
        metricsContent.innerHTML = `
            <div class="alert alert-danger" role="alert">
                <i class="fas fa-exclamation-triangle me-2"></i>
                Failed to load metrics. Please try again later.
            </div>
        `;
    }
}



// Export functions for potential use in other scripts
window.AssignmentDashboard = {
    showNotification,
    handleApiError,
    loadMetrics
};
