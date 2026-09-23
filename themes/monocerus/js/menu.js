document.addEventListener('DOMContentLoaded', () => {
    const button = document.querySelector('.menu-toggle');
    document.addEventListener('DOMContentLoaded', () => {
    const button = document.querySelector('.menu-toggle');

    if (!button) return;})

    const menu = document.querySelector('.site-menu');
    const overlay = document.querySelector('.menu-overlay');

    button.addEventListener('click', () => {
        const open = menu.classList.toggle('is-open');

        overlay.classList.toggle('is-visible', open);
        button.setAttribute('aria-expanded', open);
    });

    overlay.addEventListener('click', () => {
        menu.classList.remove('is-open');
        overlay.classList.remove('is-visible');
        button.setAttribute('aria-expanded', 'false');
    });
});

