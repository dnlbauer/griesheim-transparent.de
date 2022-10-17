let cachedInput = null  // hold the actual user input

let autocompleteNavigation = (event, element) => {
    console.log(cachedInput)
    let elements = up.element.all(".autocomplete-item")

    // find currently selected element
    let currentElementIdx = -1
    let currentElement = up.element.get(".selected")
    if (currentElement != null) {
        currentElementIdx = Array.prototype.indexOf.call(elements, currentElement)
    }

    if (event.keyCode === 40 || event.keyCode === 38) { // up or down: move to next suggestion
        console.log("arrow key pressed")
        let add
        if(event.keyCode === 40)
            add = 1
        else
            add = -1
        let nextElementIdx = Math.min(Math.max(-1, currentElementIdx + add), elements.length-1)
        if (nextElementIdx !== currentElementIdx) {
            if (nextElementIdx >= 0) {
                let newSelectedElement = elements[nextElementIdx]
                let newValue = newSelectedElement.textContent
                up.element.toggleClass(newSelectedElement, "selected")
                console.log(`Selected ${newValue}`)
                if (!cachedInput)
                    cachedInput = element.value
                element.value = newValue
            } else { // -1
                element.value = cachedInput
            }
            if (currentElement) {
                up.element.toggleClass(currentElement, "selected")
            }
            event.preventDefault()
        }
    } else if(event.keyCode === 27) { // escape: hide suggestions
        hideSuggestions()
        event.preventDefault()
    } else {
        cachedInput = null
    }
}

let hideSuggestions = function() {
    up.element.hide(up.element.get(".autocomplete-list"))
}

let loadSuggestions = function (value) {
    console.log(`Suggest for ${value}`)
    up.render({target: '.autocomplete-list', url: `/suggest?query=${value}`})
}

up.on('keydown', 'input', autocompleteNavigation)
up.on('focusout', 'input', hideSuggestions)
up.on('focusin', 'input', (_, element) => { loadSuggestions(element.value) })
up.observe('input', {delay: 200}, (value) => loadSuggestions(value))
