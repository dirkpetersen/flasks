// Set default times when dates are selected
document.addEventListener('DOMContentLoaded', function() {
    const startDateInput = document.getElementById('startDate');
    const endDateInput = document.getElementById('endDate');

    startDateInput.addEventListener('change', function() {
        if (this.value) {
            // Set time to 00:00
            const date = new Date(this.value);
            date.setHours(0, 0, 0, 0);
            this.value = date.toISOString().slice(0, 16);
        }
    });

    endDateInput.addEventListener('change', function() {
        if (this.value) {
            // Set time to 23:59
            const date = new Date(this.value);
            date.setHours(23, 59, 59, 999);
            this.value = date.toISOString().slice(0, 16);
        }
    });
});
