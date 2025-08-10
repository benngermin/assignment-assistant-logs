// Batch refresh functionality with progress tracking

let currentSyncSession = null;
let progressCheckInterval = null;

// Initialize batch refresh functionality
function initBatchRefresh() {
    // Replace the existing refresh button handler with batch processing
    const refreshBtn = document.querySelector('.btn-activity');
    if (refreshBtn) {
        refreshBtn.removeEventListener('click', refreshBtn.onclick);
        refreshBtn.addEventListener('click', startBatchRefresh);
    }
    
    // Check scheduler status on load
    checkSchedulerStatus();
}

// Start batch refresh with progress tracking
async function startBatchRefresh() {
    const refreshBtn = document.querySelector('.btn-activity');
    
    try {
        // Disable button and show initial state
        refreshBtn.disabled = true;
        refreshBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Starting batch refresh...';
        
        // Show progress modal
        showProgressModal();
        
        // Start async batch refresh
        const response = await fetch('/api/batch-refresh-async', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                batch_size: 200,
                sync_type: 'incremental'
            })
        });
        
        if (!response.ok) {
            throw new Error('Failed to start batch refresh');
        }
        
        const result = await response.json();
        
        if (result.success) {
            currentSyncSession = result.session_id;
            
            // Start monitoring progress
            startProgressMonitoring();
            
        } else {
            throw new Error(result.error || 'Unknown error');
        }
        
    } catch (error) {
        console.error('Error starting batch refresh:', error);
        showAlert('danger', 'Failed to start batch refresh: ' + error.message);
        
        // Reset button
        refreshBtn.disabled = false;
        refreshBtn.innerHTML = '<i class="fas fa-sync-alt me-2"></i>Refresh Data';
        
        // Hide progress modal
        hideProgressModal();
    }
}

// Show progress modal
function showProgressModal() {
    // Create progress modal if it doesn't exist
    let modal = document.getElementById('progressModal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'progressModal';
        modal.className = 'modal fade';
        modal.setAttribute('data-bs-backdrop', 'static');
        modal.innerHTML = `
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="fas fa-sync-alt me-2"></i>
                            Data Refresh Progress
                        </h5>
                    </div>
                    <div class="modal-body">
                        <div class="overall-progress mb-4">
                            <h6>Overall Progress</h6>
                            <div class="progress" style="height: 25px;">
                                <div id="overall-progress-bar" class="progress-bar progress-bar-striped progress-bar-animated" 
                                     role="progressbar" style="width: 0%">0%</div>
                            </div>
                        </div>
                        <div id="progress-details" class="progress-details">
                            <!-- Individual progress bars will be added here -->
                        </div>
                        <div id="progress-messages" class="mt-3">
                            <!-- Status messages will appear here -->
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" onclick="cancelBatchRefresh()">
                            Cancel
                        </button>
                        <button type="button" class="btn btn-primary" id="progress-done-btn" 
                                style="display: none;" data-bs-dismiss="modal">
                            Done
                        </button>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    }
    
    // Show the modal
    const bsModal = new bootstrap.Modal(modal);
    bsModal.show();
}

// Hide progress modal
function hideProgressModal() {
    const modal = document.getElementById('progressModal');
    if (modal) {
        const bsModal = bootstrap.Modal.getInstance(modal);
        if (bsModal) {
            bsModal.hide();
        }
    }
}

// Start monitoring progress
function startProgressMonitoring() {
    if (progressCheckInterval) {
        clearInterval(progressCheckInterval);
    }
    
    // Check progress every second
    progressCheckInterval = setInterval(async () => {
        if (!currentSyncSession) {
            stopProgressMonitoring();
            return;
        }
        
        try {
            const response = await fetch(`/api/batch-refresh-progress/${currentSyncSession}`);
            const data = await response.json();
            
            if (data.success) {
                updateProgressDisplay(data);
                
                // Check if completed
                if (data.status === 'completed' || data.status === 'failed') {
                    stopProgressMonitoring();
                    handleSyncCompletion(data);
                }
            }
        } catch (error) {
            console.error('Error checking progress:', error);
        }
    }, 1000);
}

// Stop monitoring progress
function stopProgressMonitoring() {
    if (progressCheckInterval) {
        clearInterval(progressCheckInterval);
        progressCheckInterval = null;
    }
}

// Update progress display
function updateProgressDisplay(data) {
    // Update overall progress
    const overallBar = document.getElementById('overall-progress-bar');
    if (overallBar) {
        const percentage = data.overall_progress || 0;
        overallBar.style.width = percentage + '%';
        overallBar.textContent = percentage.toFixed(1) + '%';
    }
    
    // Update detailed progress
    const detailsContainer = document.getElementById('progress-details');
    if (detailsContainer && data.detailed_progress) {
        let detailsHTML = '';
        
        const dataTypes = ['users', 'courses', 'assignments', 'conversation_starters', 'conversations', 'messages'];
        
        for (const dtype of dataTypes) {
            const progress = data.detailed_progress[dtype];
            if (progress) {
                const percentage = progress.percentage || 0;
                const current = progress.current || 0;
                const total = progress.total || 0;
                
                detailsHTML += `
                    <div class="progress-item mb-3">
                        <div class="d-flex justify-content-between align-items-center mb-1">
                            <span class="text-capitalize">${dtype.replace('_', ' ')}</span>
                            <small class="text-muted">${current} / ${total}</small>
                        </div>
                        <div class="progress" style="height: 20px;">
                            <div class="progress-bar bg-info" role="progressbar" 
                                 style="width: ${percentage}%">${percentage.toFixed(1)}%</div>
                        </div>
                    </div>
                `;
            }
        }
        
        detailsContainer.innerHTML = detailsHTML;
    }
    
    // Update messages
    const messagesContainer = document.getElementById('progress-messages');
    if (messagesContainer) {
        if (data.status === 'running') {
            messagesContainer.innerHTML = `
                <div class="alert alert-info">
                    <i class="fas fa-info-circle me-2"></i>
                    Synchronizing data in batches of 200 items...
                </div>
            `;
        }
    }
}

// Handle sync completion
function handleSyncCompletion(data) {
    const refreshBtn = document.querySelector('.btn-activity');
    const messagesContainer = document.getElementById('progress-messages');
    const doneBtn = document.getElementById('progress-done-btn');
    
    if (data.status === 'completed') {
        // Show success message
        if (messagesContainer) {
            let successMessage = '<div class="alert alert-success"><i class="fas fa-check-circle me-2"></i>';
            
            if (data.results) {
                let totalSynced = 0;
                for (const [dtype, result] of Object.entries(data.results)) {
                    if (result.count) {
                        totalSynced += result.count;
                    }
                }
                successMessage += `Successfully synchronized ${totalSynced} items!`;
            } else {
                successMessage += 'Data refresh completed successfully!';
            }
            
            successMessage += '</div>';
            messagesContainer.innerHTML = successMessage;
        }
        
        // Show done button
        if (doneBtn) {
            doneBtn.style.display = 'block';
        }
        
        // Reload dashboard data
        setTimeout(() => {
            loadStatistics();
            loadConversations();
            loadComprehensiveMetrics();
            loadCharts();
        }, 1000);
        
        showAlert('success', 'Data refresh completed successfully!');
        
    } else if (data.status === 'failed') {
        // Show error message
        if (messagesContainer) {
            messagesContainer.innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-circle me-2"></i>
                    Sync failed: ${data.error || 'Unknown error'}
                </div>
            `;
        }
        
        // Show done button
        if (doneBtn) {
            doneBtn.style.display = 'block';
        }
        
        showAlert('danger', 'Data refresh failed: ' + (data.error || 'Unknown error'));
    }
    
    // Reset refresh button
    if (refreshBtn) {
        refreshBtn.disabled = false;
        refreshBtn.innerHTML = '<i class="fas fa-sync-alt me-2"></i>Refresh Data';
    }
    
    // Clear session
    currentSyncSession = null;
}

// Cancel batch refresh
function cancelBatchRefresh() {
    stopProgressMonitoring();
    currentSyncSession = null;
    
    const refreshBtn = document.querySelector('.btn-activity');
    if (refreshBtn) {
        refreshBtn.disabled = false;
        refreshBtn.innerHTML = '<i class="fas fa-sync-alt me-2"></i>Refresh Data';
    }
    
    hideProgressModal();
}

// Check scheduler status
async function checkSchedulerStatus() {
    try {
        const response = await fetch('/api/scheduler/status');
        const data = await response.json();
        
        if (data.success && data.scheduler) {
            updateSchedulerStatus(data.scheduler);
        }
    } catch (error) {
        console.error('Error checking scheduler status:', error);
    }
}

// Update scheduler status display
function updateSchedulerStatus(scheduler) {
    // Find or create scheduler status element
    let statusElement = document.getElementById('scheduler-status');
    if (!statusElement) {
        const navBar = document.querySelector('.navbar');
        if (navBar) {
            statusElement = document.createElement('div');
            statusElement.id = 'scheduler-status';
            statusElement.className = 'scheduler-status ms-auto me-3';
            navBar.appendChild(statusElement);
        }
    }
    
    if (statusElement) {
        let statusHTML = '';
        
        if (scheduler.running && scheduler.jobs && scheduler.jobs.length > 0) {
            const nextRun = scheduler.jobs[0].next_run;
            if (nextRun) {
                const nextRunDate = new Date(nextRun);
                const timeUntil = getTimeUntil(nextRunDate);
                statusHTML = `
                    <span class="badge bg-success">
                        <i class="fas fa-clock me-1"></i>
                        Auto-sync in ${timeUntil}
                    </span>
                `;
            }
        } else {
            statusHTML = `
                <span class="badge bg-secondary">
                    <i class="fas fa-pause me-1"></i>
                    Auto-sync disabled
                </span>
            `;
        }
        
        if (scheduler.last_sync) {
            const lastSyncDate = new Date(scheduler.last_sync.date);
            const timeSince = getTimeSince(lastSyncDate);
            statusHTML += `
                <span class="badge bg-info ms-2">
                    <i class="fas fa-history me-1"></i>
                    Last sync: ${timeSince} ago
                </span>
            `;
        }
        
        statusElement.innerHTML = statusHTML;
    }
}

// Get time until a future date
function getTimeUntil(futureDate) {
    const now = new Date();
    const diff = futureDate - now;
    
    if (diff <= 0) {
        return 'now';
    }
    
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(minutes / 60);
    
    if (hours > 0) {
        return `${hours}h ${minutes % 60}m`;
    } else {
        return `${minutes}m`;
    }
}

// Get time since a past date
function getTimeSince(pastDate) {
    const now = new Date();
    const diff = now - pastDate;
    
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);
    
    if (days > 0) {
        return `${days}d`;
    } else if (hours > 0) {
        return `${hours}h`;
    } else {
        return `${minutes}m`;
    }
}

// Add this to the existing initializeDashboard function
document.addEventListener('DOMContentLoaded', function() {
    // Wait for main dashboard to initialize, then add batch refresh
    setTimeout(() => {
        initBatchRefresh();
    }, 1000);
});

// Export functions for use in other scripts
window.batchRefresh = {
    start: startBatchRefresh,
    cancel: cancelBatchRefresh,
    checkStatus: checkSchedulerStatus
};