class ContactManager {
    constructor() {
        this.contactsList = document.getElementById('contactsList');
        this.contactForm = document.getElementById('contactForm');
        this.setupEventListeners();
        this.loadContacts();
    }

    setupEventListeners() {
        document.getElementById('newContactBtn').addEventListener('click', () => this.resetForm());
        document.getElementById('cancelBtn').addEventListener('click', () => this.resetForm());
        document.getElementById('deleteBtn').addEventListener('click', () => this.deleteContact());
        this.contactForm.addEventListener('submit', (e) => this.handleSubmit(e));
    }

    async loadContacts() {
        try {
            const response = await fetch('/api/contacts');
            const contacts = await response.json();
            this.renderContacts(contacts);
        } catch (error) {
            console.error('Error loading contacts:', error);
        }
    }

    renderContacts(contacts) {
        this.contactsList.innerHTML = contacts
            .map(contact => `
                <button class="list-group-item list-group-item-action" 
                        data-contact='${JSON.stringify(contact)}'>
                    ${contact.first_name} ${contact.last_name}
                    <br>
                    <small class="text-muted">${contact.email}</small>
                </button>
            `)
            .join('');

        this.contactsList.querySelectorAll('button').forEach(btn => {
            btn.addEventListener('click', (e) => this.fillForm(JSON.parse(e.currentTarget.dataset.contact)));
        });
    }

    fillForm(contact) {
        document.getElementById('contactId').value = contact.id;
        document.getElementById('firstName').value = contact.first_name;
        document.getElementById('lastName').value = contact.last_name;
        document.getElementById('email').value = contact.email;
        document.getElementById('phone').value = contact.phone || '';
        document.getElementById('deleteBtn').style.display = 'block';
    }

    resetForm() {
        this.contactForm.reset();
        document.getElementById('contactId').value = '';
        document.getElementById('deleteBtn').style.display = 'none';
    }

    async handleSubmit(e) {
        e.preventDefault();
        const contactId = document.getElementById('contactId').value;
        const contactData = {
            first_name: document.getElementById('firstName').value,
            last_name: document.getElementById('lastName').value,
            email: document.getElementById('email').value,
            phone: document.getElementById('phone').value
        };

        try {
            const url = contactId 
                ? `/api/contacts/${contactId}`
                : '/api/contacts';
            const method = contactId ? 'PUT' : 'POST';
            
            await fetch(url, {
                method,
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(contactData)
            });

            this.loadContacts();
            this.resetForm();
        } catch (error) {
            console.error('Error saving contact:', error);
        }
    }

    async deleteContact() {
        const contactId = document.getElementById('contactId').value;
        if (!contactId) return;

        if (confirm('Are you sure you want to delete this contact?')) {
            try {
                await fetch(`/api/contacts/${contactId}`, {
                    method: 'DELETE'
                });
                this.loadContacts();
                this.resetForm();
            } catch (error) {
                console.error('Error deleting contact:', error);
            }
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new ContactManager();
});
