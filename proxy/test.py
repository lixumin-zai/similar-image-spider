from typing import List, Tuple
import requests

def test():
    url = "http://localhost:8000/proxy"
    response = requests.get(url)
    print(response.text)

if __name__ == "__main__":
    test()