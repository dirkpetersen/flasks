// Function declarations first
function setEmail() {
    const email = document.getElementById('emailInput').value;
    if (!email) return;

    fetch('/api/set-email', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email }),
    })
    .then(response => response.json())
    .then(() => {
        loadRecords();
    });
}

function loadRecords() {
    fetch('/api/records')
        .then(response => response.json())
        .then(records => {
            const recordsList = document.getElementById('recordsList');
            recordsList.innerHTML = records.map(record => `
                <div class="list-group-item record-item py-2" onclick="loadRecord('${record.id}')">
                    <div class="d-flex justify-content-between align-items-center">
                        <div class="text-truncate me-2">
                            <strong>${record.id}</strong> - ${record.title}
                            <span class="badge bg-secondary">${record.work_type}</span>
                            <span class="badge bg-info">Apps: ${record.required_apps.join(', ') || 'None'}</span>
                            ${record.active ? '<span class="badge bg-success">Active</span>' : '<span class="badge bg-danger">Inactive</span>'}
                        </div>
                        <small class="text-muted">${new Date(record.created_at).toLocaleDateString()}</small>
                    </div>
                    <div class="small text-muted text-truncate mt-1">${record.description || 'No description'}</div>
                </div>
            `).join('');
        });
}

function loadRecord(id) {
    document.body.classList.add('loading');
    console.log('Loading record with ID:', id);
    fetch('/api/records')
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to fetch records');
            }
            return response.json();
        })
        .then(records => {
            const record = records.find(r => r.id === id);
            if (!record) {
                throw new Error(`Record with ID ${id} not found`);
            }
            console.log('Found record:', record);
            return record;
        })
        .then(record => {
            if (!record) return;
            
            console.log('Loading record:', record); // Debug log
            
            // Update form fields with strict null checks
            document.getElementById('recordId').value = record.id || '';
            document.getElementById('displayId').value = record.id || '';
            document.getElementById('title').value = record.title || '';
            document.getElementById('description').value = record.description || '';
            
            // Handle dates with proper timezone conversion
            if (record.start_date) {
                try {
                    const startDate = new Date(record.start_date);
                    const localStartDate = new Date(startDate.getTime() - startDate.getTimezoneOffset() * 60000);
                    document.getElementById('startDate').value = localStartDate.toISOString().slice(0, 16);
                    document.getElementById('startDateTimezone').textContent = `(${record.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone})`;
                } catch (e) {
                    console.error('Error parsing start_date:', e);
                    document.getElementById('startDate').value = '';
                    document.getElementById('startDateTimezone').textContent = '';
                }
            } else {
                document.getElementById('startDate').value = '';
                document.getElementById('startDateTimezone').textContent = '';
            }
            
            if (record.end_date) {
                try {
                    const endDate = new Date(record.end_date);
                    const localEndDate = new Date(endDate.getTime() - endDate.getTimezoneOffset() * 60000);
                    document.getElementById('endDate').value = localEndDate.toISOString().slice(0, 16);
                    document.getElementById('endDateTimezone').textContent = `(${record.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone})`;
                } catch (e) {
                    console.error('Error parsing end_date:', e);
                    document.getElementById('endDate').value = '';
                    document.getElementById('endDateTimezone').textContent = '';
                }
            } else {
                document.getElementById('endDate').value = '';
                document.getElementById('endDateTimezone').textContent = '';
            }
            
            // Handle work type with validation
            const workTypeSelect = document.getElementById('workType');
            if (workTypeSelect) {
                workTypeSelect.value = record.work_type || '';
                // Trigger change event for any dependent behaviors
                workTypeSelect.dispatchEvent(new Event('change'));
            }
            
            // Handle required apps with Select2
            const requiredAppsSelect = $('#requiredApps');
            if (requiredAppsSelect.length) {
                const apps = Array.isArray(record.required_apps) ? record.required_apps : [];
                requiredAppsSelect.val(apps).trigger('change');
            }
            
            // Handle active status with default true
            document.getElementById('active').checked = record.active !== undefined ? record.active : true;
        })
        .catch(error => {
            console.error('Error loading record:', error);
            alert(`Failed to load record: ${error.message}`);
        })
        .finally(() => {
            document.body.classList.remove('loading');
        });
}

function resetForm() {
    fetch('/api/new-id')
        .then(response => response.json())
        .then(data => {
            document.getElementById('recordForm').reset();
            const recordIdInput = document.getElementById('recordId');
            recordIdInput.value = data.id;
            recordIdInput.setAttribute('data-new-id', data.id);
            document.getElementById('displayId').value = data.id;
            $('#requiredApps').val([]).trigger('change');
            // Reset CAPTCHA state
            document.getElementById('captchaContainer').classList.add('d-none');
            document.getElementById('captchaInput').value = '';
        });
}

function searchRecords() {
    const query = document.getElementById('searchInput').value;
    const userOnly = document.getElementById('userOnlyCheck').checked;
    
    fetch(`/api/search?q=${encodeURIComponent(query)}&user_only=${userOnly}`)
        .then(response => response.json())
        .then(records => {
            const recordsList = document.getElementById('recordsList');
            recordsList.innerHTML = records.map(record => `
                <div class="list-group-item record-item py-2" onclick="loadRecord('${record.id}')">
                    <div class="d-flex justify-content-between align-items-center">
                        <div class="text-truncate me-2">
                            <strong>${record.id}</strong> - ${record.title}
                            <span class="badge bg-secondary">${record.work_type}</span>
                            <span class="badge bg-info">Apps: ${record.required_apps.join(', ') || 'None'}</span>
                            ${record.active ? '<span class="badge bg-success">Active</span>' : '<span class="badge bg-danger">Inactive</span>'}
                        </div>
                        <small class="text-muted">${new Date(record.created_at).toLocaleDateString()}</small>
                    </div>
                    <div class="small text-muted text-truncate mt-1">${record.description || 'No description'}</div>
                </div>
            `).join('');
        });
}

// Form submission handler
function loadCaptcha() {
    return fetch('/api/captcha')
        .then(response => response.json())
        .then(data => {
            const captchaImage = document.getElementById('captchaImage');
            captchaImage.src = 'data:image/png;base64,' + data.image;
            captchaImage.style.display = 'block';
            document.getElementById('captchaInput').value = '';
        })
        .catch(error => {
            console.error('Error loading CAPTCHA:', error);
            alert('Failed to load CAPTCHA. Please try again.');
        });
}

// Function to handle form submission with CAPTCHA
// Main initialization
document.addEventListener('DOMContentLoaded', function() {
    loadRecords();
    
    // Initialize Select2 for multi-select fields after jQuery is ready
    $(function() {
        $('.form-select[multiple]').select2({
            width: '100%',
            placeholder: 'Select options',
            closeOnSelect: false,
            allowClear: true,
            tags: false
        });
    });

    const recordIdInput = document.getElementById('recordId');
    // Store the initial ID as the new-id
    recordIdInput.setAttribute('data-new-id', recordIdInput.value);

    // Set up form submission handler
    document.getElementById('recordForm').addEventListener('submit', function(e) {
        e.preventDefault();
        
        // Validate title field
        const titleInput = document.getElementById('title');
        if (!titleInput.value.trim()) {
            alert('Title is required');
            titleInput.focus();
            return false;
        }

        // Show CAPTCHA modal on save attempt
        const captchaModal = new bootstrap.Modal(document.getElementById('captchaModal'));
        loadCaptcha().then(() => {
            captchaModal.show();
        }).catch(error => {
            console.error('Failed to load CAPTCHA:', error);
            alert('Failed to load CAPTCHA. Please try again.');
        });
    });
});

function submitWithCaptcha() {
    const captchaInput = document.getElementById('captchaInput');
    const titleInput = document.getElementById('title');
    const submitButton = document.querySelector('#captchaModal .btn-primary');

    if (!titleInput.value.trim()) {
        alert('Title is required');
        titleInput.focus();
        return;
    }

    if (!captchaInput.value.trim()) {
        alert('Please complete the CAPTCHA verification');
        captchaInput.focus();
        return;
    }

    // Disable submit button and show loading state
    const loadingSpinner = '<span class="spinner-border spinner-border-sm me-2"></span>Saving...';
    submitButton.disabled = true;
    submitButton.innerHTML = loadingSpinner;

    const formData = {
        id: document.getElementById('recordId').value,
        title: document.getElementById('title').value,
        description: document.getElementById('description').value,
        start_date: document.getElementById('startDate').value,
        end_date: document.getElementById('endDate').value,
        work_type: document.getElementById('workType').value,
        required_apps: $('#requiredApps').val() || [],
        active: document.getElementById('active').checked,
        captcha: captchaInput.value
    };

    const isNewRecord = formData.id === document.getElementById('recordId').getAttribute('data-new-id');
    const method = isNewRecord ? 'POST' : 'PUT';
    const url = method === 'POST' ? '/api/records' : `/api/records/${formData.id}`;

    fetch(url, {
        method: method,
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(err => {
                throw new Error(err.error || 'Failed to save record');
            });
        }
        return response.json();
    })
    .then(() => {
        loadRecords();
        if (method === 'POST') {
            resetForm();
        }
        // Hide modal after successful verification
        const captchaModal = bootstrap.Modal.getInstance(document.getElementById('captchaModal'));
        if (captchaModal) {
            captchaModal.hide();
        }
        // Clear CAPTCHA input
        captchaInput.value = '';
        // Show success message
        const toast = new bootstrap.Toast(Object.assign(document.createElement('div'), {
            className: 'toast position-fixed top-0 end-0 m-3',
            innerHTML: `
                <div class="toast-header bg-success text-white">
                    <strong class="me-auto">Success</strong>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast"></button>
                </div>
                <div class="toast-body">Record saved successfully!</div>
            `
        }));
        document.body.appendChild(toast._element);
        toast.show();
        setTimeout(() => toast._element.remove(), 3000);
    })
    .catch(error => {
        alert(error.message);
        if (error.message.includes('CAPTCHA')) {
            loadCaptcha();  // Reload CAPTCHA if invalid
        }
    })
    .finally(() => {
        // Re-enable submit button
        submitButton.disabled = false;
        submitButton.innerHTML = 'Submit';
    });
}
