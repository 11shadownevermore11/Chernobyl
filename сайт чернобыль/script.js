document.addEventListener('DOMContentLoaded', function() {
    console.log('Темная тема с градиентом загружена!');
        const sections = document.querySelectorAll('section');
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
            }
        });
    }, { threshold: 0.1 });
    
    sections.forEach(section => {
        section.style.opacity = '0';
        section.style.transform = 'translateY(30px)';
        section.style.transition = 'all 0.8s ease-out';
        observer.observe(section);
    });
    
    sections.forEach(section => {
        if (section.classList.contains('visible')) {
            section.style.opacity = '1';
            section.style.transform = 'translateY(0)';
        }
    });
    
    const headings = document.querySelectorAll('h1, h2');
    headings.forEach(heading => {
        heading.style.textShadow = '0 0 10px rgba(255, 215, 0, 0.5)';
    });
});