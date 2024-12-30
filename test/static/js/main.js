$(document).ready(function() {
    // Initialize Select2
    $('.select2-single').select2({
        theme: 'bootstrap-5'
    });
    $('.select2-multiple').select2({
        theme: 'bootstrap-5',
        placeholder: 'Select options'
    });

    // Dark mode toggle
    $('#darkModeToggle').click(function() {
        $('body').toggleClass('dark-mode');
        localStorage.setItem('darkMode', $('body').hasClass('dark-mode'));
    });

    // Check for saved dark mode preference
    if (localStorage.getItem('darkMode') === 'true') {
        $('body').addClass('dark-mode');
    }

    // Show loading animation on form submit
    $('form').on('submit', function() {
        $('#loading').fadeIn();
    });

    // Animate new elements
    $('.card').addClass('animate__animated animate__fadeIn');
    
    // Smooth scroll to top after delete
    $('.btn-danger').click(function() {
        if(confirm('Are you sure you want to delete this record?')) {
            $('#loading').fadeIn();
            $('html, body').animate({ scrollTop: 0 }, 'slow');
            return true;
        }
        return false;
    });

    // Hide loading animation on page load
    $('#loading').fadeOut();
});
