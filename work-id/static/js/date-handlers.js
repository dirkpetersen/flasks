// Set default times when dates are selected
document.addEventListener('DOMContentLoaded', function() {
    const startDateInput = document.getElementById('startDate');
    const endDateInput = document.getElementById('endDate');

    startDateInput.addEventListener('change', function() {
        if (this.value) {
            let date = new Date(this.value);
            // Get just the date part in YYYY-MM-DD format
            const datePart = date.toISOString().split('T')[0];
            // Set to midnight (00:00)
            this.value = datePart + 'T00:00';
        }
    });

    endDateInput.addEventListener('change', function() {
        if (this.value) {
            let date = new Date(this.value);
            // Get just the date part in YYYY-MM-DD format
            const datePart = date.toISOString().split('T')[0];
            // Set to 23:59
            this.value = datePart + 'T23:59';
        }
    });
});
