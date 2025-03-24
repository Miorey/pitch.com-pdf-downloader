from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from PIL import Image, ImageChops
from io import BytesIO

from tqdm import tqdm
import time

from utils import sources
from enum import Enum


# Helper: Loading from memory and converting RGBA to RGB
def _rgba_to_rgb(png):
    img = Image.open(BytesIO(png))
    img.load()
    background = Image.new('RGB', img.size, (255, 255, 255))

    if img.mode == 'RGBA':
        background.paste(img, mask=img.split()[3])
    else:
        background.paste(img)
    return background


def _crop_black_borders(png):
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


def get_chrome_driver(resolution: ResolutionEnum, disable_headless: bool = False) -> webdriver.Chrome:
    chrome_options = Options()

    if not disable_headless:
        chrome_options.add_argument('--headless')

    # Setting resolution
    if resolution == ResolutionEnum.RES_HD:
        res = 'window-size=1920,1080'
    elif resolution == ResolutionEnum.RES_4K:
        res = 'window-size=3840,2160'
    elif resolution == ResolutionEnum.RES_8K:
        res = 'window-size=7680,4320'
    else:
        raise Exception('Only HD, 4K and 8K resolutions allowed!')

    chrome_options.add_argument('--log-level=3')
    chrome_options.add_argument(res)

    # Adding argument to disable the AutomationControlled flag
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")

    # Exclude the collection of enable-automation switches
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])

    # Turn-off userAutomationExtension
    chrome_options.add_experimental_option("useAutomationExtension", False)

    # Initializing the driver
    driver = webdriver.Chrome(options=chrome_options)

    # Changing the property of the navigator value for webdriver to undefined
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    return driver


def scrape_slides(driver: webdriver.Chrome, n_slides, next_btn, slide_selector, pitch_dot_com=False,
                  skip_border_removal=False):
    """
    Takes a screenshot of all slides and returns a list of pngs

    n_slides: int, the number of slides
    next_btn: clickable element on website to go to the next slide
    slide_selector: arguments to driver.find_element to locate the slide e.g. (By.XPATH, xpath_string)
    """

    png_slides = []
    for n in tqdm(range(n_slides)):

        # Animations in pitch.com ...
        if pitch_dot_com:
            while not sources.pitch_at_slide_end(driver):
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


def download(driver: webdriver.Chrome, url: str, skip_border_removal: bool) -> str:
    """
    Given a URL, loops over slides to screenshot them and saves a PDF
    """
    url = url.lower()
    driver.get(url)
    time.sleep(10)

    pitch = False
    if 'pitch.com' in url:
        params = sources.get_pitch_params(driver)
        pitch = True
    elif 'canva.com' in url:
        params = sources.get_canva_params(driver)
    elif 'docs.google.com/presentation/' in url:
        params = sources.get_gslides_params(driver)
    elif 'figma.com/deck' in url:
        params = sources.get_figma_params(driver)
    else:
        raise Exception('URL not supported...')

    png_slides = scrape_slides(
        driver,
        params['n_slides'], params['next_btn'], params['slide_selector'],
        skip_border_removal=skip_border_removal,
        pitch_dot_com=pitch
    )

    # Saving the screenshots as a PDF using Pillow
    print('\nConverting RGBA to RGB...')
    images = [_rgba_to_rgb(png) for png in tqdm(png_slides)]
    print('Conversion finished!')

    title = ''.join([char for char in driver.title if char.isalpha()])

    output_path = 'decks/' + title + '.pdf'

    print('\nSaving deck as "' + output_path + '"...')
    images[0].save(
        output_path, "PDF", resolution=100.0, save_all=True, append_images=images[1:]
    )
    print('Deck saved!')

    driver.close()

    return output_path
