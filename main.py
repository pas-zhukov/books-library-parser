import requests
from pathlib import Path

PATH_TO_BOOKS = "books"


def download_txt(url: str, path: str):
    response = requests.get(url)
    response.raise_for_status()
    check_for_redirect(response)
    with open(path, "xb+") as file:
        file.write(response.content)


def check_for_redirect(response: requests.Response):
    if response.history:
        raise requests.HTTPError
    else:
        return True


def main():
    Path("books").mkdir(parents=True, exist_ok=True)
    for idx in range(1, 11):
        try:
            download_txt(f'https://tululu.org/txt.php?id={idx}', f'books/book_id{idx}.txt')
        except requests.HTTPError:
            continue


if __name__ == "__main__":
    main()
