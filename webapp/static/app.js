// Storj Monitor Dashboard JavaScript Application

class StorjMonitor {
    constructor() {
        this.apiBase = '/api';
        this.refreshInterval = 900000; // 15 minutes (900,000ms)
        this.charts = {};
        this.currentView = 'dashboard';
        this.nodes = [];
        this.systemSummary = {};
        
        this.init();
    }

    async init() {
        console.log('Initializing Storj Monitor Dashboard...');
        
        // Show loading text
        document.getElementById('lastUpdate').textContent = 'Initializing...';
        
        try {
            console.log('Loading initial data...');
            // Initial data load
            await this.loadInitialData();
            
            console.log('Setting up event listeners...');
            // Setup event listeners
            this.setupEventListeners();
            
            console.log('Starting auto-refresh...');
            // Start auto-refresh
            this.startAutoRefresh();
            
            console.log('Dashboard initialized successfully');
        } catch (error) {
            console.error('Failed to initialize dashboard:', error);
            alert('Failed to initialize dashboard. Please check your connection. Error: ' + error.message);
        }
    }

    async loadInitialData() {
        console.log('Loading initial data...');
        
        try {
            // Load all required data
            console.log('Loading nodes...');
            await this.loadNodes();
            console.log('Loaded nodes:', this.nodes);
            
            console.log('Loading system summary...');
            await this.loadSystemSummary();
            console.log('Loaded system summary:', this.systemSummary);
            
            console.log('Loading recent events...');
            await this.loadRecentEvents();
            console.log('Loaded recent events:', this.recentEvents);
            
            console.log('Loading vetting summary...');
            await this.loadVettingSummary();
            console.log('Loaded vetting summary:', this.vettingSummary);
            
            console.log('Loading satellites...');
            await this.loadSatellites();
            console.log('Loaded satellites:', this.satellites);
            
            console.log('Updating dashboard UI...');
            // Update UI
            this.updateDashboard();
            this.populateHistoryFilters();
            console.log('Dashboard update complete.');
        } catch (error) {
            console.error('Error in loadInitialData:', error);
            throw error;
        }
    }

    setupEventListeners() {
        // History view filters
        const nodeSelect = document.getElementById('historyNodeSelect');
        const timeSelect = document.getElementById('historyTimeRange');
        
        if (nodeSelect && timeSelect) {
            nodeSelect.addEventListener('change', () => this.updateHistoryCharts());
            timeSelect.addEventListener('change', () => this.updateHistoryCharts());
        }
    }

    startAutoRefresh() {
        setInterval(async () => {
            if (!document.hidden) {
                await this.refreshData();
            }
        }, this.refreshInterval);
    }

    showLoading() {
        const modal = new bootstrap.Modal(document.getElementById('loadingModal'));
        modal.show();
    }

    hideLoading() {
        const modal = bootstrap.Modal.getInstance(document.getElementById('loadingModal'));
        if (modal) {
            modal.hide();
        }
    }

    showError(message) {
        // Simple error display - could be enhanced with a proper error modal
        console.error(message);
        alert(message); // Temporary - should be replaced with better UX
    }

    // API Methods
    async apiCall(endpoint) {
        try {
            const response = await fetch(`${this.apiBase}${endpoint}`);
            if (!response.ok) {
                throw new Error(`API call failed: ${response.status} ${response.statusText}`);
            }
            return await response.json();
        } catch (error) {
            console.error(`API call to ${endpoint} failed:`, error);
            throw error;
        }
    }

    async loadNodes() {
        this.nodes = await this.apiCall('/nodes');
    }

    async loadSystemSummary() {
        this.systemSummary = await this.apiCall('/system/summary');
    }

    async loadRecentEvents() {
        this.recentEvents = await this.apiCall('/system/events?limit=10');
    }

    async loadVettingSummary() {
        this.vettingSummary = await this.apiCall('/vetting/summary');
    }

    async loadSatellites() {
        this.satellites = await this.apiCall('/satellites');
    }

    async loadNodeHistory(nodeName, hours = 24) {
        const [diskHistory, bandwidthHistory, healthHistory] = await Promise.all([
            this.apiCall(`/nodes/${nodeName}/disk-usage?hours=${hours}`),
            this.apiCall(`/nodes/${nodeName}/bandwidth-usage?hours=${hours}`),
            this.apiCall(`/nodes/${nodeName}/health-metrics?hours=${hours}`)
        ]);
        
        return { diskHistory, bandwidthHistory, healthHistory };
    }

    // UI Update Methods
    updateDashboard() {
        this.updateSummaryCards();
        this.updateNodeStatusCards();
        this.updateDashboardCharts();
        this.updateRecentEvents();
        this.updateLastUpdateTime();
    }

    updateSummaryCards() {
        document.getElementById('activeNodesCount').textContent = this.systemSummary.active_nodes || 0;
        document.getElementById('totalStorage').textContent = 
            `${this.systemSummary.storage_summary?.total_used_gb || 0} GB`;
        document.getElementById('avgAuditScore').textContent = 
            (this.systemSummary.health_summary?.avg_audit_score || 0).toFixed(3);
        document.getElementById('totalBandwidth').textContent = 
            `${this.systemSummary.health_summary?.total_bandwidth_used_gb || 0} GB`;
    }

    updateNodeStatusCards() {
        const container = document.getElementById('nodeStatusCards');
        container.innerHTML = '';

        this.nodes.forEach(node => {
            const card = this.createNodeStatusCard(node);
            container.appendChild(card);
        });
    }

    createNodeStatusCard(node) {
        const col = document.createElement('div');
        col.className = 'col-lg-4 col-md-6 mb-3';
        
        const healthStatus = this.getHealthStatus(node);
        const usagePercentage = node.disk_usage_percentage || 0;
        
        // Get vetting info for this node
        const vettingInfo = this.getVettingInfo(node.name);
        const vettingHtml = this.createVettingStatusHtml(vettingInfo);
        
        col.innerHTML = `
            <div class="card status-card ${healthStatus} h-100">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-start mb-2">
                        <div>
                            <h6 class="card-title mb-1">${node.name}</h6>
                            <small class="text-muted">${node.description || ''}</small>
                        </div>
                        <span class="health-indicator ${healthStatus}"></span>
                    </div>
                    
                    <div class="row text-center mb-3">
                        <div class="col-4">
                            <div class="metric-label">Disk Used</div>
                            <div class="metric-value">${this.formatBytes(node.disk_used || 0)}</div>
                        </div>
                        <div class="col-4">
                            <div class="metric-label">Audit Score</div>
                            <div class="metric-value">${(node.audit_score || 0).toFixed(3)}</div>
                        </div>
                        <div class="col-4">
                            <div class="metric-label">Satellites</div>
                            <div class="metric-value">${node.satellites_count || 0}</div>
                        </div>
                    </div>
                    
                    <div class="mb-2">
                        <div class="d-flex justify-content-between">
                            <small>Disk Usage</small>
                            <small>${usagePercentage.toFixed(1)}%</small>
                        </div>
                        <div class="progress">
                            <div class="progress-bar ${this.getProgressBarClass(usagePercentage)}" 
                                 style="width: ${Math.min(usagePercentage, 100)}%"></div>
                        </div>
                    </div>
                    
                    ${vettingHtml}
                    
                    <small class="text-muted">
                        <i class="bi bi-clock"></i>
                        Last updated: ${this.formatTime(node.last_updated)} | Version: ${node.version || 'N/A'}
                    </small>
                </div>
            </div>
        `;
        
        return col;
    }

    getHealthStatus(node) {
        if (!node.audit_score || !node.suspension_score) return 'warning';
        
        if (node.audit_score < 0.95 || node.suspension_score < 0.95) {
            return 'critical';
        } else if (node.audit_score < 0.98 || (node.online_score && node.online_score < 0.95)) {
            return 'warning';
        }
        return 'healthy';
    }

    getProgressBarClass(percentage) {
        if (percentage > 90) return 'bg-danger';
        if (percentage > 75) return 'bg-warning';
        return 'bg-success';
    }

    getVettingInfo(nodeName) {
        if (!this.vettingSummary) return null;
        return this.vettingSummary.find(v => v.node_name === nodeName);
    }

    createVettingStatusHtml(vettingInfo) {
        if (!vettingInfo) {
            return '<div class="mb-2"><small class="text-muted">Vetting info loading...</small></div>';
        }

        const vettingPercentage = (vettingInfo.vetted_count / vettingInfo.total_satellites) * 100;
        const progressColor = vettingPercentage === 100 ? 'bg-success' : 
                             vettingPercentage > 50 ? 'bg-warning' : 'bg-info';

        return `
            <div class="mb-2">
                <div class="d-flex justify-content-between">
                    <small><i class="bi bi-satellite"></i> Satellite Vetting</small>
                    <small>${vettingInfo.vetted_count}/${vettingInfo.total_satellites} vetted (${vettingPercentage.toFixed(0)}%)</small>
                </div>
                <div class="progress" style="height: 4px;">
                    <div class="progress-bar ${progressColor}" style="width: ${vettingPercentage}%"></div>
                </div>
                <div class="mt-1">
                    <small class="text-muted">${vettingInfo.status_summary}</small>
                </div>
            </div>
        `;
    }

    updateDashboardCharts() {
        // Create disk usage trend chart
        this.createDiskUsageTrendChart();
        
        // Create storage distribution chart
        this.createStorageDistributionChart();
    }

    createDiskUsageTrendChart() {
        const canvas = document.getElementById('diskUsageChart');
        if (!canvas) return;

        // Destroy existing chart
        if (this.charts.diskUsage) {
            this.charts.diskUsage.destroy();
        }

        const ctx = canvas.getContext('2d');
        
        // Prepare data for all nodes
        const datasets = this.nodes.map((node, index) => ({
            label: node.name,
            data: [
                { x: new Date(), y: (node.disk_used || 0) / (1024**3) }
            ],
            borderColor: this.getNodeColor(index),
            backgroundColor: this.getNodeColor(index, 0.1),
            tension: 0.4
        }));

        this.charts.diskUsage = new Chart(ctx, {
            type: 'line',
            data: { datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: false
                    },
                    legend: {
                        position: 'bottom'
                    }
                },
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            unit: 'hour'
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Disk Usage (GB)'
                        }
                    }
                }
            }
        });
    }

    createStorageDistributionChart() {
        const canvas = document.getElementById('storageDistributionChart');
        if (!canvas) return;

        // Destroy existing chart
        if (this.charts.storageDistribution) {
            this.charts.storageDistribution.destroy();
        }

        const ctx = canvas.getContext('2d');
        
        const data = this.nodes.map(node => (node.disk_used || 0) / (1024**3));
        const labels = this.nodes.map(node => node.name);
        const colors = this.nodes.map((_, index) => this.getNodeColor(index));

        this.charts.storageDistribution = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels,
                datasets: [{
                    data,
                    backgroundColor: colors,
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
    }

    getNodeColor(index, alpha = 1) {
        const colors = [
            `rgba(54, 162, 235, ${alpha})`,
            `rgba(255, 99, 132, ${alpha})`,
            `rgba(75, 192, 192, ${alpha})`,
            `rgba(255, 206, 86, ${alpha})`,
            `rgba(153, 102, 255, ${alpha})`,
            `rgba(255, 159, 64, ${alpha})`
        ];
        return colors[index % colors.length];
    }

    updateRecentEvents() {
        const container = document.getElementById('recentEvents');
        
        if (!this.recentEvents || this.recentEvents.length === 0) {
            container.innerHTML = '<p class="text-muted">No recent events</p>';
            return;
        }

        container.innerHTML = this.recentEvents.map(event => `
            <div class="event-item ${event.type}">
                <div class="d-flex justify-content-between">
                    <div>
                        <strong>${event.node_name}</strong>
                        <div>${event.message}</div>
                    </div>
                    <div class="event-time">${this.formatTime(event.timestamp)}</div>
                </div>
            </div>
        `).join('');
    }

    updateLastUpdateTime() {
        document.getElementById('lastUpdate').textContent = this.formatTime(new Date());
    }

    // Navigation Methods
    showDashboard() {
        this.switchView('dashboard');
        this.setActiveNavItem('dashboard');
    }

    showNodes() {
        this.switchView('nodes');
        this.setActiveNavItem('nodes');
        this.updateNodeDetails();
    }

    showHistory() {
        this.switchView('history');
        this.setActiveNavItem('history');
        this.updateHistoryCharts();
    }

    showEvents() {
        this.switchView('events');
        this.setActiveNavItem('events');
        this.updateEventsTable();
    }

    switchView(viewName) {
        // Hide all views
        document.querySelectorAll('.view-content').forEach(view => {
            view.style.display = 'none';
        });
        
        // Show selected view
        const targetView = document.getElementById(`${viewName}View`);
        if (targetView) {
            targetView.style.display = 'block';
            this.currentView = viewName;
        }
    }

    setActiveNavItem(viewName) {
        // Remove active class from all nav items
        document.querySelectorAll('.navbar-nav .nav-link').forEach(link => {
            link.classList.remove('active');
        });
        
        // Add active class to current nav item
        const navItems = document.querySelectorAll('.navbar-nav .nav-link');
        const viewMap = { dashboard: 0, nodes: 1, history: 2, events: 3 };
        if (navItems[viewMap[viewName]]) {
            navItems[viewMap[viewName]].classList.add('active');
        }
    }

    updateNodeDetails() {
        const container = document.getElementById('nodeDetailCards');
        container.innerHTML = '';

        this.nodes.forEach(node => {
            const card = this.createDetailedNodeCard(node);
            container.appendChild(card);
        });
    }

    createDetailedNodeCard(node) {
        const col = document.createElement('div');
        col.className = 'col-12 mb-4';
        
        const healthStatus = this.getHealthStatus(node);
        
        col.innerHTML = `
            <div class="card">
                <div class="card-header">
                    <h5 class="mb-0">
                        <span class="health-indicator ${healthStatus}"></span>
                        ${node.name}
                        <span class="status-badge ${healthStatus === 'healthy' ? 'online' : healthStatus}">
                            ${healthStatus.toUpperCase()}
                        </span>
                    </h5>
                    <small class="text-muted">${node.description || ''}</small>
                </div>
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-3">
                            <div class="metric-label">Disk Usage</div>
                            <div class="metric-value">${this.formatBytes(node.disk_used || 0)}</div>
                            <div class="text-muted">of ${this.formatBytes((node.disk_used || 0) + (node.disk_available || 0))}</div>
                        </div>
                        <div class="col-md-3">
                            <div class="metric-label">Audit Score</div>
                            <div class="metric-value">${(node.audit_score || 0).toFixed(4)}</div>
                            <div class="text-muted">Suspension: ${(node.suspension_score || 0).toFixed(4)}</div>
                        </div>
                        <div class="col-md-3">
                            <div class="metric-label">Online Score</div>
                            <div class="metric-value">${(node.online_score || 0).toFixed(4)}</div>
                            <div class="text-muted">QUIC: ${node.quic_status || 'Unknown'}</div>
                        </div>
                        <div class="col-md-3">
                            <div class="metric-label">Version</div>
                            <div class="metric-value">${node.version || 'N/A'}</div>
                            <div class="text-muted">Satellites: ${node.satellites_count || 0}</div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        return col;
    }

    populateHistoryFilters() {
        const nodeSelect = document.getElementById('historyNodeSelect');
        if (!nodeSelect) return;

        // Clear existing options (except "All Nodes")
        nodeSelect.innerHTML = '<option value="">All Nodes</option>';
        
        // Add node options
        this.nodes.forEach(node => {
            const option = document.createElement('option');
            option.value = node.name;
            option.textContent = node.name;
            nodeSelect.appendChild(option);
        });
    }

    async updateHistoryCharts() {
        const nodeSelect = document.getElementById('historyNodeSelect');
        const timeSelect = document.getElementById('historyTimeRange');
        
        if (!nodeSelect || !timeSelect) return;

        const selectedNode = nodeSelect.value;
        const hours = parseInt(timeSelect.value);

        if (selectedNode) {
            // Load data for specific node
            try {
                const data = await this.loadNodeHistory(selectedNode, hours);
                this.createHistoryCharts(data, selectedNode);
            } catch (error) {
                console.error('Failed to load node history:', error);
            }
        } else {
            // Show aggregate data for all nodes
            this.createAggregateHistoryCharts(hours);
        }
    }

    createHistoryCharts(data, nodeName) {
        // Create individual charts for the selected node
        this.createHistoryDiskChart(data.diskHistory, nodeName);
        this.createHistoryBandwidthChart(data.bandwidthHistory, nodeName);
        this.createHistoryHealthChart(data.healthHistory, nodeName);
    }

    createHistoryDiskChart(diskHistory, nodeName) {
        const canvas = document.getElementById('historyDiskChart');
        if (!canvas) return;

        if (this.charts.historyDisk) {
            this.charts.historyDisk.destroy();
        }

        const ctx = canvas.getContext('2d');
        
        this.charts.historyDisk = new Chart(ctx, {
            type: 'line',
            data: {
                datasets: [{
                    label: 'Used (GB)',
                    data: diskHistory.map(item => ({
                        x: new Date(item.timestamp),
                        y: item.used_gb
                    })),
                    borderColor: 'rgb(75, 192, 192)',
                    tension: 0.4
                }, {
                    label: 'Available (GB)',
                    data: diskHistory.map(item => ({
                        x: new Date(item.timestamp),
                        y: item.available_gb
                    })),
                    borderColor: 'rgb(255, 99, 132)',
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            unit: 'hour'
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Storage (GB)'
                        }
                    }
                }
            }
        });
    }

    createHistoryBandwidthChart(bandwidthHistory, nodeName) {
        const canvas = document.getElementById('historyBandwidthChart');
        if (!canvas) return;

        if (this.charts.historyBandwidth) {
            this.charts.historyBandwidth.destroy();
        }

        const ctx = canvas.getContext('2d');
        
        this.charts.historyBandwidth = new Chart(ctx, {
            type: 'line',
            data: {
                datasets: [{
                    label: 'Bandwidth Used (GB)',
                    data: bandwidthHistory.map(item => ({
                        x: new Date(item.timestamp),
                        y: item.used_gb
                    })),
                    borderColor: 'rgb(153, 102, 255)',
                    backgroundColor: 'rgba(153, 102, 255, 0.1)',
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            unit: 'hour'
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Bandwidth (GB)'
                        }
                    }
                }
            }
        });
    }

    createHistoryHealthChart(healthHistory, nodeName) {
        const canvas = document.getElementById('historyHealthChart');
        if (!canvas) return;

        if (this.charts.historyHealth) {
            this.charts.historyHealth.destroy();
        }

        const ctx = canvas.getContext('2d');
        
        this.charts.historyHealth = new Chart(ctx, {
            type: 'line',
            data: {
                datasets: [{
                    label: 'Audit Score',
                    data: healthHistory.map(item => ({
                        x: new Date(item.timestamp),
                        y: item.audit_score
                    })),
                    borderColor: 'rgb(255, 206, 86)',
                    tension: 0.4
                }, {
                    label: 'Online Score',
                    data: healthHistory.map(item => ({
                        x: new Date(item.timestamp),
                        y: item.online_score
                    })),
                    borderColor: 'rgb(75, 192, 192)',
                    tension: 0.4
                }, {
                    label: 'Suspension Score',
                    data: healthHistory.map(item => ({
                        x: new Date(item.timestamp),
                        y: item.suspension_score
                    })),
                    borderColor: 'rgb(255, 99, 132)',
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            unit: 'hour'
                        }
                    },
                    y: {
                        min: 0,
                        max: 1,
                        title: {
                            display: true,
                            text: 'Score'
                        }
                    }
                }
            }
        });
    }

    async updateEventsTable() {
        try {
            const events = await this.apiCall('/system/events?limit=100');
            const container = document.getElementById('eventsTable');
            
            if (!events || events.length === 0) {
                container.innerHTML = '<p class="text-muted">No events found</p>';
                return;
            }

            const table = `
                <div class="table-responsive">
                    <table class="table table-hover">
                        <thead>
                            <tr>
                                <th>Time</th>
                                <th>Node</th>
                                <th>Type</th>
                                <th>Message</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${events.map(event => `
                                <tr>
                                    <td>${this.formatTime(event.timestamp)}</td>
                                    <td><span class="badge bg-primary">${event.node_name}</span></td>
                                    <td><span class="badge ${this.getEventBadgeClass(event.type)}">${event.type.toUpperCase()}</span></td>
                                    <td>${event.message}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            `;
            
            container.innerHTML = table;
        } catch (error) {
            console.error('Failed to update events table:', error);
        }
    }

    getEventBadgeClass(type) {
        switch (type) {
            case 'critical': return 'bg-danger';
            case 'warning': return 'bg-warning text-dark';
            default: return 'bg-info';
        }
    }

    // Utility Methods
    formatBytes(bytes) {
        if (bytes === 0) return '0 B';
        
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(1024));
        
        return (bytes / Math.pow(1024, i)).toFixed(2) + ' ' + sizes[i];
    }

    formatTime(dateString) {
        const date = new Date(dateString);
        return date.toLocaleString();
    }

    // Public Methods
    async refreshData() {
        const refreshBtn = document.getElementById('refreshBtn');
        const originalText = refreshBtn.innerHTML;
        
        refreshBtn.innerHTML = '<i class="bi bi-arrow-clockwise spin"></i> Refreshing...';
        refreshBtn.disabled = true;
        
        try {
            await this.loadInitialData();
            
            // Update current view
            switch (this.currentView) {
                case 'nodes':
                    this.updateNodeDetails();
                    break;
                case 'history':
                    this.updateHistoryCharts();
                    break;
                case 'events':
                    this.updateEventsTable();
                    break;
                default:
                    this.updateDashboard();
            }
        } catch (error) {
            console.error('Failed to refresh data:', error);
        } finally {
            refreshBtn.innerHTML = originalText;
            refreshBtn.disabled = false;
        }
    }
}

// Global instance
let storjMonitor;

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    storjMonitor = new StorjMonitor();
});

// Global navigation functions
function showDashboard() {
    if (storjMonitor) storjMonitor.showDashboard();
}

function showNodes() {
    if (storjMonitor) storjMonitor.showNodes();
}

function showHistory() {
    if (storjMonitor) storjMonitor.showHistory();
}

function showEvents() {
    if (storjMonitor) storjMonitor.showEvents();
}

function refreshData() {
    if (storjMonitor) storjMonitor.refreshData();
}

// Add spin animation for refresh button
const style = document.createElement('style');
style.textContent = `
    .spin {
        animation: spin 1s linear infinite;
    }
    
    @keyframes spin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }
`;
document.head.appendChild(style);