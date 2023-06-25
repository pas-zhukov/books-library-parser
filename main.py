import requests
from pathlib import Path

def download_txt(url: str, path: str):
    response = requests.get(url)
    response.raise_for_status()
    with open(path, "xb+") as file:
        file.write(response.content)


Path("books").mkdir(parents=True, exist_ok=True)
for i in range(1,11):
    download_txt(f'https://tululu.org/txt.php?id={i}', f'books/book_id{i}.txt')