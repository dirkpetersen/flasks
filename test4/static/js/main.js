// Global state
let currentRecord = null;
let metaFields = {};

// Utility functions
const formatDateTime = (timestamp) => {
    if (!timestamp) return '';
    // Convert UTC timestamp to local time with locale-aware format
    return luxon.DateTime
        .fromSeconds(parseInt(timestamp))
        .toLocal()
        .toLocaleString(luxon.DateTime.DATETIME_SHORT);
};

const showToast = (message, type = 'success') => {
    const toastEl = document.createElement('div');
    toastEl.className = `toast align-items-center text-white bg-${type} border-0 position-fixed bottom-0 end-0 m-3`;
    toastEl.setAttribute('role', 'alert');
    toastEl.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">${message}</div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    document.body.appendChild(toastEl);
    const toast = new bootstrap.Toast(toastEl);
    toast.show();
    toastEl.addEventListener('hidden.bs.toast', () => toastEl.remove());
};

// Form handling
const resetForm = async () => {
    try {
        const response = await fetch('/api/new-id');
        if (!response.ok) {
            const data = await response.json().catch(() => ({}));
            throw new Error(data.error || `Failed to get new ID: ${response.status} ${response.statusText}`);
        }
        const data = await response.json();
        
        document.getElementById('recordForm').reset();
        document.getElementById('recordId').textContent = data.id;
        document.getElementById('recordId').setAttribute('data-new-id', 'true');
        currentRecord = null;
        
        // Reset meta fields
        const metaFieldsContainer = document.getElementById('metaFields');
        Object.keys(metaFields).forEach(fieldId => {
            const field = document.getElementById(fieldId);
            if (field) {
                if (field.type === 'select-multiple') {
                    Array.from(field.options).forEach(opt => opt.selected = false);
                } else if (field.type === 'checkbox') {
                    field.checked = false;
                } else {
                    field.value = '';
                }
            }
        });
    } catch (error) {
        console.error('Error resetting form:', error);
        showToast('Failed to reset form', 'danger');
    }
};

const loadRecord = (record) => {
    currentRecord = record;
    document.getElementById('recordId').textContent = record.id;
    document.getElementById('recordId').setAttribute('data-new-id', 'false');
    document.getElementById('title').value = record.title || '';
    document.getElementById('description').value = record.description || '';
    document.getElementById('time_start').value = formatDateTime(record.time_start);
    document.getElementById('time_end').value = formatDateTime(record.time_end);
    document.getElementById('active').checked = record.active !== false;

    // Load meta fields
    Object.entries(metaFields).forEach(([fieldId, config]) => {
        const field = document.getElementById(fieldId);
        if (field && record.meta && record.meta[fieldId]) {
            const values = Array.isArray(record.meta[fieldId])
                ? record.meta[fieldId]
                : [record.meta[fieldId]];
            document.querySelector(`#${fieldId}`).setValue(values);
        }
    });
};

// Record list handling
const loadRecords = async (page = 1) => {
    const userId = document.getElementById('userIdInput').value;
    const showAll = document.getElementById('showAllRecords').checked;
    
    if (!userId) {
        document.getElementById('recordsList').innerHTML = `
            <div class="list-group-item text-center text-muted py-4">
                <i class="bi bi-person-exclamation fs-2 mb-2"></i><br>
                Please set your user ID above to view records
            </div>`;
        return;
    }

    try {
        const response = await fetch(`/api/records?page=${page}&show_all=${showAll}&user_id=${userId}`);
        if (!response.ok) throw new Error('Failed to load records');
        const data = await response.json();
        console.log('Received records data:', data);
        if (!data.records) {
            console.error('No records array in response:', data);
            throw new Error('Invalid response format');
        }
        updateRecordsList(data.records);
        updatePagination(data.pages, page);
    } catch (error) {
        console.error('Error loading records:', error);
        showToast('Failed to load records', 'danger');
    }
};

const updateRecordsList = (records) => {
    const recordsList = document.getElementById('recordsList');
    
    console.log('Updating records list with:', records);
    
    if (!Array.isArray(records)) {
        console.error('Records is not an array:', records);
        recordsList.innerHTML = `
            <div class="list-group-item text-center text-muted py-4">
                <i class="bi bi-exclamation-triangle fs-2 mb-2"></i><br>
                Error: Invalid records format
            </div>`;
        return;
    }
    
    if (records.length === 0) {
        recordsList.innerHTML = `
            <div class="list-group-item text-center text-muted py-4">
                <i class="bi bi-inbox fs-2 mb-2"></i><br>
                No records found
            </div>`;
        return;
    }

    recordsList.innerHTML = records.map(record => `
    
        <div class="list-group-item ${currentRecord?.id === record.id ? 'active' : ''}"
             onclick="loadRecord(${JSON.stringify(record).replace(/"/g, '&quot;')})">
            <div class="record-header">
                <span class="fw-bold">${record.id}</span>
                <span class="text-primary record-title">${record.title}</span>
                <div class="record-badges">
                    <span class="badge ${record.active ? 'bg-success' : 'bg-secondary'}">
                        ${record.active ? 'Active' : 'Inactive'}
                    </span>
                    ${(() => {
                        const nonEmptyMeta = Object.entries(record.meta || {})
                            .filter(([_, value]) => {
                                if (Array.isArray(value)) return value.length > 0;
                                if (typeof value === 'boolean') return true;
                                return value !== null && value !== undefined && value !== '';
                            });
                        
                        return nonEmptyMeta.length > 0 ? `
                            <span class="badge bg-info metadata-badge" 
                                  data-bs-toggle="tooltip" 
                                  data-bs-html="true"
                                  title="${nonEmptyMeta.map(([key, value]) => 
                                    `<strong>${key}:</strong> ${Array.isArray(value) ? value.join(', ') : value}`
                                  ).join('<br>')}">
                                Metadata
                            </span>
                        ` : '';
                    })()}
                    ${(record.time_start || record.time_end) ? `
                    <span class="badge bg-brown-subtle text-dark dates-badge" 
                          data-bs-toggle="tooltip" 
                          data-bs-html="true"
                          title="${[
                            ['Created', record.created_at],
                            ['Modified', record.changed_at],
                            ['Starts', record.time_start],
                            ['Ends', record.time_end]
                          ].filter(([_, time]) => time)
                            .map(([label, time]) => 
                              `<strong>${label}:</strong> ${formatDateTime(time)}`
                            ).join('<br>')}">
                        Dates
                    </span>
                    ` : ''}
                </div>
                <div class="record-date">
                    <div class="small text-muted text-nowrap">
                        ${formatDateTime(record.changed_at || record.created_at)}
                    </div>
                </div>
            </div>
            <div class="small text-muted mt-1 record-description text-nowrap">
                ${record.description || ''}
            </div>
        </div>
    `).join('');
    
    // Initialize tooltips
    const tooltips = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    tooltips.forEach(tooltip => new bootstrap.Tooltip(tooltip));
};

const updatePagination = (totalPages, currentPage) => {
    const pagination = document.querySelector('.pagination');
    if (totalPages <= 1) {
        pagination.innerHTML = '';
        return;
    }

    let pages = [];
    const delta = 2;
    const left = currentPage - delta;
    const right = currentPage + delta + 1;
    const range = [];
    const rangeWithDots = [];
    let l;

    for (let i = 1; i <= totalPages; i++) {
        if (i === 1 || i === totalPages || (i >= left && i < right)) {
            range.push(i);
        }
    }

    for (const i of range) {
        if (l) {
            if (i - l === 2) {
                rangeWithDots.push(l + 1);
            } else if (i - l !== 1) {
                rangeWithDots.push('...');
            }
        }
        rangeWithDots.push(i);
        l = i;
    }

    pagination.innerHTML = `
        <li class="page-item ${currentPage === 1 ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="loadRecords(${currentPage - 1}); return false;">
                <i class="bi bi-chevron-left"></i>
            </a>
        </li>
        ${rangeWithDots.map(page => `
            <li class="page-item ${page === currentPage ? 'active' : ''} ${page === '...' ? 'disabled' : ''}">
                <a class="page-link" href="#" onclick="loadRecords(${page}); return false;">
                    ${page}
                </a>
            </li>
        `).join('')}
        <li class="page-item ${currentPage === totalPages ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="loadRecords(${currentPage + 1}); return false;">
                <i class="bi bi-chevron-right"></i>
            </a>
        </li>
    `;
};

// Search functionality
const searchRecords = async () => {
    const userId = document.getElementById('userIdInput').value;
    let query = document.getElementById('searchInput').value.trim();
    const showAll = document.getElementById('showAllRecords').checked;

    if (!userId) {
        document.getElementById('recordsList').innerHTML = `
            <div class="list-group-item text-center text-muted py-4">
                <i class="bi bi-person-exclamation fs-2 mb-2"></i><br>
                Please set your user ID above to view records
            </div>`;
        return;
    }

    // No need to encode here since fetch will encode the URL parameters
    // Just pass the raw query string

    try {
        const response = await fetch(`/api/search?q=${encodeURIComponent(query)}&show_all=${showAll}&user_id=${userId}`);
        if (!response.ok) throw new Error('Search failed');
        const records = await response.json();
        updateRecordsList(records);
        document.querySelector('.pagination').innerHTML = ''; // Hide pagination during search
    } catch (error) {
        console.error('Search error:', error);
        showToast('Search failed', 'danger');
    }
};

// Form submission
const submitForm = async (event) => {
    event.preventDefault();
    const form = event.target;
    const submitButton = form.querySelector('button[type="submit"]');
    submitButton.disabled = true;
    submitButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Saving...';

    // Set a timeout for the request
    const timeout = 10000; // 10 seconds
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    try {
        const formData = {
            id: document.getElementById('recordId').textContent,
            title: document.getElementById('title').value,
            description: document.getElementById('description').value,
            time_start: document.getElementById('time_start').value || null,
            time_end: document.getElementById('time_end').value || null,
            active: document.getElementById('active').checked,
            creator_id: document.getElementById('userIdInput').value,
            meta: {}
        };

        // Validate required fields
        if (!formData.title) throw new Error('Title is required');
        if (!formData.creator_id) throw new Error('User ID is required');

        // Collect meta fields
        Object.entries(metaFields).forEach(([fieldId, config]) => {
            const field = document.getElementById(fieldId);
            if (field) {
                if (field) {
                    if (config.multiple) {
                        formData.meta[fieldId] = field.value;
                    } else if (field.type === 'checkbox') {
                        formData.meta[fieldId] = field.checked;
                    } else {
                        formData.meta[fieldId] = field.value;
                    }
                }
            }
        });

        const isNewRecord = document.getElementById('recordId').getAttribute('data-new-id') === 'true';
        const method = isNewRecord ? 'POST' : 'PUT';
        const url = `/api/records${isNewRecord ? '' : '/' + formData.id}`;

        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(formData),
            signal: controller.signal
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.error || `Failed to save record: ${response.status} ${response.statusText}`);
        }

        clearTimeout(timeoutId);
        showToast('Record saved successfully');
        await loadRecords(); // Refresh the list
        if (isNewRecord) await resetForm();
    } catch (error) {
        clearTimeout(timeoutId);
        console.error('Form submission error:', error);
        showToast(error.message, 'danger');
    } finally {
        submitButton.disabled = false;
        submitButton.innerHTML = '<i class="bi bi-save"></i> Save Record';
    }
};

// Date handling functions
const handleDateTimeChange = (type) => {
    const input = document.getElementById(`time_${type}`);
    if (!input.value) return;

    const selectedDate = luxon.DateTime.fromISO(input.value);
    const today = luxon.DateTime.now().startOf('day');
    const previousValue = input._previousValue;
    
    // Only modify times if the date was changed and there was no previous value
    if (!selectedDate.hasSame(today, 'day') && !previousValue) {
        if (type === 'start') {
            // Set to beginning of day (00:00)
            input.value = selectedDate.startOf('day').toFormat("yyyy-MM-dd'T'HH:mm");
        } else if (type === 'end') {
            // Set to end of day (23:59)
            input.value = selectedDate.set({hour: 23, minute: 59}).toFormat("yyyy-MM-dd'T'HH:mm");
        }
    }
    
    // Store the current value for future reference
    input._previousValue = input.value;
};

// Event Listeners

document.addEventListener('DOMContentLoaded', async () => {
    // Start with a new record
    await resetForm();
    // Initialize form submission
    document.getElementById('recordForm').addEventListener('submit', submitForm);

    // Initialize search
    document.getElementById('searchButton').addEventListener('click', searchRecords);
    document.getElementById('searchInput').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') searchRecords();
    });

    // Initialize show all records toggle
    document.getElementById('showAllRecords').addEventListener('change', () => loadRecords(1));

    // Initialize user ID validation
    const userIdInput = document.getElementById('userIdInput');
    
    // Load creator ID from cookie
    const savedCreatorId = document.cookie.split('; ').find(row => row.startsWith('creatorId='));
    if (savedCreatorId) {
        userIdInput.value = decodeURIComponent(savedCreatorId.split('=')[1]);
        loadRecords(1);
    }

    userIdInput.addEventListener('change', async () => {
        const email = userIdInput.value.trim();
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (email && !emailRegex.test(email)) {
            userIdInput.classList.add('is-invalid');
            showToast('Please enter a valid email address', 'danger');
        } else {
            userIdInput.classList.remove('is-invalid');
            if (email) {
                try {
                    // Save creator ID in cookie (expires in 30 days)
                    const expiryDate = new Date();
                    expiryDate.setDate(expiryDate.getDate() + 30);
                    document.cookie = `creatorId=${encodeURIComponent(email)};expires=${expiryDate.toUTCString()};path=/`;
                    await loadRecords(1);
                } catch (error) {
                    console.error('Error loading records:', error);
                    showToast('Failed to load records', 'danger');
                }
            } else {
                // Clear cookie if email is empty
                document.cookie = 'creatorId=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=/';
            }
        }
    });

    // Initialize meta fields
    fetch('/api/meta-fields')
        .then(response => {
            if (!response.ok) {
                throw new Error(`Failed to fetch meta fields: ${response.status} ${response.statusText}`);
            }
            return response.json();
        })
        .then(fields => {
            metaFields = fields;
            const container = document.getElementById('metaFields');
            if (!fields) {
                console.warn('No meta fields configuration received');
                return;
            }
            // Sort fields: single-select first, then multi-select
            const sortedFields = Object.entries(fields).sort(([, a], [, b]) => {
                if (a.multiple === b.multiple) return 0;
                return a.multiple ? 1 : -1;
            });

            sortedFields.forEach(([fieldId, config]) => {
                if (!config || !config.options) {
                    console.warn(`Invalid config for field ${fieldId}`);
                    return;
                }
                const fieldDiv = document.createElement('div');
                fieldDiv.className = 'mb-3';
                fieldDiv.innerHTML = `
                    <div id="${fieldId}" 
                         data-bs-toggle="tooltip" 
                         data-bs-placement="top" 
                         title="${config.name}">
                    </div>
                `;
                container.appendChild(fieldDiv);
                
                // Initialize tooltip for the field
                new bootstrap.Tooltip(fieldDiv);
                
                VirtualSelect.init({
                    ele: `#${fieldId}`,
                    options: config.options.map(opt => ({ label: opt, value: opt })),
                    placeholder: `Select ${config.name}`,
                    multiple: config.multiple,
                    search: true,
                    maxWidth: '100%',
                    showSelectedOptionsFirst: true,
                    hideClearButton: false,
                    markSearchResults: true,
                    usePassiveEventListener: true
                });
                container.appendChild(fieldDiv);
            });
        })
        .catch(error => {
            console.error('Error loading meta fields:', error);
            showToast('Failed to load meta fields', 'danger');
        });
});
