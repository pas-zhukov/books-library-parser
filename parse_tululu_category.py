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

from main import download_image, download_txt, parse_book_page
from main import SITE_URL, RedirectDetectedError, raise_if_redirect


def main():
    load_dotenv()
    args = parse_args()
    if args.start_page > args.end_page:
        raise PageNumberError("End page number must be greater than start number!")
    if args.start_page <= 0 or args.end_page <= 0:
        raise PageNumberError("Page numbers must be positive integers!")

    master_folder = args.dest_folder
    _books_folder = os.getenv("BOOKS_PATH", "downloaded_books")
    books_folder = os.path.join(master_folder, _books_folder)
    _images_folder = os.getenv("IMAGES_PATH", "downloaded_images")
    images_folder = os.path.join(master_folder, _images_folder)
    connection_timeout = os.getenv("CONNECTION_TIMEOUT", 120)

    book_links = parse_category(args.category_id,
                                args.start_page,
                                args.end_page,
                                connection_timeout)
    downloaded_books = []
    for book_link in tqdm(book_links, desc="Downloading books"):
        book_id = re.search(r"\d+", urlsplit(book_link).path).group()
        try:
            response = requests.get(book_link)
            response.raise_for_status()
            raise_if_redirect(response)
            page_html = response.text

            book = parse_book_page(page_html=page_html, page_url=book_link)
            if not args.skip_txt:
                book["book_path"] = download_txt(
                    f"{SITE_URL}/txt.php",
                    f"{book['title']}.txt",
                    books_folder,
                    params={"id": book_id}
                )
            if not args.skip_imgs:
                book["img_src"] = download_image(
                    book.pop("image_url"),
                    book.pop("image_filename"),
                    images_folder
                )
            downloaded_books.append(book)
        except RedirectDetectedError:
            # Метод write() используется чтобы прогресс-бар
            # не ломался из-за вывода через print()
            tqdm.write(f"Book with ID={book_id} wasn't "
                       "downloaded because there is no TXT for this book.")
        except requests.HTTPError:
            tqdm.write(f"Book with ID={book_id} wasn't "
                       "downloaded because URL used for "
                       "downloading this book "
                       "is wrong or incorrect.")
        except requests.ConnectionError:
            tqdm.write(f"Book with ID={book_id} wasn't "
                       "downloaded because of Connection error. "
                       f"Waiting {connection_timeout} seconds for "
                       "internet connection to restore.")
            time.sleep(connection_timeout)
    with open(os.path.join(master_folder, "books_metadata.json"),
              "w+",
              encoding="utf-8") as file:
        json.dump(downloaded_books, file, ensure_ascii=False)


def parse_category(category_id: int,
                   start_page: int = 1,
                   end_page: int = None,
                   connection_timeout: int = 60) -> list:
    """
    Parses the book links from a given category on the Tululu website.

    :param category_id: ID of the category to download
    :param start_page: page number from which to begin downloading
    :param end_page: end page where to stop
    :param connection_timeout: time to wait before next request if connection is lost
    :return: A list of book links
    """
    book_links = []
    for page_index in trange(start_page,
                             end_page + 1,
                             desc=f"Downloading books links from "
                                  f"category with ID={category_id}"):
        category_url = f"{SITE_URL}/l{category_id}/{page_index}/"

        try:
            response = requests.get(category_url)
            response.raise_for_status()
            raise_if_redirect(response)
            page_html = response.text

            soup = BeautifulSoup(page_html, "lxml")
            selector = "div[id='content'] table.d_book"
            books = soup.select(selector)
            for book in books:
                url_selector = "a"
                book_url = book.select_one(url_selector).get("href")
                book_full_url = urljoin(category_url, book_url)
                book_links.append(book_full_url)
        except RedirectDetectedError:
            tqdm.write(f"Unable to download links from page №{page_index}. "
                       f"Probably out of pages count."
                       f" Check the amount of pages per chosen category.")
            break
        except requests.HTTPError:
            tqdm.write(f"Unable to download links from page {page_index}. "
                       f"Wrong URL. Check the category ID.")
        except requests.ConnectionError:
            tqdm.write(f"Connection Error! "
                       f"Links from page {page_index} won't be downloaded."
                       f"Please check your internet connection.")
            time.sleep(connection_timeout)
    return book_links


def parse_args():
    """
    Parse the command-line arguments provided
    by the user and returning them as an object.

    :return: object containing the parsed arguments as attributes
    """
    arg_parser = ArgumentParser(
        description="This program allows to download "
                    "some books from tululu specified by genre."
    )
    arg_parser.add_argument(
        "-s",
        "--start_page",
        help="Page number from which to "
             "begin downloading books (in category).",
        default=1,
        type=int
    )
    arg_parser.add_argument(
        "-e",
        "--end_page",
        help="End page where to stop.",
        default=1000,
        type=int
    )
    arg_parser.add_argument(
        "-cat",
        "--category_id",
        help="ID of the category to download.",
        default=55,
        type=int
    )
    arg_parser.add_argument(
        "-d",
        "--dest_folder",
        help="Name for the folder, where you want to store downloaded data.",
        default="",
        type=str
    )
    arg_parser.add_argument("--skip_imgs",
                            action="store_true",
                            help="Discard downloading book covers.",
                            default=False)
    arg_parser.add_argument("--skip_txt",
                            action="store_true",
                            help="Discard downloading book texts.",
                            default=False)
    args = arg_parser.parse_args()
    return args


class PageNumberError(ValueError):
    """Custom exception, that handles wrong page numbers."""
    def __init__(self, message: str = "Wrong page number!"):
        super().__init__(message)


if __name__ == "__main__":
    main()
