let cachedInput = null  // hold the actual user input
const selectedClass = "selected"

function autocompleteNavigation(event, searchBox) {
    let elements = up.element.all(".autocomplete-item")

    // find currently selected element
    let currentElementIdx = -1
    let currentElement = up.element.get('.' + selectedClass)
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
            up.element.toggleClass(newSelectedElement, selectedClass)
            console.log(`Selected ${newValue}`)
            if (!cachedInput)
                cachedInput = searchBox.value
            searchBox.value = newValue
        } else { // -1
            searchBox.value = cachedInput
        }
        if (currentElement) {
            up.element.toggleClass(currentElement, selectedClass)
        }
        event.preventDefault()
    }
}

function hideSuggestions() {
    up.element.hide(up.element.get(".autocomplete-list"))
    up.element.toggleClass(up.element.get('input'), 'search-box-active', false)
}

function loadSuggestions(value) {
    if (value.length <= 3) // no suggestions for < 3 letters
        return
    console.log(`Loading suggestions: ${value}`)
    // load suggestions, change search box style; hide suggestions if loading failed
    up.render({target: '.autocomplete-list', url: `/suggest?query=${value}`})
        .then(up.element.toggleClass(up.element.get('input'), 'search-box-active', true))
        .catch(hideSuggestions())
}

up.on('keydown', 'input', autocompleteNavigation)
up.on('focusout', 'input', hideSuggestions)
up.on('focusin', 'input', (_, element) => { loadSuggestions(element.value) })
up.observe('input', {delay: 200}, (value) => loadSuggestions(value))
// up.on('keyup', 'input', function(event, element) {
//     if (event.keyCode === 13) {
//         console.log("test")
//         element.blur()
//         hideSuggestions()
//     }
// })
