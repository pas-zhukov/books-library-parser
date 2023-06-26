import os
from pathlib import Path
from typing import Tuple, Any

from bs4 import BeautifulSoup
import requests
from pathvalidate import sanitize_filename
from urllib.parse import urljoin, urlsplit, unquote

SITE_URL = "https://tululu.org"


def main():

    for idx in range(1, 11):
        try:
            book = parse_book(f"https://tululu.org/b{idx}/")
            bookname = book[0]
            download_txt(f'https://tululu.org/txt.php?id={idx}', str(idx) + '. ' + bookname + '.txt', 'books')
            download_image(book[2], book[3], 'images')
        except RedirectDetectedError:
            print(idx)
            continue


def parse_book(url: str) -> tuple[str, str, str, Any]:
    response = requests.get(url)
    response.raise_for_status()
    raise_if_redirect(response)
    page_html = response.text

    book_title = BeautifulSoup(page_html, 'lxml').find('h1').get_text().split("::")[0].strip()
    book_author = BeautifulSoup(page_html, 'lxml').find('h1').find('a').get_text()
    book_title, book_author = sanitize_filename(book_title), sanitize_filename(book_author)

    image_url = BeautifulSoup(page_html, 'lxml').find('div', {'class': 'bookimage'}).find('a').find('img').get('src')
    full_image_url = urljoin(SITE_URL, image_url)

    filename = os.path.split(image_url)[1]

    return book_title, book_author, full_image_url, filename


def download_txt(url: str, filename: str, folder: str = 'downloaded_texts') -> str:
    Path(folder).mkdir(parents=True, exist_ok=True)
    path = os.path.join(folder, filename)
    response = requests.get(url)
    response.raise_for_status()
    raise_if_redirect(response)

    with open(path, "xb+") as file:
        file.write(response.content)
    return path


def download_image(image_url: str,
                   filename: str,
                   folder: str = 'downloaded_images'):
    """

    This function downloads an image from a given URL
    and save it to a specified path on the local machine.

    :param image_url: the URL of the image to be downloaded
    :param filename: name of the image file on your computer
    :param folder: path to a folder where image will be saved
    :return: None
    """
    Path(folder).mkdir(parents=True, exist_ok=True)
    path = os.path.join(folder, filename)

    response = requests.get(image_url)
    response.raise_for_status()
    binary_image = response.content

    with open(path, 'bw+') as file:
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
    def __init__(self, message: str = 'Redirect detected!'):
        super().__init__(message)


if __name__ == "__main__":
    main()
