from argparse import ArgumentParser
import os
from pathlib import Path
import textwrap as tw
import time
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from dotenv import load_dotenv
from pathvalidate import sanitize_filename
import requests
from tqdm import tqdm

SITE_URL = "https://tululu.org"


def main():
    load_dotenv()
    arg_parser = ArgumentParser(
        description="This program allows to download some books from elibrary."
    )
    arg_parser.add_argument(
        "-s",
        "--start_id",
        help="Books start id. Must be greater than 0.",
        default=1,
        type=int
    )
    arg_parser.add_argument(
        "-e",
        "--end_id",
        help="Books end id. Must be greater than start id.",
        default=10,
        type=int
    )
    arg_parser.add_argument("--list",
                            action="store_true",
                            help="Use this flag if you want the list of books to be printed after download.")
    args = arg_parser.parse_args()
    if args.start_id > args.end_id:
        raise ValueError("End ID must be greater than start ID!")

    books_folder = os.getenv("BOOKS_PATH", "downloaded_books")
    images_folder = os.getenv("IMAGES_PATH", "downloaded_images")
    connection_timeout = os.getenv("CONNECTION_TIMEOUT", 120)

    downloaded_books = []
    for book_id in tqdm(range(args.start_id, args.end_id)):
        try:
            response = requests.get(f"{SITE_URL}/b{book_id}/")
            response.raise_for_status()
            raise_if_redirect(response)
            page_html = response.text
            page_url = response.url

            book = parse_book_page(page_html=page_html, page_url=page_url)
            downloaded_books.append(book)

            download_txt(f"{SITE_URL}/txt.php",
                         f"{book_id}. {book['title']}.txt",
                         books_folder,
                         params={"id": book_id})
            download_image(book["image_url"],
                           book["image_filename"],
                           images_folder)
        except RedirectDetectedError:
            # Метод write() используется чтобы прогресс-бар не ломался из-за вывода через print()
            tqdm.write(f"Book with ID={book_id} wasn't "
                       "downloaded because there is no page for this book.")
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

    print("Download finished.")
    if args.list:
        print("Books list: \n")
        for book in downloaded_books:
            book_str_repr = f"""
                        Название: {book["title"]}
                        Автор: {book["author"]}
                        Жанр: {book["genre"]}"""
            book_str_repr = tw.dedent(book_str_repr)
            print(book_str_repr)


def parse_book_page(page_html: str, page_url: str):
    """

     Function parses the HTML content of a book page
     from the Tululu website and extract relevant
     information such as book title, author, image URL,
     image filename, comments, and genre.
     The function returns a dictionary containing this information.

    :param page_html: HTML content of a book page
    :param page_url: page URL (required to find image_url)
    :return: dictionary containing book metadata
    """
    soup = BeautifulSoup(page_html, "lxml")

    book_title = soup.find("h1").get_text().split("::")[0].strip()
    book_title = sanitize_filename(book_title)
    book_author = soup.find("h1").find("a").get_text()
    book_author = sanitize_filename(book_author)

    _image_url = soup.find("div", {"class": "bookimage"}).find("a").find("img").get(
        "src")
    full_image_url = urljoin(page_url, _image_url)
    image_filename = os.path.split(_image_url)[1]

    _comments = soup.find("div", {"id": "content"}).find_all("div", {"class": "texts"})
    comments_texts = [comment.find("span").get_text() for comment in _comments]

    genre = soup.find("span", class_="d_book").find("a").get_text()

    book_metadata = {
        'title': book_title,
        'author': book_author,
        'image_url': full_image_url,
        'image_filename': image_filename,
        'comments_texts': comments_texts,
        'genre': genre
    }
    return book_metadata


def download_txt(url: str,
                 filename: str,
                 folder: str = "downloaded_texts",
                 params: dict = None) -> str:
    """

    This function downloads a txt file from a given URL
    and save it to a specified path on the local machine.

    :param url: the URL of the text file to be downloaded
    :param filename: name of the text file on your computer
    :param folder: path to a folder where the text file will be saved
    :param params: optional parameters to be passed in the request
    :return: the path of the saved text file
    """
    Path(folder).mkdir(parents=True, exist_ok=True)
    path = os.path.join(folder, filename)
    response = requests.get(url, params=params)
    response.raise_for_status()
    raise_if_redirect(response)

    with open(path, "wb+") as file:
        file.write(response.content)
    return path


def download_image(image_url: str,
                   filename: str,
                   folder: str = "downloaded_images") -> str:
    """

    This function downloads an image from a given URL
    and save it to a specified path on the local machine.

    :param image_url: the URL of the image to be downloaded
    :param filename: name of the image file on your computer
    :param folder: path to a folder where image will be saved
    :return: the path of the saved image file
    """
    Path(folder).mkdir(parents=True, exist_ok=True)
    path = os.path.join(folder, filename)

    response = requests.get(image_url)
    response.raise_for_status()
    binary_image = response.content

    with open(path, "bw+") as file:
        file.write(binary_image)
    return path


def raise_if_redirect(response: requests.Response) -> None:
    """

    Raises an HTTPError if the response contains a redirect

    :param response: a requests.Response object to be checked for redirects
    """
    if response.history:
        raise RedirectDetectedError


class RedirectDetectedError(requests.HTTPError):
    """

    Custom exception, that handles redirect responses
    from HTTP requests made with requests library.
    """
    def __init__(self, message: str = "Redirect detected!"):
        super().__init__(message)


if __name__ == "__main__":
    main()
