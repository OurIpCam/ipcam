"""
---MUST HAVE DOWNLOADED---

# install tensorflow
!pip install tensorflow tensorflow-gpu opencv-python matplotlib

# easily search for images and download them
!pip install google_images_download

# library for image scraping that allows you to implement various strategies to avoid being blocked
!pip install icrawler
"""

import time
from google_images_download import google_images_download
from icrawler.builtin import GoogleImageCrawler
import os
import warnings
warnings.filterwarnings('ignore')

def download_images(keyword:str, limit:int, output_dir:str):
    google_crawler = GoogleImageCrawler(
        downloader_threads=4,  # Number of downloader threads (adjust as needed)
        storage={'root_dir': output_dir}
    )

    filters = dict(type='photo')  # Specify filters as needed

    google_crawler.crawl(
        keyword=keyword,
        filters=filters,
        max_num=limit,
        file_idx_offset=0,
        min_size=(200, 200),  # Minimum image size (adjust as needed)
        max_size=None  # Maximum image size (adjust as needed)
    )
    
if __name__ == "__main__":
    search_keywords = ["bicycle", "motorcycle"]
    image_limit = 100  # Set the number of images you want to download for each keyword

    for keyword in search_keywords:
        output_directory = f"../data/{keyword}"  
        download_images(keyword, image_limit, output_directory)
        time.sleep(10)  # Add a delay between keyword searches to avoid being blocked
