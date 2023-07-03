from argparse import ArgumentParser
import os
import re
import time
import json
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup
from dotenv import load_dotenv
import requests
from tqdm import tqdm, trange

from main import download_image, download_txt, parse_book_page, raise_if_redirect, SITE_URL, RedirectDetectedError

CATEGORY_ID = 55


def main():
    load_dotenv()
    arg_parser = ArgumentParser(
        description="This program allows to download some books from tululu specified by genre."
    )
    arg_parser.add_argument(
        "-s",
        "--start_page",
        help="Page number from which to begin downloading books (in category).",
        default=1,
        type=int
    )
    arg_parser.add_argument(
        "-e",
        "--end_page",
        help="End page where to stop.",
        default=None,
        type=int
    )
    args = arg_parser.parse_args()
    if args.end_page is not None and args.start_page > args.end_page:
        raise ValueError("End page number must be greater than start number!")

    books_folder = os.getenv("BOOKS_PATH", "downloaded_books")
    images_folder = os.getenv("IMAGES_PATH", "downloaded_images")
    connection_timeout = os.getenv("CONNECTION_TIMEOUT", 120)

    try:
        book_links = parse_category(CATEGORY_ID, args.start_page, args.end_page)
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


def parse_category(category_id: int, start_page: int = 1, end_page: int = None) -> list:
    book_links = []
    if not end_page:
        end_page = get_pages_count(f"{SITE_URL}/l{category_id}/1/")
    for page_index in trange(start_page, end_page, desc=f'Downloading books links from category with ID={category_id}'):
        category_url = f"{SITE_URL}/l{category_id}/{page_index}/"

        response = requests.get(category_url)
        response.raise_for_status()
        raise_if_redirect(response)
        page_html = response.text

        soup = BeautifulSoup(page_html, 'lxml')
        selector = 'div[id="content"] table.d_book'
        books = soup.select(selector)
        for book in books:
            url_selector = 'a'
            book_url = book.select_one(url_selector).get('href')
            book_full_url = urljoin(category_url, book_url)
            book_links.append(book_full_url)
    print(book_links)
    return book_links


def get_pages_count(category_page_url: str) -> int:
    response = requests.get(category_page_url)
    response.raise_for_status()
    raise_if_redirect(response)
    category_page = response.text
    soup = BeautifulSoup(category_page, 'lxml')
    selector = 'a.npage:nth-child(7)'
    _pages_count = soup.select_one(selector)
    pages_count = int(_pages_count.get_text())
    return pages_count


if __name__ == '__main__':
    main()
