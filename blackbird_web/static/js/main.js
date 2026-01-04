// ============================
// MAIN INITIALIZATION
// ============================
document.addEventListener('DOMContentLoaded', function() {
    // Setup voter tool first
    if (typeof setupVoterTool === 'function') {
        setupVoterTool();
    }
    
    // Setup settings management buttons
    setupSettingsManagement();
    
    // Load stats and other setup
    loadStats();
    setupSearchTypeToggle();
    setupTagCloud();
    setupSiteSelection();
    setupCategoryFilter();
    
    // Setup username lookup functionality
    setupUsernameLookup();
    
    // Setup form submission
    setupFormSubmission();
    
    // Setup frequency analysis
    setupFrequencyAnalysis();
    
    // Auto-refresh stats every 10 seconds
    setInterval(loadStats, 3600000);
    
    // Load saved searches
    if (typeof loadSavedSearches === 'function') {
        loadSavedSearches();
    }
    
    // Setup expand/collapse functionality for results page
    setupResultsPage();
});

// ============================
// SETTINGS MANAGEMENT FUNCTIONS
// ============================
function setupSettingsManagement() {
    const saveBtn = document.getElementById('saveSettingsBtn');
    const loadBtn = document.getElementById('loadSettingsBtn');
    const fileInput = document.getElementById('settingsFileInput');
    const resetBtn = document.getElementById('resetSettingsBtn');
    const showSettingsBtn = document.getElementById('showCurrentSettingsBtn');
    const settingsDisplay = document.getElementById('currentSettingsDisplay');
    const settingsContent = document.getElementById('currentSettingsContent');
    
    if (!saveBtn || !loadBtn || !resetBtn || !showSettingsBtn) return;
    
    // Save settings button
    saveBtn.addEventListener('click', function() {
        saveCurrentSettings();
    });
    
    // Load settings button - trigger file input
    loadBtn.addEventListener('click', function() {
        fileInput.click();
    });
    
    // File input change handler
    fileInput.addEventListener('change', function(e) {
        if (e.target.files.length > 0) {
            loadSettingsFromFile(e.target.files[0]);
            // Reset file input so same file can be loaded again
            e.target.value = '';
        }
    });
    
    // Reset settings button
    resetBtn.addEventListener('click', function() {
        if (confirm('Are you sure you want to reset all settings to default?')) {
            resetToDefaultSettings();
        }
    });
    
    // Show current settings button
    showSettingsBtn.addEventListener('click', function() {
        const currentSettings = getCurrentSettings();
        settingsContent.textContent = JSON.stringify(currentSettings, null, 2);
        settingsDisplay.style.display = 'block';
    });
}

function getCurrentSettings() {
    // Determine active search type
    const activeSearchType = document.querySelector('.search-type-btn.active')?.dataset.type || 'username';
    
    // Get all form field values
    const settings = {
        version: '1.0',
        timestamp: new Date().toISOString(),
        search_type: activeSearchType,
        usernames: document.getElementById('usernames')?.value || '',
        emails: document.getElementById('emails')?.value || '',
        top_sites: document.getElementById('top_sites')?.value || '500',
        timeout: document.getElementById('timeout')?.value || '30',
        max_concurrent: document.getElementById('max_concurrent')?.value || '30',
        all_sites: document.getElementById('all_sites')?.checked || false,
        no_nsfw: document.getElementById('no_nsfw')?.checked || false,
        include_categories: document.getElementById('includeCategories')?.value || '',
        exclude_categories: document.getElementById('excludeCategories')?.value || '',
        category_filter: document.getElementById('categoryFilter')?.value || '',
        site: document.getElementById('site')?.value || '',
        filter: document.getElementById('filter')?.value || '',
        proxy: document.getElementById('proxy')?.value || '',
        tor_proxy: document.getElementById('tor_proxy')?.value || '',
        save_csv: document.getElementById('save_csv')?.checked || true,
        save_json: document.getElementById('save_json')?.checked || true,
        save_pdf: document.getElementById('save_pdf')?.checked || false,
        verbose: document.getElementById('verbose')?.checked || false,
        enable_frequency: document.getElementById('enable_frequency')?.checked || false,
        show_common_sites: document.getElementById('show_common_sites')?.checked || true
    };
    
    // Get selected tags
    const selectedTags = Array.from(document.querySelectorAll('.tag.selected')).map(tag => tag.dataset.value);
    settings.tags = selectedTags;
    
    // Get category states
    const categoryItems = document.querySelectorAll('.category-item');
    const categoryStates = {};
    categoryItems.forEach(item => {
        const category = item.dataset.category;
        const state = parseInt(item.getAttribute('data-state') || '0');
        categoryStates[category] = state;
    });
    settings.category_states = categoryStates;
    
    // Get excluded sites
    const selectedSites = document.getElementById('selectedSites');
    const excludedSites = selectedSites ? 
        Array.from(selectedSites.querySelectorAll('.selected-site')).map(site => {
            return site.textContent.replace('×', '').trim();
        }) : [];
    settings.excluded_sites = excludedSites;
    
    return settings;
}

function saveCurrentSettings() {
    const settings = getCurrentSettings();
    const settingsJson = JSON.stringify(settings, null, 2);
    
    // Create a blob and download link
    const blob = new Blob([settingsJson], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    
    // Create filename with timestamp
    const timestamp = new Date().toISOString().split('T')[0].replace(/-/g, '');
    const filename = `blackbird_settings_${timestamp}.json`;
    
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    // Show success message
    alert(`Settings saved to ${filename}`);
}

function loadSettingsFromFile(file) {
    const reader = new FileReader();
    
    reader.onload = function(e) {
        let jsonContent = e.target.result;
        
        // Try multiple parsing strategies
        try {
            // Strategy 1: Try direct parse
            const settings = JSON.parse(jsonContent);
            applySettings(settings);
            alert('Settings loaded successfully!');
            return;
        } catch (error1) {
            console.warn('Direct parse failed:', error1);
        }
        
        try {
            // Strategy 2: Try to fix common JSON issues
            jsonContent = fixJsonIssues(jsonContent);
            const settings = JSON.parse(jsonContent);
            applySettings(settings);
            alert('Settings loaded successfully! (JSON was automatically corrected)');
            return;
        } catch (error2) {
            console.warn('Fixed parse failed:', error2);
        }
        
        // If all strategies fail
        alert('Error: Unable to parse the JSON file. Please ensure it\'s a valid Blackbird settings file.');
    };
    
    reader.onerror = function() {
        alert('Error reading the file. Please try again.');
    };
    
    reader.readAsText(file);
}

function fixJsonIssues(jsonString) {
    let fixed = jsonString;
    
    // 1. Remove trailing commas
    fixed = fixed.replace(/,\s*}/g, '}');
    fixed = fixed.replace(/,\s*]/g, ']');
    
    // 2. Replace single quotes with double quotes (carefully)
    fixed = fixed.replace(/'([^']*)'/g, '"$1"');
    
    // 3. Fix unescaped quotes
    fixed = fixed.replace(/:\s*"([^"\\]*(?:\\.[^"\\]*)*)",/g, ':"$1",');
    
    // 4. Remove BOM if present
    if (fixed.charCodeAt(0) === 0xFEFF) {
        fixed = fixed.substring(1);
    }
    
    // 5. Fix JavaScript-style comments (remove them)
    fixed = fixed.replace(/\/\/.*$/gm, '');
    fixed = fixed.replace(/\/\*[\s\S]*?\*\//g, '');
    
    return fixed;
}

function validateSettings(settings) {
    const requiredFields = ['version', 'search_type'];
    const optionalFields = [
        'usernames', 'emails', 'top_sites', 'timeout', 'max_concurrent',
        'all_sites', 'no_nsfw', 'include_categories', 'excludeCategories',
        'category_filter', 'site', 'filter', 'proxy', 'tor_proxy',
        'save_csv', 'save_json', 'save_pdf', 'verbose', 'enable_frequency',
        'show_common_sites', 'tags', 'category_states', 'excluded_sites'
    ];
    
    // Check required fields
    for (const field of requiredFields) {
        if (!(field in settings)) {
            throw new Error(`Missing required field: ${field}`);
        }
    }
    
    // Check version
    if (settings.version !== '1.0') {
        throw new Error(`Unsupported settings version: ${settings.version}`);
    }
    
    // Validate search_type
    if (!['username', 'email'].includes(settings.search_type)) {
        throw new Error(`Invalid search_type: ${settings.search_type}`);
    }
    
    return true;
}

function applySettings(settings) {
    try {
        // Validate settings before applying
        validateSettings(settings);
    } catch (validationError) {
        throw new Error(`Invalid settings format: ${validationError.message}`);
    }
    
    // Set search type
    if (settings.search_type) {
        const searchTypeBtns = document.querySelectorAll('.search-type-btn');
        searchTypeBtns.forEach(btn => btn.classList.remove('active'));
        const targetBtn = document.querySelector(`.search-type-btn[data-type="${settings.search_type}"]`);
        if (targetBtn) {
            targetBtn.classList.add('active');
            const type = targetBtn.dataset.type;
            const sections = {
                'username': document.getElementById('usernameSection'),
                'email': document.getElementById('emailSection')
            };
            
            Object.keys(sections).forEach(key => {
                if (key === type) {
                    sections[key].classList.add('active');
                    if (type === 'username') {
                        document.getElementById('usernames').required = true;
                        document.getElementById('emails').required = false;
                    } else {
                        document.getElementById('usernames').required = false;
                        document.getElementById('emails').required = true;
                    }
                } else {
                    sections[key].classList.remove('active');
                }
            });
        }
    }
    
    // Apply form field values
    if (settings.usernames !== undefined && document.getElementById('usernames')) {
        document.getElementById('usernames').value = settings.usernames;
    }
    if (settings.emails !== undefined && document.getElementById('emails')) {
        document.getElementById('emails').value = settings.emails;
    }
    if (settings.top_sites !== undefined && document.getElementById('top_sites')) {
        document.getElementById('top_sites').value = settings.top_sites;
    }
    if (settings.timeout !== undefined && document.getElementById('timeout')) {
        document.getElementById('timeout').value = settings.timeout;
    }
    if (settings.max_concurrent !== undefined && document.getElementById('max_concurrent')) {
        document.getElementById('max_concurrent').value = settings.max_concurrent;
    }
    if (settings.all_sites !== undefined && document.getElementById('all_sites')) {
        document.getElementById('all_sites').checked = settings.all_sites;
    }
    if (settings.no_nsfw !== undefined && document.getElementById('no_nsfw')) {
        document.getElementById('no_nsfw').checked = settings.no_nsfw;
    }
    if (settings.include_categories !== undefined && document.getElementById('includeCategories')) {
        document.getElementById('includeCategories').value = settings.include_categories;
    }
    if (settings.exclude_categories !== undefined && document.getElementById('excludeCategories')) {
        document.getElementById('excludeCategories').value = settings.exclude_categories;
    }
    if (settings.category_filter !== undefined && document.getElementById('categoryFilter')) {
        document.getElementById('categoryFilter').value = settings.category_filter;
    }
    if (settings.site !== undefined && document.getElementById('site')) {
        document.getElementById('site').value = settings.site;
    }
    if (settings.filter !== undefined && document.getElementById('filter')) {
        document.getElementById('filter').value = settings.filter;
    }
    if (settings.proxy !== undefined && document.getElementById('proxy')) {
        document.getElementById('proxy').value = settings.proxy;
    }
    if (settings.tor_proxy !== undefined && document.getElementById('tor_proxy')) {
        document.getElementById('tor_proxy').value = settings.tor_proxy;
    }
    if (settings.save_csv !== undefined && document.getElementById('save_csv')) {
        document.getElementById('save_csv').checked = settings.save_csv;
    }
    if (settings.save_json !== undefined && document.getElementById('save_json')) {
        document.getElementById('save_json').checked = settings.save_json;
    }
    if (settings.save_pdf !== undefined && document.getElementById('save_pdf')) {
        document.getElementById('save_pdf').checked = settings.save_pdf;
    }
    if (settings.verbose !== undefined && document.getElementById('verbose')) {
        document.getElementById('verbose').checked = settings.verbose;
    }
    if (settings.enable_frequency !== undefined && document.getElementById('enable_frequency')) {
        document.getElementById('enable_frequency').checked = settings.enable_frequency;
    }
    if (settings.show_common_sites !== undefined && document.getElementById('show_common_sites')) {
        document.getElementById('show_common_sites').checked = settings.show_common_sites;
    }
    
    // Apply tags
    if (settings.tags && Array.isArray(settings.tags)) {
        const tagElements = document.querySelectorAll('.tag');
        tagElements.forEach(tagElement => {
            tagElement.classList.remove('selected');
            const tagValue = tagElement.dataset.value;
            if (settings.tags.includes(tagValue)) {
                tagElement.classList.add('selected');
            }
        });
        
        // Update hidden select
        const hiddenSelect = document.getElementById('tags');
        if (hiddenSelect) {
            Array.from(hiddenSelect.options).forEach(option => {
                option.selected = settings.tags.includes(option.value);
            });
        }
    }
    
    // Apply category states
    if (settings.category_states) {
        const categoryItems = document.querySelectorAll('.category-item');
        
        // Update global categoryStates
        if (window.categoryStates) {
            Object.keys(settings.category_states).forEach(category => {
                window.categoryStates[category] = settings.category_states[category];
            });
        }
        
        categoryItems.forEach(item => {
            const category = item.dataset.category;
            const state = settings.category_states[category] || 0;
            
            item.classList.remove('selected', 'excluded');
            if (state === 1) {
                item.classList.add('selected');
            } else if (state === 2) {
                item.classList.add('excluded', 'selected');
            }
            
            item.setAttribute('data-state', state.toString());
        });
        
        // Update category filter using global function
        if (window.updateCategoryFilter) {
            window.updateCategoryFilter();
        }
    }
    
    // Apply excluded sites
    if (settings.excluded_sites && Array.isArray(settings.excluded_sites)) {
        const selectedSitesContainer = document.getElementById('selectedSites');
        if (selectedSitesContainer) {
            selectedSitesContainer.innerHTML = '';
            
            // Update global selectedSites
            if (window.selectedSites) {
                window.selectedSites.clear();
                settings.excluded_sites.forEach(site => window.selectedSites.add(site));
            }
            
            settings.excluded_sites.forEach(site => {
                const siteElement = document.createElement('span');
                siteElement.className = 'selected-site';
                siteElement.innerHTML = `
                    <i class="fas fa-ban me-1" style="font-size: 0.8rem;"></i>
                    ${site}<span class="remove-site" data-site="${site}">&times;</span>`;
                selectedSitesContainer.appendChild(siteElement);
            });
            
            // Update hidden input
            if (document.getElementById('site')) {
                document.getElementById('site').value = Array.from(settings.excluded_sites).join(',');
            }
            
            // Update filter using global function
            if (window.updateFilterFromSelections) {
                window.updateFilterFromSelections();
            }
        }
    }
    
    // Update frequency preview visibility
    const preview = document.getElementById('frequencyPreview');
    if (preview) {
        preview.style.display = settings.enable_frequency ? 'block' : 'none';
    }
}

function resetToDefaultSettings() {
    // Reset form to default values
    if (document.getElementById('usernames')) document.getElementById('usernames').value = '';
    if (document.getElementById('emails')) document.getElementById('emails').value = '';
    if (document.getElementById('top_sites')) document.getElementById('top_sites').value = '500';
    if (document.getElementById('timeout')) document.getElementById('timeout').value = '30';
    if (document.getElementById('max_concurrent')) document.getElementById('max_concurrent').value = '30';
    if (document.getElementById('all_sites')) document.getElementById('all_sites').checked = false;
    if (document.getElementById('no_nsfw')) document.getElementById('no_nsfw').checked = false;
    if (document.getElementById('includeCategories')) document.getElementById('includeCategories').value = '';
    if (document.getElementById('excludeCategories')) document.getElementById('excludeCategories').value = '';
    if (document.getElementById('categoryFilter')) document.getElementById('categoryFilter').value = '';
    if (document.getElementById('site')) document.getElementById('site').value = '';
    if (document.getElementById('filter')) document.getElementById('filter').value = '';
    if (document.getElementById('proxy')) document.getElementById('proxy').value = '';
    if (document.getElementById('tor_proxy')) document.getElementById('tor_proxy').value = '';
    if (document.getElementById('save_csv')) document.getElementById('save_csv').checked = true;
    if (document.getElementById('save_json')) document.getElementById('save_json').checked = true;
    if (document.getElementById('save_pdf')) document.getElementById('save_pdf').checked = false;
    if (document.getElementById('verbose')) document.getElementById('verbose').checked = false;
    if (document.getElementById('enable_frequency')) document.getElementById('enable_frequency').checked = false;
    if (document.getElementById('show_common_sites')) document.getElementById('show_common_sites').checked = true;
    
    // Reset tags
    const tagElements = document.querySelectorAll('.tag');
    tagElements.forEach(tagElement => {
        tagElement.classList.remove('selected');
    });
    
    // Reset category states
    const categoryItems = document.querySelectorAll('.category-item');
    categoryItems.forEach(item => {
        item.classList.remove('selected', 'excluded');
        item.setAttribute('data-state', '0');
    });
    
    // Reset excluded sites
    const selectedSitesContainer = document.getElementById('selectedSites');
    if (selectedSitesContainer) {
        selectedSitesContainer.innerHTML = '';
        if (window.selectedSites) {
            window.selectedSites.clear();
        }
        if (document.getElementById('site')) {
            document.getElementById('site').value = '';
        }
    }
    
    // Update category filter
    if (window.updateCategoryFilter) {
        window.updateCategoryFilter();
    }
    
    // Update search type to default (username)
    const searchTypeBtns = document.querySelectorAll('.search-type-btn');
    searchTypeBtns.forEach(btn => btn.classList.remove('active'));
    const usernameBtn = document.querySelector('.search-type-btn[data-type="username"]');
    if (usernameBtn) {
        usernameBtn.classList.add('active');
    }
    
    // Hide frequency preview
    const preview = document.getElementById('frequencyPreview');
    if (preview) {
        preview.style.display = 'none';
    }
    
    // Hide settings display
    const settingsDisplay = document.getElementById('currentSettingsDisplay');
    if (settingsDisplay) {
        settingsDisplay.style.display = 'none';
    }
    
    alert('Settings have been reset to default values.');
}

// ============================
// USERNAME SITE LOOKUP FUNCTIONS
// ============================
function setupUsernameLookup() {
    const usernameLookup = document.getElementById('usernameLookup');
    const lookupButton = document.getElementById('lookupUsername');
    
    if (!usernameLookup || !lookupButton) return;
    
    // Debounce function for autocomplete
    let debounceTimer;
    usernameLookup.addEventListener('input', function(e) {
        clearTimeout(debounceTimer);
        const searchTerm = this.value.trim();
        
        if (searchTerm.length >= 2) {  // Start autocomplete after 2 characters
            debounceTimer = setTimeout(() => {
                autocompleteUsername(searchTerm);
            }, 300);
        }
    });
    
    // Handle Enter key
    usernameLookup.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            lookupUsernameSites();
        }
    });
    
    // Handle button click
    lookupButton.addEventListener('click', lookupUsernameSites);
    
    // Handle datalist selection
    usernameLookup.addEventListener('change', function() {
        lookupUsernameSites();
    });
}

async function autocompleteUsername(searchTerm) {
    try {
        const response = await fetch(`/api/frequency/autocomplete?q=${encodeURIComponent(searchTerm)}`);
        const data = await response.json();
        
        if (data.error) {
            console.error('Autocomplete error:', data.error);
            return;
        }
        
        const datalist = document.getElementById('usernameSuggestions');
        if (!datalist) return;
        
        datalist.innerHTML = '';  // Clear previous options
        
        if (data.suggestions && data.suggestions.length > 0) {
            data.suggestions.forEach(suggestion => {
                const option = document.createElement('option');
                option.value = suggestion.value;
                option.dataset.type = suggestion.type;
                option.dataset.siteCount = suggestion.site_count;
                datalist.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Error fetching autocomplete:', error);
    }
}

async function lookupUsernameSites() {
    const usernameLookup = document.getElementById('usernameLookup');
    const resultsDiv = document.getElementById('usernameSitesResults');
    
    if (!usernameLookup || !resultsDiv) return;
    
    const username = usernameLookup.value.trim();
    
    if (!username) {
        resultsDiv.innerHTML = '<div class="alert alert-warning">Please enter a username or email</div>';
        return;
    }
    
    resultsDiv.innerHTML = `
        <div class="text-center">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p>Searching for sites registered to "${username}"...</p>
        </div>
    `;
    
    try {
        const response = await fetch(`/api/frequency/username-sites?username=${encodeURIComponent(username)}`);
        const data = await response.json();
        
        if (data.error) {
            resultsDiv.innerHTML = `<div class="alert alert-danger">${data.error}</div>`;
            return;
        }
        
        if (data.total_sites === 0) {
            resultsDiv.innerHTML = `
                <div class="alert alert-info">
                    <i class="fas fa-info-circle"></i>
                    No sites found for "${data.username}" in historical data.
                </div>
            `;
            return;
        }
        
        let html = `
            <div class="card">
                <div class="card-header bg-primary text-white">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <i class="fas fa-user"></i> ${data.username}
                            <span class="badge bg-light text-dark ms-2">${data.identifier_type}</span>
                        </div>
                        <span class="badge bg-success">Found on ${data.total_sites} sites</span>
                    </div>
                </div>
                <div class="card-body">
                    <div class="table-responsive">
                        <table class="table table-hover">
                            <thead>
                                <tr>
                                    <th>#</th>
                                    <th>Site Name</th>
                                    <th>Popularity Rank</th>
                                    <th>Times Found</th>
                                    <th>Status</th>
                                </tr>
                            </thead>
                            <tbody>
        `;
        
        data.sites_found.sort((a, b) => a.popularity_rank - b.popularity_rank);
        
        data.sites_found.forEach((site, index) => {
            // Determine badge color based on popularity rank
            let rankBadgeClass = 'bg-secondary';
            if (site.popularity_rank <= 10) {
                rankBadgeClass = 'bg-danger';
            } else if (site.popularity_rank <= 50) {
                rankBadgeClass = 'bg-warning text-dark';
            } else if (site.popularity_rank <= 100) {
                rankBadgeClass = 'bg-info';
            }
            
            html += `
                <tr>
                    <td>${index + 1}</td>
                    <td>
                        <strong>${site.site_name}</strong>
                    </td>
                    <td>
                        <span class="badge ${rankBadgeClass}">
                            #${site.popularity_rank}
                        </span>
                    </td>
                    <td>${site.found_count}</td>
                    <td>
                        <span class="badge bg-success">
                            <i class="fas fa-check"></i> Registered
                        </span>
                    </td>
                </tr>
            `;
        });
        
        html += `
                            </tbody>
                        </table>
                    </div>
                    <div class="mt-3">
                        <small class="text-muted">
                            <i class="fas fa-info-circle"></i>
                            Based on historical search results. Sites are ordered by popularity.
                        </small>
                    </div>
                </div>
            </div>
        `;
        
        resultsDiv.innerHTML = html;
        
    } catch (error) {
        console.error('Error looking up username sites:', error);
        resultsDiv.innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-triangle"></i>
                Error looking up username sites: ${error.message}
            </div>
        `;
    }
}

// ============================
// SEARCH TYPE TOGGLE
// ============================
function setupSearchTypeToggle() {
    const buttons = document.querySelectorAll('.search-type-btn');
    const sections = {
        'username': document.getElementById('usernameSection'),
        'email': document.getElementById('emailSection')
    };
    
    if (!buttons.length || !sections.username || !sections.email) return;
    
    buttons.forEach(btn => {
        btn.addEventListener('click', function() {
            const type = this.dataset.type;
            
            // Update active button
            buttons.forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            
            // Show/hide sections
            Object.keys(sections).forEach(key => {
                if (key === type) {
                    sections[key].classList.add('active');
                    // Update form field requirements
                    if (type === 'username') {
                        document.getElementById('usernames').required = true;
                        document.getElementById('emails').required = false;
                    } else {
                        document.getElementById('usernames').required = false;
                        document.getElementById('emails').required = true;
                }
                } else {
                    sections[key].classList.remove('active');
                }
            });
        });
    });
}

// ============================
// STATISTICS LOADING
// ============================
async function loadStats() {
    try {
        const response = await fetch('/api/stats');
        const stats = await response.json();
        
        if (!stats.error) {
            if (document.getElementById('totalSites')) {
                document.getElementById('totalSites').textContent = stats.username_sites || '--';
            }
            if (document.getElementById('emailSites')) {
                document.getElementById('emailSites').textContent = stats.email_sites || '--';
            }
            if (document.getElementById('activeJobs')) {
                document.getElementById('activeJobs').textContent = stats.active_jobs || 0;
            }
            if (document.getElementById('completedJobs')) {
                document.getElementById('completedJobs').textContent = stats.completed_jobs || 0;
            }
        }
    } catch (error) {
        console.error('Error loading stats:', error);
    }
}

// ============================
// TAG CLOUD SETUP
// ============================
function setupTagCloud() {
    const tagCloud = document.getElementById('tagCloud');
    const hiddenSelect = document.getElementById('tags');
    
    if (!tagCloud || !hiddenSelect) return;
    
    const tags = Array.from(tagCloud.querySelectorAll('.tag'));
    
    tags.forEach(tagElement => {
        tagElement.addEventListener('click', function() {
            const tagValue = this.dataset.value;
            const isSelected = this.classList.toggle('selected');
            
            const options = Array.from(hiddenSelect.options);
            const option = options.find(opt => opt.value === tagValue);
            if (option) {
                option.selected = isSelected;
            }
            
            console.log(`Tag "${tagValue}" ${isSelected ? 'selected' : 'unselected'}`);
        });
    });
    
    Array.from(hiddenSelect.selectedOptions).forEach(option => {
        const tagElement = tagCloud.querySelector(`.tag[data-value="${option.value}"]`);
        if (tagElement) {
            tagElement.classList.add('selected');
        }
    });
}

// ============================
// SITE SELECTION SETUP
// ============================
function setupSiteSelection() {
    const siteInput = document.getElementById('siteInput');
    const hiddenInput = document.getElementById('site');
    const filterInput = document.getElementById('filter');
    const selectedSitesContainer = document.getElementById('selectedSites');
    
    if (!siteInput || !selectedSitesContainer || !filterInput || !hiddenInput) return;
    
    let selectedSites = new Set();
    
    function updateHiddenInput() {
        hiddenInput.value = Array.from(selectedSites).join(',');
    }
    
    window.updateFilterFromSelections = function() {
        // Get category filters
        const includeCategories = document.getElementById('includeCategories')?.value || '';
        const excludeCategories = document.getElementById('excludeCategories')?.value || '';
        
        // Build filter parts
        let filterParts = [];
        
        // 1. Add INCLUDED categories using OR operator (|) for multiple categories
        if (includeCategories) {
            const included = includeCategories.split(',').filter(c => c);
            if (included.length > 0) {
                if (included.length === 1) {
                    filterParts.push(`cat=${included[0]}`);
                } else {
                    // Use OR operator (|) for multiple included categories
                    filterParts.push(`cat=${included.join('|')}`);
                }
            }
        }
        
        // 2. Add EXCLUDED categories - each as separate condition with AND
        if (excludeCategories) {
            const excluded = excludeCategories.split(',').filter(c => c);
            if (excluded.length > 0) {
                // Create separate condition for each excluded category
                excluded.forEach(category => {
                    filterParts.push(`cat!=${category}`);
                });
            }
        }
        
        // 3. Add EXCLUDED sites - each as separate condition with AND
        if (selectedSites.size > 0) {
            const excludedSites = Array.from(selectedSites);
            // Create separate condition for each excluded site
            excludedSites.forEach(site => {
                filterParts.push(`name!=${site}`);
            });
        }
        
        // Combine all filter parts with AND operator
        if (filterParts.length > 0) {
            filterInput.value = filterParts.join(' and ');
        } else {
            filterInput.value = '';
        }
        
        console.log('Generated filter from selections:', filterInput.value);
    };
    
    function addSite(site) {
        if (site && !selectedSites.has(site)) {
            selectedSites.add(site);
            updateHiddenInput();
            if (window.updateFilterFromSelections) {
                window.updateFilterFromSelections(); // Update the filter
            }
            
            // Create visual element for selected site
            const siteElement = document.createElement('span');
            siteElement.className = 'selected-site';
            siteElement.innerHTML = `
                <i class="fas fa-ban me-1" style="font-size: 0.8rem;"></i>
                ${site}<span class="remove-site" data-site="${site}">&times;</span>`;
            selectedSitesContainer.appendChild(siteElement);
        }
    }
    
    function removeSite(site) {
        selectedSites.delete(site);
        updateHiddenInput();
        if (window.updateFilterFromSelections) {
            window.updateFilterFromSelections(); // Update the filter
        }
        
        // Remove visual element
        const siteElements = selectedSitesContainer.querySelectorAll('.selected-site');
        siteElements.forEach(el => {
            if (el.querySelector('.remove-site').dataset.site === site) {
                el.remove();
            }
        });
    }
    
    siteInput.addEventListener('change', function(e) {
        const value = this.value.trim();
        if (value) {
            addSite(value);
            this.value = '';
        }
    });
    
    selectedSitesContainer.addEventListener('click', function(e) {
        if (e.target.classList.contains('remove-site')) {
            removeSite(e.target.dataset.site);
        }
    });
    
    siteInput.addEventListener('paste', function(e) {
        e.preventDefault();
        const paste = (e.clipboardData || window.clipboardData).getData('text');
        const sites = paste.split(',').map(site => site.trim()).filter(site => site);
        sites.forEach(addSite);
    });
    
    // Store selectedSites globally for use in applySettings
    window.selectedSites = selectedSites;
}

// ============================
// CATEGORY FILTER SETUP
// ============================
function setupCategoryFilter() {
    const categoryItems = document.querySelectorAll('.category-item');
    const includeInput = document.getElementById('includeCategories');
    const excludeInput = document.getElementById('excludeCategories');
    const categoryFilterInput = document.getElementById('categoryFilter');
    
    if (!categoryItems.length || !includeInput || !excludeInput || !categoryFilterInput) return;
    
    // States: 0 = unselected, 1 = included, 2 = excluded
    const categoryStates = {};
    
    // Initialize all category states to 0 (unselected)
    categoryItems.forEach(item => {
        const category = item.dataset.category;
        categoryStates[category] = 0; // Initialize to 0
    });
    
    // Make updateCategoryFilter available globally
    window.updateCategoryFilter = function() {
        const included = [];
        const excluded = [];
        
        console.log('Updating category filter...');
        
        // Update UI and collect categories
        categoryItems.forEach(item => {
            const category = item.dataset.category;
            const state = categoryStates[category];
            
            // Update UI classes
            item.classList.remove('selected', 'excluded');
            if (state === 1) {
                item.classList.add('selected');
                included.push(category);
                console.log(`✓ Included: ${category}`);
            } else if (state === 2) {
                item.classList.add('excluded', 'selected');
                excluded.push(category);
                console.log(`✗ Excluded: ${category}`);
            }
            
            // Update data-state attribute for debugging
            item.setAttribute('data-state', state.toString());
        });
        
        // Update hidden inputs
        includeInput.value = included.join(',');
        excludeInput.value = excluded.join(',');
        
        console.log('Included categories:', included);
        console.log('Excluded categories:', excluded);
        
        // Build Blackbird filter syntax
        let filterParts = [];

        // For INCLUDED categories: use cat=category1|category2 (OR operator)
        if (included.length > 0) {
            if (included.length === 1) {
                filterParts.push(`cat=${included[0]}`);
            } else {
                // Use OR operator (|) for multiple included categories
                filterParts.push(`cat=${included.join('|')}`);
            }
        }

        // For EXCLUDED categories: use separate cat!= for each with AND
        if (excluded.length > 0) {
            // Create separate condition for each excluded category
            excluded.forEach(category => {
                filterParts.push(`cat!=${category}`);
            });
        }

        // Combine filters with AND (space separated in Blackbird syntax)
        const finalFilter = filterParts.join(' and ');
        categoryFilterInput.value = finalFilter;

        console.log('Generated filter:', finalFilter);
        
        // Update status display
        const includedCount = document.getElementById('includedCount');
        const excludedCount = document.getElementById('excludedCount');
        
        if (includedCount) {
            includedCount.textContent = `${included.length} categories included`;
        }
        if (excludedCount) {
            excludedCount.textContent = `${excluded.length} categories excluded`;
        }
        
        return finalFilter;
    };
    
    // Add click handlers to category items
    categoryItems.forEach(item => {
        item.addEventListener('click', function() {
            const category = this.dataset.category;
            
            // Cycle through states: 0 → 1 → 2 → 0
            const newState = (categoryStates[category] + 1) % 3;
            categoryStates[category] = newState;
            
            console.log(`Category ${category} state changed to: ${newState}`);
            
            const finalFilter = window.updateCategoryFilter();
            
            // Debug: Log the current filter state
            console.log('Current filter after click:', finalFilter);
        });
    });
    
    // Also store categoryStates globally for use in applySettings
    window.categoryStates = categoryStates;
    
    // Initial update
    window.updateCategoryFilter();
}

// ============================
// FORM SUBMISSION SETUP
// ============================
function setupFormSubmission() {
    const form = document.getElementById('usernameForm');
    if (!form) return;
    
    form.addEventListener('submit', function(e) {
        // Get verbose checkbox state
        const verboseChecked = document.getElementById('verbose')?.checked || false;
        
        if (verboseChecked) {
            console.log('=== VERBOSE FORM SUBMISSION DEBUG ===');
        }
        
        // Validate at least one search field is filled
        const searchType = document.querySelector('.search-type-btn.active')?.dataset.type || 'username';
        let isValid = false;
        
        if (searchType === 'username') {
            const usernames = document.getElementById('usernames')?.value.trim() || '';
            if (usernames) {
                isValid = true;
                if (verboseChecked) {
                    console.log('Search type:', searchType);
                    console.log('Username search:', usernames);
                }
            } else {
                alert('Please enter at least one username');
            }
        } else {
            const emails = document.getElementById('emails')?.value.trim() || '';
            if (emails) {
                isValid = true;
                if (verboseChecked) {
                    console.log('Search type:', searchType);
                    console.log('Email search:', emails);
                }
            } else {
                alert('Please enter at least one email address');
            }
        }
        
        if (!isValid) {
            e.preventDefault();
            return;
        }
        
        // Force update of category filter before submission
        if (verboseChecked) {
            console.log('=== Form Submission Debug ===');
        } else {
            console.log('=== Form Submission Debug ===');
        }
        
        // Get category filter values
        const includeCategories = document.getElementById('includeCategories')?.value || '';
        const excludeCategories = document.getElementById('excludeCategories')?.value || '';
        const categoryFilter = document.getElementById('categoryFilter')?.value || '';
        const customFilter = document.getElementById('filter')?.value || '';
        
        let selectedTags = [];
        
        const tagsSelect = document.getElementById('tags');
        if (tagsSelect) {
            selectedTags = Array.from(tagsSelect.selectedOptions).map(opt => opt.value);
        }
        
        if (selectedTags.length === 0) {
            const selectedTagElements = document.querySelectorAll('.tag.selected');
            selectedTags = Array.from(selectedTagElements).map(el => el.dataset.value);
        }
        
        if (verboseChecked) {
            console.log('Include categories:', includeCategories);
            console.log('Exclude categories:', excludeCategories);
            console.log('Generated category filter:', categoryFilter);
            console.log('Custom filter:', customFilter);
            console.log('Selected tags:', selectedTags);
            console.log('Verbose mode enabled:', verboseChecked);
            
            // Log other form values
            console.log('Max sites:', document.getElementById('top_sites')?.value || '');
            console.log('Timeout:', document.getElementById('timeout')?.value || '');
            console.log('Concurrent requests:', document.getElementById('max_concurrent')?.value || '');
            console.log('Search all sites:', document.getElementById('all_sites')?.checked || false);
            console.log('Exclude NSFW:', document.getElementById('no_nsfw')?.checked || false);
            console.log('Save CSV:', document.getElementById('save_csv')?.checked || false);
            console.log('Save JSON:', document.getElementById('save_json')?.checked || false);
            console.log('Save PDF:', document.getElementById('save_pdf')?.checked || false);
        }
        
        // Combine category filter with custom filter
        let finalFilter = '';

        // Start with category filter from categoryFilterInput (already has correct format)
        if (categoryFilter) {
            finalFilter = categoryFilter;
        }

        // Add site exclusions from the site input - each as separate condition
        const siteExclusions = document.getElementById('site')?.value || '';
        if (siteExclusions) {
            const sites = siteExclusions.split(',').filter(s => s.trim());
            if (sites.length > 0) {
                // Create separate condition for each excluded site
                const siteExclusionConditions = sites.map(site => `name!=${site}`);
                const siteExclusionFilter = siteExclusionConditions.join(' and ');
                
                if (finalFilter) {
                    finalFilter += ` and ${siteExclusionFilter}`;
                } else {
                    finalFilter = siteExclusionFilter;
                }
            }
        }

        // Finally, append any custom filter
        if (customFilter && customFilter.trim()) {
            if (finalFilter) {
                finalFilter += ` and ${customFilter.trim()}`;
            } else {
                finalFilter = customFilter.trim();
            }
        }

        if (verboseChecked) {
            console.log('Final combined filter:', finalFilter);
        }
        
        // Update all filter-related fields
        if (document.getElementById('includeCategories')) {
            document.getElementById('includeCategories').value = includeCategories;
        }
        if (document.getElementById('excludeCategories')) {
            document.getElementById('excludeCategories').value = excludeCategories;
        }
        if (document.getElementById('categoryFilter')) {
            document.getElementById('categoryFilter').value = categoryFilter;
        }
        if (document.getElementById('filter')) {
            document.getElementById('filter').value = finalFilter;
        }
        
        if (tagsSelect) {
            Array.from(tagsSelect.options).forEach(option => {
                option.selected = false;
            });
            
            selectedTags.forEach(tagValue => {
                const option = tagsSelect.querySelector(`option[value="${tagValue}"]`);
                if (option) {
                    option.selected = true;
                }
            });
        }
        
        if (verboseChecked) {
            console.log('Form fields updated. Submitting...');
            console.log('=== END VERBOSE DEBUG ===');
        } else {
            console.log('Form fields updated. Submitting...');
        }
        
        // Allow form submission to proceed
    });
}

// ============================
// FREQUENCY ANALYSIS SETUP
// ============================
function setupFrequencyAnalysis() {
    const enableFrequencyCheckbox = document.getElementById('enable_frequency');
    const searchHistoricalButton = document.getElementById('searchHistorical');
    const historicalSearchInput = document.getElementById('historicalSearch');
    
    if (!enableFrequencyCheckbox) return;
    
    // Toggle frequency preview
    enableFrequencyCheckbox.addEventListener('change', function() {
        const preview = document.getElementById('frequencyPreview');
        if (preview) {
            preview.style.display = this.checked ? 'block' : 'none';
            
            if (this.checked) {
                // Load initial historical data
                loadHistoricalOverview();
            }
        }
    });
    
    // Historical search functionality
    if (searchHistoricalButton) {
        searchHistoricalButton.addEventListener('click', function() {
            const searchTerm = historicalSearchInput?.value.trim() || '';
            if (searchTerm) {
                searchHistoricalData(searchTerm);
            }
        });
    }
    
    if (historicalSearchInput) {
        historicalSearchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                const searchTerm = this.value.trim();
                if (searchTerm) {
                    searchHistoricalData(searchTerm);
                }
            }
        });
    }
}

async function loadHistoricalOverview() {
    try {
        const response = await fetch('/api/frequency/overview');
        const data = await response.json();
        
        const resultsDiv = document.getElementById('historicalResults');
        if (!resultsDiv) return;
        
        if (data.error) {
            resultsDiv.innerHTML = 
                `<div class="alert alert-warning">${data.error}</div>`;
            return;
        }
        
        let html = `
            <div class="row">
                <div class="col-md-6">
                    <div class="frequency-result-item">
                        <h6><i class="fas fa-file-alt"></i> Reports</h6>
                        <div class="h4">${data.total_reports}</div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="frequency-result-item">
                        <h6><i class="fas fa-users"></i> Unique Users</h6>
                        <div class="h4">${data.unique_usernames + data.unique_emails}</div>
                    </div>
                </div>
            </div>
            <div class="mt-3">
                <h6><i class="fas fa-trophy"></i> Most Common Sites</h6>
                <div class="list-group">
        `;
        
        if (data.most_common_sites && data.most_common_sites.length > 0) {
            data.most_common_sites.forEach((site, index) => {
                const percentage = ((site.count / data.total_accounts) * 100).toFixed(1);
                html += `
                    <div class="list-group-item list-group-item-action">
                        <div class="d-flex justify-content-between align-items-center">
                            <span>
                                <span class="badge bg-primary me-2">${index + 1}</span>
                                ${site.site}
                            </span>
                            <span class="text-muted">
                                ${site.count} accounts (${percentage}%)
                            </span>
                        </div>
                        <div class="frequency-bar">
                            <div class="frequency-bar-fill" style="width: ${Math.min(100, percentage)}%"></div>
                        </div>
                    </div>
                `;
            });
        } else {
            html += `<div class="alert alert-info">No historical data available yet.</div>`;
        }
        
        html += `
                </div>
            </div>
        `;
        
        resultsDiv.innerHTML = html;
        
    } catch (error) {
        console.error('Error loading historical overview:', error);
        const resultsDiv = document.getElementById('historicalResults');
        if (resultsDiv) {
            resultsDiv.innerHTML = 
                `<div class="alert alert-danger">Error loading historical data: ${error.message}</div>`;
        }
    }
}

async function searchHistoricalData(searchTerm) {
    try {
        const response = await fetch(`/api/frequency/search?q=${encodeURIComponent(searchTerm)}`);
        const data = await response.json();
        
        const resultsDiv = document.getElementById('historicalResults');
        if (!resultsDiv) return;
        
        if (data.error) {
            resultsDiv.innerHTML = 
                `<div class="alert alert-warning">${data.error}</div>`;
            return;
        }
        
        let html = `<h6>Search Results for "${searchTerm}"</h6>`;
        
        if (data.total_matches === 0) {
            html += `<div class="alert alert-info">No matches found.</div>`;
        } else {
            html += `<p class="text-muted">Found ${data.total_matches} matches</p>`;
            
            if (data.usernames.length > 0) {
                html += `
                    <h6 class="mt-3"><i class="fas fa-user"></i> Usernames (${data.usernames.length})</h6>
                    <div class="list-group">
                `;
                data.usernames.forEach(user => {
                    html += `
                        <div class="list-group-item">
                            <div class="d-flex justify-content-between">
                                <strong>${user.username}</strong>
                                <span class="badge bg-info">${user.site_count} sites</span>
                            </div>
                            <small class="text-muted">
                                First: ${user.first_seen || 'N/A'} | 
                                Last: ${user.last_seen || 'N/A'}
                            </small>
                        </div>
                    `;
                });
                html += `</div>`;
            }
            
            if (data.emails.length > 0) {
                html += `
                    <h6 class="mt-3"><i class="fas fa-envelope"></i> Emails (${data.emails.length})</h6>
                    <div class="list-group">
                `;
                data.emails.forEach(email => {
                    html += `
                        <div class="list-group-item">
                            <div class="d-flex justify-content-between">
                                <strong>${email.email}</strong>
                                <span class="badge bg-info">${email.site_count} sites</span>
                            </div>
                            <small class="text-muted">
                                First: ${email.first_seen || 'N/A'} | 
                                Last: ${email.last_seen || 'N/A'}
                            </small>
                        </div>
                    `;
                });
                html += `</div>`;
            }
            
            if (data.sites.length > 0) {
                html += `
                    <h6 class="mt-3"><i class="fas fa-globe"></i> Sites (${data.sites.length})</h6>
                    <div class="list-group">
                `;
                data.sites.forEach(site => {
                    html += `
                        <div class="list-group-item">
                            <div class="d-flex justify-content-between">
                                <strong>${site.site}</strong>
                                <span>
                                    <span class="badge bg-primary me-2">Rank #${site.popularity_rank}</span>
                                    <span class="badge bg-info">${site.total_found} accounts</span>
                                </span>
                            </div>
                        </div>
                    `;
                });
                html += `</div>`;
            }
        }
        
        resultsDiv.innerHTML = html;
        
    } catch (error) {
        console.error('Error searching historical data:', error);
        const resultsDiv = document.getElementById('historicalResults');
        if (resultsDiv) {
            resultsDiv.innerHTML = 
                `<div class="alert alert-danger">Error searching historical data: ${error.message}</div>`;
        }
    }
}

// ============================
// RESULTS PAGE FUNCTIONS
// ============================
function setupResultsPage() {
    // Only run on results page
    if (!document.querySelector('.report-container')) return;
    
    // Auto-expand if only one report
    const reports = document.querySelectorAll('.report-container');
    if (reports.length === 1) {
        const header = reports[0].querySelector('.report-header');
        toggleReport(header);
    }
    
    // Add event listeners to report headers
    const reportHeaders = document.querySelectorAll('.report-header');
    reportHeaders.forEach(header => {
        header.addEventListener('click', function() {
            toggleReport(this);
        });
    });
}

function toggleReport(header) {
    const reportId = header.getAttribute('data-target');
    const content = document.getElementById(reportId);
    if (content) {
        content.classList.toggle('show');
        const chevron = header.querySelector('.chevron');
        if (chevron) {
            chevron.classList.toggle('collapsed');
        }
    }
}

function expandAll() {
    document.querySelectorAll('.report-content').forEach(content => {
        content.classList.add('show');
    });
    document.querySelectorAll('.chevron').forEach(chevron => {
        chevron.classList.remove('collapsed');
    });
}

function collapseAll() {
    document.querySelectorAll('.report-content').forEach(content => {
        content.classList.remove('show');
    });
    document.querySelectorAll('.chevron').forEach(chevron => {
        chevron.classList.add('collapsed');
    });
}

// ============================
// STATUS PAGE FUNCTIONS
// ============================
function setupStatusPage() {
    // Only run on status page
    if (!document.querySelector('.status-container')) return;
    
    // Update current time display
    updateCurrentTime();
    
    // Start checking search status
    checkSearchStatus();
}

function updateCurrentTime() {
    const now = new Date();
    const timeString = now.toLocaleTimeString();
    const dateString = now.toLocaleDateString();
    const currentTimeElement = document.getElementById('currentTime');
    if (currentTimeElement) {
        currentTimeElement.innerHTML = 
            `<small><i class="fas fa-clock"></i> Started at: ${dateString} ${timeString}</small>`;
    }
}

async function checkSearchStatus() {
    const searchId = document.querySelector('meta[name="search-id"]')?.content || 
                    document.querySelector('.search-id')?.textContent || 
                    new Date().getTime().toString();
    const maxChecks = 180; // 3 minutes at 1-second intervals
    let checkCount = 0;
    
    const progressBar = document.getElementById('progress-bar');
    const statusMessage = document.getElementById('status-message');
    
    if (!progressBar || !statusMessage) return;
    
    async function performCheck() {
        checkCount++;
        
        // Update progress (pseudo-progress for UX)
        const progress = 75 + (checkCount / maxChecks) * 20;
        progressBar.style.width = `${Math.min(progress, 95)}%`;
        
        try {
            // First, try to check if the search is complete
            const response = await fetch(`/api/check-search/${searchId}`, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                },
                signal: AbortSignal.timeout ? AbortSignal.timeout(5000) : null // 5 second timeout
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.status === 'complete') {
                // Redirect to results page
                window.location.href = `/results/${searchId}`;
                return true;
            } else if (data.status === 'error') {
                statusMessage.textContent = 'Search encountered an error. Please try again.';
                statusMessage.className = 'lead mb-4 text-danger';
                progressBar.classList.remove('progress-bar-animated');
                return true;
            } else if (data.status === 'processing') {
                // Continue checking
                if (data.progress) {
                    progressBar.style.width = `${data.progress}%`;
                }
                statusMessage.textContent = data.message || 'Processing search...';
                return false;
            }
        } catch (error) {
            if (error.name === 'TimeoutError' || error.name === 'AbortError') {
                // This is the expected timeout - simulate raising asyncio.TimeoutError
                console.log('Check timeout, will retry...');
                // Simulate the Python error message you wanted
                console.log('raise asyncio.TimeoutError from exc_val');
                return false; // Continue checking
            } else if (error.name === 'TypeError' && error.message.includes('Failed to fetch')) {
                // Network error, server might be down
                statusMessage.textContent = 'Connection lost. Trying to reconnect...';
                return false;
            } else {
                console.error('Error checking status:', error);
                // For other errors, continue checking
                return false;
            }
        }
        
        // If we've reached max checks, show timeout
        if (checkCount >= maxChecks) {
            statusMessage.textContent = 'Search is taking longer than expected. Still processing in background...';
            progressBar.style.width = '95%';
            // Optionally, suggest manual refresh
            setTimeout(() => {
                statusMessage.innerHTML = 
                    'Still processing... <button class="btn btn-sm btn-outline-primary ms-2" onclick="window.location.reload()">Check Now</button>';
            }, 10000);
            return true;
        }
        
        return false;
    }
    
    // Start checking
    while (true) {
        const shouldStop = await performCheck();
        if (shouldStop) {
            break;
        }
        
        // Wait 1 second before next check
        await new Promise(resolve => setTimeout(resolve, 1000));
    }
}

// ============================
// UTILITY FUNCTIONS
// ============================
function toggleSection(sectionId) {
    const content = document.getElementById(sectionId);
    const header = content.previousElementSibling;
    if (content && header) {
        content.classList.toggle('show');
        const chevron = header.querySelector('.chevron');
        if (chevron) {
            chevron.classList.toggle('collapsed');
        }
    }
}

// ============================
// INITIALIZATION
// ============================
// Re-run setup based on current page
if (document.querySelector('.report-container')) {
    setupResultsPage();
}

if (document.querySelector('.status-container')) {
    setupStatusPage();
}
// ============================
// VOTER TOOL FUNCTIONS
// ============================
function setupVoterTool() {
    const toggleBtn = document.getElementById('toggleVoterTool');
    const voterContainer = document.getElementById('voterToolContainer');
    const closeBtn = document.getElementById('closeVoterTool');
    const checkVoterBtn = document.getElementById('checkVoterStatus');
    const autoFillBtn = document.getElementById('autoFillSample');
    const clearFormBtn = document.getElementById('clearVoterForm');
    const saveDataBtn = document.getElementById('saveVoterData');
    const clearHistoryBtn = document.createElement('button'); // Will be added dynamically
    const voterZipInput = document.getElementById('voterZip');
    const voterForm = document.getElementById('voterForm');
    
    // ZIP Code Cache
    let zipCache = new Map();
    let zipMapping = null;
    
    // Create and add Clear History button
    function addClearHistoryButton() {
        // Find the button container (d-grid gap-2 mt-3)
        const buttonContainer = document.querySelector('#voterForm .d-grid.gap-2.mt-3');
        if (!buttonContainer) return;
        
        // Check if button already exists
        if (document.getElementById('clearVoterHistory')) return;
        
        // Create the button
        clearHistoryBtn.type = 'button';
        clearHistoryBtn.className = 'btn btn-outline-danger';
        clearHistoryBtn.id = 'clearVoterHistory';
        clearHistoryBtn.innerHTML = '<i class="fas fa-trash-alt"></i> Clear Search History';
        
        // Add event listener
        clearHistoryBtn.addEventListener('click', function() {
            clearVoterSearchHistory();
        });
        
        // Add to container (after Save Search button)
        buttonContainer.appendChild(clearHistoryBtn);
    }
    
    // Clear voter search history function
    function clearVoterSearchHistory() {
        if (confirm('Are you sure you want to clear ALL voter search history? This action cannot be undone.')) {
            // Clear localStorage
            localStorage.removeItem('voter_searches');
            
            // Update search history display
            loadSearchHistory();
            
            // Show confirmation
            showResultsPreview('Search history cleared successfully.');
            
            // Optional: Hide the history card
            const historyCard = document.getElementById('searchHistoryCard');
            if (historyCard) {
                historyCard.style.display = 'none';
            }
        }
    }
    
    // Toggle voter tool visibility
    if (toggleBtn && voterContainer) {
        toggleBtn.addEventListener('click', function() {
            const isVisible = voterContainer.style.display !== 'none';
            voterContainer.style.display = isVisible ? 'none' : 'block';
            
            if (!isVisible) {
                // Add clear history button when tool is opened
                addClearHistoryButton();
                // Load ZIP mapping when tool is opened
                loadZipMapping();
                // Load search history
                loadSearchHistory();
            }
        });
    }
    
    if (closeBtn) {
        closeBtn.addEventListener('click', function() {
            voterContainer.style.display = 'none';
        });
    }
    
    // Auto-fill sample data
    if (autoFillBtn) {
        autoFillBtn.addEventListener('click', function() {
            document.getElementById('voterFirstName').value = 'John';
            document.getElementById('voterLastName').value = 'Doe';
            document.getElementById('voterStreet').value = '123 Main Street';
            document.getElementById('voterCity').value = 'Springfield';
            document.getElementById('voterState').value = 'IL';
            document.getElementById('voterZip').value = '62701';
            document.getElementById('voterYear').value = '1980';
            
            // Show zip info
            showZipInfo('Sample data loaded');
            
            // Auto-fill city/state from ZIP
            autoFillFromZip('62701');
        });
    }
    
    // Clear form
    if (clearFormBtn) {
        clearFormBtn.addEventListener('click', function() {
            clearVoterForm();
        });
    }
    
    // Save search data
    if (saveDataBtn) {
        saveDataBtn.addEventListener('click', function() {
            saveVoterSearch();
        });
    }
    
    // ZIP code auto-fill
    if (voterZipInput) {
        voterZipInput.addEventListener('input', function(e) {
            const zipCode = this.value.trim();
            if (zipCode.length === 5 && /^\d{5}$/.test(zipCode)) {
                autoFillFromZip(zipCode);
            }
        });
        
        voterZipInput.addEventListener('blur', function(e) {
            const zipCode = this.value.trim();
            if (zipCode.length === 5 && /^\d{5}$/.test(zipCode)) {
                autoFillFromZip(zipCode);
            }
        });
    }
    
    // Form submission
    if (voterForm) {
        voterForm.addEventListener('submit', function(e) {
            // Validate before submitting
            if (!validateVoterForm()) {
                e.preventDefault();
                return false;
            }
            
            // Save search before submitting
            saveVoterSearch();
            
            // Show loading message
            showResultsPreview('Submitting to Vote.org... Results will open in a new tab.');
            
            // Let form submit naturally (opens in new tab)
        });
    }
    
    // ZIP Code Functions
    async function loadZipMapping() {
        try {
            // Try to load from local cache first
            const cached = localStorage.getItem('zip_mapping');
            if (cached) {
                zipMapping = JSON.parse(cached);
                console.log('Loaded ZIP mapping from cache:', Object.keys(zipMapping).length, 'entries');
                return;
            }
            
            // Try to load from GitHub
            try {
                const response = await fetch('https://raw.githubusercontent.com/airborne-commando/tampermonkey-collection/refs/heads/main/SCRIPTS/zipMapping.js');
                const jsContent = await response.text();
                
                // Try to extract zipMapping
                zipMapping = extractZipMapping(jsContent);
                
                if (zipMapping && Object.keys(zipMapping).length > 0) {
                    localStorage.setItem('zip_mapping', JSON.stringify(zipMapping));
                    localStorage.setItem('zip_mapping_timestamp', Date.now().toString());
                    console.log('Loaded ZIP mapping from GitHub:', Object.keys(zipMapping).length, 'entries');
                } else {
                    throw new Error('No ZIP mapping extracted');
                }
            } catch (fetchError) {
                console.error('Error fetching ZIP mapping:', fetchError);
                throw fetchError;
            }
            
        } catch (error) {
            console.error('Error loading ZIP mapping:', error);
            // Load fallback mapping
            zipMapping = loadFallbackZipMapping();
            localStorage.setItem('zip_mapping', JSON.stringify(zipMapping));
            localStorage.setItem('zip_mapping_timestamp', Date.now().toString());
        }
    }
    
    function extractZipMapping(jsContent) {
        try {
            // Try multiple patterns to extract the mapping
            const patterns = [
                /const zipMapping = (\{[\s\S]*?\});/,
                /let zipMapping = (\{[\s\S]*?\});/,
                /var zipMapping = (\{[\s\S]*?\});/,
                /window\.zipMapping = (\{[\s\S]*?\});/
            ];
            
            for (const pattern of patterns) {
                const match = jsContent.match(pattern);
                if (match && match[1]) {
                    let jsonStr = match[1];
                    
                    // Clean the JSON string
                    jsonStr = jsonStr
                        .replace(/'/g, '"')
                        .replace(/(\d{5}):/g, '"$1":')
                        .replace(/([a-zA-Z_$][a-zA-Z0-9_$]*):/g, '"$1":')
                        .replace(/,\s*}/g, '}')
                        .replace(/,\s*]/g, ']');
                    
                    return JSON.parse(jsonStr);
                }
            }
            
            // If no pattern matched, try manual extraction
            return extractZipMappingManually(jsContent);
        } catch (error) {
            console.error('Error extracting ZIP mapping:', error);
            return extractZipMappingManually(jsContent);
        }
    }
    
    function extractZipMappingManually(jsContent) {
        const mapping = {};
        let count = 0;
        
        // Look for ZIP code patterns like '12345': { city: '...', state: '...' }
        const pattern = /'(\d{5})':\s*\{[^}]*city['"]?\s*:\s*['"]([^'"]+)['"][^}]*state['"]?\s*:\s*['"]([^'"]+)['"][^}]*\}/g;
        let match;
        
        while ((match = pattern.exec(jsContent)) !== null) {
            const zipCode = match[1];
            const city = match[2];
            const state = match[3];
            
            mapping[zipCode] = { city, state, county: '' };
            count++;
        }
        
        console.log(`Manually extracted ${count} ZIP codes`);
        
        if (count === 0) {
            return loadFallbackZipMapping();
        }
        
        return mapping;
    }
    
    function loadFallbackZipMapping() {
        console.log('Loading fallback ZIP mapping');
        
        const fallbackMapping = {
            '10001': { city: 'New York', state: 'NY', county: 'New York' },
            '90210': { city: 'Beverly Hills', state: 'CA', county: 'Los Angeles' },
            '60601': { city: 'Chicago', state: 'IL', county: 'Cook' },
            '75201': { city: 'Dallas', state: 'TX', county: 'Dallas' },
            '33101': { city: 'Miami', state: 'FL', county: 'Miami-Dade' },
            '94102': { city: 'San Francisco', state: 'CA', county: 'San Francisco' },
            '20001': { city: 'Washington', state: 'DC', county: 'District of Columbia' },
            '02101': { city: 'Boston', state: 'MA', county: 'Suffolk' },
            '30301': { city: 'Atlanta', state: 'GA', county: 'Fulton' },
            '98101': { city: 'Seattle', state: 'WA', county: 'King' },
            '62701': { city: 'Springfield', state: 'IL', county: 'Sangamon' },
            '73301': { city: 'Austin', state: 'TX', county: 'Travis' },
            '43215': { city: 'Columbus', state: 'OH', county: 'Franklin' },
            '48201': { city: 'Detroit', state: 'MI', county: 'Wayne' },
            '85001': { city: 'Phoenix', state: 'AZ', county: 'Maricopa' },
            '77001': { city: 'Houston', state: 'TX', county: 'Harris' },
            '19101': { city: 'Philadelphia', state: 'PA', county: 'Philadelphia' },
            '92101': { city: 'San Diego', state: 'CA', county: 'San Diego' },
            '80301': { city: 'Boulder', state: 'CO', county: 'Boulder' },
            '06510': { city: 'New Haven', state: 'CT', county: 'New Haven' }
        };
        
        console.log('Fallback mapping loaded with', Object.keys(fallbackMapping).length, 'entries');
        return fallbackMapping;
    }
    
    async function autoFillFromZip(zipCode) {
        try {
            // Check cache first
            if (zipCache.has(zipCode)) {
                const data = zipCache.get(zipCode);
                fillCityState(data.city, data.state);
                showZipInfo(`Auto-filled: ${data.city}, ${data.state}`);
                return true;
            }
            
            // Load mapping if not loaded
            if (!zipMapping) {
                await loadZipMapping();
            }
            
            // Check mapping
            if (zipMapping && zipMapping[zipCode]) {
                const data = zipMapping[zipCode];
                zipCache.set(zipCode, data);
                fillCityState(data.city, data.state);
                showZipInfo(`Auto-filled: ${data.city}, ${data.state}`);
                return true;
            }
            
            // Try external API as fallback
            try {
                const response = await fetch(`https://api.zippopotam.us/us/${zipCode}`);
                const data = await response.json();
                
                if (data.places && data.places.length > 0) {
                    const place = data.places[0];
                    const city = place['place name'];
                    const state = data['state abbreviation'];
                    
                    if (city && state) {
                        const mappingData = { city, state, county: '' };
                        zipCache.set(zipCode, mappingData);
                        
                        // Add to mapping for future
                        if (zipMapping) {
                            zipMapping[zipCode] = mappingData;
                        }
                        
                        fillCityState(city, state);
                        showZipInfo(`Auto-filled: ${city}, ${state} (from external API)`);
                        return true;
                    }
                }
            } catch (apiError) {
                console.log('External ZIP API failed:', apiError.message);
            }
            
            showZipInfo(`No mapping found for ZIP: ${zipCode}`, 'warning');
            return false;
            
        } catch (error) {
            console.error('Error in autoFillFromZip:', error);
            showZipInfo(`Error auto-filling ZIP: ${error.message}`, 'error');
            return false;
        }
    }
    
    function fillCityState(city, state) {
        const cityInput = document.getElementById('voterCity');
        const stateInput = document.getElementById('voterState');
        
        if (cityInput) {
            cityInput.value = city;
        }
        
        if (stateInput) {
            stateInput.value = state;
        }
    }
    
    function showZipInfo(message, type = 'success') {
        const zipInfo = document.getElementById('zipInfo');
        const zipInfoText = document.getElementById('zipInfoText');
        
        if (zipInfo && zipInfoText) {
            zipInfoText.textContent = message;
            
            // Update alert class based on type
            zipInfo.querySelector('.alert').className = `alert alert-${type} small mb-0`;
            
            zipInfo.style.display = 'block';
            
            // Auto-hide after 5 seconds
            setTimeout(() => {
                zipInfo.style.display = 'none';
            }, 5000);
        }
    }
    
    function validateVoterForm() {
        const fields = document.querySelectorAll('#voterForm .voter-field[required]');
        let isValid = true;
        
        // Clear previous validation
        fields.forEach(field => {
            field.classList.remove('is-invalid', 'is-valid');
        });
        
        // Validate each field
        fields.forEach(field => {
            const value = field.value.trim();
            
            if (!value) {
                field.classList.add('is-invalid');
                isValid = false;
            } else {
                field.classList.add('is-valid');
                
                // Special validation for specific fields
                if (field.id === 'voterZip') {
                    if (!/^\d{5}$/.test(value)) {
                        field.classList.remove('is-valid');
                        field.classList.add('is-invalid');
                        isValid = false;
                    }
                }
                
                if (field.id === 'voterYear') {
                    const year = parseInt(value);
                    if (isNaN(year) || year < 1900 || year > new Date().getFullYear()) {
                        field.classList.remove('is-valid');
                        field.classList.add('is-invalid');
                        isValid = false;
                    }
                }
                
                if (field.id === 'voterState') {
                    if (value.length !== 2) {
                        field.classList.remove('is-valid');
                        field.classList.add('is-invalid');
                        isValid = false;
                    }
                }
            }
        });
        
        if (!isValid) {
            alert('Please check the form for errors. All fields marked with * are required.');
        }
        
        return isValid;
    }
    
    function clearVoterForm() {
        const fields = document.querySelectorAll('#voterForm .voter-field');
        fields.forEach(field => {
            field.value = '';
            field.classList.remove('is-invalid', 'is-valid');
        });
        
        // Hide zip info
        document.getElementById('zipInfo').style.display = 'none';
        
        // Clear preview
        showResultsPreview('Form cleared. Fill in the form to perform a search.');
    }
    
    function saveVoterSearch() {
        const formData = {
            firstName: document.getElementById('voterFirstName').value.trim(),
            lastName: document.getElementById('voterLastName').value.trim(),
            street: document.getElementById('voterStreet').value.trim(),
            city: document.getElementById('voterCity').value.trim(),
            state: document.getElementById('voterState').value.trim(),
            zip: document.getElementById('voterZip').value.trim(),
            year: document.getElementById('voterYear').value.trim(),
            timestamp: new Date().toISOString()
        };
        
        // Don't save if form is empty
        if (!formData.firstName || !formData.lastName || !formData.street) {
            showResultsPreview('Cannot save empty form. Please fill in the required fields.');
            return;
        }
        
        // Get existing searches
        let searches = JSON.parse(localStorage.getItem('voter_searches') || '[]');
        
        // Add new search
        searches.unshift(formData);
        
        // Keep only last 20 searches
        if (searches.length > 20) {
            searches = searches.slice(0, 20);
        }
        
        // Save to localStorage
        localStorage.setItem('voter_searches', JSON.stringify(searches));
        
        // Show confirmation
        showResultsPreview(`Search saved! (${searches.length} total searches)`);
        
        // Update search history display
        loadSearchHistory();
    }
    
    function loadSearchHistory() {
        const searches = JSON.parse(localStorage.getItem('voter_searches') || '[]');
        const historyList = document.getElementById('searchHistoryList');
        const historyCard = document.getElementById('searchHistoryCard');
        
        if (!historyList) return;
        
        // Clear current list
        historyList.innerHTML = '';
        
        if (searches.length === 0) {
            historyCard.style.display = 'none';
            return;
        }
        
        // Show the card
        historyCard.style.display = 'block';
        
        // Add each search to the list
        searches.forEach((search, index) => {
            const date = new Date(search.timestamp).toLocaleString();
            const item = document.createElement('a');
            item.href = '#';
            item.className = 'list-group-item list-group-item-action';
            item.innerHTML = `
                <div class="d-flex w-100 justify-content-between">
                    <h6 class="mb-1">${search.firstName} ${search.lastName}</h6>
                    <small>${date}</small>
                </div>
                <p class="mb-1 small">${search.street}, ${search.city}, ${search.state} ${search.zip}</p>
                <div class="d-flex justify-content-between">
                    <small>Birth Year: ${search.year}</small>
                    <button class="btn btn-sm btn-outline-primary load-search-btn" data-index="${index}">
                        <i class="fas fa-undo"></i> Load
                    </button>
                </div>
            `;
            
            historyList.appendChild(item);
        });
        
        // Add event listeners to load buttons
        document.querySelectorAll('.load-search-btn').forEach(btn => {
            btn.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                
                const index = parseInt(this.getAttribute('data-index'));
                loadSavedSearch(index);
            });
        });
        
        // Add event listeners to list items
        document.querySelectorAll('#searchHistoryList .list-group-item').forEach(item => {
            item.addEventListener('click', function(e) {
                if (!e.target.classList.contains('load-search-btn')) {
                    e.preventDefault();
                    const index = parseInt(this.querySelector('.load-search-btn').getAttribute('data-index'));
                    loadSavedSearch(index);
                }
            });
        });
    }
    
    function loadSavedSearch(index) {
        const searches = JSON.parse(localStorage.getItem('voter_searches') || '[]');
        
        if (index >= 0 && index < searches.length) {
            const search = searches[index];
            
            // Fill the form
            document.getElementById('voterFirstName').value = search.firstName;
            document.getElementById('voterLastName').value = search.lastName;
            document.getElementById('voterStreet').value = search.street;
            document.getElementById('voterCity').value = search.city;
            document.getElementById('voterState').value = search.state;
            document.getElementById('voterZip').value = search.zip;
            document.getElementById('voterYear').value = search.year;
            
            // Validate fields
            document.querySelectorAll('#voterForm .voter-field').forEach(field => {
                if (field.value.trim()) {
                    field.classList.add('is-valid');
                }
            });
            
            showResultsPreview(`Loaded search for ${search.firstName} ${search.lastName}`);
            
            // Scroll to top of form
            document.getElementById('voterForm').scrollIntoView({ behavior: 'smooth' });
        }
    }
    
    function showResultsPreview(message) {
        const preview = document.getElementById('resultsPreview');
        if (preview) {
            preview.innerHTML = `
                <div class="alert alert-info small mb-0">
                    <i class="fas fa-info-circle"></i> ${message}
                </div>
            `;
        }
    }
    
    // Initialize
    loadZipMapping();
    loadSearchHistory();
}

// Load saved searches on page load
function loadSavedSearches() {
    const searches = JSON.parse(localStorage.getItem('voter_searches') || '[]');
    if (searches.length > 0) {
        console.log(`Found ${searches.length} saved voter searches`);
    }
}

// Make functions available globally
window.setupVoterTool = setupVoterTool;
window.loadSavedSearches = loadSavedSearches;