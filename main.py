import os
from pathlib import Path
from typing import Tuple, Any, List

from bs4 import BeautifulSoup
import requests
from pathvalidate import sanitize_filename
from urllib.parse import urljoin, urlsplit, unquote

SITE_URL = "https://tululu.org"


def main():

    for idx in range(1, 11):
        try:
            book = parse_book_page(f"https://tululu.org/b{idx}/")
            bookname = book[0]
            download_txt(f'https://tululu.org/txt.php?id={idx}', str(idx) + '. ' + bookname + '.txt', 'books')
            download_image(book[2], book[3], 'images')
            print(book)
        except RedirectDetectedError:
            print(idx)
            continue


class ParseBookPage:
    def __init__(self, page_html):
        self.page_html = page_html

    @property
    def book_title(self):
        book_title = BeautifulSoup(self.page_html, 'lxml').find('h1').get_text().split("::")[0].strip()
        return sanitize_filename(book_title)

    @property
    def book_author(self):
        book_author = BeautifulSoup(self.page_html, 'lxml').find('h1').find('a').get_text()
        return sanitize_filename(book_author)

    @property
    def image(self):
        _image_url = BeautifulSoup(self.page_html, 'lxml').find('div', {'class': 'bookimage'}).find('a').find('img').get(
            'src')
        full_image_url = urljoin(SITE_URL, _image_url)
        image_filename = os.path.split(_image_url)[1]
        return {
            'url': full_image_url,
            'filename': image_filename
        }

    @property
    def comments(self):
        _comments = BeautifulSoup(self.page_html, 'lxml').find('div', {'id': 'content'}).find_all('div', {'class': 'texts'})
        comments_texts = []
        for comment in _comments:
            comments_texts.append(comment.find('span').get_text())
        return comments_texts

    @property
    def genre(self):
        genre = BeautifulSoup(self.page_html, 'lxml').find('span', class_="d_book").find('a').get_text()
        return genre


def parse_book_page(page_html: str):
    book_title = BeautifulSoup(page_html, 'lxml').find('h1').get_text().split("::")[0].strip()
    book_author = BeautifulSoup(page_html, 'lxml').find('h1').find('a').get_text()
    book_title, book_author = sanitize_filename(book_title), sanitize_filename(book_author)

    image_url = BeautifulSoup(page_html, 'lxml').find('div', {'class': 'bookimage'}).find('a').find('img').get('src')
    full_image_url = urljoin(SITE_URL, image_url)

    image_filename = os.path.split(image_url)[1]

    comments = BeautifulSoup(page_html, 'lxml').find('div', {'id': 'content'}).find_all('div', {'class': 'texts'})
    comments_texts = []
    for comment in comments:
        comments_texts.append(comment.find('span').get_text())

    genre = BeautifulSoup(page_html, 'lxml').find('span', class_="d_book").find('a').get_text()

    return book_title, book_author, full_image_url, image_filename, comments_texts, genre


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
