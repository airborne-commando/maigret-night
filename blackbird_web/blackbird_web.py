from flask import Flask, render_template, request, send_file, flash, redirect, url_for, get_flashed_messages, jsonify
import logging
from logging.handlers import RotatingFileHandler
import os
import sys
import json
from datetime import datetime
from threading import Thread
import asyncio
import aiohttp
from pathlib import Path
import importlib.util
import traceback
import nest_asyncio
import re
import hashlib
import csv
import requests
import chardet
import time
from collections import defaultdict, Counter

nest_asyncio.apply()
app = Flask(__name__)
app.secret_key = 'your-secret-key-here'
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# Configure logging
def setup_logging():
    log_dir = os.path.join(CURRENT_DIR, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # File handler for all logs
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, 'blackbird_web.log'),
        maxBytes=10*1024*1024,  # 10 MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    return root_logger

# Initialize logging
logger = setup_logging()

class BlackbirdConfig:
    def __init__(self):
        self.console = None
        self.verbose = False
        self.proxy = None
        self.timeout = 30
        self.max_concurrent_requests = 30
        self.filter = None
        self.no_nsfw = False
        self.dump = False
        self.csv = True
        self.json = True
        self.pdf = False
        self.ai = False
        self.setup_ai = False
        self.no_update = True
        self.about = False
        self.instagram_session_id = None
        self.api_url = None
        self.dateRaw = datetime.now().strftime("%m_%d_%Y")
        self.datePretty = datetime.now().strftime("%B %d, %Y")
        self.userAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        self.usernameFoundAccounts = None
        self.emailFoundAccounts = None
        self.currentUser = None
        self.currentEmail = None
        self.saveDirectory = None
        self.splash_line = ""
        self.ASSETS_DIRECTORY = BLACKBIRD_ASSETS_DIR if BLACKBIRD_ASSETS_DIR else "assets"
        self.FONTS_DIRECTORY = "fonts"
        self.FONT_REGULAR_FILE = "Montserrat-Regular.ttf"
        self.FONT_BOLD_FILE = "Montserrat-Bold.ttf"
        self.FONT_NAME_REGULAR = "Montserrat"
        self.FONT_NAME_BOLD = "Montserrat-Bold"
        self.IMAGES_DIRECTORY = "img"
        self.ai_analysis = None
        self.USERNAME_list_PATH = self._find_data_file('wmn-data.json')
        self.EMAIL_list_PATH = self._find_data_file('email-data.json')
        self.USERNAME_METADATA_list_PATH = self._find_data_file('wmn-metadata.json')
        self.USERNAME_list_URL = "https://raw.githubusercontent.com/WebBreacher/WhatsMyName/main/wmn-data.json"
        self.username_sites = []
        self.email_sites = []
        self.metadata_params = {}
        self.include_categories = []
        self.exclude_categories = []
    
    def _find_data_file(self, filename):
        possible_locations = [
            os.path.join(CURRENT_DIR, '..', 'blackbird', 'data', filename),
            os.path.join(CURRENT_DIR, 'blackbird', 'data', filename),
            os.path.join(CURRENT_DIR, '..', 'data', filename),
            os.path.join(CURRENT_DIR, 'data', filename),
            os.path.join('/usr', 'local', 'share', 'blackbird', 'data', filename),
            os.path.join(os.path.expanduser('~'), '.local', 'share', 'blackbird', 'data', filename),
            os.path.join(os.path.expanduser('~'), 'blackbird', 'data', filename),
        ]
        for location in possible_locations:
            abs_path = os.path.abspath(location)
            if os.path.exists(abs_path):
                return abs_path
        fallback_path = os.path.join(CURRENT_DIR, 'data', filename)
        os.makedirs(os.path.dirname(fallback_path), exist_ok=True)
        if not os.path.exists(fallback_path):
            with open(fallback_path, 'w') as f:
                json.dump({"sites": []}, f)
        return fallback_path

def find_blackbird_assets():
    possible_asset_locations = [
        os.path.join(CURRENT_DIR, '..', 'blackbird', 'assets'),
        os.path.join(CURRENT_DIR, '..', 'assets'),
        os.path.join(CURRENT_DIR, 'blackbird', 'assets'),
        os.path.join('/usr', 'local', 'share', 'blackbird', 'assets'),
        os.path.join(os.path.expanduser('~'), '.local', 'share', 'blackbird', 'assets'),
        os.path.join(os.path.expanduser('~'), 'blackbird', 'assets'),
    ]
    for location in possible_asset_locations:
        abs_path = os.path.abspath(location)
        if os.path.exists(abs_path):
            return abs_path
    return None

BLACKBIRD_ASSETS_DIR = find_blackbird_assets()

def find_blackbird_root():
    SIGNATURES = [
        ('blackbird.py', 'main script'),
        (os.path.join('src', 'modules'), 'modules directory'),
        ('data/wmn-data.json', 'username data file'),
        ('assets', 'assets directory'),
        ('requirements.txt', 'requirements file with blackbird'),
    ]
    
    def is_blackbird_dir(directory):
        for signature, description in SIGNATURES:
            path = os.path.join(directory, signature)
            if os.path.exists(path):
                return True, f"contains {description}"
        return False, None
    
    current_dir = os.path.abspath(CURRENT_DIR)
    for i in range(5):
        is_bb, reason = is_blackbird_dir(current_dir)
        if is_bb:
            return current_dir
        parent = os.path.dirname(current_dir)
        if parent == current_dir:
            break
        current_dir = parent
    
    common_paths = []
    home = os.path.expanduser("~")
    common_paths.extend([
        os.path.join(home, 'blackbird'),
        os.path.join(home, '.blackbird'),
        os.path.join(home, '.local', 'share', 'blackbird'),
        os.path.join(home, '.local', 'lib', 'blackbird'),
        os.path.join(home, 'Desktop', 'blackbird'),
        os.path.join(home, 'Documents', 'blackbird'),
        os.path.join(home, 'Projects', 'blackbird'),
        '/usr/local/share/blackbird',
        '/usr/local/lib/blackbird',
        '/usr/share/blackbird',
        '/usr/lib/blackbird',
        '/opt/blackbird',
    ])
    script_dir = os.path.dirname(os.path.abspath(__file__))
    common_paths.extend([
        os.path.join(script_dir, '..', '..', 'blackbird'),
        os.path.join(script_dir, '..', 'blackbird'),
        os.path.join(script_dir, 'blackbird'),
    ])
    for path in common_paths:
        abs_path = os.path.abspath(path)
        if os.path.exists(abs_path):
            is_bb, reason = is_blackbird_dir(abs_path)
            if is_bb:
                return abs_path
    
    env_path = os.environ.get('BLACKBIRD_PATH')
    if env_path and os.path.exists(env_path):
        abs_env_path = os.path.abspath(env_path)
        is_bb, reason = is_blackbird_dir(abs_env_path)
        if is_bb:
            return abs_env_path
    
    try:
        import blackbird
        return os.path.dirname(os.path.abspath(blackbird.__file__))
    except ImportError:
        pass
    
    return None

def load_blackbird_modules():
    blackbird_root = find_blackbird_root()
    if not blackbird_root:
        create_minimal_mocks()
        return False
    
    src_dir = os.path.join(blackbird_root, 'src')
    if os.path.exists(src_dir):
        if src_dir not in sys.path:
            sys.path.insert(0, src_dir)
    
    if blackbird_root not in sys.path:
        sys.path.insert(0, blackbird_root)
    
    try:
        import modules
        return True
    except ImportError as e:
        modules_dir = os.path.join(blackbird_root, 'src', 'modules')
        if os.path.exists(modules_dir):
            create_minimal_mocks()
            return False
        else:
            create_minimal_mocks()
            return False

def create_minimal_mocks():
    mock_modules = type(sys)('modules')
    mock_utils = type(sys)('modules.utils')
    
    class MockHTTPClient:
        @staticmethod
        async def do_async_request(method, url, session, config, **kwargs):
            try:
                headers = {"User-Agent": config.userAgent}
                async with session.request(
                    method=method,
                    url=url,
                    headers=headers,
                    timeout=config.timeout,
                    ssl=False
                ) as response:
                    content = await response.text()
                    return {
                        "url": str(response.url),
                        "status_code": response.status,
                        "headers": dict(response.headers),
                        "content": content,
                        "json": None
                    }
            except Exception as e:
                return None
    
    mock_utils.http_client = type(sys)('http_client')
    mock_utils.http_client.do_async_request = MockHTTPClient.do_async_request
    
    class MockParse:
        @staticmethod
        def extractMetadata(metadata_config, response, site_name, config):
            return []
        
        @staticmethod
        def remove_duplicates(items):
            return items
    
    mock_utils.parse = type(sys)('parse')
    mock_utils.parse.extractMetadata = MockParse.extractMetadata
    mock_utils.parse.remove_duplicates = MockParse.remove_duplicates
    
    class MockFilter:
        @staticmethod
        def applyFilters(sites, config):
            filtered = sites
            if config.no_nsfw:
                filtered = [s for s in filtered if s.get("cat") != "xx NSFW xx"]
            if config.filter:
                filter_lower = config.filter.lower()
                filtered = [s for s in filtered if filter_lower in str(s.get('name', '')).lower()]
            return filtered
        
        @staticmethod
        def filterFoundAccounts(account):
            return account.get("status") == "FOUND"
    
    mock_utils.filter = type(sys)('filter')
    mock_utils.filter.applyFilters = MockFilter.applyFilters
    mock_utils.filter.filterFoundAccounts = MockFilter.filterFoundAccounts
    
    class MockLog:
        @staticmethod
        def logError(e, msg, config):
            print(f"[ERROR] {msg}: {e}")
    
    mock_utils.log = type(sys)('log')
    mock_utils.log.logError = MockLog.logError
    
    class MockInput:
        @staticmethod
        def processInput(value, operation, config):
            return value
    
    mock_utils.input = type(sys)('input')
    mock_utils.input.processInput = MockInput.processInput
    
    class MockPrecheck:
        @staticmethod
        def perform_pre_check(pre_check_config, headers, config):
            return headers
    
    mock_utils.precheck = type(sys)('precheck')
    mock_utils.precheck.perform_pre_check = MockPrecheck.perform_pre_check
    
    class MockDump:
        @staticmethod
        def dumpContent(path, site, response, config):
            return True
    
    mock_utils.dump = type(sys)('dump')
    mock_utils.dump.dumpContent = MockDump.dumpContent
    
    mock_whatsmyname = type(sys)('modules.whatsmyname')
    
    class MocklistOperations:
        @staticmethod
        def readlist(list_type, config):
            if list_type == "username":
                path = config.USERNAME_list_PATH
            elif list_type == "metadata":
                path = config.USERNAME_METADATA_list_PATH
            elif list_type == "email":
                path = config.EMAIL_list_PATH
            else:
                return {"sites": []}
            
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {"sites": []}
    
    mock_whatsmyname.list_operations = type(sys)('list_operations')
    mock_whatsmyname.list_operations.readlist = MocklistOperations.readlist
    
    mock_core = type(sys)('modules.core')
    mock_core.email = type(sys)('modules.core.email')
    
    class MockEmail:
        @staticmethod
        def verifyEmail(email, config):
            return [
                {
                    "name": "Mock Email Service",
                    "url": f"https://example.com/email/{email}",
                    "category": "email",
                    "status": "FOUND",
                    "metadata": None
                }
            ]
    
    mock_core.email.verifyEmail = MockEmail.verifyEmail
    
    sys.modules['modules'] = mock_modules
    sys.modules['modules.utils'] = mock_utils
    sys.modules['modules.utils.http_client'] = mock_utils.http_client
    sys.modules['modules.utils.parse'] = mock_utils.parse
    sys.modules['modules.utils.filter'] = mock_utils.filter
    sys.modules['modules.utils.log'] = mock_utils.log
    sys.modules['modules.utils.input'] = mock_utils.input
    sys.modules['modules.utils.precheck'] = mock_utils.precheck
    sys.modules['modules.utils.dump'] = mock_utils.dump
    sys.modules['modules.whatsmyname'] = mock_whatsmyname
    sys.modules['modules.whatsmyname.list_operations'] = mock_whatsmyname.list_operations
    sys.modules['modules.core'] = mock_core
    sys.modules['modules.core.email'] = mock_core.email

class WebConsole:
    def __init__(self, verbose=False, log_file=None):
        self.output = []
        self.is_terminal = False
        self.is_interactive = False
        self.is_jupyter = False
        self.is_dumb_terminal = False
        self.quiet = False
        self.soft_wrap = False
        self._width = 80
        self._height = 24
        self.encoding = "utf-8"
        self.color_system = "standard"
        self.legacy_windows = False
        self.no_color = False
        self.tab_size = 8
        self.file = None
        self.record = False
        self._theme_stack = None
        self._log_render = None
        self.verbose = verbose
        self.log_file = log_file
        self.log_entries = []
    
    def print(self, message, **kwargs):
        msg = str(message)
        self.output.append(msg)
        
        # Log to file if verbose mode
        if self.verbose and self.log_file:
            self.log_entries.append(msg)
    
    def get_log_content(self):
        return "\n".join(self.log_entries)
    
    def set_live(self, live):
        pass
    
    def clear(self):
        pass
    
    def show_cursor(self, show=True):
        pass
    
    def bell(self):
        pass
    
    def begin_capture(self):
        pass
    
    def end_capture(self):
        return ""
    
    def get_style(self, name):
        return None
    
    def push_theme(self, theme):
        pass
    
    def pop_theme(self):
        pass
    
    def status(self, status):
        return self
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
    
    def update(self, renderable):
        pass

def create_simple_async_request():
    async def simple_do_async_request(method, url, session, config, **kwargs):
        try:
            headers = {"User-Agent": config.userAgent}
            async with session.request(
                method=method,
                url=url,
                headers=headers,
                timeout=config.timeout,
                ssl=False,
                allow_redirects=True
            ) as response:
                content = await response.text()
                json_data = None
                if 'application/json' in response.headers.get('Content-Type', ''):
                    try:
                        json_data = json.loads(content)
                    except:
                        pass
                return {
                    "url": str(response.url),
                    "status_code": response.status,
                    "headers": dict(response.headers),
                    "content": content,
                    "json": json_data
                }
        except Exception as e:
            return None
    return simple_do_async_request

def simple_remove_duplicates(items):
    seen = set()
    unique = []
    for item in items:
        identifier = str(item)
        if identifier not in seen:
            seen.add(identifier)
            unique.append(item)
    return unique

class FrequencyAnalyzer:
    def __init__(self, reports_folder: str):
        self.reports_folder = Path(reports_folder)
        self.username_cache = {}
        self.frequency_cache = {}
        self.cache_file = self.reports_folder / ".frequency_cache.json"
        self.last_scan_time = None
        self._load_cache()
    
    def _load_cache(self):
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r') as f:
                    cache_data = json.load(f)
                    self.frequency_cache = cache_data.get('frequency_data', {})
                    self.last_scan_time = cache_data.get('last_scan_time')
        except Exception as e:
            self.frequency_cache = {}
    
    def _save_cache(self):
        try:
            cache_data = {
                'frequency_data': self.frequency_cache,
                'last_scan_time': datetime.now().isoformat(),
                'version': '1.0'
            }
            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
        except Exception as e:
            pass
    
    def scan_reports(self, force_rescan: bool = False) -> dict:
        if not force_rescan and self.frequency_cache and self._is_cache_fresh():
            return self.frequency_cache
        
        frequency_data = {
            'total_reports': 0,
            'total_accounts': 0,
            'unique_usernames': set(),
            'unique_emails': set(),
            'unique_sites': set(),
            'site_frequency': defaultdict(int),
            'username_frequency': defaultdict(int),
            'username_site_map': defaultdict(set),
            'site_username_map': defaultdict(set),
            'category_frequency': defaultdict(int),
            'recent_searches': [],
            'search_timeline': defaultdict(list),
            'last_scan': datetime.now().isoformat()
        }
        
        json_files = list(self.reports_folder.rglob("*.json"))
        csv_files = list(self.reports_folder.rglob("*.csv"))
        
        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                filename = json_file.stem
                username_match = re.match(r'^([^_]+)_', filename)
                if username_match:
                    username = username_match.group(1)
                    is_email = '@' in username
                    
                    if is_email:
                        frequency_data['unique_emails'].add(username)
                        identifier = f"email:{username}"
                    else:
                        frequency_data['unique_usernames'].add(username)
                        identifier = f"username:{username}"
                    
                    frequency_data['total_reports'] += 1
                    
                    if isinstance(data, list):
                        for account in data:
                            site_name = account.get('name', 'Unknown')
                            category = account.get('category', 'unknown')
                            status = account.get('status', 'UNKNOWN')
                            
                            if status == 'FOUND':
                                frequency_data['total_accounts'] += 1
                                frequency_data['unique_sites'].add(site_name)
                                frequency_data['site_frequency'][site_name] += 1
                                frequency_data['username_frequency'][identifier] += 1
                                frequency_data['username_site_map'][identifier].add(site_name)
                                frequency_data['site_username_map'][site_name].add(identifier)
                                frequency_data['category_frequency'][category] += 1
                    
                    try:
                        date_match = re.search(r'(\d{2})_(\d{2})_(\d{4})', str(json_file.parent))
                        if date_match:
                            date_str = f"{date_match.group(3)}-{date_match.group(1)}-{date_match.group(2)}"
                            frequency_data['search_timeline'][date_str].append({
                                'username': username,
                                'file': str(json_file.relative_to(self.reports_folder)),
                                'timestamp': datetime.fromtimestamp(json_file.stat().st_mtime).isoformat(),
                                'accounts_found': len([a for a in data if isinstance(data, list) and a.get('status') == 'FOUND'])
                            })
                    except:
                        pass
                        
            except Exception as e:
                continue
        
        for csv_file in csv_files:
            try:
                json_version = csv_file.with_suffix('.json')
                if json_version.exists():
                    continue
                
                filename = csv_file.stem
                username_match = re.match(r'^([^_]+)_', filename)
                if username_match:
                    username = username_match.group(1)
                    is_email = '@' in username
                    
                    if is_email:
                        identifier = f"email:{username}"
                    else:
                        identifier = f"username:{username}"
                    
                    frequency_data['total_reports'] += 1
                    
                    with open(csv_file, 'r', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            site_name = row.get('Site', 'Unknown')
                            category = row.get('Category', 'unknown')
                            status = row.get('Status', 'UNKNOWN')
                            
                            if status == 'FOUND':
                                frequency_data['total_accounts'] += 1
                                frequency_data['unique_sites'].add(site_name)
                                frequency_data['site_frequency'][site_name] += 1
                                frequency_data['username_frequency'][identifier] += 1
                                frequency_data['username_site_map'][identifier].add(site_name)
                                frequency_data['site_username_map'][site_name].add(identifier)
                                frequency_data['category_frequency'][category] += 1
                                
            except Exception as e:
                continue
        
        frequency_data['unique_usernames'] = list(frequency_data['unique_usernames'])
        frequency_data['unique_emails'] = list(frequency_data['unique_emails'])
        frequency_data['unique_sites'] = list(frequency_data['unique_sites'])
        frequency_data['site_frequency'] = dict(frequency_data['site_frequency'])
        frequency_data['username_frequency'] = dict(frequency_data['username_frequency'])
        frequency_data['username_site_map'] = {k: list(v) for k, v in frequency_data['username_site_map'].items()}
        frequency_data['site_username_map'] = {k: list(v) for k, v in frequency_data['site_username_map'].items()}
        frequency_data['category_frequency'] = dict(frequency_data['category_frequency'])
        frequency_data['search_timeline'] = dict(frequency_data['search_timeline'])
        
        all_searches = []
        for date_str, searches in frequency_data['search_timeline'].items():
            for search in searches:
                search['date'] = date_str
                all_searches.append(search)
        
        all_searches.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        frequency_data['recent_searches'] = all_searches[:10]
        
        self.frequency_cache = frequency_data
        self._save_cache()
        
        return frequency_data
    
    def _is_cache_fresh(self, max_age_hours: int = 1) -> bool:
        if not self.last_scan_time:
            return False
        try:
            last_scan = datetime.fromisoformat(self.last_scan_time)
            age = datetime.now() - last_scan
            return age.total_seconds() < (max_age_hours * 3600)
        except:
            return False
    
    def get_username_frequency(self, username: str) -> dict:
        if not self.frequency_cache:
            self.scan_reports()
        
        identifiers_to_check = [f"username:{username}"]
        if '@' in username:
            identifiers_to_check.append(f"email:{username}")
        
        result = {
            'username': username,
            'total_searches': 0,
            'sites_found': [],
            'site_count': 0,
            'categories': defaultdict(int),
            'first_seen': None,
            'last_seen': None,
            'search_history': []
        }
        
        for identifier in identifiers_to_check:
            if identifier in self.frequency_cache.get('username_site_map', {}):
                sites = self.frequency_cache['username_site_map'][identifier]
                result['sites_found'].extend(sites)
                result['site_count'] = len(sites)
                result['total_searches'] = self.frequency_cache['username_frequency'].get(identifier, 0)
        
        for date_str, searches in self.frequency_cache.get('search_timeline', {}).items():
            for search in searches:
                if search['username'] == username:
                    result['search_history'].append({
                        'date': date_str,
                        'accounts_found': search['accounts_found'],
                        'file': search['file']
                    })
        
        result['search_history'].sort(key=lambda x: x['date'], reverse=True)
        
        if result['search_history']:
            result['first_seen'] = result['search_history'][-1]['date']
            result['last_seen'] = result['search_history'][0]['date']
        
        return result
    
    def get_site_frequency(self, site_name: str) -> dict:
        if not self.frequency_cache:
            self.scan_reports()
        
        result = {
            'site_name': site_name,
            'total_found': self.frequency_cache.get('site_frequency', {}).get(site_name, 0),
            'usernames_found': self.frequency_cache.get('site_username_map', {}).get(site_name, []),
            'username_count': len(self.frequency_cache.get('site_username_map', {}).get(site_name, [])),
            'popularity_rank': 0,
            'percentage_of_searches': 0
        }
        
        if self.frequency_cache.get('site_frequency'):
            sorted_sites = sorted(
                self.frequency_cache['site_frequency'].items(),
                key=lambda x: x[1],
                reverse=True
            )
            for rank, (site, _) in enumerate(sorted_sites, 1):
                if site == site_name:
                    result['popularity_rank'] = rank
                    break
        
        total_accounts = self.frequency_cache.get('total_accounts', 1)
        result['percentage_of_searches'] = (result['total_found'] / total_accounts * 100) if total_accounts > 0 else 0
        
        return result
    
    def get_most_common_sites(self, limit: int = 10) -> list[tuple[str, int]]:
        if not self.frequency_cache:
            self.scan_reports()
        site_freq = self.frequency_cache.get('site_frequency', {})
        return sorted(site_freq.items(), key=lambda x: x[1], reverse=True)[:limit]
    
    def get_most_active_usernames(self, limit: int = 10) -> list[tuple[str, int]]:
        if not self.frequency_cache:
            self.scan_reports()
        username_freq = {}
        for identifier, sites in self.frequency_cache.get('username_site_map', {}).items():
            username_freq[identifier] = len(sites)
        return sorted(username_freq.items(), key=lambda x: x[1], reverse=True)[:limit]
    
    def search_historical_data(self, search_term: str) -> dict:
        if not self.frequency_cache:
            self.scan_reports()
        
        results = {
            'usernames': [],
            'emails': [],
            'sites': [],
            'total_matches': 0
        }
        
        search_term_lower = search_term.lower()
        
        for username in self.frequency_cache.get('unique_usernames', []):
            if search_term_lower in username.lower():
                freq_data = self.get_username_frequency(username)
                results['usernames'].append({
                    'username': username,
                    'site_count': freq_data['site_count'],
                    'first_seen': freq_data['first_seen'],
                    'last_seen': freq_data['last_seen']
                })
        
        for email in self.frequency_cache.get('unique_emails', []):
            if search_term_lower in email.lower():
                freq_data = self.get_username_frequency(email)
                results['emails'].append({
                    'email': email,
                    'site_count': freq_data['site_count'],
                    'first_seen': freq_data['first_seen'],
                    'last_seen': freq_data['last_seen']
                })
        
        for site in self.frequency_cache.get('unique_sites', []):
            if search_term_lower in site.lower():
                freq_data = self.get_site_frequency(site)
                results['sites'].append({
                    'site': site,
                    'total_found': freq_data['total_found'],
                    'username_count': freq_data['username_count'],
                    'popularity_rank': freq_data['popularity_rank']
                })
        
        results['total_matches'] = (
            len(results['usernames']) + 
            len(results['emails']) + 
            len(results['sites'])
        )
        
        return results
    
    def get_username_sites(self, username: str) -> dict:
        """
        Get all sites where a username was found
        
        Args:
            username: Username to look up
            
        Returns:
            Dictionary with sites and their details
        """
        if not self.frequency_cache:
            self.scan_reports()
        
        # Check both username and email formats
        identifiers_to_check = [f"username:{username}"]
        if '@' in username:
            identifiers_to_check.append(f"email:{username}")
        
        sites = []
        
        for identifier in identifiers_to_check:
            if identifier in self.frequency_cache.get('username_site_map', {}):
                site_list = self.frequency_cache['username_site_map'][identifier]
                
                # Get additional details for each site
                for site_name in site_list:
                    site_details = {
                        'site_name': site_name,
                        'found_count': self.frequency_cache.get('site_frequency', {}).get(site_name, 0),
                        'popularity_rank': 0,
                        'found_date': None
                    }
                    
                    # Calculate popularity rank
                    if self.frequency_cache.get('site_frequency'):
                        sorted_sites = sorted(
                            self.frequency_cache['site_frequency'].items(),
                            key=lambda x: x[1],
                            reverse=True
                        )
                        for rank, (site, _) in enumerate(sorted_sites, 1):
                            if site == site_name:
                                site_details['popularity_rank'] = rank
                                break
                    
                    sites.append(site_details)
        
        return {
            'username': username,
            'sites_found': sites,
            'total_sites': len(sites),
            'identifier_type': 'email' if '@' in username else 'username'
        }
    
    def get_overall_statistics(self) -> dict:
        if not self.frequency_cache:
            self.scan_reports()
        return {
            'total_reports': self.frequency_cache.get('total_reports', 0),
            'total_accounts': self.frequency_cache.get('total_accounts', 0),
            'unique_usernames': len(self.frequency_cache.get('unique_usernames', [])),
            'unique_emails': len(self.frequency_cache.get('unique_emails', [])),
            'unique_sites': len(self.frequency_cache.get('unique_sites', [])),
            'most_common_sites': self.get_most_common_sites(5),
            'most_active_usernames': self.get_most_active_usernames(5),
            'last_scan': self.frequency_cache.get('last_scan', 'Never'),
            'cache_fresh': self._is_cache_fresh()
        }

frequency_analyzer = None

def init_frequency_analyzer():
    global frequency_analyzer
    try:
        frequency_analyzer = FrequencyAnalyzer(app.config["REPORTS_FOLDER"])
        def background_scan():
            try:
                frequency_analyzer.scan_reports()
            except Exception as e:
                pass
        Thread(target=background_scan).start()
        return True
    except Exception as e:
        return False

app.config["REPORTS_FOLDER"] = os.path.abspath('../results/')
os.makedirs(app.config["REPORTS_FOLDER"], exist_ok=True)

background_jobs = {}
job_results = {}

async def simple_fetch_results(username, config):
    try:
        if config.verbose:
            config.console.print(f"[VERBOSE] Starting fetch for {username}")
            config.console.print(f"[VERBOSE] Checking {len(config.username_sites)} sites")
        
        try:
            from modules.utils.http_client import do_async_request
            from modules.utils.parse import extractMetadata, remove_duplicates
        except ImportError as e:
            do_async_request = create_simple_async_request()
            extractMetadata = create_simple_extract_metadata()
            remove_duplicates = simple_remove_duplicates
        
        async with aiohttp.ClientSession() as session:
            results = []
            
            async def check_site(site):
                try:
                    url = site["uri_check"].replace("{account}", username)
                    
                    if config.verbose:
                        config.console.print(f"[VERBOSE] Checking {site.get('name')} at {url}")
                    
                    response = await do_async_request("GET", url, session, config)
                    
                    if response is None:
                        if config.verbose:
                            config.console.print(f"[VERBOSE] {site.get('name')}: No response (ERROR)")
                        return {
                            "name": site.get("name", "unknown"),
                            "url": url,
                            "category": site.get("cat", "unknown"),
                            "status": "ERROR",
                            "metadata": None
                        }
                    
                    e_string = site.get("e_string", "")
                    e_code = site.get("e_code", 200)
                    m_string = site.get("m_string", "")
                    m_code = site.get("m_code", 404)
                    
                    content = response.get("content", "")
                    status_code = response.get("status_code", 0)
                    
                    account_found = (
                        e_string in content and 
                        (e_code == status_code or e_code == 0)
                    )
                    
                    if account_found:
                        account_not_found = (
                            m_string in content or
                            (m_code == status_code and m_code != e_code)
                        )
                        
                        if not account_not_found:
                            if config.verbose:
                                config.console.print(f"[VERBOSE] {site.get('name')}: FOUND ({status_code})")
                            result = {
                                "name": site.get("name", "unknown"),
                                "url": response.get("url", url),
                                "category": site.get("cat", "unknown"),
                                "status": "FOUND",
                                "metadata": None
                            }
                            
                            try:
                                if (config.metadata_params and 
                                    site.get("name") in config.metadata_params.get("sites", {})):
                                    
                                    metadata_config = config.metadata_params["sites"][site["name"]]
                                    metadata = extractMetadata(
                                        metadata_config,
                                        response,
                                        site["name"],
                                        config,
                                    )
                                    if metadata:
                                        metadata = remove_duplicates(metadata)
                                        metadata.sort(key=lambda x: x.get("name", ""))
                                        result["metadata"] = metadata
                            except Exception as e:
                                if config.verbose:
                                    config.console.print(f"[VERBOSE] {site.get('name')}: Metadata error - {str(e)}")
                            
                            return result
                    
                    if config.verbose:
                        config.console.print(f"[VERBOSE] {site.get('name')}: NOT FOUND ({status_code})")
                    
                    return {
                        "name": site.get("name", "unknown"),
                        "url": response.get("url", url),
                        "category": site.get("cat", "unknown"),
                        "status": "NOT-FOUND",
                        "metadata": None
                    }
                    
                except Exception as e:
                    if config.verbose:
                        config.console.print(f"[VERBOSE] {site.get('name')}: Exception - {str(e)}")
                    return {
                        "name": site.get("name", "unknown"),
                        "url": url,
                        "category": site.get("cat", "unknown"),
                        "status": "ERROR",
                        "metadata": None
                    }
            
            tasks = []
            for site in config.username_sites:
                task = asyncio.create_task(check_site(site))
                tasks.append(task)
            
            results = await asyncio.gather(*tasks)
            
            if config.verbose:
                found_count = len([r for r in results if r.get('status') == 'FOUND'])
                config.console.print(f"[VERBOSE] Fetch completed: {found_count} found out of {len(results)} sites")
            
            return {
                "results": results,
                "username": username,
                "total_checked": len(results)
            }
            
    except Exception as e:
        if config.verbose:
            config.console.print(f"[VERBOSE] Overall fetch error: {str(e)}")
        return {"results": [], "username": username, "total_checked": 0}

def web_applyFilters(sites, config):
    if not hasattr(config, 'filter') or not config.filter:
        return sites
    
    filter_string = config.filter
    
    # Handle "and" conditions by splitting on " and " (case-insensitive)
    if ' and ' in filter_string.lower():
        and_parts = re.split(r'\s+and\s+', filter_string, flags=re.IGNORECASE)
        for part in and_parts:
            sites = _apply_single_filter(sites, part.strip())
        return sites
    
    # Handle "or" conditions by splitting on " or " (case-insensitive)
    elif ' or ' in filter_string.lower():
        or_parts = re.split(r'\s+or\s+', filter_string, flags=re.IGNORECASE)
        filtered_results = []
        for part in or_parts:
            filtered_sites = _apply_single_filter(sites, part.strip())
            filtered_results.extend(filtered_sites)
        # Remove duplicates
        seen = set()
        unique_sites = []
        for site in filtered_results:
            site_id = site.get('name', '') + site.get('uri_check', '')
            if site_id not in seen:
                seen.add(site_id)
                unique_sites.append(site)
        return unique_sites
    
    # Single filter condition
    else:
        return _apply_single_filter(sites, filter_string)


def _apply_single_filter(sites, filter_part):
    """
    Apply a single filter condition to sites.
    """
    if not filter_part:
        return sites
    
    if filter_part.startswith('name!='):
        excluded_name = filter_part[6:].strip()
        excluded_name_lower = excluded_name.lower()
        return [
            s for s in sites 
            if s.get('name', '').lower() != excluded_name_lower
        ]
    
    elif filter_part.startswith('name='):
        required_name = filter_part[5:].strip()
        required_name_lower = required_name.lower()
        return [
            s for s in sites 
            if s.get('name', '').lower() == required_name_lower
        ]
    
    elif filter_part.startswith('name~'):
        search_term = filter_part[5:].strip()
        search_term_lower = search_term.lower()
        return [
            s for s in sites 
            if search_term_lower in s.get('name', '').lower()
        ]
    
    elif filter_part.startswith('cat!='):
        excluded_categories = filter_part[5:].strip().split('|')
        excluded_categories = [c.strip() for c in excluded_categories]
        return [
            s for s in sites 
            if s.get('cat', '').strip() not in excluded_categories
        ]
    
    elif filter_part.startswith('cat='):
        required_categories = filter_part[4:].strip().split('|')
        required_categories = [c.strip() for c in required_categories]
        return [
            s for s in sites 
            if s.get('cat', '').strip() in required_categories
        ]
    
    elif filter_part.startswith('cat~'):
        search_term = filter_part[4:].strip()
        search_term_lower = search_term.lower()
        return [
            s for s in sites 
            if search_term_lower in s.get('cat', '').lower()
        ]
    
    elif '!=' in filter_part and not (filter_part.startswith('cat') or filter_part.startswith('name')):
        key, value = filter_part.split('!=', 1)
        key = key.strip()
        value = value.strip().lower()
        return [
            s for s in sites 
            if str(s.get(key, '')).lower() != value
        ]
    
    elif '=' in filter_part and not (filter_part.startswith('cat') or filter_part.startswith('name')):
        key, value = filter_part.split('=', 1)
        key = key.strip()
        value = value.strip().lower()
        return [
            s for s in sites 
            if str(s.get(key, '')).lower() == value
        ]
    
    elif '~' in filter_part and not (filter_part.startswith('cat') or filter_part.startswith('name')):
        key, value = filter_part.split('~', 1)
        key = key.strip()
        value = value.strip().lower()
        return [
            s for s in sites 
            if value in str(s.get(key, '')).lower()
        ]
    
    else:
        # Simple text search across multiple fields
        search_term = filter_part.strip().lower()
        return [
            s for s in sites 
            if (search_term in str(s.get('name', '')).lower() or
                search_term in str(s.get('cat', '')).lower() or
                search_term in str(s.get('uri_check', '')).lower())
        ]

async def search_username_blackbird(username, config):
    try:
        if config.verbose:
            config.console.print(f"[VERBOSE] Starting username search for: {username}")
        
        try:
            from modules.whatsmyname.list_operations import readlist
            from modules.utils.filter import applyFilters as blackbird_applyFilters
            use_blackbird_modules = True
        except ImportError as e:
            use_blackbird_modules = False
        
        def fallback_readlist(list_type, config):
            if list_type == "username":
                path = config.USERNAME_list_PATH
            elif list_type == "metadata":
                path = config.USERNAME_METADATA_list_PATH
            elif list_type == "email":
                path = config.EMAIL_list_PATH
            else:
                return {"sites": []}
            
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {"sites": []}
        
        if not use_blackbird_modules:
            if config.verbose:
                config.console.print(f"[VERBOSE] Using fallback site list reading")
            data = fallback_readlist("username", config)
            sitesToSearch = data["sites"]
            filtered_sites = web_applyFilters(sitesToSearch, config)
            config.username_sites = filtered_sites
            if config.verbose:
                config.console.print(f"[VERBOSE] Loaded {len(sitesToSearch)} sites, filtered to {len(filtered_sites)}")
        else:
            if config.verbose:
                config.console.print(f"[VERBOSE] Using Blackbird module site list")
            data = readlist("username", config)
            sitesToSearch = data["sites"]
            config.username_sites = blackbird_applyFilters(sitesToSearch, config)
            if config.verbose:
                config.console.print(f"[VERBOSE] Loaded {len(sitesToSearch)} sites, filtered to {len(config.username_sites)}")
        
        results = await simple_fetch_results(username, config)
        
        try:
            from modules.utils.filter import filterFoundAccounts
            found_accounts = [acc for acc in results.get('results', []) if filterFoundAccounts(acc)]
            if config.verbose:
                config.console.print(f"[VERBOSE] Using Blackbird module account filtering")
        except ImportError:
            found_accounts = [acc for acc in results.get('results', []) if acc.get('status') == 'FOUND']
            if config.verbose:
                config.console.print(f"[VERBOSE] Using fallback account filtering")
        
        if config.verbose:
            config.console.print(f"[VERBOSE] Username search completed: {len(found_accounts)} accounts found")
        
        return found_accounts
        
    except Exception as e:
        if config.verbose:
            config.console.print(f"[VERBOSE] Error in username search: {str(e)}")
            config.console.print(traceback.format_exc())
        return []

async def search_email_blackbird(email, config):
    try:
        from modules.core.email import verifyEmail
        from modules.whatsmyname.list_operations import readlist
        from modules.utils.filter import applyFilters
        
        data = readlist("email", config)
        sitesToSearch = data["sites"]
        config.email_sites = applyFilters(sitesToSearch, config)
        
        async def simple_email_fetch(email, config):
            import asyncio
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                tasks = []
                semaphore = asyncio.Semaphore(config.max_concurrent_requests)
                total_sites = len(config.email_sites)
                completed = 0
                results = []
                
                async def check_site_wrapper(site):
                    nonlocal completed
                    
                    from modules.core.email import checkSite
                    from modules.utils.input import processInput
                    
                    if site.get("input_operation") is not None:
                        email_processed = processInput(email, site["input_operation"], config)
                        if email_processed is None:
                            email_processed = email
                        elif not isinstance(email_processed, str):
                            email_processed = str(email_processed)
                    else:
                        email_processed = email
                    
                    url = site["uri_check"].replace("{account}", email_processed)
                    data = site["data"].replace("{account}", email_processed) if site["data"] else None
                    headers = site["headers"] if site["headers"] else None
                    
                    result = await checkSite(
                        site=site,
                        method=site.get("method", "GET"),
                        url=url,
                        session=session,
                        semaphore=semaphore,
                        config=config,
                        data=data,
                        headers=headers,
                    )
                    
                    completed += 1
                    return result
                
                tasks = [check_site_wrapper(site) for site in config.email_sites]
                
                for task in asyncio.as_completed(tasks):
                    result = await task
                    results.append(result)
                
                return {"results": results, "email": email}
        
        results = await simple_email_fetch(email, config)
        
        from modules.utils.filter import filterFoundAccounts
        found_accounts = [acc for acc in results.get('results', []) if filterFoundAccounts(acc)]
        
        formatted_results = []
        for account in found_accounts:
            formatted_account = {
                "name": account.get("name", "unknown"),
                "url": account.get("url", "#"),
                "category": account.get("category", account.get("cat", "unknown")),
                "status": account.get("status", "UNKNOWN"),
                "metadata": account.get("metadata")
            }
            formatted_results.append(formatted_account)
        
        return formatted_results
        
    except Exception as e:
        return []

def create_web_config(options):
    config = BlackbirdConfig()
    config.verbose = options.get('verbose', False)
    config.proxy = options.get('proxy')
    config.timeout = int(options.get('timeout', 30))
    config.max_concurrent_requests = int(options.get('max_concurrent', 30))
    config.filter = options.get('filter')
    config.include_categories = options.get('include_categories', '')
    config.exclude_categories = options.get('exclude_categories', '')
    config.no_nsfw = options.get('no_nsfw', False)
    config.dump = options.get('dump', False)
    config.csv = options.get('save_csv', True)
    config.json = options.get('save_json', True)
    config.pdf = options.get('save_pdf', False)
    config.ai = options.get('ai', False)
    config.email_sites = []
    
    # Create log directory if it doesn't exist
    log_dir = os.path.join(CURRENT_DIR, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # Set up console with log file if verbose mode
    if config.verbose:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"search_{timestamp}.log"
        log_path = os.path.join(log_dir, log_filename)
        config.console = WebConsole(verbose=True, log_file=log_path)
        
        # Log start of search
        config.console.print(f"[{timestamp}] Starting search with verbose mode")
        config.console.print(f"Search parameters: {options}")
    else:
        config.console = WebConsole(verbose=False)
    
    return config

def save_reports(found_accounts, identifier, session_folder, config, search_type="username"):
    try:
        os.makedirs(session_folder, exist_ok=True)
        
        if search_type == "username":
            config.currentUser = identifier
            prefix = f"{identifier}_{config.dateRaw}_blackbird"
        else:
            config.currentEmail = identifier
            prefix = f"{identifier}_{config.dateRaw}_blackbird"
        
        config.saveDirectory = session_folder
        reports = {}
        
        if config.json and found_accounts:
            try:
                json_file = f"{prefix}.json"
                json_path = os.path.join(session_folder, json_file)
                
                json_data = []
                for account in found_accounts:
                    account_data = {
                        'name': account.get('name', 'Unknown'),
                        'url': account.get('url', '#'),
                        'category': account.get('category', 'unknown'),
                        'status': account.get('status', 'UNKNOWN')
                    }
                    
                    metadata = account.get('metadata')
                    if metadata:
                        formatted_metadata = []
                        for meta_item in metadata:
                            formatted_meta = {
                                'name': meta_item.get('name', ''),
                                'value': meta_item.get('value', '')
                            }
                            if 'type' in meta_item:
                                formatted_meta['type'] = meta_item['type']
                            if 'path' in meta_item:
                                formatted_meta['path'] = meta_item['path']
                            formatted_metadata.append(formatted_meta)
                        account_data['metadata'] = formatted_metadata
                    
                    json_data.append(account_data)
                
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(json_data, f, indent=4, ensure_ascii=False)
                
                reports['json_file'] = json_file
                if config.verbose:
                    config.console.print(f"[VERBOSE] Saved JSON report: {json_file}")
            except Exception as e:
                if config.verbose:
                    config.console.print(f"[VERBOSE] Failed to save JSON: {e}")
        
        if config.csv and found_accounts:
            try:
                csv_file = f"{prefix}.csv"
                csv_path = os.path.join(session_folder, csv_file)
                
                with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['Site', 'URL', 'Category', 'Status'])
                    for account in found_accounts:
                        writer.writerow([
                            account.get('name', 'Unknown'),
                            account.get('url', '#'),
                            account.get('category', 'unknown'),
                            account.get('status', 'UNKNOWN')
                        ])
                
                reports['csv_file'] = csv_file
                if config.verbose:
                    config.console.print(f"[VERBOSE] Saved CSV report: {csv_file}")
            except Exception as e:
                if config.verbose:
                    config.console.print(f"[VERBOSE] Failed to save CSV: {e}")
        
        # Save log file if verbose mode is enabled
        if config.verbose and hasattr(config.console, 'get_log_content'):
            try:
                log_content = config.console.get_log_content()
                log_file = f"{prefix}_verbose.log"
                log_path = os.path.join(session_folder, log_file)
                
                with open(log_path, 'w', encoding='utf-8') as f:
                    f.write(f"=== Blackbird Verbose Log ===\n")
                    f.write(f"Search: {identifier}\n")
                    f.write(f"Type: {search_type}\n")
                    f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"Total Accounts Found: {len(found_accounts)}\n")
                    f.write("=" * 50 + "\n\n")
                    f.write(log_content)
                
                reports['log_file'] = log_file
                if config.verbose:
                    config.console.print(f"[VERBOSE] Saved verbose log: {log_file}")
            except Exception as e:
                if config.verbose:
                    config.console.print(f"[VERBOSE] Failed to save log file: {e}")
        
        config.currentUser = None
        config.currentEmail = None
        config.saveDirectory = None
        
        return reports
        
    except Exception as e:
        if config.verbose:
            config.console.print(f"[VERBOSE] Error in save_reports: {e}")
        return {}

async def process_single_search(item, search_type, config):
    try:
        if config.verbose:
            config.console.print(f"[VERBOSE] Starting search for {item} (type: {search_type})")
            config.console.print(f"[VERBOSE] Config: filter={config.filter}, timeout={config.timeout}s")
        
        if search_type == "username":
            found_accounts = await search_username_blackbird(item, config)
        elif search_type == "email":
            found_accounts = await search_email_blackbird(item, config)
        else:
            if config.verbose:
                config.console.print(f"[VERBOSE] Invalid search type: {search_type}")
            return None
        
        if config.verbose:
            config.console.print(f"[VERBOSE] Found {len(found_accounts)} accounts for {item}")
            for account in found_accounts[:5]:  # Log first 5 accounts
                config.console.print(f"  - {account.get('name')}: {account.get('status')}")
            if len(found_accounts) > 5:
                config.console.print(f"  ... and {len(found_accounts) - 5} more")
        
        claimed_profiles = []
        for account in found_accounts:
            profile = {
                'site_name': account.get('name', 'Unknown'),
                'url': account.get('url', '#'),
                'category': account.get('category', 'unknown'),
                'status': account.get('status', 'UNKNOWN')
            }
            
            metadata = account.get('metadata')
            if metadata:
                profile['metadata'] = metadata
            
            claimed_profiles.append(profile)
        
        return {
            'item': item,
            'search_type': search_type,
            'found_accounts': found_accounts,
            'claimed_profiles': claimed_profiles,
            'total_found': len(found_accounts)
        }
        
    except Exception as e:
        if config.verbose:
            config.console.print(f"[VERBOSE] Error in search: {str(e)}")
            config.console.print(traceback.format_exc())
        return None

def create_session_folder(username, search_type):
    date_str = datetime.now().strftime("%m_%d_%Y")
    if search_type == "email":
        folder_name = f"{username}_{date_str}_blackbird"
    else:
        folder_name = f"{username}_{date_str}_blackbird"
    
    session_folder = os.path.join(app.config["REPORTS_FOLDER"], folder_name)
    return folder_name, session_folder

def process_search_task(search_items, search_type, options, timestamp, enable_frequency=False):
    try:
        # Add start time to job tracking
        background_jobs[timestamp]['start_time'] = time.time()
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        individual_reports = []
        
        # Process each username ONE AT A TIME
        for item in search_items:
            try:
                folder_name, session_folder = create_session_folder(item, search_type)
                config = create_web_config(options)
                config.saveDirectory = session_folder
                
                # Process this single username
                result = loop.run_until_complete(
                    process_single_search(item, search_type, config)
                )
                
                if result is None:
                    continue
                    
                found_accounts = result['found_accounts']
                claimed_profiles = result['claimed_profiles']
                
                os.makedirs(session_folder, exist_ok=True)
                
                config = create_web_config(options)
                config.saveDirectory = session_folder
                config.currentUser = item if search_type == "username" else None
                config.currentEmail = item if search_type == "email" else None
                
                reports = save_reports(found_accounts, item, session_folder, config, search_type)
                
                # Save log file if verbose mode was enabled
                log_content = None
                if config.verbose and hasattr(config.console, 'get_log_content'):
                    log_content = config.console.get_log_content()
                    log_file_path = os.path.join(session_folder, f"{item}_{timestamp}_verbose.log")
                    try:
                        with open(log_file_path, 'w', encoding='utf-8') as log_file:
                            log_file.write(f"=== Blackbird Verbose Log ===\n")
                            log_file.write(f"Search Item: {item}\n")
                            log_file.write(f"Search Type: {search_type}\n")
                            log_file.write(f"Timestamp: {timestamp}\n")
                            log_file.write(f"Options: {options}\n")
                            log_file.write("=" * 50 + "\n\n")
                            log_file.write(log_content)
                        
                        reports['log_file'] = f"{item}_{timestamp}_verbose.log"
                        if config.verbose:
                            config.console.print(f"[VERBOSE] Saved detailed log file: {reports['log_file']}")
                    except Exception as e:
                        if config.verbose:
                            config.console.print(f"[VERBOSE] Failed to save log file: {e}")
                
                report_data = {
                    'username': item,
                    'search_type': search_type,
                    'folder_name': folder_name,
                    'csv_file': reports.get('csv_file'),
                    'json_file': reports.get('json_file'),
                    'pdf_file': reports.get('pdf_file'),
                    'log_file': reports.get('log_file'),
                    'claimed_profiles': claimed_profiles,
                    'total_found': result['total_found']
                }
                
                if enable_frequency and frequency_analyzer:
                    frequency_analyzer.scan_reports()
                    freq_data = frequency_analyzer.get_username_frequency(item)
                    
                    total_reports = frequency_analyzer.frequency_cache.get('total_reports', 1)
                    user_reports = len(freq_data.get('search_history', []))
                    frequency_percentage = (user_reports / total_reports * 100) if total_reports > 0 else 0
                    
                    common_sites = []
                    for site in freq_data.get('sites_found', []):
                        site_freq = frequency_analyzer.get_site_frequency(site)
                        common_sites.append({
                            'site': site,
                            'count': site_freq.get('total_found', 0),
                            'username_count': site_freq.get('username_count', 0)
                        })
                    
                    common_sites.sort(key=lambda x: x['count'], reverse=True)
                    
                    report_data['frequency_data'] = {
                        'username': item,
                        'search_type': search_type,
                        'total_occurrences': user_reports,
                        'site_count': freq_data.get('site_count', 0),
                        'first_seen': freq_data.get('first_seen'),
                        'last_seen': freq_data.get('last_seen'),
                        'common_sites': common_sites[:5],
                        'frequency_percentage': frequency_percentage
                    }
                
                individual_reports.append(report_data)
                
                # Small delay between usernames
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error processing {item}: {e}")
                continue
        
        common_sites_formatted = []
        if enable_frequency and frequency_analyzer:
            common_sites_overall = frequency_analyzer.get_most_common_sites(10)
            for site, count in common_sites_overall:
                site_freq = frequency_analyzer.get_site_frequency(site)
                common_sites_formatted.append({
                    'site': site,
                    'count': count,
                    'username_count': site_freq.get('username_count', 0)
                })
        
        job_results[timestamp] = {
            'status': 'completed',
            'search_items': search_items,
            'search_type': search_type,
            'individual_reports': individual_reports,
            'timestamp': timestamp,
            'enable_frequency': enable_frequency,
            'frequency_data': [r.get('frequency_data') for r in individual_reports if r.get('frequency_data')],
            'common_sites_overall': common_sites_formatted
        }
        
    except Exception as e:
        job_results[timestamp] = {
            'status': 'failed',
            'error': str(e)
        }
        logger.error(f"Search task failed: {e}", exc_info=True)
    finally:
        background_jobs[timestamp]['completed'] = True

@app.route('/')
def index():
    try:
        site_names = []
        tag_options = []
        categories = []
        
        try:
            config = BlackbirdConfig()
            
            if os.path.exists(config.USERNAME_list_PATH):
                with open(config.USERNAME_list_PATH, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                site_names = sorted(set([
                    site.get('name', '') for site in data.get('sites', []) 
                    if site.get('name')
                ]))
                
                for site in data.get('sites', []):
                    tags = site.get('tags', [])
                    if isinstance(tags, list):
                        tag_options.extend(tags)
                    elif isinstance(tags, str):
                        tag_options.append(tags)
                
                tag_options = sorted(set(tag_options))
                
                if 'categories' in data:
                    categories = data['categories']
                else:
                    categories = sorted(set([
                        site.get('cat', '').strip() for site in data.get('sites', [])
                        if site.get('cat', '').strip()
                    ]))
            else:
                site_names = ["Twitter", "Facebook", "Instagram", "GitHub", "LinkedIn"]
                tag_options = ["social", "tech", "coding", "professional"]
                categories = ["social", "tech", "business", "coding", "gaming", "art", "misc"]
                
        except Exception as e:
            site_names = ["Twitter", "Facebook", "Instagram", "GitHub", "LinkedIn"]
            tag_options = ["social", "tech", "coding", "professional"]
            categories = ["social", "tech", "business", "coding", "gaming", "art", "misc"]
        
        email_site_names = []
        email_categories = []
        
        try:
            config = BlackbirdConfig()
            if os.path.exists(config.EMAIL_list_PATH):
                with open(config.EMAIL_list_PATH, 'r', encoding='utf-8') as f:
                    email_data = json.load(f)
                
                email_site_names = sorted(set([
                    site.get('name', '') for site in email_data.get('sites', []) 
                    if site.get('name')
                ]))
                
                email_categories = sorted(set([
                    site.get('cat', '').strip() for site in email_data.get('sites', [])
                    if site.get('cat', '').strip()
                ]))
            else:
                email_site_names = ["Have I Been Pwned", "DeHashed", "Hunter.io", "EmailRep", "BreachDirectory"]
                email_categories = ["security", "professional", "verification"]
        except Exception as e:
            email_site_names = ["Have I Been Pwned", "DeHashed", "Hunter.io", "EmailRep", "BreachDirectory"]
            email_categories = ["security", "professional", "verification"]
        
        category_icons = {
            "archived": "📁",
            "art": "🎨",
            "blog": "📝",
            "business": "💼",
            "coding": "💻",
            "dating": "❤️",
            "finance": "💰",
            "gaming": "🎮",
            "health": "🏥",
            "hobby": "🎨",
            "images": "🖼️",
            "misc": "📂",
            "music": "🎵",
            "news": "📰",
            "political": "🏛️",
            "search": "🔍",
            "security": "🔒",
            "professional": "💼",
            "verification": "✅",
            "shopping": "🛒",
            "social": "💬",
            "tech": "💻",
            "video": "🎥"
        }
        
        all_categories = sorted(set(categories + email_categories))
        category_data = []
        for category in all_categories:
            if category == "xx NSFW xx":
                continue
                
            icon = category_icons.get(category, "📁")
            display_name = category
            
            source = []
            if category in categories:
                source.append("username")
            if category in email_categories:
                source.append("email")
            
            category_data.append({
                'id': category,
                'name': display_name,
                'icon': icon,
                'source': '|'.join(source)
            })
        
        email_category_data = []
        for category in email_categories:
            icon = category_icons.get(category, "📧")
            email_category_data.append({
                'id': f"email_{category}",
                'name': f"{category} (Email)",
                'icon': icon,
                'source': 'email'
            })
        
        return render_template('index.html', 
                             site_options=site_names,
                             tag_options=tag_options,
                             categories=category_data,
                             email_site_options=email_site_names,
                             email_categories=email_category_data)
        
    except Exception as e:
        return render_template('index.html', 
                             site_options=[], 
                             tag_options=[], 
                             categories=[],
                             email_site_options=[],
                             email_categories=[])

@app.route('/search', methods=['POST'])
def search():
    try:
        enable_frequency = 'enable_frequency' in request.form
        show_common_sites = 'show_common_sites' in request.form
        search_type = 'username'
        search_input = ''
        
        if 'usernames' in request.form and request.form['usernames'].strip():
            search_type = 'username'
            search_input = request.form['usernames'].strip()
        elif 'emails' in request.form and request.form['emails'].strip():
            search_type = 'email'
            search_input = request.form['emails'].strip()
        else:
            flash('Please enter a username or email to search', 'danger')
            return redirect(url_for('index'))
        
        if not search_input:
            flash('Please enter a username or email to search', 'danger')
            return redirect(url_for('index'))
        
        search_items = [
            item.strip() for item in search_input.replace(',', ' ').split() 
            if item.strip()
        ]
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        selected_tags = request.form.getlist('tags')
        site_list = [
            s.strip() for s in request.form.get('site', '').split(',') 
            if s.strip()
        ]
        
        include_categories = request.form.get('include_categories', '')
        exclude_categories = request.form.get('exclude_categories', '')
        custom_filter = request.form.get('filter', '')
        
        filter_parts = []
        
        if include_categories:
            included = [c for c in include_categories.split(',') if c]
            if included:
                filter_parts.append(f'cat={("|".join(included))}')
        
        if exclude_categories:
            excluded = [c for c in exclude_categories.split(',') if c]
            if excluded:
                filter_parts.append(f'cat!=({"|".join(excluded)})')
        
        if custom_filter and custom_filter.strip():
            filter_parts.append(custom_filter.strip())
        
        final_filter = ' '.join(filter_parts) if filter_parts else None
        
        options = {
            'top_sites': request.form.get('top_sites', '500'),
            'timeout': request.form.get('timeout', '30'),
            'max_concurrent': request.form.get('max_concurrent', '30'),
            'proxy': request.form.get('proxy'),
            'tor_proxy': request.form.get('tor_proxy'),
            # 'i2p_proxy': request.form.get('i2p_proxy'),
            'all_sites': 'all_sites' in request.form,
            'no_nsfw': 'no_nsfw' in request.form,
            'dump': 'dump' in request.form,
            'save_csv': 'save_csv' in request.form,
            'save_json': 'save_json' in request.form,
            'save_pdf': 'save_pdf' in request.form,
            'ai': 'ai' in request.form,
            'verbose': 'verbose' in request.form,
            'tags': selected_tags,
            'site_list': site_list,
            'filter': final_filter,
            'include_categories': include_categories,
            'exclude_categories': exclude_categories,
            'enable_frequency': enable_frequency,
            'show_common_sites': show_common_sites
        }
        
        background_jobs[timestamp] = {
            'completed': False,
            'start_time': time.time(),  # Add this line
            'thread': Thread(
                target=process_search_task,
                args=(search_items, search_type, options, timestamp, enable_frequency)
            ),
            'enable_frequency': enable_frequency,
            'show_common_sites': show_common_sites
        }
        background_jobs[timestamp]['thread'].start()
        
        flash(f'Search started! Your search ID is: {timestamp}', 'info')
        return redirect(url_for('results', session_id=timestamp))
        
    except Exception as e:
        flash(f'Error starting search: {str(e)}', 'danger')
        return redirect(url_for('index'))

@app.route('/status/<timestamp>')
def status(timestamp):
    if timestamp not in background_jobs:
        flash('Invalid search session', 'danger')
        return redirect(url_for('index'))
    
    if background_jobs[timestamp]['completed']:
        result = job_results.get(timestamp)
        
        if not result:
            flash('No results found for this search session', 'warning')
            return redirect(url_for('index'))
        
        if result['status'] == 'completed':
            return redirect(url_for('results', session_id=timestamp))
        else:
            error_msg = result.get('error', 'Unknown error')
            flash(f'Search failed: {error_msg}', 'danger')
            return redirect(url_for('index'))
    
    return render_template('status.html', timestamp=timestamp)

@app.route('/results/<session_id>')
def results(session_id):
    try:
        get_flashed_messages()
        
        result_data = job_results.get(session_id)
        
        if not result_data:
            if session_id in background_jobs and not background_jobs[session_id]['completed']:
                return render_template('status.html', timestamp=session_id)
            else:
                flash('No results found for this session', 'danger')
                return redirect(url_for('index'))
        if result_data.get('status') != 'completed':
            error_msg = result_data.get('error', 'Unknown error')
            flash(f'Search failed: {error_msg}', 'danger')
            return redirect(url_for('index'))
        
        adapted_reports = []
        for report in result_data.get('individual_reports', []):
            adapted_report = {
                'username': report['username'],
                'search_type': report.get('search_type', 'username'),
                'folder_name': report.get('folder_name'),
                'claimed_profiles': report.get('claimed_profiles', []),
                'total_found': report.get('total_found', 0)
            }
            
            folder_name = report.get('folder_name', '')
            if report.get('csv_file'):
                adapted_report['csv_file'] = os.path.join(folder_name, report['csv_file'])
            if report.get('json_file'):
                adapted_report['json_file'] = os.path.join(folder_name, report['json_file'])
            if report.get('pdf_file'):
                adapted_report['pdf_file'] = os.path.join(folder_name, report['pdf_file'])
            
            adapted_reports.append(adapted_report)
        
        return render_template(
            'results.html',
            usernames=result_data['search_items'],
            search_type=result_data['search_type'],
            individual_reports=adapted_reports,
            timestamp=session_id,
            enable_frequency=result_data.get('enable_frequency', False),
            frequency_data=result_data.get('frequency_data', []),
            common_sites_overall=result_data.get('common_sites_overall', [])
        )
        
    except Exception as e:
        flash(f'Error loading results: {str(e)}', 'danger')
        return redirect(url_for('index'))

@app.route('/reports/<path:filename>')
def download_report(filename):
    try:
        path_parts = filename.split('/')
        if len(path_parts) == 1:
            file_path = None
            for root, dirs, files in os.walk(app.config["REPORTS_FOLDER"]):
                if filename in files:
                    file_path = os.path.join(root, filename)
                    break
            
            if not file_path:
                raise Exception(f"File not found: {filename}")
        else:
            file_path = os.path.normpath(
                os.path.join(app.config["REPORTS_FOLDER"], filename)
            )
        
        if not file_path.startswith(app.config["REPORTS_FOLDER"]):
            raise Exception("Invalid file path")
        
        if not os.path.exists(file_path):
            raise Exception(f"File not found: {file_path}")
        
        return send_file(file_path, as_attachment=True)
        
    except Exception as e:
        return "File not found", 404

@app.route('/api/site-tags')
def get_site_tags():
    try:
        config = BlackbirdConfig()
        
        if not os.path.exists(config.USERNAME_list_PATH):
            return {'tags': [], 'total_sites': 0, 'status': 'no_data'}
        
        with open(config.USERNAME_list_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        all_tags = set()
        for site in data.get('sites', []):
            tags = site.get('tags', [])
            if isinstance(tags, list):
                all_tags.update(tags)
            elif isinstance(tags, str):
                all_tags.add(tags)
        
        tags_list = sorted(all_tags)
        
        return {
            'tags': tags_list, 
            'total_sites': len(data.get('sites', [])),
            'status': 'success'
        }
        
    except Exception as e:
        return {'tags': [], 'error': str(e), 'status': 'error'}

@app.route('/api/stats')
def get_stats():
    try:
        stats = {
            'active_jobs': len([j for j in background_jobs.values() if not j.get('completed', True)]),
            'completed_jobs': len(job_results),
            'reports_folder': app.config["REPORTS_FOLDER"],
            'username_sites': 0,
            'email_sites': 0,
        }
        
        try:
            config = BlackbirdConfig()
            
            if os.path.exists(config.USERNAME_list_PATH):
                with open(config.USERNAME_list_PATH, 'r', encoding='utf-8') as f:
                    username_data = json.load(f)
                stats['username_sites'] = len(username_data.get('sites', []))
            
            if os.path.exists(config.EMAIL_list_PATH):
                with open(config.EMAIL_list_PATH, 'r', encoding='utf-8') as f:
                    email_data = json.load(f)
                stats['email_sites'] = len(email_data.get('sites', []))
                
        except Exception as e:
            pass
        
        return stats
        
    except Exception as e:
        return {'error': str(e)}

@app.route('/api/frequency/overview')
def get_frequency_overview():
    try:
        if not frequency_analyzer:
            return {'error': 'Frequency analyzer not initialized', 'status': 'error'}
        
        data = frequency_analyzer.scan_reports()
        
        response = {
            'total_reports': data.get('total_reports', 0),
            'total_accounts': data.get('total_accounts', 0),
            'unique_usernames': len(data.get('unique_usernames', [])),
            'unique_emails': len(data.get('unique_emails', [])),
            'unique_sites': len(data.get('unique_sites', [])),
            'most_common_sites': [],
            'last_scan': data.get('last_scan', 'Never'),
            'status': 'success'
        }
        
        top_sites = frequency_analyzer.get_most_common_sites(10)
        for site, count in top_sites:
            response['most_common_sites'].append({
                'site': site,
                'count': count
            })
        
        return response
        
    except Exception as e:
        return {'error': str(e), 'status': 'error'}

@app.route('/api/frequency/search')
def search_frequency_data():
    try:
        search_term = request.args.get('q', '')
        if not search_term:
            return {'error': 'No search term provided', 'status': 'error'}
        
        if not frequency_analyzer:
            return {'error': 'Frequency analyzer not initialized'}
        
        results = frequency_analyzer.search_historical_data(search_term)
        results['status'] = 'success'
        return results
        
    except Exception as e:
        return {'error': str(e), 'status': 'error'}

@app.route('/api/frequency/username-sites')
def get_username_sites():
    """Get all sites for a specific username"""
    username = request.args.get('username', '').strip()
    
    if not username:
        return jsonify({'error': 'Username is required'}), 400
    
    try:
        # Use the REPORTS_FOLDER from app config
        results_folder = app.config["REPORTS_FOLDER"]
        analyzer = FrequencyAnalyzer(results_folder)
        result = analyzer.get_username_sites(username)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/frequency/autocomplete')
def autocomplete_usernames():
    """Autocomplete usernames based on partial input"""
    search_term = request.args.get('q', '').strip().lower()
    
    if not search_term:
        return jsonify({'suggestions': []})
    
    try:
        # Use the REPORTS_FOLDER from app config
        results_folder = app.config["REPORTS_FOLDER"]
        analyzer = FrequencyAnalyzer(results_folder)
        if not analyzer.frequency_cache:
            analyzer.scan_reports()
        
        suggestions = []
        
        # Search in usernames
        for username in analyzer.frequency_cache.get('unique_usernames', []):
            if search_term in username.lower():
                suggestions.append({
                    'value': username,
                    'type': 'username',
                    'site_count': len(analyzer.frequency_cache.get('username_site_map', {}).get(f"username:{username}", []))
                })
        
        # Search in emails
        for email in analyzer.frequency_cache.get('unique_emails', []):
            if search_term in email.lower():
                suggestions.append({
                    'value': email,
                    'type': 'email',
                    'site_count': len(analyzer.frequency_cache.get('username_site_map', {}).get(f"email:{email}", []))
                })
        
        # Sort by relevance (exact match first, then by site count)
        suggestions.sort(key=lambda x: (
            0 if x['value'].lower().startswith(search_term) else 1,
            -x['site_count']
        ))
        
        return jsonify({'suggestions': suggestions[:10]})  # Limit to 10
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/frequency/username/<username>')
def get_username_frequency(username):
    try:
        if not frequency_analyzer:
            return {'error': 'Frequency analyzer not initialized'}
        
        freq_data = frequency_analyzer.get_username_frequency(username)
        freq_data['status'] = 'success'
        return freq_data
        
    except Exception as e:
        return {'error': str(e), 'status': 'error'}

@app.route('/api/frequency/site/<site_name>')
def get_site_frequency(site_name):
    try:
        if not frequency_analyzer:
            return {'error': 'Frequency analyzer not initialized'}
        
        freq_data = frequency_analyzer.get_site_frequency(site_name)
        freq_data['status'] = 'success'
        return freq_data
        
    except Exception as e:
        return {'error': str(e), 'status': 'error'}

@app.route('/api/check-search/<search_id>')
def check_search(search_id):
    """Check the status of a search job"""
    try:
        # Check if search exists in background jobs
        if search_id not in background_jobs:
            return jsonify({
                'status': 'not_found',
                'message': 'Search ID not found'
            }), 404
        
        job = background_jobs[search_id]
        
        # If job is completed, check results
        if job.get('completed', False):
            result = job_results.get(search_id)
            
            if not result:
                return jsonify({
                    'status': 'error',
                    'message': 'No results available'
                })
            
            if result.get('status') == 'completed':
                return jsonify({
                    'status': 'complete',
                    'message': 'Search completed successfully',
                    'results_available': True,
                    'total_items': len(result.get('search_items', [])),
                    'individual_reports': len(result.get('individual_reports', []))
                })
            elif result.get('status') == 'failed':
                return jsonify({
                    'status': 'error',
                    'message': result.get('error', 'Search failed'),
                    'results_available': False
                })
            else:
                return jsonify({
                    'status': 'processing',
                    'progress': 95,
                    'message': 'Finishing up...'
                })
        
        # Job is still running, estimate progress
        # This is a rough estimate - you could make it more accurate if you track progress
        total_estimated_time = 180  # 3 minutes max
        elapsed_time = 0
        
        # Calculate elapsed time if we have start time
        if 'start_time' in job:
            elapsed_time = time.time() - job['start_time']
        else:
            # Use a fallback based on when the job was created
            job['start_time'] = time.time()
            elapsed_time = 0
        
        progress = min(int((elapsed_time / total_estimated_time) * 100), 95)
        
        if progress < 25:
            message = "Starting search..."
        elif progress < 50:
            message = "Gathering site data..."
        elif progress < 75:
            message = "Checking sites..."
        else:
            message = "Processing results..."
        
        return jsonify({
            'status': 'processing',
            'progress': progress,
            'message': message,
            'elapsed_time': int(elapsed_time)
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Error checking status: {str(e)}'
        }), 500

@app.route('/api/breachvip/search', methods=['POST'])
def proxy_breachvip_search():
    """Proxy requests to BreachVIP API to avoid CORS issues"""
    try:
        # Get the search data from the request
        search_data = request.get_json()
        if not search_data:
            return jsonify({'error': 'No search data provided'}), 400
        
        # Rate limiting check (server-side)
        client_ip = request.remote_addr
        rate_limit_key = f'breachvip_rate_limit_{client_ip}'
        
        # Check if client made a request recently (15 second cooldown)
        last_request = app.config.get(rate_limit_key, 0)
        current_time = time.time()
        
        if current_time - last_request < 15:  # 15 seconds
            wait_time = int(15 - (current_time - last_request))
            return jsonify({
                'error': f'Rate limited. Please wait {wait_time} seconds before trying again.',
                'retry_after': wait_time
            }), 429
        
        # Update rate limit timestamp
        app.config[rate_limit_key] = current_time
        
        # Forward request to BreachVIP API
        api_url = 'https://breach.vip/api/search'
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Blackbird-Web/1.0'
        }
        
        # Make the request with a timeout
        response = requests.post(
            api_url,
            json=search_data,
            headers=headers,
            timeout=30  # 30 second timeout
        )
        
        # Return the response from BreachVIP
        return jsonify(response.json()), response.status_code
        
    except requests.exceptions.Timeout:
        return jsonify({'error': 'Request to BreachVIP API timed out'}), 504
    except requests.exceptions.RequestException as e:
        return jsonify({'error': f'Network error: {str(e)}'}), 502
    except Exception as e:
        return jsonify({'error': f'Server error: {str(e)}'}), 500

# Add a cleanup function for old rate limit data
@app.before_request
def cleanup_rate_limits():
    """Clean up old rate limit entries"""
    current_time = time.time()
    keys_to_delete = []
    
    for key in list(app.config.keys()):
        if key.startswith('breachvip_rate_limit_'):
            timestamp = app.config[key]
            if current_time - timestamp > 300:  # Clean up entries older than 5 minutes
                keys_to_delete.append(key)
    
    for key in keys_to_delete:
        app.config.pop(key, None)

@app.route('/health')
def health():
    return {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'jobs': len(background_jobs),
        'completed_jobs': len(job_results),
    }

if __name__ == '__main__':
    print("Starting Blackbird Web Interface")
    
    # Create logs directory
    log_dir = os.path.join(CURRENT_DIR, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    print(f"Logs directory: {log_dir}")
    
    blackbird_root = find_blackbird_root()
    
    if blackbird_root:
        src_dir = os.path.join(blackbird_root, 'src')
        if os.path.exists(src_dir):
            sys.path.insert(0, src_dir)
        sys.path.insert(0, blackbird_root)
    
    load_blackbird_modules()
    init_frequency_analyzer()
    
    debug_mode = os.getenv('FLASK_DEBUG', 'True').lower() in ['true', '1', 't']
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', '5000'))
    
    print(f"Starting server on {host}:{port} (debug: {debug_mode})")
    print(f"Reports folder: {app.config['REPORTS_FOLDER']}")
    
    app.run(host=host, port=port, debug=True)