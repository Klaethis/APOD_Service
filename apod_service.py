import flask
import requests
import cachetools
from bs4 import BeautifulSoup
import os
import json

app = flask.Flask(__name__)

API_KEY = os.environ.get('API_KEY', 'DEMO_KEY')
CACHE_TIMEOUT = int(os.environ.get('CACHE_TIMEOUT', 24*60*60))
SERVICE_PORT = int(os.environ.get('SERVICE_PORT', 5000))

if os.path.exists('config.json'):
    with open('config.json', 'r') as f:
        config = json.load(f)
        if config is not None:
            API_KEY = config.get('api_key', API_KEY)
            CACHE_TIMEOUT = config.get('cache_timeout', CACHE_TIMEOUT)
            SERVICE_PORT = config.get('service_port', SERVICE_PORT)

def get_nasa_apod():
    url = f'https://api.nasa.gov/planetary/apod?api_key={API_KEY}'
    apod_info = requests.get(url).json()
    return apod_info

class APODCache:
    def __init__(self):
        self.cache = cachetools.TTLCache(maxsize=1, ttl=CACHE_TIMEOUT)
        
    def get_apod_info(self):
        apod_info = self.cache.get('apod')
        
        if apod_info is None:
            apod_info = get_nasa_apod()
            self.cache.update(apod=apod_info)
        
        return apod_info

    def clear(self):
        self.cache.clear()

apod_cache = APODCache()

@app.route('/', methods=['GET'])
def index():
    with open('Pages/index.html', 'r') as f:
        page_html = f.read()
    page = BeautifulSoup(page_html, 'html.parser')
    api_key_container = page.find('div', {'id': 'api_key_container'})
    api_key_box = api_key_container.find('input', {'id': 'api_key'})
    api_key_box['value'] = API_KEY
    cache_timeout_container = page.find('div', {'id': 'cache_timeout_container'})
    cache_timeout_box = cache_timeout_container.find('input', {'id': 'cache_timeout'})
    cache_timeout_box['value'] = str(CACHE_TIMEOUT)
    service_port_container = page.find('div', {'id': 'service_port_container'})
    service_port_box = service_port_container.find('input', {'id': 'service_port'})
    service_port_box['value'] = str(SERVICE_PORT)
    return str(page)

@app.route('/info', methods=['GET'])
def info():
    apod_info = apod_cache.get_apod_info()
    return apod_info, 200, {'Content-Type': 'application/json'}

@app.route('/image', methods=['GET'])
def image():
    apod_info = apod_cache.get_apod_info()
    image_url = apod_info.get('url')
    
    if image_url is None:
        return 'No image found', 400
    
    image_content = requests.get(image_url).content
    return image_content, 200, {'Content-Type': 'image/jpeg'}

@app.route('/favicon.ico')
def favicon():
    image_path = './images/favicon.ico'
    return flask.send_file(image_path)

@app.route('/clear', methods=['GET'])
def clear():
    apod_cache.clear()
    return 'Cleared cache', 200

@app.route('/submit', methods=['POST'])
def submit():
    api_key = flask.request.json.get('api_key')
    cache_timeout = flask.request.json.get('cache_timeout')
    service_port = flask.request.json.get('service_port')
    
    if api_key is not None:
        API_KEY = api_key
    if cache_timeout is not None:
        CACHE_TIMEOUT = int(cache_timeout)
    if service_port is not None:
        SERVICE_PORT = int(service_port)
    
    config = {
        'api_key': API_KEY,
        'cache_timeout': CACHE_TIMEOUT,
        'service_port': SERVICE_PORT
    }
    
    with open('config.json', 'w') as f:
        json.dump(config, f)

    return 'Config saved', 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=SERVICE_PORT)