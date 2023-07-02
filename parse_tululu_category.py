import os
import re
import time
import json
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup
import requests
from tqdm import tqdm, trange

from main import download_image, download_txt, parse_book_page, raise_if_redirect, SITE_URL, RedirectDetectedError

CATEGORY_ID = 55


def main():
    books_folder = os.getenv("BOOKS_PATH", "downloaded_books")
    images_folder = os.getenv("IMAGES_PATH", "downloaded_images")
    connection_timeout = os.getenv("CONNECTION_TIMEOUT", 120)

    try:
        book_links = parse_category(CATEGORY_ID, 2)
        downloaded_books = []
        for book_link in tqdm(book_links, desc='Downloading books'):
            book_id = re.search(r'\d+', urlsplit(book_link).path).group()
            try:
                response = requests.get(book_link)
                response.raise_for_status()
                raise_if_redirect(response)
                page_html = response.text

                book = parse_book_page(page_html=page_html, page_url=book_link)
                book['book_path'] = download_txt(f"{SITE_URL}/txt.php",
                                                 f"{book['title']}.txt",
                                                 books_folder,
                                                 params={'id': book_id})
                book['img_src'] = download_image(book.pop("image_url"),
                                                 book.pop("image_filename"),
                                                 images_folder)
                downloaded_books.append(book)
            except RedirectDetectedError:
                # Метод write() используется чтобы прогресс-бар не ломался из-за вывода через print()
                tqdm.write(f"Book with ID={book_id} wasn't "
                           "downloaded because there is no TXT for this book.")
            except requests.HTTPError:
                tqdm.write(f"Book with ID={book_id} wasn't "
                           "downloaded because URL used for downloading this book "
                           "is wrong or incorrect.")
            except requests.ConnectionError:
                tqdm.write(f"Book with ID={book_id} wasn't "
                           "downloaded because of Connection error. "
                           f"Waiting {connection_timeout} seconds for "
                           "internet connection to restore.")
                time.sleep(connection_timeout)
        downloaded_books = json.dumps(downloaded_books, ensure_ascii=False)
        with open("books_metadata.json", 'w+', encoding='utf-8') as file:
            file.write(downloaded_books)
    except RedirectDetectedError:
        tqdm.write(f"Unable to download links. Probably out of pages count."
                   f" Check the amount of pages per chosen category.")
    except requests.HTTPError:
        tqdm.write(f"Unable to download links. Wrong URL. Check the category ID.")
    except requests.ConnectionError:
        tqdm.write(f"Connection Error! Please check your internet connection.")


def parse_category(category_id: int, pages_count: int = 200) -> list:
    book_links = []
    for page_index in trange(1, pages_count, desc=f'Downloading books links from category with ID={category_id}'):
        category_url = f"{SITE_URL}/l{category_id}/{page_index}/"

        response = requests.get(category_url)
        response.raise_for_status()
        raise_if_redirect(response)
        page_html = response.text

        soup = BeautifulSoup(page_html, 'lxml')
        books = soup.find('div', {'id': 'content'}).find_all('table', class_='d_book')
        for book in books:
            book_url = book.find('a').get('href')
            book_full_url = urljoin(category_url, book_url)
            book_links.append(book_full_url)
    return book_links


if __name__ == '__main__':
    main()
