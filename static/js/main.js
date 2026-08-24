// Main global application logic
document.addEventListener('DOMContentLoaded', () => {
    console.log('MineGuard AI Core Initialized.');
    
    // Highlight active sidebar links dynamically based on current path
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('aside nav a');
    
    navLinks.forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('bg-zinc-100', 'text-black', 'font-semibold');
            link.classList.remove('text-gray-600');
        }
    });
});