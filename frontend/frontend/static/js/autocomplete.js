let cachedInput = null  // hold the actual user input

function autocompleteNavigation(event, searchBox) {
    let elements = up.element.all(".autocomplete-item")

    // find currently selected element
    let currentElementIdx = -1
    let currentElement = up.element.get('.selected')
    if (currentElement != null) {
        currentElementIdx = Array.prototype.indexOf.call(elements, currentElement)
    }

    if (event.keyCode === 40)  // arrow down
        incrSelection(1, currentElement, currentElementIdx, elements, searchBox)
    else if (event.keyCode === 38)  // arrow up
        incrSelection(-1, currentElement, currentElementIdx, elements, searchBox)
    else if(event.keyCode === 27) { // escape: hide suggestions
        hideSuggestions()
        event.preventDefault()
    } else if (event.keyCode === 13) { // enter
        setTimeout(hideSuggestions, 100)
    } else {  // normal letter: reset cached input
        cachedInput = null
    }
}

function incrSelection(incr, currentElement, currentElementIdx, elements, searchBox) {
    let nextElementIdx = Math.min(Math.max(-1, currentElementIdx + incr), elements.length-1)
    if (nextElementIdx !== currentElementIdx) {
        if (nextElementIdx >= 0) {
            let newSelectedElement = elements[nextElementIdx]
            let newValue = newSelectedElement.textContent
            up.element.toggleClass(newSelectedElement, 'selected')
            console.log(`Selected ${newValue}`)
            if (!cachedInput)
                cachedInput = searchBox.value
            searchBox.value = newValue
        } else { // -1
            searchBox.value = cachedInput
        }
        if (currentElement) {
            up.element.toggleClass(currentElement, 'selected')
        }
        event.preventDefault()
    }
}

function hideSuggestions() {
    console.log("hide autocomplete results")
    up.element.hide(up.element.get(".autocomplete-list"))
    up.element.toggleClass(up.element.get('input'), 'search-box-active', false)
}

function loadSuggestions(value) {
    console.log(`Loading suggestions: ${value}`)
    // load suggestions, change search box style; hide suggestions if loading failed
    up.render({target: '.autocomplete-list', url: `/suggest?query=${value}`})
        .then(
            up.element.toggleClass(up.element.get('input'), 'search-box-active', true),
            up.element.toggleClass(up.element.get('input'), 'search-box-active', false)
            )
        .catch(hideSuggestions)
}

// navigate in suggestions
up.on('keydown', 'input', autocompleteNavigation)

// hide suggestions when input focus is lost
up.on('focusout', 'input', (event) => {
    // only if clicked outside suggestion area
    let target = event.relatedTarget
    let links = up.element.subtree(up.element.get(".input-field"), '*')
    if (!target || !Array.prototype.indexOf.call(target, links))
        hideSuggestions()
})

// show suggestions on focus gain
up.on('focusin', 'input', (_, element) => {
    console.log("focus")
    loadSuggestions(element.value)
})

// autoload suggestions while typing
up.observe('input', {delay: 200}, (value, element) => {
    console.log("input " + value)
    loadSuggestions(value)
})
// up.on('keyup', 'input', function(event, element) {
//     if (event.keyCode === 13) {
//         console.log("test")
//         element.blur()
//         hideSuggestions()
//     }
// })
