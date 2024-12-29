document.addEventListener('DOMContentLoaded', function() {
    const startDateInput = document.getElementById('startDate');
    const endDateInput = document.getElementById('endDate');

    // Helper function to format date with specific time
    function setDateWithTime(inputElement, hours, minutes) {
        if (!inputElement.value) return;
        
        // Get the date part only (YYYY-MM-DD)
        const datePart = inputElement.value.split('T')[0];
        
        // Set the new datetime with specified hours and minutes
        const formattedTime = `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`;
        inputElement.value = `${datePart}T${formattedTime}`;
    }

    // Set start date to beginning of day (00:00)
    startDateInput.addEventListener('change', function() {
        setDateWithTime(this, 0, 0);
    });

    // Set end date to end of day (23:59)
    endDateInput.addEventListener('change', function() {
        setDateWithTime(this, 23, 59);
    });

    // Also set times when the page loads if dates are pre-filled
    if (startDateInput.value) {
        setDateWithTime(startDateInput, 0, 0);
    }
    if (endDateInput.value) {
        setDateWithTime(endDateInput, 23, 59);
    }
});
