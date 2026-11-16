// Cloud Inventory - interactive client-side scripts

document.addEventListener('DOMContentLoaded', function () {
    const appLayout = document.getElementById('appLayout');
    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebarCloseBtn = document.getElementById('sidebarCloseBtn');
    const sidebarBackdrop = document.getElementById('sidebarBackdrop');

    // Restore desktop sidebar collapsed preference from localStorage
    if (window.innerWidth >= 992) {
        const isCollapsed = localStorage.getItem('cloud_inventory_sidebar_collapsed') === 'true';
        if (isCollapsed && appLayout) {
            appLayout.classList.add('sidebar-collapsed');
        }
    }

    // Toggle navigation menu
    if (sidebarToggle && appLayout) {
        sidebarToggle.addEventListener('click', function () {
            if (window.innerWidth >= 992) {
                // Desktop: collapse/expand
                appLayout.classList.toggle('sidebar-collapsed');
                const collapsed = appLayout.classList.contains('sidebar-collapsed');
                localStorage.setItem('cloud_inventory_sidebar_collapsed', collapsed ? 'true' : 'false');
            } else {
                // Mobile: open offcanvas drawer
                appLayout.classList.toggle('mobile-sidebar-open');
            }
        });
    }

    // Close mobile sidebar via close button
    if (sidebarCloseBtn && appLayout) {
        sidebarCloseBtn.addEventListener('click', function () {
            appLayout.classList.remove('mobile-sidebar-open');
        });
    }

    // Close mobile sidebar when clicking backdrop
    if (sidebarBackdrop && appLayout) {
        sidebarBackdrop.addEventListener('click', function () {
            appLayout.classList.remove('mobile-sidebar-open');
        });
    }

    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(function (alert) {
        setTimeout(function () {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            if (bsAlert) {
                bsAlert.close();
            }
        }, 5000);
    });

    // Form validation
    const forms = document.querySelectorAll('form[novalidate]');
    forms.forEach(function (form) {
        form.addEventListener('submit', function (event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });
});
