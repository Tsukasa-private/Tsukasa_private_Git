import urllib
import urllib3
from urllib import request
import requests
import json

url = 'https://api.flickr.com/services/rest/'
API_KEY = '74606b1d39d56ed1db1bfa6445b84197'
SECRET_KEY = '4028d6921f2e38ac'

query = {
        'method': 'flickr.photos.search',
        'api_key': API_KEY,
        'text': 'sky',  #検索ワード
        'per_page': '5',  #1ページ辺りのデータ数
        'format': 'json',
        'nojsoncallback': '1'
        }

r = requests.get(url, params=query)

print (r)
print (json.dumps(r.json(), sort_keys=True, indent=2))    
