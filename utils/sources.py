from selenium.webdriver.common.by import By
from selenium.webdriver import Chrome
import time


def get_pitch_params(driver: Chrome):
    """
    Preprocesses Pitch.com and returns params to find all slides
    """

    # Cookie accept - do not accept tracking
    btn = driver.find_elements(By.XPATH, '//button[@type="text"]')
    if len(btn) > 0:
        btn = btn[0]
        btn.click()
        time.sleep(1)
        no_tracking = driver.find_elements(By.XPATH, '//input[@name="engagement"]')[0]
        no_tracking.click()
        time.sleep(1)
        confirm = driver.find_elements(By.XPATH, '//button[@type="submit"]')[0]
        confirm.click()
        time.sleep(1)

    # Deleting the popup shown at the end of the presentation
    try:
        driver.execute_script("document.getElementsByClassName('player-branding-popover')[0].remove();")
    except Exception:
        print('Could not remove branding popover...')

    n_slides = len(driver.find_elements(By.CLASS_NAME, 'dash'))

    # Named differently at times?
    btns = driver.find_elements(By.CLASS_NAME, 'ng-player-v2--button')
    if len(btns) == 0:
        btns = driver.find_elements(By.CLASS_NAME, 'player-v2--button')
    next_btn = btns[1]

    params = dict(
        n_slides=n_slides,
        next_btn=next_btn,
        slide_selector=(By.CLASS_NAME, 'slide-wrapper')
    )

    return params


# Check if we're at the end of the current slide (gradually adding elements)
def pitch_at_slide_end(driver: Chrome):
    current_dash = driver.find_element(By.CSS_SELECTOR, '.dash.selected [aria-valuenow]')

    aria_valuenow = current_dash.get_attribute('aria-valuenow')

    return aria_valuenow == '100'


def get_gslides_params(driver: Chrome):
    """
    Preprocesses Google Slides and returns params to find all slides
    """

    content = driver.find_element(By.CLASS_NAME, 'punch-viewer-container')

    n_slides_button = driver.find_elements(By.CSS_SELECTOR, "[aria-setsize]")[0]
    n_slides = n_slides_button.get_attribute('aria-setsize')

    return dict(
        n_slides=int(n_slides),
        next_btn=content,
        slide_selector=(By.CLASS_NAME, 'punch-viewer-svgpage-svgcontainer')
    )


def get_figma_params(driver: Chrome):
    """
    Preprocesses Figma presentation and returns params to find all slides
    """

    # Removing the header so it doesn't show up on slides
    header = driver.find_elements(By.CSS_SELECTOR, '[aria-label="Prototype controls"]')
    if header:
        driver.execute_script("""
            var element = arguments[0];
            element.parentNode.removeChild(element);
        """, header[0])

    next_btn = driver.find_elements(By.CSS_SELECTOR, '[aria-label="Next frame"]')[0]

    slide_no_text = driver.find_elements(By.CSS_SELECTOR, '[role="status"]')[0].get_attribute('innerText')
    print(slide_no_text)
    n_slides = slide_no_text.split('/')[1].strip()

    return dict(
        n_slides=int(n_slides),
        next_btn=next_btn,
        slide_selector=(By.TAG_NAME, 'canvas')

    )
