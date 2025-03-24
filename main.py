import argparse
from utils.slide_downloader import ResolutionEnum, get_chrome_driver, download

if __name__ == '__main__':
    # Parsing input args
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'url',
        help='The url to download the slides from'
    )
    parser.add_argument(
        '-r',
        '--resolution',
        help='The slide resolution, HD, 4K or 8K allowed',
        default='4K'
    )
    parser.add_argument(
        '--disable-headless',
        action='store_true',
        dest='disable_headless',
        help='Disable headless mode')
    parser.add_argument(
        '--skip-border-removal',
        action='store_true',
        dest='skip_border_removal',
        help='Disable removing black borders if present'
    )
    args = parser.parse_args()

    # Saving the presentation as a PDF
    resolution = ResolutionEnum(args.resolution)
    chrome_driver = get_chrome_driver(resolution, args.disable_headless)
    download(chrome_driver, args.url, args.skip_border_removal)
