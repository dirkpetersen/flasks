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

    // Reset form handler
    $('#resetForm').click(function() {
        $('#recordForm')[0].reset();
        $('#record_id').val('');
        $('.select2-single, .select2-multiple').val(null).trigger('change');
        $('#formTitle').text('Create New Record');
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

    // Handle edit button click to load record into editor
    $('.edit-btn').click(function(e) {
        e.preventDefault();
        const recordId = $(this).data('record-id');
        console.log('Clicked record ID:', recordId);
        
        if (!recordId) {
            console.error('No record ID found');
            return;
        }
        
        $('#loading').fadeIn();
        
        $.get('/get_record/' + recordId)
            .done(function(record) {
                console.log('Received record:', record);
                
                // Update form title
                $('#formTitle').text('Edit Record');
                
                // Clear all form fields first
                $('#recordForm')[0].reset();
                $('#record_id').val(record._id);
                $('.select2-single, .select2-multiple').val(null).trigger('change');
                
                // Populate the name field
                $('#name').val(record.name);
                
                // Populate select fields
                Object.keys(record).forEach(key => {
                    if (key !== 'name' && key !== 'created_at' && key !== '_id') {
                        const $select = $(`#${key}`);
                        if ($select.length) {
                            if (Array.isArray(record[key])) {
                                // Handle multiple select fields
                                $select.val(record[key]).trigger('change');
                            } else {
                                // Handle single select fields
                                $select.val(record[key]).trigger('change');
                            }
                        }
                    }
                });

                // Scroll to form
                $('html, body').animate({
                    scrollTop: $("#recordForm").offset().top - 20
                }, 'slow');
            })
            .fail(function() {
                alert('Failed to load record');
            })
            .always(function() {
                $('#loading').fadeOut();
            });
    });
});
