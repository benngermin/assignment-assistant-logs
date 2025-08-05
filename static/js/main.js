// Main JavaScript file for Assignment Assistant Dashboard
// This file will contain client-side functionality as the application grows

document.addEventListener('DOMContentLoaded', function() {
    console.log('Assignment Assistant Dashboard loaded');
    
    // Add any initialization code here
    initializeDashboard();
    
    // Load metrics after a short delay to prioritize main stats
    setTimeout(loadMetrics, 1000);
    
    // Load conversations after a slightly longer delay
    setTimeout(loadConversations, 1500);
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



// Function to load conversations
async function loadConversations() {
    console.log('Loading conversations...');
    const conversationsContent = document.getElementById('conversations-content');
    
    // Show loading state
    conversationsContent.innerHTML = `
        <div class="text-center py-3">
            <div class="spinner-border text-info" role="status">
                <span class="visually-hidden">Loading conversations...</span>
            </div>
            <p class="mt-2 text-muted">Loading conversation logs...</p>
        </div>
    `;
    
    try {
        const response = await fetch('/api/conversations');
        const conversations = await response.json();
        
        if (conversations.length === 0) {
            conversationsContent.innerHTML = `
                <div class="alert alert-info" role="alert">
                    <i class="fas fa-info-circle me-2"></i>
                    No conversations found. API authentication may be required.
                </div>
            `;
            return;
        }
        
        // Build conversations display
        let html = '<div class="table-responsive">';
        html += '<table class="table table-hover">';
        html += `
            <thead>
                <tr>
                    <th>Date</th>
                    <th>User</th>
                    <th>Course</th>
                    <th>Assignment</th>
                    <th>Status</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
        `;
        
        for (const conv of conversations.slice(0, 20)) {  // Show first 20
            const date = conv['Created Date'] ? new Date(conv['Created Date']).toLocaleString() : 'N/A';
            html += `
                <tr>
                    <td>${date}</td>
                    <td>${conv.user ? conv.user.substring(0, 8) + '...' : 'N/A'}</td>
                    <td>${conv.course ? conv.course.substring(0, 8) + '...' : 'N/A'}</td>
                    <td>${conv.assignment ? conv.assignment.substring(0, 8) + '...' : 'N/A'}</td>
                    <td><span class="badge bg-${conv.status === 'active' ? 'success' : 'secondary'}">${conv.status || 'unknown'}</span></td>
                    <td>
                        <button class="btn btn-sm btn-outline-primary" onclick="viewMessages('${conv._id}')">
                            <i class="fas fa-eye me-1"></i>View Messages
                        </button>
                    </td>
                </tr>
            `;
        }
        
        html += '</tbody></table></div>';
        
        if (conversations.length > 20) {
            html += '<p class="text-muted text-center mt-3">Showing first 20 conversations of ' + conversations.length + ' total</p>';
        }
        
        // Add messages modal container
        html += `
            <div class="modal fade" id="messagesModal" tabindex="-1" aria-labelledby="messagesModalLabel" aria-hidden="true">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title" id="messagesModalLabel">Conversation Messages</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body" id="messagesModalBody">
                            <!-- Messages will be loaded here -->
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        conversationsContent.innerHTML = html;
        
    } catch (error) {
        console.error('Error loading conversations:', error);
        conversationsContent.innerHTML = `
            <div class="alert alert-danger" role="alert">
                <i class="fas fa-exclamation-triangle me-2"></i>
                Failed to load conversations. Please try again later.
            </div>
        `;
    }
}

// Function to view messages for a specific conversation
async function viewMessages(conversationId) {
    console.log('Loading messages for conversation:', conversationId);
    const modalBody = document.getElementById('messagesModalBody');
    
    // Show loading state
    modalBody.innerHTML = `
        <div class="text-center py-3">
            <div class="spinner-border text-info" role="status">
                <span class="visually-hidden">Loading messages...</span>
            </div>
        </div>
    `;
    
    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('messagesModal'));
    modal.show();
    
    try {
        const response = await fetch(`/api/conversation/${conversationId}`);
        const data = await response.json();
        
        if (data.messages.length === 0) {
            modalBody.innerHTML = `
                <div class="alert alert-info" role="alert">
                    <i class="fas fa-info-circle me-2"></i>
                    No messages found for this conversation.
                </div>
            `;
            return;
        }
        
        // Build messages display
        let html = '<div class="messages-container" style="max-height: 500px; overflow-y: auto;">';
        
        for (const msg of data.messages) {
            const date = msg['Created Date'] ? new Date(msg['Created Date']).toLocaleString() : 'N/A';
            const isAssistant = msg.role === 'assistant' || msg.role === 'bot';
            
            html += `
                <div class="message mb-3 p-3 rounded ${isAssistant ? 'bg-dark' : 'bg-primary bg-opacity-10'}">
                    <div class="d-flex justify-content-between align-items-start mb-2">
                        <span class="badge bg-${isAssistant ? 'info' : 'primary'}">
                            <i class="fas fa-${isAssistant ? 'robot' : 'user'} me-1"></i>
                            ${msg.role}
                        </span>
                        <small class="text-muted">${date}</small>
                    </div>
                    <div class="message-text">${msg.text || 'No content'}</div>
                </div>
            `;
        }
        
        html += '</div>';
        html += `<p class="text-muted text-center mt-3">Total messages: ${data.message_count}</p>`;
        
        modalBody.innerHTML = html;
        
    } catch (error) {
        console.error('Error loading messages:', error);
        modalBody.innerHTML = `
            <div class="alert alert-danger" role="alert">
                <i class="fas fa-exclamation-triangle me-2"></i>
                Failed to load messages. Please try again later.
            </div>
        `;
    }
}



// Export functions for potential use in other scripts
window.AssignmentDashboard = {
    showNotification,
    handleApiError,
    loadMetrics,
    loadConversations,
    viewMessages
};
