# Download PDF from Pitch.com or Canva
Simple python script to download a presentation from Pitch.com or Canva as a searchable PDF. 

## Usage
Install the requirements and run the script via:
```bash
python main.py url [-r resolution] [--skip-ocr]
```

Valid resolutions are HD, 4K and 8K. Default resolution is 4K.

## Requirements
Base functionality requires Selenium + Chromedriver, Pillow and tqdm. If you want OCR you also need to install ocrmypdf and it's dependencies. If you prefer not to, run the script with the --skip-ocr flag.  