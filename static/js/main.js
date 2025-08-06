// Assignment Assistant Dashboard - Compact Version
let mainChart;
let currentEnvironment = 'dev'; // Default to dev environment

document.addEventListener('DOMContentLoaded', function() {
    console.log('Assignment Assistant Dashboard loaded');
    
    // Initialize dashboard
    initializeDashboard();
    
    // Set up event listeners
    setupEventListeners();
    
    // Load data
    loadAllData();
});

function initializeDashboard() {
    console.log('Dashboard initialized');
}

function setupEventListeners() {
    // Date range and grouping controls
    const dateRange = document.getElementById('date-range');
    const grouping = document.getElementById('grouping');
    const envSelector = document.getElementById('env-selector');
    
    if (dateRange) {
        dateRange.addEventListener('change', function() {
            loadMainChart();
        });
    }
    
    if (grouping) {
        grouping.addEventListener('change', function() {
            loadMainChart();
        });
    }
    
    if (envSelector) {
        envSelector.addEventListener('change', function() {
            currentEnvironment = this.value;
            console.log(`Switched to ${currentEnvironment} environment`);
            // Reload all data for the new environment
            loadAllData();
        });
    }
    
    console.log('Event listeners set up');
}

function loadAllData() {
    console.log('Loading all data...');
    loadMetrics();
    loadMainChart();
    loadCourseStats();
}

async function loadMetrics() {
    try {
        console.log('Loading metrics...');
        const response = await fetch(`/api/metrics?env=${currentEnvironment}`);
        const data = await response.json();
        
        // Update quick stats
        document.getElementById('total-conversations').textContent = data.total_conversations || 0;
        document.getElementById('total-users').textContent = data.total_users || 0;
        document.getElementById('quiz-count').textContent = data.quiz_count || 0;
        
        // Update activity counts
        document.getElementById('quiz-display').textContent = data.quiz_count || 0;
        document.getElementById('review-count').textContent = data.review_count || 0;
        document.getElementById('takeaway-count').textContent = data.takeaway_count || 0;
        document.getElementById('simplify-count').textContent = data.simplify_count || 0;
        document.getElementById('study-count').textContent = data.study_count || 0;
        document.getElementById('motivate-count').textContent = data.motivate_count || 0;
        
        console.log('Metrics loaded successfully');
    } catch (error) {
        console.error('Error loading metrics:', error);
        // Set fallback values
        ['total-conversations', 'total-users', 'quiz-count', 'quiz-display', 'review-count', 'takeaway-count', 'simplify-count', 'study-count', 'motivate-count'].forEach(id => {
            const element = document.getElementById(id);
            if (element) element.textContent = '0';
        });
    }
}

async function loadMainChart() {
    try {
        const dateRange = document.getElementById('date-range').value || 30;
        const grouping = document.getElementById('grouping').value || 'days';
        
        console.log(`Loading main chart for ${dateRange} days, grouped by ${grouping}...`);
        
        const response = await fetch(`/api/chart/sessions-by-date?days=${dateRange}&grouping=${grouping}&env=${currentEnvironment}`);
        const data = await response.json();
        
        // Destroy existing chart
        if (mainChart) {
            mainChart.destroy();
        }
        
        // Create new chart
        const ctx = document.getElementById('mainChart').getContext('2d');
        
        mainChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.labels || [],
                datasets: [{
                    label: 'Sessions',
                    data: data.data || [],
                    borderColor: '#2E8B57',
                    backgroundColor: 'rgba(46, 139, 87, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 3,
                    pointHoverRadius: 5
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: '#f1f3f4'
                        },
                        ticks: {
                            font: {
                                size: 11
                            },
                            color: '#6c757d'
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        },
                        ticks: {
                            font: {
                                size: 11
                            },
                            color: '#6c757d',
                            maxTicksLimit: 8
                        }
                    }
                },
                elements: {
                    point: {
                        hoverBackgroundColor: '#2E8B57'
                    }
                }
            }
        });
        
        console.log('Main chart loaded successfully');
    } catch (error) {
        console.error('Error loading main chart:', error);
    }
}

async function loadCourseStats() {
    try {
        console.log('Loading course stats...');
        const response = await fetch(`/api/chart/sessions-by-course?env=${currentEnvironment}`);
        const data = await response.json();
        
        const courseList = document.getElementById('course-list');
        
        if (data.labels && data.labels.length > 0) {
            courseList.innerHTML = '';
            
            data.labels.forEach((course, index) => {
                const count = data.data[index];
                const courseItem = document.createElement('div');
                courseItem.className = 'course-item';
                courseItem.innerHTML = `
                    <span class="course-name">${course}</span>
                    <span class="course-count">${count}</span>
                `;
                courseList.appendChild(courseItem);
            });
        } else {
            courseList.innerHTML = '<div class="loading">No course data available</div>';
        }
        
        console.log('Course stats loaded successfully');
    } catch (error) {
        console.error('Error loading course stats:', error);
        document.getElementById('course-list').innerHTML = '<div class="loading">Error loading courses</div>';
    }
}

// Utility function to format numbers
function formatNumber(num) {
    if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'k';
    }
    return num.toString();
}