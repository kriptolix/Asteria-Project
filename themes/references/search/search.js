const form = document.querySelector("#search-form");
const overlay = document.querySelector("#search-overlay");

form.addEventListener("submit", (event) => {

    event.preventDefault();

    overlay.classList.add("is-open");

});


overlay.addEventListener("click", (event) => {

    if (event.target === overlay) {
        overlay.classList.remove("is-open");
    }

});