document.addEventListener('DOMContentLoaded', function() {
    const contactForm = document.getElementById('contactForm');
    const contactsList = document.getElementById('contactsList');
    const searchInput = document.getElementById('searchInput');
    const newContactBtn = document.getElementById('newContact');

    // Load all contacts on page load
    loadContacts();

    // Event listeners
    contactForm.addEventListener('submit', handleFormSubmit);
    searchInput.addEventListener('input', debounce(handleSearch, 300));
    newContactBtn.addEventListener('click', clearForm);

    function loadContacts() {
        fetch('/api/records')
            .then(response => response.json())
            .then(records => {
                Promise.all(records.map(id =>
                    fetch(`/api/record/${id}`).then(res => res.json())
                )).then(contacts => {
                    displayContacts(contacts);
                });
            });
    }

    function displayContacts(contacts) {
        contactsList.innerHTML = contacts.map(contact => `
            <a href="#" class="list-group-item list-group-item-action" 
               data-id="${contact.id}">
                <div class="d-flex justify-content-between align-items-center">
                    <h6 class="mb-1">${contact.name}</h6>
                    <small>${contact.email}</small>
                </div>
                <small class="text-muted">${contact.phone || ''}</small>
            </a>
        `).join('');

        // Add click handlers to list items
        contactsList.querySelectorAll('.list-group-item').forEach(item => {
            item.addEventListener('click', () => loadContact(item.dataset.id));
        });
    }

    function loadContact(id) {
        fetch(`/api/record/${id}`)
            .then(response => response.json())
            .then(contact => {
                document.getElementById('contactId').value = id;
                document.getElementById('name').value = contact.name;
                document.getElementById('email').value = contact.email;
                document.getElementById('phone').value = contact.phone || '';
                document.getElementById('address').value = contact.address || '';
                
                // Update active state
                contactsList.querySelectorAll('.list-group-item').forEach(item => {
                    item.classList.remove('active');
                    if (item.dataset.id === id) {
                        item.classList.add('active');
                    }
                });
            });
    }

    async function handleFormSubmit(e) {
        e.preventDefault();
        const formData = {
            name: document.getElementById('name').value,
            email: document.getElementById('email').value,
            phone: document.getElementById('phone').value,
            address: document.getElementById('address').value
        };
        
        const id = document.getElementById('contactId').value;
        const method = id ? 'PUT' : 'POST';
        const url = id ? `/api/record/${id}` : '/api/record';

        try {
            const response = await fetch(url, {
                method: method,
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(formData)
            });

            if (response.ok) {
                loadContacts();
                if (!id) clearForm();
            }
        } catch (error) {
            console.error('Error:', error);
        }
    }

    function handleSearch() {
        const query = searchInput.value.trim();
        if (query) {
            fetch(`/api/search?q=${encodeURIComponent(query)}`)
                .then(response => response.json())
                .then(records => {
                    Promise.all(records.map(id =>
                        fetch(`/api/record/${id}`).then(res => res.json())
                    )).then(contacts => {
                        displayContacts(contacts);
                    });
                });
        } else {
            loadContacts();
        }
    }

    function clearForm() {
        document.getElementById('contactId').value = '';
        contactForm.reset();
        contactsList.querySelectorAll('.list-group-item').forEach(item => {
            item.classList.remove('active');
        });
    }

    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
});
