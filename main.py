from argparse import ArgumentParser
import os
from pathlib import Path
import textwrap as tw
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
    arg_parser.add_argument('--list',
                            action='store_true',
                            help='Use this flag if you want the list of books to be printed after download.')
    args = arg_parser.parse_args()
    books_ids = args.start_id, args.end_id
    if books_ids[0] > books_ids[1]:
        raise ValueError("End ID must be greater than start ID!")

    books_folder = os.getenv("BOOKS_PATH", 'downloaded_books')
    images_folder = os.getenv("IMAGES_PATH", 'downloaded_images')

    downloaded_books = []
    for book_id in tqdm(range(*books_ids)):
        try:
            response = requests.get(f"{SITE_URL}/b{book_id}/")
            response.raise_for_status()
            raise_if_redirect(response)
            page_html = response.text

            book = ParsedBook(page_html=page_html)
            downloaded_books.append(book)

            download_txt(f"{SITE_URL}/txt.php",
                         f"{book_id}. {book.title}.txt",
                         books_folder,
                         params={'id': book_id})
            download_image(book.image['url'],
                           book.image['filename'],
                           images_folder)
        except RedirectDetectedError:
            continue

    print("Download complete!")
    if args.list:
        print("Books list: \n")
        for book in downloaded_books:
            print(book)


class ParsedBook:
    """

    The ParsedBook class is responsible for parsing the HTML page of a book
    from the Tululu website and extracting relevant information
    such as the book title, author, genre, image URL, and comments.
    It also provides a string representation of the book object.
    """
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
        comments_texts = [comment.find('span').get_text() for comment in _comments]
        return comments_texts

    @property
    def genre(self):
        genre = BeautifulSoup(self.page_html, 'lxml').find('span', class_="d_book").find('a').get_text()
        return genre

    def __str__(self):
        text = f"""
            Название: {self.title}
            Автор: {self.author}
            Жанр: {self.genre}"""
        text = tw.dedent(text)
        return text


def download_txt(url: str,
                 filename: str,
                 folder: str = 'downloaded_texts',
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
                   folder: str = 'downloaded_images') -> str:
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
