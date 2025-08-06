// Assignment Assistant Dashboard - Main JavaScript

// Global flag to track initialization
let dashboardInitialized = false;

function initializeDashboard() {
    // Prevent double initialization
    if (dashboardInitialized) {
        console.log('Dashboard already initialized, skipping...');
        return;
    }
    dashboardInitialized = true;
    
    console.log('Dashboard initialized');
    
    // Initialize environment toggle
    initializeEnvironmentToggle();
    
    // Load initial statistics
    loadStatistics();
    
    // Load conversations
    loadConversations();
    
    // Load comprehensive metrics
    loadComprehensiveMetrics();
    
    // Load charts
    loadCharts();
    
    // Set up event listeners
    setupEventListeners();
    
    // Set up refresh button
    const refreshBtn = document.querySelector('.btn-activity');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', function() {
            loadStatistics();
            loadConversations();
            loadComprehensiveMetrics();
            loadCharts();
            showAlert('success', 'Data refreshed successfully!');
        });
    }
    
    console.log('Event listeners set up');
}

// Initialize environment toggle functionality
function initializeEnvironmentToggle() {
    // Get current environment from server
    fetch('/api/environment')
        .then(response => response.json())
        .then(data => {
            const currentEnv = data.environment || 'dev';
            
            // Set the correct radio button
            if (currentEnv === 'live') {
                document.getElementById('env-live').checked = true;
                document.getElementById('env-status').innerHTML = '<i class="fas fa-circle text-success"></i> Live';
            } else {
                document.getElementById('env-dev').checked = true;
                document.getElementById('env-status').innerHTML = '<i class="fas fa-circle text-primary"></i> Dev';
            }
        })
        .catch(error => {
            console.error('Error getting environment:', error);
        });
    
    // Add event listeners to environment radio buttons
    const envRadios = document.querySelectorAll('input[name="environment"]');
    envRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            const newEnv = this.value;
            
            // Show loading state
            const statusElement = document.getElementById('env-status');
            statusElement.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Switching...';
            
            // Send environment change to server
            fetch('/api/environment', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ environment: newEnv })
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    throw new Error(data.error);
                }
                
                // Update status display
                if (newEnv === 'live') {
                    statusElement.innerHTML = '<i class="fas fa-circle text-success"></i> Live';
                    showAlert('success', 'Switched to Live environment');
                } else {
                    statusElement.innerHTML = '<i class="fas fa-circle text-primary"></i> Dev';
                    showAlert('success', 'Switched to Dev environment');
                }
                
                // Reload all data with new environment
                loadStatistics();
                loadConversations();
                loadComprehensiveMetrics();
                loadCharts();
            })
            .catch(error => {
                console.error('Error switching environment:', error);
                showAlert('danger', `Failed to switch environment: ${error.message}`);
                
                // Revert the radio button
                if (newEnv === 'live') {
                    document.getElementById('env-dev').checked = true;
                    statusElement.innerHTML = '<i class="fas fa-circle text-primary"></i> Dev';
                } else {
                    document.getElementById('env-live').checked = true;
                    statusElement.innerHTML = '<i class="fas fa-circle text-success"></i> Live';
                }
            });
        });
    });
}

// Load basic statistics
function loadStatistics() {
    console.log('Loading statistics...');
    
    fetch('/api/stats')
        .then(response => response.json())
        .then(data => {
            // Update statistics in the UI
            updateStatElement('total-users', data.users || 0);
            updateStatElement('total-conversations', data.conversations || 0);
            updateStatElement('total-messages', data.messages || 0);
            
            // Calculate average
            const avgMessages = data.conversations > 0 
                ? (data.messages / data.conversations).toFixed(1) 
                : 0;
            updateStatElement('avg-messages', avgMessages);
            
            // Show error messages if any
            if (data.users_error) {
                console.error('Users API error:', data.users_error);
                showAlert('warning', 'Unable to load user data. API may be down.');
            }
            
            if (data.conversations_error) {
                console.error('Conversations API error:', data.conversations_error);
                showAlert('warning', 'Unable to load conversation data. API may be down.');
            }
            
            if (data.messages_error) {
                console.error('Messages API error:', data.messages_error);
                showAlert('warning', 'Unable to load message data. API may be down.');
            }
        })
        .catch(error => {
            console.error('Error loading statistics:', error);
            showAlert('danger', 'Failed to load statistics. Please try again.');
            
            // Show zeros on error
            updateStatElement('total-users', 0);
            updateStatElement('total-conversations', 0);
            updateStatElement('total-messages', 0);
            updateStatElement('avg-messages', 0);
        });
}

// Load comprehensive metrics
function loadComprehensiveMetrics() {
    console.log('Loading comprehensive metrics...');
    
    fetch('/api/metrics')
        .then(response => response.json())
        .then(data => {
            // Update feature counts
            updateStatElement('quiz-count', data.quiz_count || 0);
            updateStatElement('review-count', data.review_count || 0);
            updateStatElement('takeaway-count', data.takeaway_count || 0);
            updateStatElement('simplify-count', data.simplify_count || 0);
            updateStatElement('study-count', data.study_count || 0);
            updateStatElement('motivate-count', data.motivate_count || 0);
            
            // Handle errors
            if (data.error) {
                console.error('Metrics API error:', data.error);
                showAlert('warning', 'Unable to load complete metrics. Check API key.');
            }
        })
        .catch(error => {
            console.error('Error loading metrics:', error);
            
            // Set all counts to 0 on error
            updateStatElement('quiz-count', 0);
            updateStatElement('review-count', 0);
            updateStatElement('takeaway-count', 0);
            updateStatElement('simplify-count', 0);
            updateStatElement('study-count', 0);
            updateStatElement('motivate-count', 0);
        });
}

// Load conversations with optional filters
function loadConversations() {
    console.log('Loading conversations...');
    
    const email = document.getElementById('email-filter')?.value || '';
    const courseNumber = document.getElementById('course-number-filter')?.value || '';
    const dateStart = document.getElementById('date-start-filter')?.value || '';
    const dateEnd = document.getElementById('date-end-filter')?.value || '';
    
    let url = '/api/conversations';
    const params = new URLSearchParams();
    if (email) params.append('email', email);
    if (courseNumber) params.append('course_number', courseNumber);
    if (dateStart) params.append('date_start', dateStart);
    if (dateEnd) params.append('date_end', dateEnd);
    if (params.toString()) url += '?' + params.toString();
    
    const conversationsList = document.getElementById('conversations-list');
    conversationsList.innerHTML = `
        <div class="loading-message">
            <span class="spinner-border spinner-border-sm me-2" role="status"></span>
            Loading conversations...
        </div>
    `;
    
    fetch(url)
        .then(response => response.json())
        .then(conversations => {
            if (conversations.length === 0) {
                conversationsList.innerHTML = `
                    <div class="empty-state">
                        <i class="fas fa-inbox"></i>
                        <p>No conversations found</p>
                    </div>
                `;
                return;
            }
            
            // Clear existing content
            conversationsList.innerHTML = '';
            
            conversations.forEach(conv => {
                const date = new Date(conv['Created Date']).toLocaleDateString();
                const time = new Date(conv['Created Date']).toLocaleTimeString('en-US', { 
                    hour: '2-digit', 
                    minute: '2-digit' 
                });
                
                // Extract email from user field if available
                const userEmail = conv.user_email || conv.user || 'Unknown User';
                const courseInfo = conv.course || 'No Course';
                const assignmentInfo = conv.assignment || 'No Assignment';
                
                // Create elements safely using createElement and textContent
                const conversationItem = document.createElement('div');
                conversationItem.className = 'conversation-item';
                conversationItem.onclick = () => showMessages(conv._id);
                
                // Create header
                const header = document.createElement('div');
                header.className = 'conversation-header';
                
                const idSpan = document.createElement('span');
                idSpan.className = 'conversation-id';
                const idIcon = document.createElement('i');
                idIcon.className = 'fas fa-hashtag';
                idSpan.appendChild(idIcon);
                idSpan.appendChild(document.createTextNode(' ' + conv._id.substring(0, 8)));
                
                const dateSpan = document.createElement('span');
                dateSpan.className = 'conversation-date';
                const dateIcon = document.createElement('i');
                dateIcon.className = 'fas fa-calendar';
                dateSpan.appendChild(dateIcon);
                dateSpan.appendChild(document.createTextNode(' ' + date + ' at ' + time));
                
                header.appendChild(idSpan);
                header.appendChild(dateSpan);
                
                // Create details
                const details = document.createElement('div');
                details.className = 'conversation-details';
                
                // Helper function to create detail rows
                function createDetailRow(label, value) {
                    const row = document.createElement('div');
                    row.className = 'detail-row';
                    
                    const labelSpan = document.createElement('span');
                    labelSpan.className = 'detail-label';
                    labelSpan.textContent = label + ':';
                    
                    const valueSpan = document.createElement('span');
                    valueSpan.className = 'detail-value';
                    valueSpan.textContent = value;
                    
                    row.appendChild(labelSpan);
                    row.appendChild(valueSpan);
                    return row;
                }
                
                details.appendChild(createDetailRow('Email', userEmail));
                details.appendChild(createDetailRow('Course', courseInfo));
                details.appendChild(createDetailRow('Assignment', assignmentInfo));
                details.appendChild(createDetailRow('Messages', conv.message_count || 0));
                
                conversationItem.appendChild(header);
                conversationItem.appendChild(details);
                conversationsList.appendChild(conversationItem);
            });
        })
        .catch(error => {
            console.error('Error loading conversations:', error);
            conversationsList.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-exclamation-triangle"></i>
                    <p>Failed to load conversations</p>
                </div>
            `;
            showAlert('danger', 'Failed to load conversations. Please check your connection.');
        });
}

// Clear all filters and reload conversations
function clearFilters() {
    document.getElementById('email-filter').value = '';
    document.getElementById('course-number-filter').value = '';
    document.getElementById('date-start-filter').value = '';
    document.getElementById('date-end-filter').value = '';
    loadConversations();
}

// Show messages for a specific conversation
function showMessages(conversationId) {
    console.log('Loading messages for conversation:', conversationId);
    
    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('messagesModal'));
    modal.show();
    
    // Set loading state
    const messagesContainer = document.getElementById('messages-container');
    messagesContainer.innerHTML = `
        <div class="loading-message">
            <span class="spinner-border spinner-border-sm me-2" role="status"></span>
            Loading messages...
        </div>
    `;
    
    // Fetch messages
    fetch(`/api/conversation/${conversationId}`)
        .then(response => response.json())
        .then(data => {
            if (!data.messages || data.messages.length === 0) {
                messagesContainer.innerHTML = `
                    <div class="empty-state">
                        <i class="fas fa-comment-slash"></i>
                        <p>No messages found in this conversation</p>
                    </div>
                `;
                return;
            }
            
            // Clear existing content
            messagesContainer.innerHTML = '';
            
            const messagesList = document.createElement('div');
            messagesList.className = 'messages-list';
            
            data.messages.forEach(msg => {
                const role = msg.role || 'user';
                const messageClass = role === 'assistant' ? 'assistant' : 'user';
                const date = msg['Created Date'] ? new Date(msg['Created Date']).toLocaleString() : '';
                
                // Create message item safely
                const messageItem = document.createElement('div');
                messageItem.className = `message-item ${messageClass}`;
                
                // Create header
                const messageHeader = document.createElement('div');
                messageHeader.className = 'message-header';
                
                const roleSpan = document.createElement('span');
                roleSpan.className = 'message-role';
                roleSpan.textContent = role;
                
                const dateSpan = document.createElement('span');
                dateSpan.className = 'message-date';
                dateSpan.textContent = date;
                
                messageHeader.appendChild(roleSpan);
                messageHeader.appendChild(dateSpan);
                
                // Create message text
                const messageText = document.createElement('div');
                messageText.className = 'message-text';
                messageText.textContent = msg.text || 'No content';
                
                messageItem.appendChild(messageHeader);
                messageItem.appendChild(messageText);
                messagesList.appendChild(messageItem);
            });
            
            messagesContainer.appendChild(messagesList);
        })
        .catch(error => {
            console.error('Error loading messages:', error);
            messagesContainer.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-exclamation-triangle"></i>
                    <p>Failed to load messages</p>
                </div>
            `;
            showAlert('danger', 'Failed to load messages. Please try again.');
        });
}

// Update stat element with animation
function updateStatElement(elementId, value) {
    const element = document.getElementById(elementId);
    if (element) {
        // Remove spinner and add value with animation
        element.innerHTML = value;
        element.style.opacity = '0';
        setTimeout(() => {
            element.style.transition = 'opacity 0.5s ease';
            element.style.opacity = '1';
        }, 100);
    }
}

// Show alert message
function showAlert(type, message) {
    const alertContainer = document.getElementById('alert-container');
    const alertId = 'alert-' + Date.now();
    
    // Create alert safely using createElement
    const alertDiv = document.createElement('div');
    alertDiv.id = alertId;
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.setAttribute('role', 'alert');
    
    // Set message text safely
    alertDiv.textContent = message;
    
    // Create close button
    const closeButton = document.createElement('button');
    closeButton.type = 'button';
    closeButton.className = 'btn-close';
    closeButton.setAttribute('data-bs-dismiss', 'alert');
    
    alertDiv.appendChild(closeButton);
    alertContainer.appendChild(alertDiv);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        const alertElement = document.getElementById(alertId);
        if (alertElement) {
            const bsAlert = new bootstrap.Alert(alertElement);
            bsAlert.close();
        }
    }, 5000);
}

// Chart instances
let dateChart = null;
let courseChart = null;
let activityChart = null;

// Chart colors
const chartColors = {
    primary: '#667eea',
    secondary: '#764ba2',
    success: '#10b981',
    warning: '#f59e0b',
    danger: '#ef4444',
    info: '#3b82f6'
};

// Load chart data and create charts
function loadCharts() {
    console.log('Loading charts...');
    loadDateChart();
    loadCourseChart();
    loadActivityChart();
}

function loadDateChart(days = 30, grouping = 'days') {
    console.log(`Loading date chart for ${days} days, grouped by ${grouping}...`);
    
    fetch(`/api/chart/sessions-by-date?days=${days}&grouping=${grouping}`)
        .then(response => response.json())
        .then(data => {
            const ctx = document.getElementById('dateChart').getContext('2d');
            
            // Destroy existing chart if exists
            if (dateChart) {
                dateChart.destroy();
            }
            
            // Format labels based on grouping
            let formattedLabels = data.labels;
            if (grouping === 'days') {
                formattedLabels = data.labels.map(label => {
                    const date = new Date(label);
                    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
                });
            } else if (grouping === 'weeks') {
                // Labels are already formatted as "Jan 01 - Jan 07"
                formattedLabels = data.labels;
            } else if (grouping === 'months') {
                // Labels are already formatted as "January 2025"
                formattedLabels = data.labels;
            }
            
            dateChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: formattedLabels,
                    datasets: [{
                        label: 'Sessions',
                        data: data.data,
                        borderColor: chartColors.info,
                        backgroundColor: chartColors.info + '20',
                        borderWidth: 3,
                        fill: true,
                        tension: 0.4,
                        pointBackgroundColor: chartColors.info,
                        pointBorderColor: '#ffffff',
                        pointBorderWidth: 2,
                        pointRadius: 6,
                        pointHoverRadius: 8
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        },
                        tooltip: {
                            backgroundColor: 'rgba(0, 0, 0, 0.8)',
                            titleColor: '#ffffff',
                            bodyColor: '#ffffff',
                            borderColor: chartColors.info,
                            borderWidth: 1
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: {
                                color: 'rgba(0, 0, 0, 0.1)'
                            }
                        },
                        x: {
                            grid: {
                                display: false
                            },
                            ticks: {
                                maxTicksLimit: grouping === 'days' ? 10 : undefined
                            }
                        }
                    }
                }
            });
        })
        .catch(error => {
            console.error('Error loading date chart:', error);
        });
}

function loadCourseChart() {
    console.log('Loading course chart...');
    
    fetch('/api/chart/sessions-by-course')
        .then(response => response.json())
        .then(data => {
            const ctx = document.getElementById('courseChart').getContext('2d');
            
            // Destroy existing chart if exists
            if (courseChart) {
                courseChart.destroy();
            }
            
            courseChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: data.labels,
                    datasets: [{
                        label: 'Sessions',
                        data: data.data,
                        backgroundColor: chartColors.warning,
                        borderColor: chartColors.warning,
                        borderWidth: 1,
                        borderRadius: 6,
                        borderSkipped: false
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        },
                        tooltip: {
                            backgroundColor: 'rgba(0, 0, 0, 0.8)',
                            titleColor: '#ffffff',
                            bodyColor: '#ffffff',
                            borderColor: chartColors.warning,
                            borderWidth: 1
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: {
                                color: 'rgba(0, 0, 0, 0.1)'
                            }
                        },
                        x: {
                            grid: {
                                display: false
                            }
                        }
                    }
                }
            });
        })
        .catch(error => {
            console.error('Error loading course chart:', error);
        });
}

function loadActivityChart() {
    console.log('Loading activity chart...');
    
    fetch('/api/chart/sessions-by-activity')
        .then(response => response.json())
        .then(data => {
            const ctx = document.getElementById('activityChart').getContext('2d');
            
            // Destroy existing chart if exists
            if (activityChart) {
                activityChart.destroy();
            }
            
            activityChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: data.labels,
                    datasets: [{
                        label: 'Sessions',
                        data: data.data,
                        backgroundColor: chartColors.success,
                        borderColor: chartColors.success,
                        borderWidth: 1,
                        borderRadius: 6,
                        borderSkipped: false
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        },
                        tooltip: {
                            backgroundColor: 'rgba(0, 0, 0, 0.8)',
                            titleColor: '#ffffff',
                            bodyColor: '#ffffff',
                            borderColor: chartColors.success,
                            borderWidth: 1
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: {
                                color: 'rgba(0, 0, 0, 0.1)'
                            }
                        },
                        x: {
                            grid: {
                                display: false
                            }
                        }
                    }
                }
            });
        })
        .catch(error => {
            console.error('Error loading activity chart:', error);
        });
}

// Setup event listeners
function setupEventListeners() {
    console.log('Event listeners set up');
    
    // Date range selector change event
    const dateRangeSelector = document.getElementById('date-range-selector');
    const dateGroupingSelector = document.getElementById('date-grouping-selector');
    
    function reloadDateChart() {
        const days = parseInt(dateRangeSelector?.value || 30);
        const grouping = dateGroupingSelector?.value || 'days';
        loadDateChart(days, grouping);
    }
    
    if (dateRangeSelector) {
        dateRangeSelector.addEventListener('change', reloadDateChart);
    }
    
    if (dateGroupingSelector) {
        dateGroupingSelector.addEventListener('change', reloadDateChart);
    }
}

// Initialize dashboard when page loads
document.addEventListener('DOMContentLoaded', function() {
    console.log('Assignment Assistant Dashboard loaded');
    initializeDashboard();
});

// Export functions for global use
window.loadConversations = loadConversations;
window.showMessages = showMessages;