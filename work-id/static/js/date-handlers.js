document.addEventListener('DOMContentLoaded', function() {
    const startDateInput = document.getElementById('startDate');
    const endDateInput = document.getElementById('endDate');

    // Function to get ISO datetime string with specific time
    function getDateTimeString(dateStr, hours, minutes) {
        if (!dateStr) return '';
        return `${dateStr}T${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`;
    }

    // Store the actual datetime value in a data attribute
    function updateDateTime(inputElement, hours, minutes) {
        if (!inputElement.value) {
            inputElement.setAttribute('data-datetime', '');
            return;
        }
        const dateTimeStr = getDateTimeString(inputElement.value, hours, minutes);
        inputElement.setAttribute('data-datetime', dateTimeStr);
    }

    // Set start date to beginning of day (00:00)
    startDateInput.addEventListener('change', function() {
        updateDateTime(this, 0, 0);
    });

    // Set end date to end of day (23:59)
    endDateInput.addEventListener('change', function() {
        updateDateTime(this, 23, 59);
    });

    // Handle form submission
    document.getElementById('recordForm').addEventListener('submit', function(e) {
        // Update the form data with the stored datetime values
        const formData = new FormData(this);
        if (startDateInput.value) {
            formData.set('start_date', startDateInput.getAttribute('data-datetime'));
        }
        if (endDateInput.value) {
            formData.set('end_date', endDateInput.getAttribute('data-datetime'));
        }
    });

    // Initialize if dates are pre-filled
    if (startDateInput.value) {
        updateDateTime(startDateInput, 0, 0);
    }
    if (endDateInput.value) {
        updateDateTime(endDateInput, 23, 59);
    }
});
