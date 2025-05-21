const search_results = document.querySelector("#search_results");
const input_search = document.querySelector("#input_search");
let my_timer = null;

function search() {
    clearInterval(my_timer);
    if (input_search.value.trim() !== "") {
        my_timer = setTimeout(async function () {
            try {
                const search_for = input_search.value.trim();
                const conn = await fetch(`/search?q=${search_for}`);
                const data = await conn.json();

                search_results.innerHTML = "";

                if (data.length === 0) {
                    search_results.classList.add("hidden");
                    return;
                }

                data.forEach(item => {
                    const html = `
                        <div mix-get="/items/${item.item_pk}" class="search-result">
                            <img src="/static/uploads/${item.item_image}" alt="">
                            <span>${item.item_name}</span>
                        </div>
                    `;
                    search_results.insertAdjacentHTML("beforeend", html);
                });

                mix_convert();

                search_results.classList.remove("hidden");

            } catch (err) {
                console.error(err);
                search_results.classList.add("hidden");
            }
        }, 500);
    } else {
        search_results.innerHTML = "";
        search_results.classList.add("hidden");
    }
}


addEventListener("click", function (event) {
    if (!search_results.contains(event.target)) {
        search_results.classList.add("hidden");
    }
    if (input_search.contains(event.target)) {
        search_results.classList.remove("hidden");
    }
});


function add_markers_to_map(data){
    console.log(data)
    data = JSON.parse(data)
    console.log(data)
    data.forEach(item => {
        const customIcon = L.divIcon({
            className: 'custom-marker',
            html: `<div mix-get="/items/${item.item_pk}" class="custom-marker">${item.item_name?.[0] || '?'}</div>`,
            iconSize: [50, 50],
            iconAnchor: [25, 25],
        });
       
        L.marker([item.item_lat, item.item_lon], { icon: customIcon })
            .addTo(map)
            .bindPopup(item.item_name)
    });
}

// Tjek om brugeren er på index-siden (med eller uden /en eller /dk)
document.addEventListener("DOMContentLoaded", () => {
  const searchContainer = document.getElementById("search_container");
  const path = window.location.pathname;

  const isIndex = path === "/" || path === "/en" || path === "/dk";

  if (isIndex && searchContainer) {
    searchContainer.classList.remove("hidden");
  }
});
