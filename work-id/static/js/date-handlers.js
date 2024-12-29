// Set default times when dates are selected
document.addEventListener('DOMContentLoaded', function() {
    const startDateInput = document.getElementById('startDate');
    const endDateInput = document.getElementById('endDate');

    function formatDateWithTime(date, hour, minute) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}T${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}`;
    }

    startDateInput.addEventListener('change', function() {
        if (this.value) {
            const selectedDate = new Date(this.value);
            this.value = formatDateWithTime(selectedDate, 0, 0);
        }
    });

    endDateInput.addEventListener('change', function() {
        if (this.value) {
            const selectedDate = new Date(this.value);
            this.value = formatDateWithTime(selectedDate, 23, 59);
        }
    });
});
