// MediLink main JavaScript file

document.addEventListener('DOMContentLoaded', function() {
    // Initialize all Feather icons
    if (typeof feather !== 'undefined') {
        feather.replace();
    }
    
    // Toast notifications
    const toasts = document.querySelectorAll('.toast');
    toasts.forEach(toast => {
        setTimeout(() => {
            toast.classList.add('fade-out');
            setTimeout(() => {
                toast.remove();
            }, 300);
        }, 5000);
    });
    
    // Close buttons for alerts
    const closeButtons = document.querySelectorAll('.alert .close');
    closeButtons.forEach(button => {
        button.addEventListener('click', function() {
            const alert = this.parentElement;
            alert.classList.add('fade-out');
            setTimeout(() => {
                alert.remove();
            }, 300);
        });
    });
    
    // Tabs functionality
    const tabLinks = document.querySelectorAll('[data-tab]');
    if (tabLinks.length > 0) {
        tabLinks.forEach(link => {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                
                const targetId = this.getAttribute('data-tab');
                const tabContent = document.querySelectorAll('.tab-content');
                const tabLinks = document.querySelectorAll('[data-tab]');
                
                // Hide all tab content
                tabContent.forEach(content => {
                    content.classList.add('hidden');
                });
                
                // Deactivate all tab links
                tabLinks.forEach(link => {
                    link.classList.remove('active-tab');
                });
                
                // Show target tab content and activate link
                document.getElementById(targetId).classList.remove('hidden');
                this.classList.add('active-tab');
            });
        });
        
        // Activate first tab by default
        tabLinks[0].click();
    }
    
    // Date formatting
    const formatDates = document.querySelectorAll('.format-date');
    formatDates.forEach(element => {
        const dateString = element.textContent;
        const date = new Date(dateString);
        
        if (!isNaN(date)) {
            element.textContent = new Intl.DateTimeFormat('en-US', {
                year: 'numeric',
                month: 'long',
                day: 'numeric'
            }).format(date);
        }
    });
    
    // Time formatting
    const formatTimes = document.querySelectorAll('.format-time');
    formatTimes.forEach(element => {
        const timeString = element.textContent;
        const date = new Date(`1970-01-01T${timeString}`);
        
        if (!isNaN(date)) {
            element.textContent = new Intl.DateTimeFormat('en-US', {
                hour: 'numeric',
                minute: 'numeric',
                hour12: true
            }).format(date);
        }
    });
    
    // Form validation
    const forms = document.querySelectorAll('form[data-validate]');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            let isValid = true;
            
            // Check required fields
            const requiredFields = form.querySelectorAll('[required]');
            requiredFields.forEach(field => {
                if (!field.value.trim()) {
                    isValid = false;
                    field.classList.add('border-red-500');
                    
                    const errorElement = document.createElement('p');
                    errorElement.classList.add('text-red-500', 'text-xs', 'mt-1', 'validation-error');
                    errorElement.textContent = 'This field is required';
                    
                    // Remove any existing error message
                    const existingError = field.parentElement.querySelector('.validation-error');
                    if (existingError) {
                        existingError.remove();
                    }
                    
                    field.parentElement.appendChild(errorElement);
                } else {
                    field.classList.remove('border-red-500');
                    const existingError = field.parentElement.querySelector('.validation-error');
                    if (existingError) {
                        existingError.remove();
                    }
                }
            });
            
            // Check email fields
            const emailFields = form.querySelectorAll('[type="email"]');
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            emailFields.forEach(field => {
                if (field.value.trim() && !emailRegex.test(field.value.trim())) {
                    isValid = false;
                    field.classList.add('border-red-500');
                    
                    const errorElement = document.createElement('p');
                    errorElement.classList.add('text-red-500', 'text-xs', 'mt-1', 'validation-error');
                    errorElement.textContent = 'Please enter a valid email address';
                    
                    // Remove any existing error message
                    const existingError = field.parentElement.querySelector('.validation-error');
                    if (existingError) {
                        existingError.remove();
                    }
                    
                    field.parentElement.appendChild(errorElement);
                }
            });
            
            if (!isValid) {
                e.preventDefault();
            }
        });
    });
});