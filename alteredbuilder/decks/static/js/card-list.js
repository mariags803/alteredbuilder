// Modal to add a Card to a Deck
let cardModal = document.getElementById('add-card-modal');

if (cardModal) {
    cardModal.addEventListener('show.bs.modal', event => {
        // When the modal is to be shown, file its fields with the Card's data
        let button = event.relatedTarget;
        let cardNameElement = document.getElementById("modal-card-name");
        let cardReferenceElement = document.getElementById("modal-card-reference");

        cardNameElement.value = button.getAttribute('data-bs-name');
        cardReferenceElement.value = button.getAttribute('data-bs-reference');
    });
}

/**
 * Receive a list of labels (where each points to a checkbox input) and return a list of
 * values for each one that is checked.
 * 
 * @param {string[]} labels List of labels
 * @returns {string[]} List of values for the checked elements.
 */
function parseFilter(labels) {
    let filter = [];

    for (let label of labels) {
        let labelElement = document.getElementById("filter" + label);
        if (labelElement.checked) {
          filter.push(labelElement.value);
        }
    }
    return filter;
}

/**
 * Retrieve the checked checkboxes, build the filters into the GET parameters and query
 * the server.
 * 
 * @param {HTMLElement} e Element that triggered the event.
 * @returns 
 */
function searchCards(e) {
    e.preventDefault();
    let params = new URLSearchParams();

    // Retrieve the FACTION filters
    let factions = parseFilter(["Axiom", "Bravos", "Lyra", "Muna", "Ordis", "Yzmir"]);
    if (factions.length > 0) {
        params.append("faction", factions.join(","));
    }

    // Retrieve the RARITY filters
    let rarities = parseFilter(["Common", "Rare", "Unique"]);
    if (rarities.length > 0) {
        params.append("rarity", rarities.join(","));
    }

    // Retrieve the TYPE filters
    let types = parseFilter(["Character", "Hero", "Permanent", "Spell"]);
    if (types.length > 0) {
        params.append("type", types.join(","));
    }

    // Retrieve the QUERY from the search input
    let queryElement = document.getElementById("querySearch");
    if (queryElement.value != "") {
        params.append("query", queryElement.value);
    }

    // Retrieve the marked order on the dropdown
    let orderingElement = document.getElementById("filterOrdering");
    if (orderingElement.selectedIndex > 1) {
        params.append("order", orderingElement.value);
    }

    let deckId = (new URLSearchParams(window.location.search)).get("deck");
    if (deckId) {
        params.append("deck", deckId);
    }

    // Go to the built URL
    let url = window.location.pathname + "?" + params.toString();
    window.open(url, "_self");
    return false;
}

document.getElementById("filterSearchButton").addEventListener("click", searchCards);
document.getElementById("querySearchForm").addEventListener("submit", searchCards);
document.getElementById("filterOrdering").addEventListener("change", searchCards);

var decklistChanges = {}

document.getElementById("deckSelector").addEventListener("change", (e) => {
    e.preventDefault();

    let params = new URLSearchParams(window.location.search);
    params.delete("deck");
    params.append("deck", e.target.value);
    let url = window.location.pathname + "?" + params.toString();
    window.open(url, "_self");

    return false;
});

// Decrease the quantity of the card
function decreaseCardQuantity(event) {
    let quantityElement = event.target.nextElementSibling;
    let quantity = Number(quantityElement.innerText) - 1;
    if (quantity > 0) {
        quantityElement.innerText = quantity;
    } else {
        // If the quantity reaches 0, remove the card from the deck list
        event.target.parentElement.parentElement.parentElement.remove();
    }
}

// Increase the quantity of the card
function increaseCardQuantity(event) {
    let quantityElement = event.target.previousElementSibling;
    quantityElement.innerText = Number(quantityElement.innerText) + 1;
}

// Retrieve all the buttons to decrease the card quantity
let removeCardButtons = document.getElementsByClassName("remove-card-btn");
Array.from(removeCardButtons).forEach(function(element) {
    element.addEventListener("click", decreaseCardQuantity);
});

// Retrieve all the buttons to increase the card quantity
let addCardButtons = document.getElementsByClassName("add-card-btn");
Array.from(addCardButtons).forEach(function(element) {
    element.addEventListener("click", increaseCardQuantity);
});

let removeHeroButton = document.getElementById("remove-hero");
removeHeroButton.addEventListener("click", function(event) {
    let heroTextElement = event.currentTarget.previousElementSibling;
    let heroReference = heroTextElement.dataset.cardReference;

    heroTextElement.value = "";
    heroTextElement.dataset.cardReference = "";
    event.currentTarget.disabled = true;

    if (heroReference in decklistChanges) {
        delete decklistChanges[heroReference];
    } else {
        decklistChanges[heroReference] = 0;
    }
});

// Retrieve all the buttons to increase the card quantity
let cardDisplayElements = document.getElementsByClassName("card-display");
Array.from(cardDisplayElements).forEach(function(element) {
    element.addEventListener("click", function(event) {
        let cardReference = event.currentTarget.dataset.cardReference;
        let cardName = event.currentTarget.dataset.cardName;
        let cardType = event.currentTarget.dataset.cardType;
        
        if (cardType === "hero") {
            let heroElement = document.getElementById("hero-name");
            let removeHeroButton = document.getElementById("remove-hero");

            if (heroElement.value === "") {
                heroElement.value = cardName;
                heroElement.dataset.cardReference = cardReference;
                removeHeroButton.disabled = false;
                decklistChanges[cardReference] = 1;
            }
            return;
        }

        let cardElement = document.getElementById("row-" + cardReference);

        if (cardElement){
            let quantity = decklistChanges[cardReference] || Number(cardElement.getElementsByClassName("card-quantity")[0].innerText);
            decklistChanges[cardReference] = quantity + 1;
            cardElement.getElementsByClassName("card-quantity")[0].innerText = decklistChanges[cardReference];

        } else {
            let editDeckColumn = document.getElementById("edit-deck-column");
            let newCardElement = editDeckColumn.lastElementChild.cloneNode(true);
            newCardElement.id = "row-" + cardReference;
            newCardElement.getElementsByClassName("card-quantity")[0].innerText = 1;
            newCardElement.getElementsByClassName("card-name")[0].innerText = cardName;
            newCardElement.getElementsByClassName("remove-card-btn")[0].addEventListener("click", decreaseCardQuantity);
            newCardElement.getElementsByClassName("add-card-btn")[0].addEventListener("click", increaseCardQuantity);
            newCardElement.hidden = false;
            editDeckColumn.appendChild(newCardElement);
            decklistChanges[cardReference] = 1;
        }
    });
});