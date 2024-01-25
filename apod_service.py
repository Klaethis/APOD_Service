import cachetools
import requests
import sqlite3
import json
import os

from oauthlib.oauth2 import WebApplicationClient
# from db import init_db_command
from bs4 import BeautifulSoup
from user import User
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from flask import (
    Flask, 
    redirect, 
    request, 
    url_for, 
    send_file,
)

app = Flask(__name__)
app.secret_key = os.urandom(24)

API_KEY = os.environ.get('API_KEY', 'DEMO_KEY')
CACHE_TIMEOUT = int(os.environ.get('CACHE_TIMEOUT', 24*60*60))

CONFIG_PATH = os.path.join(os.path.dirname(__file__), os.environ.get('CONFIG_PATH', 'Config/config.json'))

if os.path.exists(CONFIG_PATH):
    with open(CONFIG_PATH, 'r') as f:
        config = json.load(f)
        if config is not None:
            API_KEY = config.get('api_key', API_KEY)
            CACHE_TIMEOUT = config.get('cache_timeout', CACHE_TIMEOUT)
            
OAUTH_CLIENT_ID = os.environ.get('OAUTH_CLIENT_ID')
OAUTH_CLIENT_SECRET = os.environ.get('OAUTH_CLIENT_SECRET')
OAUTH_DISCOVERY_URL = ('https://authentik.mikezim.org/application/o/apod/.well-known/openid-configuration')

login_manager = LoginManager()
login_manager.init_app(app)

# # Naive database setup
# try:
#     init_db_command()
# except sqlite3.OperationalError:
#     # Assume it's already been created
#     pass

client = WebApplicationClient(OAUTH_CLIENT_ID)

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

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

def get_oauth_provider_cfg():
    return requests.get(OAUTH_DISCOVERY_URL).json()

@app.route('/', methods=['GET'])
def index():
    if current_user.is_authenticated:
        with open('Pages/index.html', 'r') as f:
            page_html = f.read()
        page = BeautifulSoup(page_html, 'html.parser')
        api_key_container = page.find('div', {'id': 'api_key_container'})
        api_key_box = api_key_container.find('input', {'id': 'api_key'})
        api_key_box['value'] = API_KEY
        cache_timeout_container = page.find('div', {'id': 'cache_timeout_container'})
        cache_timeout_box = cache_timeout_container.find('input', {'id': 'cache_timeout'})
        cache_timeout_box['value'] = str(CACHE_TIMEOUT)
        return str(page)
    else:
        with open('Pages/login.html', 'r') as f:
            page_html = f.read()
        page = BeautifulSoup(page_html, 'html.parser')
        return str(page)
    
@app.route('/login')
def login():
    oauth_provider_cfg = get_oauth_provider_cfg()
    authorization_endpoint = oauth_provider_cfg['authorization_endpoint']
    
    request_uri = client.prepare_request_uri(
        authorization_endpoint,
        redirect_uri='https://apod.mikezim.org/login/callback',
        scope=['openid', 'profile', 'email'],
    )
    return redirect(request_uri)

@app.route('/login/callback')
def callback():
    code = request.args.get('code')
    
    oauth_provider_cfg = get_oauth_provider_cfg()
    token_endpoint = oauth_provider_cfg['token_endpoint']
    
    token_url, headers, body = client.prepare_token_request(
        token_endpoint,
        authorization_response='https://apod.mikezim.org/login/callback',
        redirect_url='https://apod.mikezim.org/login/callback',
        code=code
    )
    token_response = requests.post(
        token_url,
        headers=headers,
        data=body,
        auth=(OAUTH_CLIENT_ID, OAUTH_CLIENT_SECRET),
    )
    
    client.parse_request_body_response(json.dumps(token_response.json()))
    
    userinfo_endpoint = oauth_provider_cfg['userinfo_endpoint']
    uri, headers, body = client.add_token(userinfo_endpoint)
    userinfo_response = requests.get(uri, headers=headers, data=body)
    
    if userinfo_response.json().get('email_verified'):
        unique_id = userinfo_response.json()['sub']
        users_email = userinfo_response.json()['email']
        users_name = userinfo_response.json()['given_name']
    else:
        return 'User email not available or not verified.', 400
    
    user = User(id_=unique_id, name=users_name, email=users_email)
    
    if not User.get(unique_id):
        User.create(unique_id, users_name, users_email)
    
    login_user(user)
    
    return redirect(url_for('index'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

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
@login_required
def clear():
    apod_cache.clear()
    return 'Cleared cache', 200

@app.route('/submit', methods=['POST'])
@login_required
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
    
    with open(CONFIG_PATH, 'w') as f:
        json.dump(config, f)

    return 'Config saved', 200

if __name__ == '__main__':
    app.run(ssl_context='adhoc', host='0.0.0.0', port=5000)