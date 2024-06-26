from flask import Flask, request, send_file, redirect, url_for, session
from flask_oidc import OpenIDConnect
from bs4 import BeautifulSoup
import cachetools
import requests
import hashlib
import json
import os

API_KEY = os.environ.get('API_KEY', 'DEMO_KEY')
CACHE_TIMEOUT = int(os.environ.get('CACHE_TIMEOUT', 24*60*60))

APP_CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'Config/config.json')
OIDC_SECRETS_PATH = os.path.join(os.path.dirname(__file__), 'Config/client_secrets.json')
OIDC_BASE_URL = os.environ.get('OIDC_BASE_URL', 'https://localhost:5000')

if os.path.exists(OIDC_SECRETS_PATH):
    OIDC_CLIENT_SECRETS = json.load(open(OIDC_SECRETS_PATH, 'r'))
else:
    OIDC_CLIENT_SECRETS = {
        "web": {
            'issuer': os.environ.get('OIDC_ISSUER'),
            'client_id': os.environ.get('OIDC_CLIENT_ID'),
            'client_secret': os.environ.get('OIDC_CLIENT_SECRET'),
        }
    }
    

app = Flask(__name__)
app.config.update({
    'SECRET_KEY': os.environ.get('SECRET_KEY', os.urandom(24)),
    'OIDC_CLIENT_SECRETS': OIDC_CLIENT_SECRETS,
    'OIDC_SCOPES': ['openid', 'profile', 'email'],
    'OIDC_ID_TOKEN_COOKIE_SECURE': True,
    'OIDC_COOKIES_SECURE': True,
    'OIDC_BASE_URL': OIDC_BASE_URL,
    'OIDC_SCHEME': 'https',
    'OVERWRITE_REDIRECT_URI': os.environ.get('OIDC_REDIRECT_URI', 'http://localhost:5000/authorize'),
})

oidc = OpenIDConnect(app)

if os.path.exists(APP_CONFIG_PATH):
    with open(APP_CONFIG_PATH, 'r') as f:
        config = json.load(f)
        if config is not None:
            API_KEY = config.get('api_key', API_KEY)
            CACHE_TIMEOUT = config.get('cache_timeout', CACHE_TIMEOUT)

def get_gravatar_url(email, size=80, default='identicon', rating='g'):
    hash = hashlib.md5(email.lower().encode('utf-8')).hexdigest()
    return f'https://secure.gravatar.com/avatar/{hash}?s={size}&d={default}&r={rating}'

def get_nasa_apod():
    url = f'https://api.nasa.gov/planetary/apod?api_key={API_KEY}'
    try:
        apod_info = requests.get(url, timeout=5).json()
    except:
        apod_info = {'error': 'Could not get APOD information from Nasa API'}
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
    
    user_container = page.find('div', id='user_container')
    if oidc.user_loggedin:
        greet_container = page.new_tag('div', id='greet_container')
        
        avatar = page.new_tag('img', id='avatar')
        avatar['src'] = get_gravatar_url(session["oidc_auth_profile"]["email"])
        avatar['title'] = session["oidc_auth_profile"]["email"]
        greet_container.append(avatar)
        
        greet_container.append(page.new_tag('br'))
        greet_container.append(f'Hello {session["oidc_auth_profile"]["name"]}!')
        
        admin_link = page.new_tag('a', id='admin_link')
        admin_link['href'] = '/admin'
        admin_link.string = 'Admin'
        
        logout_button = page.new_tag('button', id='logout_button')
        logout_button['onclick'] = 'window.location.href = "/logout"'
        logout_button.string = 'Logout'
        
        user_container.append(greet_container)
        user_container.append(admin_link)
        user_container.append(page.new_tag('br'))
        user_container.append(page.new_tag('br'))
        user_container.append(logout_button)
    else:
        login_container = page.new_tag('div', id='login_container')
        login_container.string = 'You are not logged in. Please click the login button below to log in.'
        
        login_button = page.new_tag('button', id='login_button')
        login_button['onclick'] = 'window.location.href = "/login"'
        login_button.string = 'Login'
        
        user_container.append(login_container)
        user_container.append(login_button)
        
    apod_info_container = page.find('div', id='apod_info_container')
    apod_info_text = page.new_tag('div', id='apod_info_text')
    apod_info_text.string = str(apod_cache.get_apod_info())
    apod_info_container.append(apod_info_text)
    
    BeautifulSoup.prettify(page)
    
    return str(page)

@app.route('/login')
@oidc.require_login
def login():
    return redirect(url_for('.index'))

@app.route('/logout')
def logout():
    oidc.logout()
    return redirect(url_for('.index'))

@app.route('/admin', methods=['GET'])
@oidc.require_login
def admin():
    with open('Pages/admin.html', 'r') as f:
        page_html = f.read()
    page = BeautifulSoup(page_html, 'html.parser')
    api_key_container = page.find('div', {'id': 'api_key_container'})
    api_key_box = api_key_container.find('input', {'id': 'api_key'})
    api_key_box['value'] = API_KEY
    cache_timeout_container = page.find('div', {'id': 'cache_timeout_container'})
    cache_timeout_box = cache_timeout_container.find('input', {'id': 'cache_timeout'})
    cache_timeout_box['value'] = str(CACHE_TIMEOUT)
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
    return send_file(image_path)

@app.route('/clear', methods=['GET'])
@oidc.require_login
def clear():
    apod_cache.clear()
    return 'Cleared cache', 200

@app.route('/submit', methods=['POST'])
@oidc.require_login
def submit():
    api_key = request.json.get('api_key')
    cache_timeout = request.json.get('cache_timeout')
    
    if api_key is not None:
        API_KEY = api_key
    if cache_timeout is not None:
        CACHE_TIMEOUT = int(cache_timeout)
    
    config = {
        'api_key': API_KEY,
        'cache_timeout': CACHE_TIMEOUT
    }
    
    with open(APP_CONFIG_PATH, 'w') as f:
        json.dump(config, f)

    return 'Config saved', 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)