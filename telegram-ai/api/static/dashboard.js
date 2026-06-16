// Dashboard JavaScript
const API_BASE = window.location.origin;

// Utility functions - must be defined early
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDate(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
    const now = new Date();
    const diff = now - date;

    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return 'Just now';
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    if (days < 7) return `${days}d ago`;

    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function formatFileSize(bytes) {
    if (!bytes) return '-';
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / 1048576).toFixed(1) + ' MB';
}

function formatPrice(price, currency) {
    if (!price) return '-';
    const curr = currency || 'USD';
    return `${price.toLocaleString()} ${curr}`;
}

function truncate(str, length) {
    if (!str) return '';
    return str.length > length ? str.substring(0, length) + '...' : str;
}

// Real-time listings state
let currentPage = 1;
let currentChannel = '';
let currentSearch = '';
let currentSort = 'newest';
let allListings = [];

// CSV Export state
let csvCurrentPage = 1;
let csvCurrentChannel = '';
let csvCurrentSearch = '';
let csvAllListings = [];
let availableChannels = [];
let selectedChannels = new Set();
let crawlPollingInterval = null;

// Initialize dashboard
document.addEventListener('DOMContentLoaded', () => {
    checkAPIHealth();
    loadDashboard();
    setupEventListeners();
    setupTabNavigation();
    loadAvailableChannels();
    loadCSVListings();
    loadOutputStats();
    checkCrawlStatus();

    // Auto-refresh every 30 seconds
    setInterval(() => {
        const activeTab = document.querySelector('.tab-content.active').id;
        if (activeTab === 'realtime-tab') {
            loadDashboard();
        } else {
            loadCSVListings();
            loadOutputStats();
        }
    }, 30000);
});

// Setup tab navigation
function setupTabNavigation() {
    const tabBtns = document.querySelectorAll('.tab-btn');

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const tabId = btn.dataset.tab;

            // Update button states
            tabBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            // Update content visibility
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });
            document.getElementById(`${tabId}-tab`).classList.add('active');

            // Load data for the active tab
            if (tabId === 'csv-export') {
                loadCSVListings();
                loadOutputStats();
            }
        });
    });
}

// Setup event listeners
function setupEventListeners() {
    // Real-time listings events
    document.getElementById('refreshBtn').addEventListener('click', () => {
        const activeTab = document.querySelector('.tab-content.active').id;
        if (activeTab === 'realtime-tab') {
            loadDashboard();
        } else {
            loadCSVListings();
            loadOutputStats();
            loadAvailableChannels();
        }
    });

    document.getElementById('searchInput').addEventListener('input', (e) => {
        currentSearch = e.target.value.toLowerCase();
        currentPage = 1;
        filterAndDisplayListings();
    });

    document.getElementById('channelFilter').addEventListener('change', (e) => {
        currentChannel = e.target.value;
        currentPage = 1;
        filterAndDisplayListings();
    });

    document.getElementById('sortBy').addEventListener('change', (e) => {
        currentSort = e.target.value;
        filterAndDisplayListings();
    });

    document.getElementById('prevPage').addEventListener('click', () => {
        if (currentPage > 1) {
            currentPage--;
            filterAndDisplayListings();
        }
    });

    document.getElementById('nextPage').addEventListener('click', () => {
        currentPage++;
        filterAndDisplayListings();
    });

    // Modal close
    document.querySelector('.close').addEventListener('click', () => {
        document.getElementById('detailModal').style.display = 'none';
    });

    document.querySelector('.csv-close').addEventListener('click', () => {
        document.getElementById('csvDetailModal').style.display = 'none';
    });

    window.addEventListener('click', (e) => {
        if (e.target.classList.contains('modal')) {
            e.target.style.display = 'none';
        }
    });

    // CSV Export events
    document.getElementById('startCrawlBtn').addEventListener('click', startCrawl);
    document.getElementById('stopCrawlBtn').addEventListener('click', stopCrawl);
    document.getElementById('downloadCsvBtn').addEventListener('click', downloadCSV);
    document.getElementById('selectAllChannels').addEventListener('click', selectAllChannels);
    document.getElementById('deselectAllChannels').addEventListener('click', deselectAllChannels);

    // CSV Search and Filter
    document.getElementById('csvSearchInput').addEventListener('input', (e) => {
        csvCurrentSearch = e.target.value.toLowerCase();
        csvCurrentPage = 1;
        loadCSVListings();
    });

    document.getElementById('csvChannelFilter').addEventListener('change', (e) => {
        csvCurrentChannel = e.target.value;
        csvCurrentPage = 1;
        loadCSVListings();
    });

    document.getElementById('csvPrevPage').addEventListener('click', () => {
        if (csvCurrentPage > 1) {
            csvCurrentPage--;
            loadCSVListings();
        }
    });

    document.getElementById('csvNextPage').addEventListener('click', () => {
        csvCurrentPage++;
        loadCSVListings();
    });
}

// Check API health
async function checkAPIHealth() {
    try {
        const response = await fetch(`${API_BASE}/health`);
        const data = await response.json();

        const statusDot = document.getElementById('apiStatus');
        const statusText = document.getElementById('apiStatusText');

        if (data.status === 'healthy') {
            statusDot.classList.remove('error');
            statusText.textContent = 'API Online';
        } else {
            statusDot.classList.add('error');
            statusText.textContent = 'API Error';
        }
    } catch (error) {
        const statusDot = document.getElementById('apiStatus');
        const statusText = document.getElementById('apiStatusText');
        statusDot.classList.add('error');
        statusText.textContent = 'API Offline';
    }
}

// Load complete dashboard
async function loadDashboard() {
    await Promise.all([
        loadStatistics(),
        loadListings(),
        loadChannelStats()
    ]);
}

// Load statistics
async function loadStatistics() {
    try {
        const response = await fetch(`${API_BASE}/api/Crawler/statistics`);
        const data = await response.json();

        document.getElementById('totalListings').textContent = data.total_listings || 0;
        document.getElementById('totalChannels').textContent = data.unique_channels || 0;
        document.getElementById('totalImages').textContent = data.total_images || 0;
        document.getElementById('todayListings').textContent = data.today_listings || 0;
    } catch (error) {
        console.error('Error loading statistics:', error);
    }
}

// Load listings
async function loadListings() {
    try {
        const response = await fetch(`${API_BASE}/api/Crawler/listings?page=1&per_page=1000`);
        const data = await response.json();

        allListings = data.listings || [];
        populateChannelFilter();
        filterAndDisplayListings();
    } catch (error) {
        console.error('Error loading listings:', error);
        document.getElementById('listingsTableBody').innerHTML =
            '<tr><td colspan="6" class="loading">Error loading listings</td></tr>';
    }
}

// Populate channel filter dropdown
function populateChannelFilter() {
    const channelFilter = document.getElementById('channelFilter');
    const channels = [...new Set(allListings.map(l => l.user_name))].sort();

    channelFilter.innerHTML = '<option value="">All Channels</option>';
    channels.forEach(channel => {
        const option = document.createElement('option');
        option.value = channel;
        option.textContent = `@${channel}`;
        channelFilter.appendChild(option);
    });
}

// Filter and display listings
function filterAndDisplayListings() {
    let filtered = [...allListings];

    // Apply channel filter
    if (currentChannel) {
        filtered = filtered.filter(l => l.user_name === currentChannel);
    }

    // Apply search filter
    if (currentSearch) {
        filtered = filtered.filter(l =>
            l.description.toLowerCase().includes(currentSearch) ||
            l.user_name.toLowerCase().includes(currentSearch)
        );
    }

    // Apply sorting
    filtered.sort((a, b) => {
        switch (currentSort) {
            case 'newest':
                return new Date(b.created_at) - new Date(a.created_at);
            case 'oldest':
                return new Date(a.created_at) - new Date(b.created_at);
            case 'images':
                return (b.image_count || 0) - (a.image_count || 0);
            default:
                return 0;
        }
    });

    // Pagination
    const perPage = 20;
    const totalPages = Math.ceil(filtered.length / perPage);
    const start = (currentPage - 1) * perPage;
    const end = start + perPage;
    const paginated = filtered.slice(start, end);

    // Display listings
    displayListings(paginated);

    // Update pagination
    document.getElementById('prevPage').disabled = currentPage === 1;
    document.getElementById('nextPage').disabled = currentPage >= totalPages || totalPages === 0;
    document.getElementById('pageInfo').textContent =
        `Page ${currentPage} of ${totalPages || 1} (${filtered.length} listings)`;
}

// Display listings in table
function displayListings(listings) {
    const tbody = document.getElementById('listingsTableBody');

    if (listings.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="loading">No listings found</td></tr>';
        return;
    }

    tbody.innerHTML = listings.map(listing => `
        <tr>
            <td><strong>#${listing.id}</strong></td>
            <td class="description-cell" title="${escapeHtml(listing.description)}">
                ${escapeHtml(truncate(listing.description, 80))}
            </td>
            <td>
                <span class="channel-badge">@${escapeHtml(listing.user_name)}</span>
            </td>
            <td>
                <span class="image-count">${listing.image_count || 0}</span>
            </td>
            <td class="date-cell">${formatDate(listing.created_at)}</td>
            <td>
                <button class="btn btn-primary" onclick="viewDetails(${listing.id})">View</button>
            </td>
        </tr>
    `).join('');
}

// Load channel statistics
async function loadChannelStats() {
    try {
        const response = await fetch(`${API_BASE}/api/Crawler/channel-stats`);
        const data = await response.json();

        const tbody = document.getElementById('channelStatsBody');

        if (data.channels.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="loading">No channel data</td></tr>';
            return;
        }

        tbody.innerHTML = data.channels.map(channel => `
            <tr>
                <td><span class="channel-badge">@${escapeHtml(channel.channel_name)}</span></td>
                <td><strong>${channel.listing_count}</strong></td>
                <td><span class="image-count">${channel.image_count}</span></td>
                <td class="date-cell">${formatDate(channel.last_activity)}</td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Error loading channel stats:', error);
    }
}

// View listing details
async function viewDetails(id) {
    const modal = document.getElementById('detailModal');
    const content = document.getElementById('detailContent');

    modal.style.display = 'block';
    content.innerHTML = '<p class="loading">Loading...</p>';

    try {
        const response = await fetch(`${API_BASE}/api/Crawler/listings/${id}`);
        const listing = await response.json();

        content.innerHTML = `
            <div class="detail-info">
                <div class="info-item">
                    <div class="info-label">Listing ID</div>
                    <div class="info-value">#${listing.id}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Channel</div>
                    <div class="info-value">@${escapeHtml(listing.user_name)}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Message ID</div>
                    <div class="info-value">${listing.message_id}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Date</div>
                    <div class="info-value">${formatDate(listing.created_at)}</div>
                </div>
            </div>

            <h3 style="margin-top: 24px; color: #2d3748;">Description</h3>
            <div class="detail-description">${escapeHtml(listing.description)}</div>

            ${listing.images && listing.images.length > 0 ? `
                <h3 style="margin-top: 24px; color: #2d3748;">Images (${listing.images.length})</h3>
                <div class="detail-image-grid">
                    ${listing.images.map(img => `
                        <div>
                            <img src="/${img.image_path}" alt="Listing image" class="detail-image">
                            <p style="font-size: 12px; color: #718096; margin-top: 8px;">
                                ${escapeHtml(img.original_filename)}<br>
                                ${formatFileSize(img.file_size)}
                            </p>
                        </div>
                    `).join('')}
                </div>
            ` : '<p style="color: #718096; margin-top: 16px;">No images</p>'}
        `;
    } catch (error) {
        content.innerHTML = '<p class="loading" style="color: #f56565;">Error loading details</p>';
        console.error('Error loading details:', error);
    }
}

// ============================================
// CSV Export Functions
// ============================================

// Load available channels from schema
async function loadAvailableChannels() {
    try {
        const response = await fetch(`${API_BASE}/api/csv-export/channels`);
        const data = await response.json();

        availableChannels = data.channels || [];
        renderChannelCheckboxes();
    } catch (error) {
        console.error('Error loading channels:', error);
        document.getElementById('channelCheckboxes').innerHTML =
            '<p class="loading" style="color: #f56565;">Error loading channels</p>';
    }
}

// Render channel checkboxes
function renderChannelCheckboxes() {
    const container = document.getElementById('channelCheckboxes');

    if (availableChannels.length === 0) {
        container.innerHTML = '<p class="loading">No channels available</p>';
        return;
    }

    container.innerHTML = availableChannels.map(ch => `
        <div class="channel-item ${selectedChannels.has(ch.username) ? 'selected' : ''}"
             onclick="toggleChannel('${ch.username}')">
            <input type="checkbox" id="ch_${ch.username}"
                   ${selectedChannels.has(ch.username) ? 'checked' : ''}
                   onclick="event.stopPropagation(); toggleChannel('${ch.username}')">
            <label for="ch_${ch.username}">@${ch.username}</label>
        </div>
    `).join('');
}

// Toggle channel selection
function toggleChannel(username) {
    if (selectedChannels.has(username)) {
        selectedChannels.delete(username);
    } else {
        selectedChannels.add(username);
    }
    renderChannelCheckboxes();
}

// Select all channels
function selectAllChannels() {
    availableChannels.forEach(ch => selectedChannels.add(ch.username));
    renderChannelCheckboxes();
}

// Deselect all channels
function deselectAllChannels() {
    selectedChannels.clear();
    renderChannelCheckboxes();
}

// Start crawl
async function startCrawl() {
    const messagesPerChannel = parseInt(document.getElementById('messagesPerChannel').value) || 20;
    const channels = Array.from(selectedChannels);

    if (channels.length === 0) {
        alert('Please select at least one channel to crawl');
        return;
    }

    try {
        document.getElementById('startCrawlBtn').disabled = true;
        document.getElementById('stopCrawlBtn').disabled = false;

        const response = await fetch(`${API_BASE}/api/csv-export/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                channels: channels,
                messages_per_channel: messagesPerChannel
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Failed to start crawl');
        }

        // Show progress section
        document.getElementById('crawlProgress').classList.remove('hidden');

        // Start polling for status
        startStatusPolling();
    } catch (error) {
        alert('Error starting crawl: ' + error.message);
        document.getElementById('startCrawlBtn').disabled = false;
        document.getElementById('stopCrawlBtn').disabled = true;
    }
}

// Stop crawl
async function stopCrawl() {
    try {
        const response = await fetch(`${API_BASE}/api/csv-export/stop`, {
            method: 'POST'
        });

        const data = await response.json();

        if (!response.ok && response.status !== 400) {
            throw new Error(data.error || 'Failed to stop crawl');
        }
    } catch (error) {
        alert('Error stopping crawl: ' + error.message);
    }
}

// Check initial crawl status
async function checkCrawlStatus() {
    try {
        const response = await fetch(`${API_BASE}/api/csv-export/status`);

        if (response.ok) {
            const data = await response.json();

            if (data.status === 'running') {
                document.getElementById('crawlProgress').classList.remove('hidden');
                document.getElementById('startCrawlBtn').disabled = true;
                document.getElementById('stopCrawlBtn').disabled = false;
                startStatusPolling();
            } else if (data.status === 'completed' || data.status === 'failed' || data.status === 'stopped') {
                document.getElementById('crawlProgress').classList.remove('hidden');
                updateCrawlProgress(data);
            }
        }
    } catch (error) {
        console.error('Error checking crawl status:', error);
    }
}

// Start polling for crawl status
function startStatusPolling() {
    if (crawlPollingInterval) {
        clearInterval(crawlPollingInterval);
    }

    // Poll immediately
    pollCrawlStatus();

    // Then poll every 2 seconds
    crawlPollingInterval = setInterval(pollCrawlStatus, 2000);
}

// Poll crawl status
async function pollCrawlStatus() {
    try {
        const response = await fetch(`${API_BASE}/api/csv-export/status`);

        if (!response.ok) {
            throw new Error('Failed to get status');
        }

        const data = await response.json();
        updateCrawlProgress(data);

        // Stop polling if completed/failed/stopped
        if (data.status !== 'running' && data.status !== 'pending') {
            clearInterval(crawlPollingInterval);
            crawlPollingInterval = null;
            document.getElementById('startCrawlBtn').disabled = false;
            document.getElementById('stopCrawlBtn').disabled = true;

            // Refresh listings
            loadCSVListings();
            loadOutputStats();
        }
    } catch (error) {
        console.error('Error polling status:', error);
    }
}

// Update crawl progress UI
function updateCrawlProgress(data) {
    // Status badge
    const statusBadge = document.getElementById('crawlStatus');
    statusBadge.textContent = data.status;
    statusBadge.className = `status-badge ${data.status}`;

    // Current channel
    document.getElementById('crawlChannel').textContent =
        data.current_channel ? `@${data.current_channel}` : '-';

    // Progress bar
    document.getElementById('progressBar').style.width = `${data.progress_percent}%`;
    document.getElementById('progressPercent').textContent = `${data.progress_percent}%`;
    document.getElementById('progressChannels').textContent =
        `${data.current_channel_index} / ${data.total_channels} channels`;

    // Stats
    if (data.stats) {
        document.getElementById('statSuccess').textContent = data.stats.total_success || 0;
        document.getElementById('statFailed').textContent = data.stats.total_failed || 0;
        document.getElementById('statSkipped').textContent = data.stats.total_skipped || 0;
        document.getElementById('statImages').textContent = data.stats.total_images || 0;
    }

    // Logs
    if (data.recent_logs && data.recent_logs.length > 0) {
        const logContainer = document.getElementById('logContainer');
        logContainer.innerHTML = data.recent_logs.map(log => {
            let className = 'log-entry';
            if (log.includes('Success') || log.includes('Saved') || log.includes('completed')) {
                className += ' success';
            } else if (log.includes('Error') || log.includes('failed') || log.includes('Failed')) {
                className += ' error';
            } else if (log.includes('Processing') || log.includes('Connecting')) {
                className += ' info';
            }
            return `<div class="${className}">${escapeHtml(log)}</div>`;
        }).join('');
        logContainer.scrollTop = logContainer.scrollHeight;
    }
}

// Download CSV
function downloadCSV() {
    window.location.href = `${API_BASE}/api/csv-export/download`;
}

// Load output stats
async function loadOutputStats() {
    try {
        const response = await fetch(`${API_BASE}/api/csv-export/output-stats`);
        const stats = await response.json();

        document.getElementById('csvFileSize').textContent =
            stats.csv_exists ? formatFileSize(stats.csv_size) : '-';
        document.getElementById('csvImagesCount').textContent =
            stats.images_count || 0;
    } catch (error) {
        console.error('Error loading output stats:', error);
    }
}

// Load CSV listings
async function loadCSVListings() {
    try {
        const params = new URLSearchParams({
            page: csvCurrentPage,
            per_page: 20
        });

        if (csvCurrentChannel) {
            params.append('channel', csvCurrentChannel);
        }
        if (csvCurrentSearch) {
            params.append('search', csvCurrentSearch);
        }

        const response = await fetch(`${API_BASE}/api/csv-export/listings?${params}`);

        if (response.status === 404) {
            // No CSV file exists yet
            document.getElementById('csvListingsTableBody').innerHTML =
                '<tr><td colspan="8" class="loading">No CSV data yet. Run a crawl to generate listings.</td></tr>';
            document.getElementById('csvTotalListings').textContent = '0';
            document.getElementById('csvTotalChannels').textContent = '0';
            return;
        }

        const data = await response.json();

        // Update stats
        document.getElementById('csvTotalListings').textContent = data.total || 0;
        document.getElementById('csvTotalChannels').textContent =
            (data.channels || []).length;

        // Populate channel filter
        populateCSVChannelFilter(data.channels || []);

        // Display listings
        displayCSVListings(data.listings || []);

        // Update pagination
        const totalPages = data.total_pages || 1;
        document.getElementById('csvPrevPage').disabled = csvCurrentPage === 1;
        document.getElementById('csvNextPage').disabled = csvCurrentPage >= totalPages;
        document.getElementById('csvPageInfo').textContent =
            `Page ${csvCurrentPage} of ${totalPages} (${data.total} listings)`;

    } catch (error) {
        console.error('Error loading CSV listings:', error);
        document.getElementById('csvListingsTableBody').innerHTML =
            '<tr><td colspan="8" class="loading" style="color: #f56565;">Error loading CSV listings</td></tr>';
    }
}

// Populate CSV channel filter
function populateCSVChannelFilter(channels) {
    const filter = document.getElementById('csvChannelFilter');
    const currentValue = filter.value;

    filter.innerHTML = '<option value="">All Channels</option>';
    channels.forEach(channel => {
        const option = document.createElement('option');
        option.value = channel;
        option.textContent = `@${channel}`;
        filter.appendChild(option);
    });

    filter.value = currentValue;
}

// Display CSV listings
function displayCSVListings(listings) {
    const tbody = document.getElementById('csvListingsTableBody');

    if (listings.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" class="loading">No listings found</td></tr>';
        return;
    }

    tbody.innerHTML = listings.map(listing => `
        <tr>
            <td><strong>#${listing.id}</strong></td>
            <td><span class="channel-badge">@${escapeHtml(listing.channel)}</span></td>
            <td>${escapeHtml(listing.rooms || '-')}</td>
            <td>${formatPrice(listing.price, listing.currency)}</td>
            <td>${listing.area_m2 ? listing.area_m2 + ' m2' : '-'}</td>
            <td>${escapeHtml(listing.district || '-')}</td>
            <td><span class="image-count">${listing.image_count || 0}</span></td>
            <td>
                <button class="btn btn-primary" onclick="viewCSVDetails(${listing.id})">View</button>
            </td>
        </tr>
    `).join('');
}

// View CSV listing details
function viewCSVDetails(id) {
    // Find listing in current data
    fetch(`${API_BASE}/api/csv-export/listings?per_page=1000`)
        .then(response => response.json())
        .then(data => {
            const listing = data.listings.find(l => l.id === id);
            if (!listing) {
                alert('Listing not found');
                return;
            }

            const modal = document.getElementById('csvDetailModal');
            const content = document.getElementById('csvDetailContent');
            modal.style.display = 'block';

            content.innerHTML = `
                <div class="detail-info">
                    <div class="info-item">
                        <div class="info-label">Listing ID</div>
                        <div class="info-value">#${listing.id}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Channel</div>
                        <div class="info-value">@${escapeHtml(listing.channel)}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Rooms</div>
                        <div class="info-value">${escapeHtml(listing.rooms || '-')}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Price</div>
                        <div class="info-value">${formatPrice(listing.price, listing.currency)}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Area</div>
                        <div class="info-value">${listing.area_m2 ? listing.area_m2 + ' m2' : '-'}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Floor</div>
                        <div class="info-value">${listing.floor || '-'} / ${listing.total_floors || '-'}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">District</div>
                        <div class="info-value">${escapeHtml(listing.district || '-')}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Address</div>
                        <div class="info-value">${escapeHtml(listing.address || '-')}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Property Type</div>
                        <div class="info-value">${escapeHtml(listing.property_type || '-')}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Deal Type</div>
                        <div class="info-value">${escapeHtml(listing.deal_type || '-')}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Condition</div>
                        <div class="info-value">${escapeHtml(listing.condition || '-')}</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Phone</div>
                        <div class="info-value">${escapeHtml(listing.phone_numbers || '-')}</div>
                    </div>
                </div>

                <h3 style="margin-top: 24px; color: #2d3748;">Raw Text</h3>
                <div class="detail-description">${escapeHtml(listing.raw_text || '-')}</div>

                ${listing.image_paths && listing.image_paths.length > 0 ? `
                    <h3 style="margin-top: 24px; color: #2d3748;">Images (${listing.image_paths.length})</h3>
                    <div class="detail-image-grid">
                        ${listing.image_paths.map(path => `
                            <div>
                                <img src="/api/csv-export/images/${path.split('/').pop()}"
                                     alt="Listing image"
                                     class="detail-image"
                                     onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%22200%22 height=%22200%22><rect fill=%22%23f0f0f0%22 width=%22200%22 height=%22200%22/><text x=%2250%%22 y=%2250%%22 fill=%22%23999%22 text-anchor=%22middle%22 dy=%22.3em%22>No image</text></svg>'">
                                <p style="font-size: 12px; color: #718096; margin-top: 8px;">
                                    ${path.split('/').pop()}
                                </p>
                            </div>
                        `).join('')}
                    </div>
                ` : '<p style="color: #718096; margin-top: 16px;">No images</p>'}
            `;
        })
        .catch(error => {
            console.error('Error loading details:', error);
            alert('Error loading listing details');
        });
}
