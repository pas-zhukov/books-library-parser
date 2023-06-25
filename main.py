import requests

def download_txt(url: str, path: str):
    response = requests.get(url)
    response.raise_for_status()
    with open(path, "xb+") as file:
        file.write(response.content)


download_txt('https://tululu.org/txt.php?id=32168', 'book.txt')