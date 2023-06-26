import os
from argparse import ArgumentParser
from urllib.parse import urljoin
from pathlib import Path
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import requests
from pathvalidate import sanitize_filename
from tqdm import tqdm

SITE_URL = "https://tululu.org"


def main():
    load_dotenv()
    arg_parser = ArgumentParser(
        description='This program allows to download some books from elibrary.'
    )
    arg_parser.add_argument(
        '-s',
        '--start_id',
        help="Books start id. Must be greater than 0.",
        default=1,
        type=int
    )
    arg_parser.add_argument(
        '-e',
        '--end_id',
        help="Books end id. Must be greater than start id.",
        default=10,
        type=int
    )
    args = arg_parser.parse_args()
    books_ids = args.start_id, args.end_id

    books_folder = os.getenv("BOOKS_PATH")
    images_folder = os.getenv("IMAGES_PATH")

    for book_id in tqdm(range(*books_ids)):
        try:
            response = requests.get(f"{SITE_URL}/b{book_id}")
            response.raise_for_status()
            raise_if_redirect(response)
            page_html = response.text

            book = ParsedBook(page_html=page_html)

            download_txt(f"{SITE_URL}/txt.php", f"{book_id}. {book.title}", books_folder, params={'id': book_id})
            download_image(book.image['url'], book.image['filename'], images_folder)
        except RedirectDetectedError:
            continue

    print("Done!")


class ParsedBook:
    def __init__(self, page_html):
        self.page_html = page_html

    @property
    def title(self):
        _book_title = BeautifulSoup(self.page_html, 'lxml').find('h1').get_text().split("::")[0].strip()
        return sanitize_filename(_book_title)

    @property
    def author(self):
        _book_author = BeautifulSoup(self.page_html, 'lxml').find('h1').find('a').get_text()
        return sanitize_filename(_book_author)

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


def download_txt(url: str, filename: str, folder: str = 'downloaded_texts', params: dict = None) -> str:
    Path(folder).mkdir(parents=True, exist_ok=True)
    path = os.path.join(folder, filename)
    response = requests.get(url, params=params)
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
