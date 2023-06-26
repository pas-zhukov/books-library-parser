import os
from pathlib import Path
from bs4 import BeautifulSoup
import requests
from pathvalidate import sanitize_filename

PATH_TO_BOOKS = "books"


def main():

    for idx in range(1, 11):
        try:
            bookname = get_book_article(f"https://tululu.org/b{idx}/")[0]
            download_txt(f'https://tululu.org/txt.php?id={idx}', bookname + '.txt', 'books')
        except RedirectDetectedError:
            print(idx)
            continue


def get_book_article(url: str) -> tuple[str, str]:
    response = requests.get(url)
    response.raise_for_status()
    raise_if_redirect(response)
    html = response.text
    title = BeautifulSoup(html, 'lxml').find('h1').get_text().split("::")[0].strip()
    author = BeautifulSoup(html, 'lxml').find('h1').find('a').get_text()
    title, author = sanitize_filename(title), sanitize_filename(author)
    return title, author


def download_txt(url: str, filename: str, folder: str = 'downloaded_texts') -> str:
    Path(folder).mkdir(parents=True, exist_ok=True)
    path = os.path.join(folder, filename)
    print(path)
    response = requests.get(url)
    response.raise_for_status()
    raise_if_redirect(response)

    with open(path, "xb+") as file:
        file.write(response.content)
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
