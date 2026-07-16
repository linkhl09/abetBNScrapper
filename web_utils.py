from selenium.webdriver.support.ui import WebDriverWait

def find_in_shadow(driver, selectors, timeout=10, multiple=False):
    """
    Busca elementos dentro de todos los open shadow roots de la página.

    Acepta un selector CSS simple (`"d2l-card"`) para búsqueda profunda global,
    o una lista de selectores para convertirla en una ruta CSS descendente.
    """

    selector = " ".join(selectors) if isinstance(selectors, (list, tuple)) else selectors
    wait = WebDriverWait(driver, timeout)

    def _deep_query(_driver):
        return _driver.execute_script(
            """
            const selector = arguments[0];
            const results = [];
            const seen = new Set();

            function collect(root) {
                if (!root || !root.querySelectorAll) {
                    return;
                }

                for (const match of root.querySelectorAll(selector)) {
                    if (!seen.has(match)) {
                        seen.add(match);
                        results.push(match);
                    }
                }

                for (const element of root.querySelectorAll('*')) {
                    if (element.shadowRoot) {
                        collect(element.shadowRoot);
                    }
                }
            }

            collect(document);
            return results;
            """,
            selector,
        )

    try:
        matches = wait.until(lambda current_driver: _deep_query(current_driver) or False)
        return matches if multiple else matches[0]
    except Exception as e:
        print(f"Error finding element with selector '{selector}': {e}")
        return [] if multiple else None

def search_text_in_element_list(element_list, search_term):
    """Find an element whose visible text contains `search_term` (case-insensitive)."""
    matched_element = None
    for element in element_list:
        element_text = (element.get_attribute("text") or element.text or "").strip()
        if search_term.lower() in element_text.lower():
            matched_element = element
            print(f"Matched element text: {element_text}")
            break

    return matched_element

def search_element_by_id(elements, target_id):
    """Find an element in `elements` with the given DOM id."""
    for element in elements:
        if element.get_attribute("id") == target_id:
            return element
    return None
