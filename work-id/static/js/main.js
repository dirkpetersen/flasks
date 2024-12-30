// Function declarations first
function setUserId() {
    const userId = document.getElementById('userIdInput').value;
    if (!userId) return;

    fetch('/api/set-user-id', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ user_id: userId }),
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`Error setting user ID: ${response.statusText}`);
        }
        return response.json();
    })
    .then(() => {
        loadRecords();
    })
    .catch(error => {
        console.error('Error in setUserId:', error);
        alert('Failed to set user ID: ' + error.message);
    });
}

function loadRecords() {
    const userId = document.getElementById('userIdInput').value;
    if (!userId) {
        const recordsList = document.getElementById('recordsList');
        recordsList.innerHTML = '<div class="list-group-item text-center text-muted py-4">' +
            '<i class="bi bi-person-exclamation fs-2 mb-2"></i><br>' +
            'Please set your user ID above to view records</div>';
        return;
    }

    fetch('/api/records')
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to fetch records: ' + response.statusText);
            }
            return response.json();
        })
        .then(records => {
            const recordsList = document.getElementById('recordsList');
            if (!Array.isArray(records) || records.length === 0) {
                recordsList.innerHTML = '<div class="list-group-item text-center text-muted py-4">' +
                    '<i class="bi bi-inbox fs-2 mb-2"></i><br>' +
                    'No records found</div>';
                return;
            }
            recordsList.innerHTML = records.map(record => {
                // Get all meta fields that have values
                const metaBadges = Object.entries(record)
                    .filter(([key, value]) => 
                        value !== null && 
                        !['id', 'title', 'description', 'start_date', 'end_date', 
                          'active', 'creator_id', 'created_at'].includes(key)
                    )
                    .map(([key, value]) => {
                        if (Array.isArray(value)) {
                            return `<span class="badge bg-info">${key}: ${value.join(', ')}</span>`;
                        } else {
                            return `<span class="badge bg-secondary">${key}: ${value}</span>`;
                        }
                    })
                    .join(' ');

                return `
                    <div class="list-group-item record-item py-2" onclick="loadRecord('${record.id}')">
                        <div class="d-flex justify-content-between align-items-center">
                            <div class="text-truncate me-2">
                                <strong>${record.id}</strong> - ${record.title || 'Untitled'}
                                ${metaBadges}
                                ${record.active ? '<span class="badge bg-success">Active</span>' : 
                                               '<span class="badge bg-danger">Inactive</span>'}
                            </div>
                            <small class="text-muted">${new Date(record.created_at).toLocaleDateString()}</small>
                        </div>
                        <div class="small text-muted text-truncate mt-1">${record.description || 'No description'}</div>
                    </div>
                `;
            }).join('');
        })
        .catch(error => {
            console.error('Error loading records:', error);
            const recordsList = document.getElementById('recordsList');
            recordsList.innerHTML = '<div class="list-group-item text-center text-danger py-4">' +
                '<i class="bi bi-exclamation-triangle fs-2 mb-2"></i><br>' +
                'Error loading records: ' + error.message + '</div>';
        });
}

function loadRecord(id) {
    document.body.classList.add('loading');
    console.log('Loading record with ID:', id);
    
    // Set longer timeout for the fetch operation
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout
    
    fetch('/api/records', {
        signal: controller.signal
    })
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to fetch records: ' + response.statusText);
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
            document.getElementById('displayId').textContent = record.id || '';
            document.getElementById('title').value = record.title || '';
            document.getElementById('description').value = record.description || '';
            
            // Handle dates with proper timezone conversion
            if (record.start_date) {
                try {
                    const startDate = new Date(record.start_date);
                    const localStartDate = startDate.toLocaleDateString('en-CA'); // YYYY-MM-DD format
                    document.getElementById('startDate').value = localStartDate;
                    document.getElementById('startDateTimezone').textContent = `(${Intl.DateTimeFormat().resolvedOptions().timeZone})`;
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
                    const localEndDate = endDate.toLocaleDateString('en-CA'); // YYYY-MM-DD format
                    document.getElementById('endDate').value = localEndDate;
                    document.getElementById('endDateTimezone').textContent = `(${Intl.DateTimeFormat().resolvedOptions().timeZone})`;
                } catch (e) {
                    console.error('Error parsing end_date:', e);
                    document.getElementById('endDate').value = '';
                    document.getElementById('endDateTimezone').textContent = '';
                }
            } else {
                document.getElementById('endDate').value = '';
                document.getElementById('endDateTimezone').textContent = '';
            }
            
            // Handle meta fields
            document.querySelectorAll('select[id^="meta_"]').forEach(select => {
                const isMulti = select.id.startsWith('meta_msel_');
                const fieldName = (isMulti ? 'META_MSEL_' : 'META_SEL_') + 
                                select.id.split('_').slice(2).join('_').toUpperCase();
                
                if (record[fieldName] !== undefined) {
                    if (isMulti) {
                        $(select).val(record[fieldName]).trigger('change');
                    } else {
                        select.value = record[fieldName];
                    }
                    console.log(`Loading ${fieldName} with value:`, record[fieldName]);
                } else {
                    if (isMulti) {
                        $(select).val([]).trigger('change');
                    } else {
                        select.value = '';
                    }
                }
                select.dispatchEvent(new Event('change'));
            });
            
            // Handle active status with default true
            document.getElementById('active').checked = record.active !== undefined ? record.active : true;
        })
        .catch(error => {
            console.error('Error loading record:', error);
            alert(`Failed to load record: ${error.message}`);
        })
        .finally(() => {
            clearTimeout(timeoutId);
            document.body.classList.remove('loading');
        });
}

function resetForm() {
    fetch('/api/new-id')
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to fetch new ID: ' + response.statusText);
            }
            return response.json();
        })
        .then(data => {
            document.getElementById('recordForm').reset();
            const recordIdInput = document.getElementById('recordId');
            recordIdInput.value = data.id;
            recordIdInput.setAttribute('data-new-id', data.id);
            document.getElementById('displayId').textContent = data.id;
            $('#requiredApps').val([]).trigger('change');
            // Reset CAPTCHA if it exists
            const captchaInput = document.getElementById('captchaInput');
            if (captchaInput) {
                captchaInput.value = '';
                loadCaptcha();
            }
        })
        .catch(error => {
            console.error('Error resetting form:', error);
            alert('Failed to reset form: ' + error.message);
        });
}

let isSearchActive = false;

function searchRecords() {
    const userId = document.getElementById('userIdInput').value;
    if (!userId) {
        const recordsList = document.getElementById('recordsList');
        recordsList.innerHTML = '<div class="list-group-item text-center text-muted py-4">' +
            '<i class="bi bi-person-exclamation fs-2 mb-2"></i><br>' +
            'Please set your user ID above to view records</div>';
        return;
    }

    let query = document.getElementById('searchInput').value;
    // Convert asterisk to empty string
    query = query === '*' ? '' : query;
    const userOnly = document.getElementById('userOnlyCheck').checked;
    
    if (!query.trim()) {
        if (userOnly) {
            loadRecords();
        } else {
            fetch('/api/search?q=&user_only=false')
                .then(response => {
                    if (!response.ok) {
                        throw new Error('Failed to fetch records: ' + response.statusText);
                    }
                    return response.json();
                })
                .then(records => updateRecordsList(records))
                .catch(error => {
                    console.error('Search error:', error);
                    alert('Failed to load records: ' + error.message);
                });
        }
        return;
    }

    fetch(`/api/search?q=${encodeURIComponent(query)}&user_only=${userOnly}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Search failed: ' + response.statusText);
            }
            return response.json();
        })
        .then(records => updateRecordsList(records))
        .catch(error => {
            console.error('Search error:', error);
            alert('Failed to search records: ' + error.message);
        });
}

// Form submission handler
function loadCaptcha() {
    return fetch('/api/captcha')
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to load CAPTCHA: ' + response.statusText);
            }
            return response.json();
        })
        .then(data => {
            const captchaImage = document.getElementById('captchaImage');
            captchaImage.src = 'data:image/png;base64,' + data.image;
            captchaImage.style.display = 'block';
            const captchaInput = document.getElementById('captchaInput');
            captchaInput.value = '';
            
            // Add enter key handler
            captchaInput.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    submitWithCaptcha();
                }
            });
        })
        .catch(error => {
            console.error('Error loading CAPTCHA:', error);
            alert('Failed to load CAPTCHA. Please try again.');
        });
}

// Main initialization
document.addEventListener('DOMContentLoaded', function() {
    const userOnly = document.getElementById('userOnlyCheck').checked;
    if (userOnly) {
        loadRecords();
    } else {
        fetch('/api/search?q=&user_only=false')
            .then(response => {
                if (!response.ok) {
                    throw new Error('Failed to fetch records: ' + response.statusText);
                }
                return response.json();
            })
            .then(records => updateRecordsList(records))
            .catch(error => {
                console.error('Error loading records:', error);
                alert('Failed to load records: ' + error.message);
            });
    }
    
    // Add search input event listeners
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                searchRecords();
            }
        });
    }
    
    // Add search checkbox event listener
    const userOnlyCheck = document.getElementById('userOnlyCheck');
    if (userOnlyCheck) {
        userOnlyCheck.addEventListener('change', function() {
            const query = document.getElementById('searchInput').value;
            if (query.trim()) {
                searchRecords();
            } else {
                if (this.checked) {
                    loadRecords();
                } else {
                    fetch('/api/search?q=&user_only=false')
                        .then(response => {
                            if (!response.ok) {
                                throw new Error('Failed to fetch records: ' + response.statusText);
                            }
                            return response.json();
                        })
                        .then(records => updateRecordsList(records))
                        .catch(error => {
                            console.error('Error loading records:', error);
                            alert('Failed to load records: ' + error.message);
                        });
                }
            }
        });
    }
    
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
    const form = document.getElementById('recordForm');
    if (form) {
        form.addEventListener('submit', async function(e) {
            e.preventDefault();
            console.log('Form submitted'); // Debug log
            
            // Basic form validation
            if (!form.checkValidity()) {
                e.stopPropagation();
                form.classList.add('was-validated');
                return;
            }

            const titleInput = document.getElementById('title');
            if (!titleInput.value.trim()) {
                alert('Title is required');
                titleInput.focus();
                return;
            }

            // CAPTCHA validation only if force_captcha is true and section exists
            const captchaSection = document.getElementById('captchaSection');
            if (captchaSection) {
                const captchaInput = document.getElementById('captchaInput');
                if (!captchaInput.value.trim()) {
                    alert('Please complete the CAPTCHA verification');
                    captchaInput.focus();
                    return;
                }
            }

            try {
                // Prepare form data
                const formData = new FormData();
                formData.append('id', document.getElementById('recordId').value);
                formData.append('title', titleInput.value.trim());
                formData.append('description', document.getElementById('description').value.trim());
                formData.append('start_date', document.getElementById('startDate').value || null);
                formData.append('end_date', document.getElementById('endDate').value || null);
                formData.append('active', document.getElementById('active').checked);

                console.log('Initial form data:', Object.fromEntries(formData));

                // Add meta fields dynamically
                document.querySelectorAll('select[id^="meta_"]').forEach(select => {
                    const isMulti = select.id.startsWith('meta_msel_');
                    const fieldName = (isMulti ? 'META_MSEL_' : 'META_SEL_') + 
                                    select.id.split('_').slice(2).join('_').toUpperCase();
            
                    if (isMulti) {
                        const values = $(select).val() || [];
                        values.forEach(value => {
                            formData.append(fieldName, value);
                        });
                        console.log(`Processing multi-select ${fieldName}:`, values);
                    } else {
                        const value = select.value || '';
                        formData.append(fieldName, value);
                        console.log(`Processing single-select ${fieldName}:`, value);
                    }
                });

                // Convert FormData to JSON
                const jsonData = {};
                for (let [key, value] of formData.entries()) {
                    if (jsonData[key]) {
                        if (!Array.isArray(jsonData[key])) {
                            jsonData[key] = [jsonData[key]];
                        }
                        jsonData[key].push(value);
                    } else {
                        jsonData[key] = value;
                    }
                }

                // Debug information for formData
                console.log('Final Form data before submission:', formData); // Debug log

                // Add CAPTCHA only if section exists (force_captcha is true)
                const captchaSection = document.getElementById('captchaSection');
                if (captchaSection) {
                    const captchaInput = document.getElementById('captchaInput');
                    formData.captcha = captchaInput.value.trim();
                }

                await submitFormData(jsonData);
            } catch (error) {
                console.error('Form submission error:', error);
                alert(error.message || 'Failed to save record');
            }
        });
    }

    // Load initial CAPTCHA if enabled
    const captchaImage = document.getElementById('captchaImage');
    if (captchaImage) {
        loadCaptcha();
    }
});

function submitFormData(formData) {
    const submitButton = document.querySelector('#recordForm button[type="submit"]');
    submitButton.disabled = true;
    submitButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Saving...';

    const isNewRecord = formData.id === document.getElementById('recordId').getAttribute('data-new-id');
    const method = isNewRecord ? 'POST' : 'PUT';
    const url = method === 'POST' ? '/api/records' : `/api/records/${formData.id}`;

    // Detailed debug logging of form data
    console.log('\nDEBUG - Form Submission:');
    console.log('Method:', method);
    console.log('URL:', url);
    console.log('All form data:', formData);
    
    // Specifically log META fields
    const metaFields = {};
    Object.keys(formData).forEach(key => {
        if (key.startsWith('META_')) {
            metaFields[key] = formData[key];
        }
    });
    console.log('META fields being submitted:', metaFields);

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
                submitButton.classList.add('error');
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
        // Clear CAPTCHA input if it exists
        const captchaInput = document.getElementById('captchaInput');
        if (captchaInput) {
            captchaInput.value = '';
        }
        // Show success message
        // Show success alert
        alert('Record saved successfully!');
    })
    .catch(error => {
        const errorMessage = error.message || 'An error occurred';
        if (errorMessage.includes('End date cannot be before start date')) {
            alert('Error: End date cannot be before start date. Please check your dates.');
            document.getElementById('endDate').focus();
        } else {
            alert(errorMessage);
            if (errorMessage.includes('CAPTCHA')) {
                loadCaptcha();  // Reload CAPTCHA if invalid
            }
        }
    })
    .finally(() => {
        // Re-enable button and reset state
        submitButton.disabled = false;
        submitButton.innerHTML = 'Save Record';
        
        if (submitButton.classList.contains('error')) {
            submitButton.classList.remove('error');
        }
    });
}
function updateRecordsList(records) {
    const recordsList = document.getElementById('recordsList');
    if (!Array.isArray(records) || records.length === 0) {
        recordsList.innerHTML = '<div class="list-group-item text-center text-muted py-4">' +
            '<i class="bi bi-inbox fs-2 mb-2"></i><br>' +
            'No records found</div>';
        return;
    }
    recordsList.innerHTML = records.map(record => {
        // Get all meta fields that have values
        const metaBadges = Object.entries(record)
            .filter(([key, value]) => 
                value !== null && 
                !['id', 'title', 'description', 'start_date', 'end_date', 
                  'active', 'creator_id', 'created_at'].includes(key)
            )
            .map(([key, value]) => {
                if (Array.isArray(value)) {
                    return `<span class="badge bg-info">${key}: ${value.join(', ')}</span>`;
                } else {
                    return `<span class="badge bg-secondary">${key}: ${value}</span>`;
                }
            })
            .join(' ');

        return `
            <div class="list-group-item record-item py-2" onclick="loadRecord('${record.id}')">
                <div class="d-flex justify-content-between align-items-center">
                    <div class="text-truncate me-2">
                        <strong>${record.id}</strong> - ${record.title || 'Untitled'}
                        ${metaBadges}
                        ${record.active ? '<span class="badge bg-success">Active</span>' : 
                                      '<span class="badge bg-danger">Inactive</span>'}
                    </div>
                    <small class="text-muted">${new Date(record.created_at).toLocaleDateString()}</small>
                </div>
                <div class="small text-muted text-truncate mt-1">${record.description || 'No description'}</div>
            </div>
        `;
    }).join('');
}
