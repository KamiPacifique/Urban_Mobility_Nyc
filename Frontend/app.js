const API_BASE_URL = 'http://localhost:5001/api';

// == STATE MANAGEMENT ==
const state = {
    currentView: 'overview',
    currentPage: 1,
    perPage: 50,
    filters: {
        borough: '',
        hour: '',
        weekend: '',
        minFare: '',
        maxFare: ''
    },
    stats: null,
    charts: {}
};

// == API CALLS ==
async function fetchAPI(endpoint, params = {}) {
    const queryString = new URLSearchParams(params).toString();
    const url = `${API_BASE_URL}${endpoint}${queryString ? '?' + queryString : ''}`;
    
    try {
        const response = await fetch(url);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// == INITIALIZATION ==
document.addEventListener('DOMContentLoaded', async () => {
    showLoading(true);
    
    try {
        // Load initial data
        await loadHeaderStats();
        await loadOverviewData();
        
        // Setup event listeners
        setupEventListeners();
        
        showLoading(false);
    } catch (error) {
        console.error('Initialization error:', error);
        showLoading(false);
        alert('Failed to load dashboard data. Please ensure the backend API is running.');
    }
});

// == HEADER STATS ==
async function loadHeaderStats() {
    const stats = await fetchAPI('/stats');
    state.stats = stats;
    
    const headerStats = document.getElementById('headerStats');
    headerStats.innerHTML = `
        <div class="stat-item">
            <span class="stat-value">${formatNumber(stats.total_trips)}</span>
            <span class="stat-label">Total Trips</span>
        </div>
        <div class="stat-item">
            <span class="stat-value">$${stats.averages.fare.toFixed(2)}</span>
            <span class="stat-label">Avg Fare</span>
        </div>
        <div class="stat-item">
            <span class="stat-value">$${formatNumber(stats.averages.total_revenue)}</span>
            <span class="stat-label">Total Revenue</span>
        </div>
    `;
}

// == OVERVIEW VIEW ==
async function loadOverviewData() {
    // Load all overview data in parallel
    const [fareDistribution, boroughStats, weekendComparison] = await Promise.all([
        fetchAPI('/analytics/fare-distribution'),
        fetchAPI('/analytics/by-borough'),
        fetchAPI('/analytics/weekend-vs-weekday')
    ]);
    
    // Render KPIs
    renderKPIMetrics();
    
    // Render charts
    renderFareDistributionChart(fareDistribution);
    renderBoroughChart(boroughStats);
    renderWeekendComparisonChart(weekendComparison);
    
    // Load quick insights
    loadQuickInsights(boroughStats, weekendComparison);
}

function renderKPIMetrics() {
    const kpiContainer = document.getElementById('kpiMetrics');
    const metrics = [
        { label: 'Avg Distance', value: state.stats.averages.distance.toFixed(2), unit: 'mi' },
        { label: 'Avg Duration', value: state.stats.averages.duration.toFixed(0), unit: 'min' },
        { label: 'Avg Tip', value: state.stats.averages.tip_percentage.toFixed(1), unit: '%' },
        { label: 'Total Zones', value: state.stats.total_zones, unit: '' }
    ];
    
    kpiContainer.innerHTML = metrics.map(m => `
        <div class="metric-card">
            <div class="metric-label">${m.label}</div>
            <div class="metric-value">${m.value}${m.unit}</div>
        </div>
    `).join('');
}

function renderFareDistributionChart(data) {
    const ctx = document.getElementById('fareDistributionChart').getContext('2d');
    
    if (state.charts.fareDistribution) {
        state.charts.fareDistribution.destroy();
    }
    
    state.charts.fareDistribution = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.map(d => `$${d.range}`),
            datasets: [{
                label: 'Number of Trips',
                data: data.map(d => d.count),
                backgroundColor: 'rgba(37, 99, 235, 0.8)',
                borderColor: 'rgba(37, 99, 235, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: (context) => `Trips: ${formatNumber(context.raw)}`
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: { color: '#94a3b8' },
                    grid: { color: 'rgba(51, 65, 85, 0.3)' }
                },
                x: {
                    ticks: { color: '#94a3b8' },
                    grid: { display: false }
                }
            }
        }
    });
}

function renderBoroughChart(data) {
    const ctx = document.getElementById('boroughChart').getContext('2d');
    
    if (state.charts.borough) {
        state.charts.borough.destroy();
    }
    
    const colors = [
        'rgba(37, 99, 235, 0.8)',
        'rgba(16, 185, 129, 0.8)',
        'rgba(245, 158, 11, 0.8)',
        'rgba(239, 68, 68, 0.8)',
        'rgba(139, 92, 246, 0.8)'
    ];
    
    state.charts.borough = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: data.map(d => d.borough),
            datasets: [{
                data: data.map(d => d.trip_count),
                backgroundColor: colors,
                borderColor: '#1e293b',
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { color: '#f1f5f9', padding: 15 }
                },
                tooltip: {
                    callbacks: {
                        label: (context) => {
                            const label = context.label || '';
                            const value = formatNumber(context.raw);
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((context.raw / total) * 100).toFixed(1);
                            return `${label}: ${value} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

function renderWeekendComparisonChart(data) {
    const ctx = document.getElementById('weekendComparisonChart').getContext('2d');
    
    if (state.charts.weekendComparison) {
        state.charts.weekendComparison.destroy();
    }
    
    const weekday = data.weekday || {};
    const weekend = data.weekend || {};
    
    state.charts.weekendComparison = new Chart(ctx, {
        type: 'radar',
        data: {
            labels: ['Trip Count', 'Avg Fare', 'Avg Distance', 'Avg Duration', 'Avg Tip %'],
            datasets: [
                {
                    label: 'Weekday',
                    data: [
                        weekday.trip_count / 1000,
                        weekday.avg_fare,
                        weekday.avg_distance,
                        weekday.avg_duration,
                        weekday.avg_tip_pct
                    ],
                    backgroundColor: 'rgba(37, 99, 235, 0.2)',
                    borderColor: 'rgba(37, 99, 235, 1)',
                    borderWidth: 2
                },
                {
                    label: 'Weekend',
                    data: [
                        weekend.trip_count / 1000,
                        weekend.avg_fare,
                        weekend.avg_distance,
                        weekend.avg_duration,
                        weekend.avg_tip_pct
                    ],
                    backgroundColor: 'rgba(16, 185, 129, 0.2)',
                    borderColor: 'rgba(16, 185, 129, 1)',
                    borderWidth: 2
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'top',
                    labels: { color: '#f1f5f9' }
                }
            },
            scales: {
                r: {
                    beginAtZero: true,
                    ticks: { color: '#94a3b8' },
                    grid: { color: 'rgba(51, 65, 85, 0.3)' },
                    pointLabels: { color: '#f1f5f9' }
                }
            }
        }
    });
}

// == TEMPORAL PATTERNS VIEW ==
async function loadTemporalData() {
    showLoading(true);
    const hourlyData = await fetchAPI('/analytics/hourly');
    
    renderHourlyChart(hourlyData);
    renderPeakHoursChart(hourlyData);
    renderHourlyRevenueChart(hourlyData);
    
    showLoading(false);
}

function renderHourlyChart(data) {
    const ctx = document.getElementById('hourlyChart').getContext('2d');
    
    if (state.charts.hourly) {
        state.charts.hourly.destroy();
    }
    
    state.charts.hourly = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.map(d => `${d.hour}:00`),
            datasets: [{
                label: 'Trip Count',
                data: data.map(d => d.trip_count),
                borderColor: 'rgba(37, 99, 235, 1)',
                backgroundColor: 'rgba(37, 99, 235, 0.1)',
                fill: true,
                tension: 0.4,
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { labels: { color: '#f1f5f9' } },
                tooltip: {
                    callbacks: {
                        label: (context) => `Trips: ${formatNumber(context.raw)}`
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: { color: '#94a3b8' },
                    grid: { color: 'rgba(51, 65, 85, 0.3)' }
                },
                x: {
                    ticks: { color: '#94a3b8' },
                    grid: { color: 'rgba(51, 65, 85, 0.3)' }
                }
            }
        }
    });
}

function renderPeakHoursChart(data) {
    const ctx = document.getElementById('peakHoursChart').getContext('2d');
    
    if (state.charts.peakHours) {
        state.charts.peakHours.destroy();
    }
    
    // Get top 8 busiest hours
    const sorted = [...data].sort((a, b) => b.trip_count - a.trip_count).slice(0, 8);
    
    state.charts.peakHours = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: sorted.map(d => `${d.hour}:00`),
            datasets: [{
                label: 'Trip Count',
                data: sorted.map(d => d.trip_count),
                backgroundColor: 'rgba(245, 158, 11, 0.8)',
                borderColor: 'rgba(245, 158, 11, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: (context) => `Trips: ${formatNumber(context.raw)}`
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: { color: '#94a3b8' },
                    grid: { color: 'rgba(51, 65, 85, 0.3)' }
                },
                x: {
                    ticks: { color: '#94a3b8' },
                    grid: { display: false }
                }
            }
        }
    });
}

function renderHourlyRevenueChart(data) {
    const ctx = document.getElementById('hourlyRevenueChart').getContext('2d');
    
    if (state.charts.hourlyRevenue) {
        state.charts.hourlyRevenue.destroy();
    }
    
    state.charts.hourlyRevenue = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.map(d => `${d.hour}:00`),
            datasets: [{
                label: 'Revenue ($)',
                data: data.map(d => d.total_revenue),
                backgroundColor: 'rgba(16, 185, 129, 0.8)',
                borderColor: 'rgba(16, 185, 129, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: (context) => `Revenue: $${formatNumber(context.raw)}`
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: { 
                        color: '#94a3b8',
                        callback: (value) => '$' + formatNumber(value)
                    },
                    grid: { color: 'rgba(51, 65, 85, 0.3)' }
                },
                x: {
                    ticks: { color: '#94a3b8' },
                    grid: { display: false }
                }
            }
        }
    });
}

// == SPATIAL VIEW ==
let map = null;

async function loadSpatialData() {
    showLoading(true);
    
    const [geojson, boroughStats] = await Promise.all([
        fetchAPI('/zones/geojson'),
        fetchAPI('/analytics/by-borough')
    ]);
    
    initializeMap(geojson, boroughStats);
    renderTopPickups(boroughStats);
    
    showLoading(false);
}

function initializeMap(geojson, boroughStats) {
    const mapContainer = document.getElementById('map');
    
    if (map) {
        map.remove();
    }
    
    // Create map centered on NYC
    map = L.map('map').setView([40.7128, -74.0060], 11);
    
    // Add dark tile layer
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; OpenStreetMap contributors &copy; CARTO',
        maxZoom: 19
    }).addTo(map);
    
    // Create a lookup for trip counts by borough
    const boroughData = {};
    boroughStats.forEach(b => {
        boroughData[b.borough] = b.trip_count;
    });
    
    // Calculate max trips for color scaling
    const maxTrips = Math.max(...boroughStats.map(b => b.trip_count));
    
    // Add GeoJSON layer with styling
    L.geoJSON(geojson, {
        style: (feature) => {
            const borough = feature.properties.borough;
            const tripCount = boroughData[borough] || 0;
            const opacity = 0.3 + (tripCount / maxTrips) * 0.5;
            
            return {
                fillColor: getColorForBorough(borough),
                weight: 1,
                opacity: 1,
                color: '#ffffff',
                fillOpacity: opacity
            };
        },
        onEachFeature: (feature, layer) => {
            const props = feature.properties;
            const borough = props.borough;
            const tripCount = boroughData[borough] || 0;
            
            layer.bindPopup(`
                <div style="color: #000;">
                    <strong>${props.zone}</strong><br>
                    Borough: ${borough}<br>
                    Location ID: ${props.location_id}<br>
                    Trips from ${borough}: ${formatNumber(tripCount)}
                </div>
            `);
            
            layer.on('mouseover', function() {
                this.setStyle({ fillOpacity: 0.8 });
            });
            
            layer.on('mouseout', function() {
                const opacity = 0.3 + (tripCount / maxTrips) * 0.5;
                this.setStyle({ fillOpacity: opacity });
            });
        }
    }).addTo(map);
}

function getColorForBorough(borough) {
    const colors = {
        'Manhattan': '#2563eb',
        'Brooklyn': '#10b981',
        'Queens': '#f59e0b',
        'Bronx': '#ef4444',
        'Staten Island': '#8b5cf6',
        'EWR': '#6366f1'
    };
    return colors[borough] || '#64748b';
}

function renderTopPickups(boroughStats) {
    const container = document.getElementById('topPickups');
    const sorted = [...boroughStats].sort((a, b) => b.trip_count - a.trip_count);
    
    container.innerHTML = sorted.map((item, index) => `
        <div class="list-item">
            <span class="list-rank">#${index + 1}</span>
            <span class="list-name">${item.borough}</span>
            <span class="list-value">${formatNumber(item.trip_count)} trips</span>
        </div>
    `).join('');
}

// ==================== ROUTES VIEW ====================
async function loadRoutesData() {
    showLoading(true);
    const routes = await fetchAPI('/analytics/top-routes', { limit: 20 });
    renderRoutesTable(routes);
    showLoading(false);
}

function renderRoutesTable(routes) {
    const tbody = document.getElementById('routesTableBody');
    tbody.innerHTML = routes.map((route, index) => `
        <tr>
            <td><span class="rank-badge">${index + 1}</span></td>
            <td>
                <div class="zone-info">
                    <strong>${route.pickup_zone}</strong>
                    <span class="borough-tag">${route.pickup_borough}</span>
                </div>
            </td>
            <td>
                <div class="zone-info">
                    <strong>${route.dropoff_zone}</strong>
                    <span class="borough-tag">${route.dropoff_borough}</span>
                </div>
            </td>
            <td>${formatNumber(route.trip_count)}</td>
            <td>$${route.avg_fare.toFixed(2)}</td>
            <td>${route.avg_distance.toFixed(2)} mi</td>
        </tr>
    `).join('');
}

// ==================== TRIPS VIEW ====================
async function loadTripsData() {
    showLoading(true);
    
    const params = {
        page: state.currentPage,
        per_page: state.perPage,
        ...state.filters
    };
    
    const data = await fetchAPI('/trips', params);
    renderTripsTable(data.trips);
    updatePagination(data.pagination);
    
    showLoading(false);
}

function renderTripsTable(trips) {
    const tbody = document.getElementById('tripsTableBody');
    tbody.innerHTML = trips.map(trip => `
        <tr>
            <td>${formatDateTime(trip.pickup_datetime)}</td>
            <td>
                <div class="zone-info">
                    <strong>${trip.pickup_zone || 'Unknown'}</strong>
                    <span class="borough-tag">${trip.pickup_borough || 'N/A'}</span>
                </div>
            </td>
            <td>
                <div class="zone-info">
                    <strong>${trip.dropoff_zone || 'Unknown'}</strong>
                    <span class="borough-tag">${trip.dropoff_borough || 'N/A'}</span>
                </div>
            </td>
            <td>${trip.trip_distance.toFixed(2)} mi</td>
            <td>${trip.duration_min.toFixed(0)} min</td>
            <td>$${trip.fare_amount.toFixed(2)}</td>
            <td><span class="tip-badge">${trip.tip_pct ? trip.tip_pct.toFixed(1) : '0'}%</span></td>
        </tr>
    `).join('');
}

function updatePagination(pagination) {
    document.getElementById('pageInfo').textContent = `Page ${pagination.page} of ${pagination.pages}`;
    document.getElementById('prevPage').disabled = pagination.page <= 1;
    document.getElementById('nextPage').disabled = pagination.page >= pagination.pages;
}

// ==================== EVENT LISTENERS ====================
function setupEventListeners() {
    // View toggle
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const view = btn.getAttribute('data-view');
            switchView(view);
        });
    });
    
    // Filters
    document.getElementById('applyFilters').addEventListener('click', applyFilters);
    document.getElementById('resetFilters').addEventListener('click', resetFilters);
    
    // Pagination
    document.getElementById('prevPage').addEventListener('click', () => {
        if (state.currentPage > 1) {
            state.currentPage--;
            loadTripsData();
        }
    });
    
    document.getElementById('nextPage').addEventListener('click', () => {
        state.currentPage++;
        loadTripsData();
    });
}

function switchView(viewName) {
    // Update state
    state.currentView = viewName;
    
    // Update UI
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.getAttribute('data-view') === viewName);
    });
    
    document.querySelectorAll('.view-content').forEach(view => {
        view.classList.remove('active');
    });
    
    document.getElementById(`${viewName}View`).classList.add('active');
    
    // Load view-specific data
    switch(viewName) {
        case 'temporal':
            loadTemporalData();
            break;
        case 'spatial':
            loadSpatialData();
            break;
        case 'routes':
            loadRoutesData();
            break;
        case 'trips':
            loadTripsData();
            break;
    }
}

function applyFilters() {
    // Get filter values
    state.filters.borough = document.getElementById('boroughFilter').value;
    state.filters.weekend = document.getElementById('weekendFilter').value;
    
    const hourRange = document.getElementById('hourFilter').value;
    if (hourRange) {
        const [start] = hourRange.split('-');
        state.filters.hour = start;
    } else {
        state.filters.hour = '';
    }
    
    state.filters.minFare = document.getElementById('minFare').value;
    state.filters.maxFare = document.getElementById('maxFare').value;
    
    // Reset to first page
    state.currentPage = 1;
    
    // Reload current view data based on active view
    switch(state.currentView) {
        case 'trips':
            loadTripsData();
            break;
        case 'routes':
            loadRoutesData();
            break;
        case 'temporal':
            loadTemporalData();
            break;
        case 'spatial':
            loadSpatialData();
            break;
        case 'overview':
            loadOverviewData();
            break;
    }
    
    // Show feedback
    showToast('Filters applied!');
}

function resetFilters() {
    // Clear all filter inputs
    document.getElementById('boroughFilter').value = '';
    document.getElementById('hourFilter').value = '';
    document.getElementById('weekendFilter').value = '';
    document.getElementById('minFare').value = '';
    document.getElementById('maxFare').value = '';
    
    // Reset state
    state.filters = {
        borough: '',
        hour: '',
        weekend: '',
        minFare: '',
        maxFare: ''
    };
    state.currentPage = 1;
    
    // Reload data based on active view
    switch(state.currentView) {
        case 'trips':
            loadTripsData();
            break;
        case 'routes':
            loadRoutesData();
            break;
        case 'temporal':
            loadTemporalData();
            break;
        case 'spatial':
            loadSpatialData();
            break;
        case 'overview':
            loadOverviewData();
            break;
    }
    
    showToast('Filters reset!');
}

// ==================== QUICK INSIGHTS ====================
function loadQuickInsights(boroughStats, weekendComparison) {
    const insights = [];
    
    // Busiest borough
    const busiestBorough = boroughStats.reduce((max, b) => 
        b.trip_count > max.trip_count ? b : max
    );
    insights.push({
        icon: '',
        text: `${busiestBorough.borough} is the busiest borough with ${formatNumber(busiestBorough.trip_count)} trips`
    });
    
    // Highest average fare
    const highestFare = boroughStats.reduce((max, b) => 
        b.avg_fare > max.avg_fare ? b : max
    );
    insights.push({
        icon: '',
        text: `${highestFare.borough} has highest avg fare at $${highestFare.avg_fare.toFixed(2)}`
    });
    
    // Weekend vs weekday
    if (weekendComparison.weekend && weekendComparison.weekday) {
        const weekendAvgFare = weekendComparison.weekend.avg_fare;
        const weekdayAvgFare = weekendComparison.weekday.avg_fare;
        const diff = ((weekendAvgFare - weekdayAvgFare) / weekdayAvgFare * 100).toFixed(1);
        
        insights.push({
            icon: '',
            text: `Weekend fares are ${diff}% ${diff > 0 ? 'higher' : 'lower'} than weekdays`
        });
    }
    
    // Average stats
    insights.push({
        icon: '',
        text: `Average trip takes ${state.stats.averages.duration.toFixed(0)} minutes`
    });
    
    insights.push({
        icon: '',
        text: `Average trip distance is ${state.stats.averages.distance.toFixed(2)} miles`
    });
    
    const container = document.getElementById('quickInsights');
    container.innerHTML = insights.map(insight => `
        <div class="insight-item">
            <span class="insight-icon">${insight.icon}</span>
            <span class="insight-text">${insight.text}</span>
        </div>
    `).join('');
}

// ==================== UTILITY FUNCTIONS ====================
function showLoading(show) {
    const overlay = document.getElementById('loadingOverlay');
    overlay.style.display = show ? 'flex' : 'none';
}

function showToast(message) {
    // Create toast element
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;
    document.body.appendChild(toast);
    
    // Show toast
    setTimeout(() => toast.classList.add('show'), 100);
    
    // Remove toast after 3 seconds
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function formatNumber(num) {
    if (num >= 1000000) {
        return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'K';
    }
    return num.toLocaleString();
}

function formatDateTime(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { 
        month: 'short', 
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}