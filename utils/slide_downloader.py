import tempfile
import time
from enum import Enum
from io import BytesIO

from PIL import Image
from PIL import ImageChops
from selenium import webdriver
from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By


class SlideDownloaderException(Exception):
    pass


# Helper: Loading from memory and converting RGBA to RGB
def _rgba_to_rgb(png: bytes):
    img = Image.open(BytesIO(png))
    img.load()
    background = Image.new("RGB", img.size, (255, 255, 255))

    if img.mode == "RGBA":
        background.paste(img, mask=img.split()[3])
    else:
        background.paste(img)
    return background


def _crop_black_borders(png: bytes):
    """
    Crops black borders from a PNG image.
    """
    img = Image.open(BytesIO(png)).convert("RGB")
    bg = Image.new("RGB", img.size, (0, 0, 0))  # Black background for comparison
    diff = ImageChops.difference(img, bg)
    diff = ImageChops.add(diff, diff, 2.0, -100)
    bbox = diff.getbbox()
    if bbox:
        return img.crop(bbox)
    return img


class ResolutionEnum(Enum):
    RES_HD = "HD"
    RES_4K = "4K"
    RES_8K = "8K"


def get_chrome_driver(
        resolution: ResolutionEnum, disable_headless: bool = False
) -> webdriver.Chrome:
    chrome_options = Options()

    if not disable_headless:
        chrome_options.add_argument("--headless")

    # Setting resolution
    if resolution == ResolutionEnum.RES_HD:
        res = "window-size=1920,1080"
    elif resolution == ResolutionEnum.RES_4K:
        res = "window-size=3840,2160"
    elif resolution == ResolutionEnum.RES_8K:
        res = "window-size=7680,4320"
    else:
        raise SlideDownloaderException("Only HD, 4K and 8K resolutions allowed!")

    chrome_options.add_argument("--log-level=3")
    chrome_options.add_argument(res)

    # Adding argument to disable the AutomationControlled flag
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")

    # Exclude the collection of enable-automation switches
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])

    # Turn-off userAutomationExtension
    chrome_options.add_experimental_option("useAutomationExtension", False)

    # Ensure a unique user data directory
    user_data_dir = tempfile.mkdtemp()
    chrome_options.add_argument(f"--user-data-dir={user_data_dir}")

    # Initializing the driver
    driver = webdriver.Chrome(options=chrome_options)

    # Changing the property of the navigator value for webdriver to undefined
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )

    return driver


def scrape_slides(
        driver: webdriver.Chrome,
        n_slides: int,
        next_btn,
        slide_selector,
        pitch_dot_com=False,
        skip_border_removal=False,
) -> list[bytes]:
    """
    Takes a screenshot of all slides and returns a list of pngs

    n_slides: int, the number of slides
    next_btn: clickable element on website to go to the next slide
    slide_selector: arguments to driver.find_element to locate the slide e.g. (By.XPATH, xpath_string)
    """

    png_slides = []
    for n in range(n_slides):

        # Animations in pitch.com ...
        if pitch_dot_com:
            while not pitch_at_slide_end(driver):
                driver.execute_script("arguments[0].click();", next_btn)
                time.sleep(1.5)

        slide = driver.find_element(*slide_selector)
        png = slide.screenshot_as_png

        if not skip_border_removal:
            # Crop the screenshot to remove black borders
            cropped_img = _crop_black_borders(png)
            buffer = BytesIO()
            cropped_img.save(buffer, format="PNG")
            png_slides.append(buffer.getvalue())
        else:
            png_slides.append(png)

        if n < n_slides - 1:
            # Use JS in case it's hidden
            driver.execute_script("arguments[0].click();", next_btn)
            time.sleep(1.5)

    return png_slides


def download(
        driver: webdriver.Chrome, url: str, skip_border_removal: bool = False
) -> BytesIO:
    """
    Given a URL, loops over slides to screenshot them and saves a PDF
    """
    url = url.lower()
    driver.get(url)
    time.sleep(10)

    pitch = False
    if "pitch.com" in url:
        params = get_pitch_params(driver)
        pitch = True
    elif "docs.google.com/presentation/" in url:
        params = get_gslides_params(driver)
    elif "figma.com/deck" in url:
        params = get_figma_params(driver)
    else:
        raise SlideDownloaderException("URL not supported...")

    png_slides = scrape_slides(
        driver,
        params["n_slides"],
        params["next_btn"],
        params["slide_selector"],
        skip_border_removal=skip_border_removal,
        pitch_dot_com=pitch,
    )

    # Saving the screenshots as a PDF using Pillow
    images = [_rgba_to_rgb(png) for png in png_slides]

    byte_array = BytesIO()
    images[0].save(
        byte_array, "PDF", resolution=100.0, save_all=True, append_images=images[1:]
    )

    return byte_array


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
    driver.execute_script(
        "document.getElementsByClassName('player-branding-popover')[0].remove();"
    )

    n_slides = len(driver.find_elements(By.CLASS_NAME, "dash"))

    # Named differently at times?
    btns = driver.find_elements(By.CLASS_NAME, "ng-player-v2--button")
    if len(btns) == 0:
        btns = driver.find_elements(By.CLASS_NAME, "player-v2--button")
    next_btn = btns[1]

    params = dict(
        n_slides=n_slides,
        next_btn=next_btn,
        slide_selector=(By.CLASS_NAME, "slide-wrapper"),
    )

    return params


# Check if we're at the end of the current slide (gradually adding elements)
def pitch_at_slide_end(driver: Chrome):
    current_dash = driver.find_element(
        By.CSS_SELECTOR, ".dash.selected [aria-valuenow]"
    )

    aria_valuenow = current_dash.get_attribute("aria-valuenow")

    return aria_valuenow == "100"


def get_gslides_params(driver: Chrome):
    """
    Preprocesses Google Slides and returns params to find all slides
    """

    content = driver.find_element(By.CLASS_NAME, "punch-viewer-container")

    n_slides_button = driver.find_elements(By.CSS_SELECTOR, "[aria-setsize]")[0]
    n_slides = n_slides_button.get_attribute("aria-setsize")

    return dict(
        n_slides=int(n_slides),
        next_btn=content,
        slide_selector=(By.CLASS_NAME, "punch-viewer-svgpage-svgcontainer"),
    )


def get_figma_params(driver: Chrome):
    """
    Preprocesses Figma presentation and returns params to find all slides
    """

    # Removing the header so it doesn't show up on slides
    header = driver.find_elements(By.CSS_SELECTOR, '[aria-label="Prototype controls"]')
    if header:
        driver.execute_script(
            """
            var element = arguments[0];
            element.parentNode.removeChild(element);
        """,
            header[0],
        )

    next_btn = driver.find_elements(By.CSS_SELECTOR, '[aria-label="Next frame"]')[0]

    slide_no_text = driver.find_elements(By.CSS_SELECTOR, '[role="status"]')[
        0
    ].get_attribute("innerText")
    print(slide_no_text)
    n_slides = slide_no_text.split("/")[1].strip()

    return dict(
        n_slides=int(n_slides),
        next_btn=next_btn,
        slide_selector=(By.TAG_NAME, "canvas"),
    )
