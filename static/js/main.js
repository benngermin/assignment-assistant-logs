// Main JavaScript file for Assignment Assistant Dashboard

// Alert system
function showAlert(message, type = 'danger') {
    const alertContainer = document.getElementById('alert-container');
    const alertId = 'alert-' + Date.now();
    const alertHtml = `
        <div id="${alertId}" class="alert alert-${type} alert-dismissible fade show" role="alert">
            <i class="fas fa-${type === 'danger' ? 'exclamation-triangle' : type === 'success' ? 'check-circle' : 'info-circle'} me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    `;
    alertContainer.insertAdjacentHTML('beforeend', alertHtml);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        const alertElement = document.getElementById(alertId);
        if (alertElement) {
            alertElement.remove();
        }
    }, 5000);
}

// Show loading spinner
function showSpinner(elementId, message = 'Loading...') {
    const element = document.getElementById(elementId);
    if (element) {
        element.innerHTML = `
            <div class="text-center py-3">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">${message}</span>
                </div>
                <p class="mt-2">${message}</p>
            </div>
        `;
    }
}

document.addEventListener('DOMContentLoaded', function() {
    console.log('Assignment Assistant Dashboard loaded');
    
    // Load metrics with error handling
    showSpinner('metric-total-users', '...');
    showSpinner('metric-total-conversations', '...');
    showSpinner('metric-total-messages', '...');
    showSpinner('metric-avg-messages', '...');
    
    fetch('/api/metrics')
        .then(res => {
            if (!res.ok) {
                throw new Error(`API Error: ${res.status}`);
            }
            return res.json();
        })
        .then(data => {
            document.getElementById('metric-total-users').innerText = data.total_users || 0;
            document.getElementById('metric-total-conversations').innerText = data.total_conversations || 0;
            document.getElementById('metric-total-messages').innerText = data.total_messages || 0;
            document.getElementById('metric-avg-messages').innerText = data.avg_messages_per_conversation ? data.avg_messages_per_conversation.toFixed(1) : '0';
            
            // Also update the old stats cards if they exist
            const userCount = document.getElementById('user-count');
            const convCount = document.getElementById('conversation-count');
            const msgCount = document.getElementById('message-count');
            if (userCount) userCount.innerText = data.total_users || 0;
            if (convCount) convCount.innerText = data.total_conversations || 0;
            if (msgCount) msgCount.innerText = data.total_messages || 0;
            
            if (data.total_users === 0 && data.total_conversations === 0) {
                showAlert('API Error: Check API key. No data available.', 'warning');
            }
        })
        .catch(err => {
            console.error('Error loading metrics:', err);
            showAlert('API Error: Failed to load metrics. Check API key.', 'danger');
            document.getElementById('metric-total-users').innerText = '0';
            document.getElementById('metric-total-conversations').innerText = '0';
            document.getElementById('metric-total-messages').innerText = '0';
            document.getElementById('metric-avg-messages').innerText = '0';
        });
    
    // Load conversations
    loadConversationsTable();
    
    // Initialize dashboard
    initializeDashboard();
    
    // Load additional metrics after a delay
    setTimeout(loadMetrics, 1000);
});

// Load conversations table with filters
function loadConversationsTable(userId = null, courseId = null) {
    const tbody = document.getElementById('conversations-tbody');
    
    // Show loading spinner
    tbody.innerHTML = `
        <tr>
            <td colspan="5" class="text-center">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading conversations...</span>
                </div>
                <p class="mt-2">Loading conversations...</p>
            </td>
        </tr>
    `;
    
    // Build query params
    let url = '/api/conversations';
    const params = new URLSearchParams();
    if (userId) params.append('user_id', userId);
    if (courseId) params.append('course_id', courseId);
    if (params.toString()) url += '?' + params.toString();
    
    fetch(url)
        .then(res => {
            if (!res.ok) {
                throw new Error(`API Error: ${res.status}`);
            }
            return res.json();
        })
        .then(conversations => {
            if (conversations.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">No records available</td></tr>';
                return;
            }
            
            // Build table rows
            let html = '';
            conversations.forEach(conv => {
                const createdDate = conv['Created Date'] ? new Date(conv['Created Date']).toLocaleString() : 'N/A';
                html += `
                    <tr onclick="loadConversation('${conv._id}')" style="cursor: pointer;" class="conversation-row">
                        <td>${conv._id ? conv._id.substring(0, 8) + '...' : 'N/A'}</td>
                        <td>${createdDate}</td>
                        <td>${conv.user ? conv.user.substring(0, 8) + '...' : 'N/A'}</td>
                        <td>${conv.assignment ? conv.assignment.substring(0, 8) + '...' : 'N/A'}</td>
                        <td>${conv.course ? conv.course.substring(0, 8) + '...' : 'N/A'}</td>
                    </tr>
                `;
            });
            tbody.innerHTML = html;
            
            // Show success message if filtered
            if (userId || courseId) {
                showAlert(`Found ${conversations.length} filtered conversations`, 'success');
            }
        })
        .catch(err => {
            console.error('Error loading conversations:', err);
            tbody.innerHTML = '<tr><td colspan="5" class="text-center text-danger">API Error: Failed to load conversations</td></tr>';
            showAlert('API Error: Failed to load conversations. Check API key.', 'danger');
        });
}

// Apply filters
function applyFilters() {
    const userId = document.getElementById('filter-user-id').value.trim();
    const courseId = document.getElementById('filter-course-id').value.trim();
    
    if (!userId && !courseId) {
        showAlert('Please enter at least one filter value', 'warning');
        return;
    }
    
    loadConversationsTable(userId, courseId);
}

// Clear filters
function clearFilters() {
    document.getElementById('filter-user-id').value = '';
    document.getElementById('filter-course-id').value = '';
    loadConversationsTable();
    showAlert('Filters cleared', 'info');
}

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

// Function to load conversation messages
function loadConversation(id) {
    console.log('Loading conversation:', id);
    
    // Show chat display area
    document.getElementById('chat-display').style.display = 'block';
    
    // Show loading spinner in chat container
    const chatContainer = document.getElementById('chat-container');
    chatContainer.innerHTML = `
        <div class="text-center py-3">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading messages...</span>
            </div>
            <p class="mt-2">Loading messages...</p>
        </div>
    `;
    
    // Load messages
    fetch(`/api/conversation/${id}`)
        .then(res => {
            if (!res.ok) {
                throw new Error(`API Error: ${res.status}`);
            }
            return res.json();
        })
        .then(data => {
            if (!data.messages || data.messages.length === 0) {
                chatContainer.innerHTML = '<p class="text-center text-muted">No records available</p>';
                return;
            }
            
            // Build chat display
            let html = '';
            data.messages.forEach(msg => {
                const isUser = msg.role === 'user';
                const messageClass = isUser ? 'user' : 'assistant';
                
                html += `
                    <div class="chat-bubble ${messageClass} mb-3">
                        <div class="message-header">
                            <small class="text-muted">${msg.role}</small>
                        </div>
                        <div class="message-content">
                            ${msg.text || 'No content'}
                        </div>
                    </div>
                `;
            });
            
            chatContainer.innerHTML = html;
            
            // Scroll to bottom
            chatContainer.scrollTop = chatContainer.scrollHeight;
        })
        .catch(err => {
            console.error('Error loading conversation:', err);
            chatContainer.innerHTML = 
                '<p class="text-center text-danger">API Error: Failed to load messages</p>';
            showAlert('API Error: Failed to load conversation messages. Check API key.', 'danger');
        });
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
