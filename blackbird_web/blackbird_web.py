from flask import (
    Flask,
    render_template,
    request,
    send_file,
    flash,
    redirect,
    url_for,
    get_flashed_messages,
)
import logging
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

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# Get the current directory
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# Configuration matching Blackbird's config
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
        
        # Asset paths
        self.ASSETS_DIRECTORY = BLACKBIRD_ASSETS_DIR if BLACKBIRD_ASSETS_DIR else "assets"
        self.FONTS_DIRECTORY = "fonts"
        self.FONT_REGULAR_FILE = "Montserrat-Regular.ttf"
        self.FONT_BOLD_FILE = "Montserrat-Bold.ttf"
        self.FONT_NAME_REGULAR = "Montserrat"
        self.FONT_NAME_BOLD = "Montserrat-Bold"
        self.IMAGES_DIRECTORY = "img"
        
        # AI configuration
        self.ai_analysis = None
        
        # Find data files
        self.USERNAME_list_PATH = self._find_data_file('wmn-data.json')
        self.EMAIL_list_PATH = self._find_data_file('email-data.json')
        self.USERNAME_METADATA_list_PATH = self._find_data_file('wmn-metadata.json')
        self.USERNAME_list_URL = "https://raw.githubusercontent.com/WebBreacher/WhatsMyName/main/wmn-data.json"
        
        # Initialize lists
        self.username_sites = []
        self.email_sites = []  # Add this for email search
        self.metadata_params = {}
        self.include_categories = []
        self.exclude_categories = []
        
        print(f"Username list path: {self.USERNAME_list_PATH}")
        print(f"Email list path: {self.EMAIL_list_PATH}")
        print(f"Metadata path: {self.USERNAME_METADATA_list_PATH}")
    
    def _find_data_file(self, filename):
        """Find Blackbird data files in common locations"""
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
        
        # If not found, create empty file in current directory
        fallback_path = os.path.join(CURRENT_DIR, 'data', filename)
        os.makedirs(os.path.dirname(fallback_path), exist_ok=True)
        if not os.path.exists(fallback_path):
            with open(fallback_path, 'w') as f:
                json.dump({"sites": []}, f)
        return fallback_path

# Find Blackbird assets
def find_blackbird_assets():
    """Find Blackbird assets directory"""
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
            print(f"Found assets at: {abs_path}")
            return abs_path
    
    print("Warning: Could not find Blackbird assets directory")
    return None

BLACKBIRD_ASSETS_DIR = find_blackbird_assets()

def find_blackbird_root():
    """Find the Blackbird installation root directory - Universal version"""
    print("\n[Searching for Blackbird installation...]")
    
    # list of signatures that identify a Blackbird installation
    SIGNATURES = [
        ('blackbird.py', 'main script'),
        (os.path.join('src', 'modules'), 'modules directory'),
        ('data/wmn-data.json', 'username data file'),
        ('assets', 'assets directory'),
        ('requirements.txt', 'requirements file with blackbird'),
    ]
    
    # Helper function to check if a directory is a Blackbird installation
    def is_blackbird_dir(directory):
        """Check if directory contains Blackbird signatures"""
        for signature, description in SIGNATURES:
            path = os.path.join(directory, signature)
            if os.path.exists(path):
                return True, f"contains {description}"
        return False, None
    
    # 1. Check current directory and parents
    current_dir = os.path.abspath(CURRENT_DIR)
    for i in range(5):  # Check up to 5 levels up
        is_bb, reason = is_blackbird_dir(current_dir)
        if is_bb:
            print(f"✓ Found Blackbird at: {current_dir} ({reason})")
            return current_dir
        
        # Move up one directory
        parent = os.path.dirname(current_dir)
        if parent == current_dir:  # Reached filesystem root
            break
        current_dir = parent
    
    # 2. Check common installation paths
    common_paths = []
    
    # Add user home paths
    home = os.path.expanduser("~")
    common_paths.extend([
        os.path.join(home, 'blackbird'),
        os.path.join(home, '.blackbird'),
        os.path.join(home, '.local', 'share', 'blackbird'),
        os.path.join(home, '.local', 'lib', 'blackbird'),
        os.path.join(home, 'Desktop', 'blackbird'),
        os.path.join(home, 'Documents', 'blackbird'),
        os.path.join(home, 'Projects', 'blackbird'),
    ])
    
    # Add system paths
    common_paths.extend([
        '/usr/local/share/blackbird',
        '/usr/local/lib/blackbird',
        '/usr/share/blackbird',
        '/usr/lib/blackbird',
        '/opt/blackbird',
    ])
    
    # Add paths based on current directory structure
    script_dir = os.path.dirname(os.path.abspath(__file__))
    common_paths.extend([
        os.path.join(script_dir, '..', '..', 'blackbird'),
        os.path.join(script_dir, '..', 'blackbird'),
        os.path.join(script_dir, 'blackbird'),
    ])
    
    # Check all common paths
    for path in common_paths:
        abs_path = os.path.abspath(path)
        if os.path.exists(abs_path):
            is_bb, reason = is_blackbird_dir(abs_path)
            if is_bb:
                print(f"✓ Found Blackbird at: {abs_path} ({reason})")
                return abs_path
    
    # 3. Check environment variable
    env_path = os.environ.get('BLACKBIRD_PATH')
    if env_path and os.path.exists(env_path):
        abs_env_path = os.path.abspath(env_path)
        is_bb, reason = is_blackbird_dir(abs_env_path)
        if is_bb:
            print(f"✓ Found Blackbird from BLACKBIRD_PATH: {abs_env_path} ({reason})")
            return abs_env_path
    
    # 4. Try to import as package (if installed via pip)
    try:
        import blackbird
        package_path = os.path.dirname(os.path.abspath(blackbird.__file__))
        print(f"✓ Found Blackbird package at: {package_path}")
        return package_path
    except ImportError:
        pass
    
    print("✗ Could not find Blackbird installation")
    print("\nTo fix this:")
    print("1. Set the BLACKBIRD_PATH environment variable:")
    print("   export BLACKBIRD_PATH=/path/to/your/blackbird")
    print("2. Run this script from within the blackbird directory")
    print("3. Or install blackbird with: pip install blackbird-osint")
    
    return None

def load_blackbird_modules():
    """Load Blackbird modules with direct path to your installation"""
    
    print("\n=== Loading Blackbird Modules ===")
    
    # First, find the blackbird root
    blackbird_root = find_blackbird_root()
    
    if not blackbird_root:
        print("✗ Could not find Blackbird installation")
        create_minimal_mocks()
        return False
    
    print(f"✓ Found Blackbird at: {blackbird_root}")
    
    # Check if we need to add src directory to sys.path
    src_dir = os.path.join(blackbird_root, 'src')
    if os.path.exists(src_dir):
        if src_dir not in sys.path:
            sys.path.insert(0, src_dir)
            print(f"✓ Added src directory to sys.path: {src_dir}")
    
    # Also add the blackbird_root itself to sys.path
    if blackbird_root not in sys.path:
        sys.path.insert(0, blackbird_root)
        print(f"✓ Added blackbird root to sys.path: {blackbird_root}")
    
    # Try to import modules
    try:
        import modules
        print("✓ Successfully imported Blackbird modules")
        
        # Test specific imports
        test_modules = [
            ('modules.utils.http_client', 'HTTP Client'),
            ('modules.utils.parse', 'Parse'),
            ('modules.utils.filter', 'Filter'),
            ('modules.whatsmyname.list_operations', 'list Operations'),
            ('modules.core.email', 'Email Module'),
        ]
        
        print("\nModule import status:")
        for module_name, display_name in test_modules:
            try:
                __import__(module_name)
                print(f"  {display_name}: ✓")
            except ImportError as e:
                print(f"  {display_name}: ✗ ({e})")
        
        return True
        
    except ImportError as e:
        print(f"✗ Error importing modules: {e}")
        print("\nTrying alternative import strategy...")
        
        # Try to import specific modules directly
        try:
            # Check for modules in the src directory
            modules_dir = os.path.join(blackbird_root, 'src', 'modules')
            if os.path.exists(modules_dir):
                print(f"Found modules directory at: {modules_dir}")
                
                # Create mock modules for web interface
                create_minimal_mocks()
                return False
            else:
                print(f"Modules directory not found at: {modules_dir}")
                create_minimal_mocks()
                return False
                
        except Exception as e2:
            print(f"✗ Alternative strategy failed: {e2}")
            create_minimal_mocks()
            return False

def create_minimal_mocks():
    """Create minimal mock modules for essential functionality"""
    
    # Create mock modules module
    mock_modules = type(sys)('modules')
    
    # Create mock utils module
    mock_utils = type(sys)('modules.utils')
    
    # Add http_client mock
    class MockHTTPClient:
        @staticmethod
        async def do_async_request(method, url, session, config, **kwargs):
            # Simple implementation
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
                print(f"Mock request error: {e}")
                return None
    
    mock_utils.http_client = type(sys)('http_client')
    mock_utils.http_client.do_async_request = MockHTTPClient.do_async_request
    
    # Add parse mock
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
    
    # Add filter mock
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
    
    # Add log mock
    class MockLog:
        @staticmethod
        def logError(e, msg, config):
            print(f"[ERROR] {msg}: {e}")
    
    mock_utils.log = type(sys)('log')
    mock_utils.log.logError = MockLog.logError
    
    # Add input mock
    class MockInput:
        @staticmethod
        def processInput(value, operation, config):
            return value
    
    mock_utils.input = type(sys)('input')
    mock_utils.input.processInput = MockInput.processInput
    
    # Add precheck mock
    class MockPrecheck:
        @staticmethod
        def perform_pre_check(pre_check_config, headers, config):
            return headers
    
    mock_utils.precheck = type(sys)('precheck')
    mock_utils.precheck.perform_pre_check = MockPrecheck.perform_pre_check
    
    # Add dump mock
    class MockDump:
        @staticmethod
        def dumpContent(path, site, response, config):
            return True
    
    mock_utils.dump = type(sys)('dump')
    mock_utils.dump.dumpContent = MockDump.dumpContent
    
    # Create mock whatsmyname module
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
    
    # Create mock core module with email function
    mock_core = type(sys)('modules.core')
    mock_core.email = type(sys)('modules.core.email')
    
    class MockEmail:
        @staticmethod
        def verifyEmail(email, config):
            print(f"Mock email verification for: {email}")
            # Return mock results
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
    
    # Add to sys.modules
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
    
    print("✓ Created minimal mock modules")

def setup_blackbird_module_system():
    """Set up the module system to load Blackbird modules properly"""
    
    print("\n=== Setting up Blackbird Module System ===")
    
    blackbird_root = find_blackbird_root()
    
    if blackbird_root:
        # Add both blackbird_root and src directory to sys.path
        if blackbird_root not in sys.path:
            sys.path.insert(0, blackbird_root)
            print(f"✓ Added blackbird_root to sys.path: {blackbird_root}")
        
        src_dir = os.path.join(blackbird_root, 'src')
        if os.path.exists(src_dir) and src_dir not in sys.path:
            sys.path.insert(0, src_dir)
            print(f"✓ Added src directory to sys.path: {src_dir}")
        
        return src_dir if os.path.exists(src_dir) else blackbird_root
    
    print("✗ Could not find Blackbird installation")
    return None

def import_blackbird_module(module_path, module_name=None):
    """Import a Blackbird module with proper path handling"""
    try:
        if module_name:
            # Try regular import
            try:
                full_path = module_path.replace('/', '.')
                if full_path.startswith('.'):
                    full_path = full_path[1:]
                module = __import__(full_path, fromlist=[''])
                print(f"Successfully imported {full_path}")
                return module
            except ImportError:
                pass
        
        # Try file-based import
        if os.path.exists(module_path):
            spec = importlib.util.spec_from_file_location(
                module_name or os.path.basename(module_path).replace('.py', ''),
                module_path
            )
            if spec:
                module = importlib.util.module_from_spec(spec)
                
                # Inject common dependencies
                module.__dict__.update({
                    'sys': sys,
                    'os': os,
                    'json': json,
                    'logging': logging,
                    'traceback': traceback,
                    're': re,
                    'hashlib': hashlib,
                    'requests': requests,
                    'asyncio': asyncio,
                    'aiohttp': aiohttp,
                    'chardet': chardet,
                })
                
                # Execute the module
                spec.loader.exec_module(module)
                print(f"Loaded module from file: {module_path}")
                return module
        
        print(f"Failed to import module: {module_path}")
        return None
        
    except Exception as e:
        print(f"Error importing module {module_path}: {e}")
        traceback.print_exc()
        return None

# Create a proper Console wrapper
class WebConsole:
    """A console wrapper that mimics Rich's Console for web interface"""
    def __init__(self):
        self.output = []
        self.is_terminal = False
        self.is_interactive = False
        self.is_jupyter = False  # Add this attribute
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
    
    def print(self, message, **kwargs):
        msg = str(message)
        self.output.append(msg)
        print(f"[CONSOLE] {msg}")
    
    def set_live(self, live):
        """Mock set_live method for Rich compatibility"""
        pass
    
    def clear(self):
        """Mock clear method"""
        pass
    
    def show_cursor(self, show=True):
        """Mock show_cursor method"""
        pass
    
    def bell(self):
        """Mock bell method"""
        pass
    
    # Add other Rich Console methods that might be called
    def begin_capture(self):
        """Begin capturing output"""
        pass
    
    def end_capture(self):
        """End capturing output"""
        return ""
    
    def get_style(self, name):
        """Mock get_style method"""
        return None
    
    def push_theme(self, theme):
        """Mock push_theme method"""
        pass
    
    def pop_theme(self):
        """Mock pop_theme method"""
        pass
    
    def status(self, status):
        """Mock status method"""
        return self
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
    
    def update(self, renderable):
        """Mock update method for Live display"""
        pass

# Create mock implementations for missing functions
def create_simple_async_request():
    """Create a simple async request function"""
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
                
                # Try to parse as JSON
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
            print(f"Request error for {url}: {e}")
            return None
    
    return simple_do_async_request

def create_simple_extract_metadata():
    """Create a simple metadata extraction function"""
    def simple_extract_metadata(metadata_config, response, site_name, config):
        print(f"Metadata extraction for {site_name} (simplified)")
        # Return empty metadata for now
        return []
    
    return simple_extract_metadata

def simple_remove_duplicates(items):
    """Simple duplicate removal"""
    seen = set()
    unique = []
    for item in items:
        identifier = str(item)
        if identifier not in seen:
            seen.add(identifier)
            unique.append(item)
    return unique

# Frequency Analyzer Class
class FrequencyAnalyzer:
    """Analyze frequency of usernames across historical search results"""
    
    def __init__(self, reports_folder: str):
        """
        Initialize the analyzer with the reports folder
        
        Args:
            reports_folder: Path to the folder containing Blackbird results
        """
        self.reports_folder = Path(reports_folder)
        self.username_cache = {}  # Cache for username lookups
        self.frequency_cache = {}  # Cache for frequency data
        self.cache_file = self.reports_folder / ".frequency_cache.json"
        self.last_scan_time = None
        
        # Load cache if exists
        self._load_cache()
    
    def _load_cache(self):
        """Load frequency cache from file"""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r') as f:
                    cache_data = json.load(f)
                    self.frequency_cache = cache_data.get('frequency_data', {})
                    self.last_scan_time = cache_data.get('last_scan_time')
                    print(f"Loaded frequency cache with {len(self.frequency_cache)} entries")
        except Exception as e:
            print(f"Error loading cache: {e}")
            self.frequency_cache = {}
    
    def _save_cache(self):
        """Save frequency cache to file"""
        try:
            cache_data = {
                'frequency_data': self.frequency_cache,
                'last_scan_time': datetime.now().isoformat(),
                'version': '1.0'
            }
            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
            print(f"Saved frequency cache with {len(self.frequency_cache)} entries")
        except Exception as e:
            print(f"Error saving cache: {e}")
    
    def scan_reports(self, force_rescan: bool = False) -> dict:
        """
        Scan all reports and build frequency statistics
        
        Args:
            force_rescan: If True, rescan all files even if cache exists
            
        Returns:
            dictionary with frequency statistics
        """
        # Check if we need to rescan
        if not force_rescan and self.frequency_cache and self._is_cache_fresh():
            print("Using cached frequency data")
            return self.frequency_cache
        
        print("Scanning reports for frequency analysis...")
        
        # Initialize statistics
        frequency_data = {
            'total_reports': 0,
            'total_accounts': 0,
            'unique_usernames': set(),
            'unique_emails': set(),
            'unique_sites': set(),
            'site_frequency': defaultdict(int),  # site -> count
            'username_frequency': defaultdict(int),  # username -> total sites found
            'username_site_map': defaultdict(set),  # username -> set of sites
            'site_username_map': defaultdict(set),  # site -> set of usernames
            'category_frequency': defaultdict(int),  # category -> count
            'recent_searches': [],  # Most recent searches
            'search_timeline': defaultdict(list),  # date -> list of searches
            'last_scan': datetime.now().isoformat()
        }
        
        # Find all JSON and CSV files
        json_files = list(self.reports_folder.rglob("*.json"))
        csv_files = list(self.reports_folder.rglob("*.csv"))
        
        print(f"Found {len(json_files)} JSON files and {len(csv_files)} CSV files")
        
        # Process JSON files
        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Extract username/email from filename
                filename = json_file.stem
                username_match = re.match(r'^([^_]+)_', filename)
                if username_match:
                    username = username_match.group(1)
                    
                    # Check if this is email or username
                    is_email = '@' in username
                    
                    if is_email:
                        frequency_data['unique_emails'].add(username)
                        identifier = f"email:{username}"
                    else:
                        frequency_data['unique_usernames'].add(username)
                        identifier = f"username:{username}"
                    
                    frequency_data['total_reports'] += 1
                    
                    # Process found accounts
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
                    
                    # Add to timeline
                    try:
                        # Extract date from folder structure
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
                print(f"Error processing {json_file}: {e}")
                continue
        
        # Process CSV files
        for csv_file in csv_files:
            try:
                # Skip if we already processed the JSON version
                json_version = csv_file.with_suffix('.json')
                if json_version.exists():
                    continue
                
                # Extract username/email from filename
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
                    
                    # Read CSV
                    with open(csv_file, 'r', encoding='utf-8') as f:
                        reader = csv.dictReader(f)
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
                print(f"Error processing {csv_file}: {e}")
                continue
        
        # Convert sets to lists for JSON serialization
        frequency_data['unique_usernames'] = list(frequency_data['unique_usernames'])
        frequency_data['unique_emails'] = list(frequency_data['unique_emails'])
        frequency_data['unique_sites'] = list(frequency_data['unique_sites'])
        
        # Convert defaultdict to regular dict
        frequency_data['site_frequency'] = dict(frequency_data['site_frequency'])
        frequency_data['username_frequency'] = dict(frequency_data['username_frequency'])
        frequency_data['username_site_map'] = {k: list(v) for k, v in frequency_data['username_site_map'].items()}
        frequency_data['site_username_map'] = {k: list(v) for k, v in frequency_data['site_username_map'].items()}
        frequency_data['category_frequency'] = dict(frequency_data['category_frequency'])
        frequency_data['search_timeline'] = dict(frequency_data['search_timeline'])
        
        # Get recent searches (last 10)
        all_searches = []
        for date_str, searches in frequency_data['search_timeline'].items():
            for search in searches:
                search['date'] = date_str
                all_searches.append(search)
        
        # Sort by timestamp (most recent first)
        all_searches.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        frequency_data['recent_searches'] = all_searches[:10]
        
        # Update cache
        self.frequency_cache = frequency_data
        self._save_cache()
        
        print(f"Frequency analysis complete:")
        print(f"  - Total reports: {frequency_data['total_reports']}")
        print(f"  - Unique usernames: {len(frequency_data['unique_usernames'])}")
        print(f"  - Unique emails: {len(frequency_data['unique_emails'])}")
        print(f"  - Unique sites: {len(frequency_data['unique_sites'])}")
        print(f"  - Total accounts found: {frequency_data['total_accounts']}")
        
        return frequency_data
    
    def _is_cache_fresh(self, max_age_hours: int = 1) -> bool:
        """Check if cache is fresh enough"""
        if not self.last_scan_time:
            return False
        
        try:
            last_scan = datetime.fromisoformat(self.last_scan_time)
            age = datetime.now() - last_scan
            return age.total_seconds() < (max_age_hours * 3600)
        except:
            return False
    
    def get_username_frequency(self, username: str) -> dict:
        """
        Get frequency statistics for a specific username
        
        Args:
            username: Username to analyze
            
        Returns:
            dictionary with frequency statistics for the username
        """
        # Ensure we have fresh data
        if not self.frequency_cache:
            self.scan_reports()
        
        # Check both username and email formats
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
        
        # Get category distribution
        for site in result['sites_found']:
            # Try to get category from site data
            # This would require additional data - for now we'll skip
            pass
        
        # Get search history from timeline
        for date_str, searches in self.frequency_cache.get('search_timeline', {}).items():
            for search in searches:
                if search['username'] == username:
                    result['search_history'].append({
                        'date': date_str,
                        'accounts_found': search['accounts_found'],
                        'file': search['file']
                    })
        
        # Sort search history by date
        result['search_history'].sort(key=lambda x: x['date'], reverse=True)
        
        # Get first and last seen
        if result['search_history']:
            result['first_seen'] = result['search_history'][-1]['date']
            result['last_seen'] = result['search_history'][0]['date']
        
        return result
    
    def get_site_frequency(self, site_name: str) -> dict:
        """
        Get frequency statistics for a specific site
        
        Args:
            site_name: Site name to analyze
            
        Returns:
            dictionary with frequency statistics for the site
        """
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
        
        # Calculate popularity rank
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
        
        # Calculate percentage
        total_accounts = self.frequency_cache.get('total_accounts', 1)
        result['percentage_of_searches'] = (result['total_found'] / total_accounts * 100) if total_accounts > 0 else 0
        
        return result
    
    def get_most_common_sites(self, limit: int = 10) -> list[tuple[str, int]]:
        """Get most commonly found sites"""
        if not self.frequency_cache:
            self.scan_reports()
        
        site_freq = self.frequency_cache.get('site_frequency', {})
        return sorted(site_freq.items(), key=lambda x: x[1], reverse=True)[:limit]
    
    def get_most_active_usernames(self, limit: int = 10) -> list[tuple[str, int]]:
        """Get usernames found on most sites"""
        if not self.frequency_cache:
            self.scan_reports()
        
        username_freq = {}
        for identifier, sites in self.frequency_cache.get('username_site_map', {}).items():
            username_freq[identifier] = len(sites)
        
        return sorted(username_freq.items(), key=lambda x: x[1], reverse=True)[:limit]
    
    def search_historical_data(self, search_term: str) -> dict:
        """
        Search historical data for usernames or sites containing search term
        
        Args:
            search_term: Term to search for
            
        Returns:
            Search results
        """
        if not self.frequency_cache:
            self.scan_reports()
        
        results = {
            'usernames': [],
            'emails': [],
            'sites': [],
            'total_matches': 0
        }
        
        search_term_lower = search_term.lower()
        
        # Search usernames
        for username in self.frequency_cache.get('unique_usernames', []):
            if search_term_lower in username.lower():
                freq_data = self.get_username_frequency(username)
                results['usernames'].append({
                    'username': username,
                    'site_count': freq_data['site_count'],
                    'first_seen': freq_data['first_seen'],
                    'last_seen': freq_data['last_seen']
                })
        
        # Search emails
        for email in self.frequency_cache.get('unique_emails', []):
            if search_term_lower in email.lower():
                freq_data = self.get_username_frequency(email)
                results['emails'].append({
                    'email': email,
                    'site_count': freq_data['site_count'],
                    'first_seen': freq_data['first_seen'],
                    'last_seen': freq_data['last_seen']
                })
        
        # Search sites
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
    
    def get_overall_statistics(self) -> dict:
        """Get overall statistics"""
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

# Initialize frequency analyzer
frequency_analyzer = None

def init_frequency_analyzer():
    """Initialize frequency analyzer"""
    global frequency_analyzer
    try:
        frequency_analyzer = FrequencyAnalyzer(app.config["REPORTS_FOLDER"])
        print(f"✓ Frequency analyzer initialized")
        
        # Do initial scan in background
        def background_scan():
            try:
                frequency_analyzer.scan_reports()
                print("✓ Initial frequency scan completed")
            except Exception as e:
                print(f"✗ Initial frequency scan failed: {e}")
        
        Thread(target=background_scan).start()
        return True
    except Exception as e:
        print(f"✗ Failed to initialize frequency analyzer: {e}")
        return False

# Reports folder
app.config["REPORTS_FOLDER"] = os.path.abspath('../results/')
os.makedirs(app.config["REPORTS_FOLDER"], exist_ok=True)

def setup_logger():
    logger = logging.getLogger('blackbird-web')
    logger.setLevel(logging.INFO)
    return logger

logger = setup_logger()

# Background job tracking
background_jobs = {}
job_results = {}

async def simple_fetch_results(username, config):
    """A simplified version of fetchResults for web interface"""
    try:
        if config.verbose:
            print(f"VERBOSE: Starting fetch for username: {username}")
        
        # Import required utils or create fallbacks
        try:
            # Try to import the actual modules
            from modules.utils.http_client import do_async_request
            from modules.utils.parse import extractMetadata, remove_duplicates
            if config.verbose:
                print("VERBOSE: Successfully imported Blackbird utils")
        except ImportError as e:
            if config.verbose:
                print(f"VERBOSE: Import failed, using fallbacks: {e}")
            do_async_request = create_simple_async_request()
            extractMetadata = create_simple_extract_metadata()
            remove_duplicates = simple_remove_duplicates
        
        async with aiohttp.ClientSession() as session:
            results = []
            
            async def check_site(site):
                try:
                    # Build URL
                    url = site["uri_check"].replace("{account}", username)
                    
                    if config.verbose:
                        print(f"VERBOSE: Checking: {site.get('name', 'unknown')}")
                        print(f"VERBOSE: URL: {url}")
                        print(f"VERBOSE: e_string: {site.get('e_string', 'N/A')}")
                        print(f"VERBOSE: e_code: {site.get('e_code', 'N/A')}")
                    
                    # Make request
                    response = await do_async_request(
                        "GET",
                        url,
                        session,
                        config
                    )
                    
                    if response is None:
                        if config.verbose:
                            print(f"VERBOSE: No response for {site.get('name', 'unknown')}")
                        return {
                            "name": site.get("name", "unknown"),
                            "url": url,
                            "category": site.get("cat", "unknown"),
                            "status": "ERROR",
                            "metadata": None
                        }
                    
                    # Check if account exists
                    e_string = site.get("e_string", "")
                    e_code = site.get("e_code", 200)
                    m_string = site.get("m_string", "")
                    m_code = site.get("m_code", 404)
                    
                    content = response.get("content", "")
                    status_code = response.get("status_code", 0)
                    
                    if config.verbose:
                        print(f"VERBOSE: Status code: {status_code}, Content length: {len(content)}")
                        print(f"VERBOSE: e_string in content: {e_string in content}")
                        print(f"VERBOSE: Status code matches e_code: {status_code == e_code}")
                    
                    account_found = (
                        e_string in content and 
                        (e_code == status_code or e_code == 0)
                    )
                    
                    if account_found:
                        # Check for non-match string/code
                        account_not_found = (
                            m_string in content or
                            (m_code == status_code and m_code != e_code)
                        )
                        
                        if config.verbose:
                            print(f"VERBOSE: m_string in content: {m_string in content}")
                            print(f"VERBOSE: Status code matches m_code: {status_code == m_code}")
                            print(f"VERBOSE: Account not found check: {account_not_found}")
                        
                        if not account_not_found:
                            result = {
                                "name": site.get("name", "unknown"),
                                "url": response.get("url", url),
                                "category": site.get("cat", "unknown"),
                                "status": "FOUND",
                                "metadata": None
                            }
                            
                            # Try to extract metadata
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
                                    print(f"VERBOSE: Metadata extraction failed: {e}")
                            
                            if config.verbose:
                                print(f"VERBOSE: ✓ Found on {site.get('name', 'unknown')}")
                            return result
                    
                    if config.verbose:
                        print(f"VERBOSE: ✗ NOT FOUND on {site.get('name', 'unknown')}")
                    
                    return {
                        "name": site.get("name", "unknown"),
                        "url": response.get("url", url),
                        "category": site.get("cat", "unknown"),
                        "status": "NOT-FOUND",
                        "metadata": None
                    }
                    
                except Exception as e:
                    if config.verbose:
                        print(f"VERBOSE: Error checking site {site.get('name', 'unknown')}: {e}")
                    return {
                        "name": site.get("name", "unknown"),
                        "url": url,
                        "category": site.get("cat", "unknown"),
                        "status": "ERROR",
                        "metadata": None
                    }
            
            # Process sites concurrently
            if config.verbose:
                print(f"VERBOSE: Processing {len(config.username_sites)} sites with {config.max_concurrent_requests} concurrent requests")
            
            tasks = []
            for site in config.username_sites:
                task = asyncio.create_task(check_site(site))
                tasks.append(task)
            
            # Wait for all tasks
            results = await asyncio.gather(*tasks)
            
            if config.verbose:
                found = len([r for r in results if r.get("status") == "FOUND"])
                not_found = len([r for r in results if r.get("status") == "NOT-FOUND"])
                errors = len([r for r in results if r.get("status") == "ERROR"])
                print(f"VERBOSE: Completed all checks. Found: {found}, Not Found: {not_found}, Errors: {errors}")
            
            return {
                "results": results,
                "username": username,
                "total_checked": len(results)
            }
            
    except Exception as e:
        if config.verbose:
            print(f"VERBOSE: Error in simple_fetch_results: {e}")
            traceback.print_exc()
        return {"results": [], "username": username, "total_checked": 0}

def parse_blackbird_filter(filter_string):
    """Parse Blackbird filter syntax into structured data"""
    if not filter_string:
        return {}
    
    filters = {}
    parts = filter_string.split()
    
    for part in parts:
        if '~' in part:
            key, value = part.split('~', 1)
            filters[key] = {'type': 'contains', 'values': value.split('|')}
        elif '!=' in part:
            key, value = part.split('!=', 1)
            filters[key] = {'type': 'not_equal', 'values': value.split('|')}
        elif '=' in part:
            key, value = part.split('=', 1)
            filters[key] = {'type': 'equal', 'value': value}
        else:
            # Simple text search
            filters['_search'] = {'type': 'search', 'value': part}
    
    return filters

def apply_category_filters(sites, include_categories, exclude_categories):
    """Apply category filters to sites list"""
    if not include_categories and not exclude_categories:
        return sites
    
    filtered_sites = []
    
    for site in sites:
        site_category = site.get('cat', '').lower()
        
        # Check if site should be included
        include = True
        
        # Apply include categories (if any specified)
        if include_categories:
            include = False
            for cat in include_categories:
                if cat.lower() in site_category or cat.lower() == site_category:
                    include = True
                    break
        
        # Apply exclude categories (if still included)
        if include and exclude_categories:
            for cat in exclude_categories:
                if cat.lower() in site_category or cat.lower() == site_category:
                    include = False
                    break
        
        if include:
            filtered_sites.append(site)
    
    return filtered_sites

async def search_username_blackbird(username, config):
    """Use Blackbird's modules to search for username"""
    try:
        if config.verbose:
            print(f"VERBOSE: Starting Blackbird search for: {username}")
            print(f"VERBOSE: Using filter: {config.filter}")
            print(f"VERBOSE: Include categories: {config.include_categories}")
            print(f"VERBOSE: Exclude categories: {config.exclude_categories}")
            start_time = time.time()
        
        # Import list operations
        try:
            from modules.whatsmyname.list_operations import readlist
            from modules.utils.filter import applyFilters as blackbird_applyFilters
            if config.verbose:
                print("VERBOSE: Successfully imported Blackbird core modules")
            use_blackbird_modules = True
        except ImportError as e:
            if config.verbose:
                print(f"VERBOSE: Import error: {e}, using fallback functions")
            use_blackbird_modules = False
        
        # Define fallback functions
        def fallback_readlist(list_type, config):
            if config.verbose:
                print(f"VERBOSE: Fallback readlist for {list_type}")
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
        
        def web_applyFilters(sites, config):
            """Web interface filter implementation that understands Blackbird syntax"""
            if config.verbose:
                print(f"VERBOSE: Applying filters to {len(sites)} sites")
                print(f"VERBOSE: Filter string: '{config.filter}'")
                print(f"VERBOSE: Include categories: {config.include_categories}")
                print(f"VERBOSE: Exclude categories: {config.exclude_categories}")
                print(f"VERBOSE: No NSFW: {config.no_nsfw}")
            
            # Start with all sites
            filtered_sites = sites
            
            # Apply custom filter if provided
            if hasattr(config, 'filter') and config.filter:
                filter_parts = config.filter.split()
                
                for filter_part in filter_parts:
                    if config.verbose:
                        print(f"VERBOSE: Processing filter part: '{filter_part}'")
                    
                    # Handle name~ filter (site name contains)
                    if filter_part.startswith('name~'):
                        search_term = filter_part[5:]  # Remove 'name~' prefix
                        if config.verbose:
                            print(f"VERBOSE: Searching for sites with name containing: '{search_term}'")
                        
                        filtered_sites = [
                            s for s in filtered_sites 
                            if search_term.lower() in s.get('name', '').lower()
                        ]
                        if config.verbose:
                            print(f"VERBOSE: After name~ filter: {len(filtered_sites)} sites")
                    
                    # Handle name= filter (exact site name match)
                    elif filter_part.startswith('name='):
                        search_term = filter_part[5:]  # Remove 'name=' prefix
                        if config.verbose:
                            print(f"VERBOSE: Searching for exact site name: '{search_term}'")
                        
                        filtered_sites = [
                            s for s in filtered_sites 
                            if s.get('name', '').lower() == search_term.lower()
                        ]
                        if config.verbose:
                            print(f"VERBOSE: After name= filter: {len(filtered_sites)} sites")
                    
                    # Handle category filters
                    elif filter_part.startswith('cat='):
                        categories = filter_part[4:].split('|')
                        if config.verbose:
                            print(f"VERBOSE: Including categories: {categories}")
                        
                        filtered_sites = [
                            s for s in filtered_sites 
                            if s.get('cat', '') in categories
                        ]
                        if config.verbose:
                            print(f"VERBOSE: After cat= filter: {len(filtered_sarts)} sites")
                    
                    elif filter_part.startswith('cat!='):
                        categories = filter_part[5:].split('|')
                        if config.verbose:
                            print(f"VERBOSE: Excluding categories: {categories}")
                        
                        filtered_sites = [
                            s for s in filtered_sites 
                            if s.get('cat', '') not in categories
                        ]
                        if config.verbose:
                            print(f"VERBOSE: After cat!= filter: {len(filtered_sites)} sites")
                    
                    elif filter_part.startswith('cat~'):
                        search_term = filter_part[4:]
                        if config.verbose:
                            print(f"VERBOSE: Category contains: '{search_term}'")
                        
                        filtered_sites = [
                            s for s in filtered_sites 
                            if search_term.lower() in s.get('cat', '').lower()
                        ]
                        if config.verbose:
                            print(f"VERBOSE: After cat~ filter: {len(filtered_sites)} sites")
                    
                    # Handle other equality filters
                    elif '=' in filter_part and not (filter_part.startswith('cat') or filter_part.startswith('name')):
                        key, value = filter_part.split('=', 1)
                        filtered_sites = [
                            s for s in filtered_sites 
                            if str(s.get(key, '')).lower() == value.lower()
                        ]
                        if config.verbose:
                            print(f"VERBOSE: After {key}= filter: {len(filtered_sites)} sites")
                    
                    # Handle other inequality filters
                    elif '!=' in filter_part and not (filter_part.startswith('cat') or filter_part.startswith('name')):
                        key, value = filter_part.split('!=', 1)
                        filtered_sites = [
                            s for s in filtered_sites 
                            if str(s.get(key, '')).lower() != value.lower()
                        ]
                        if config.verbose:
                            print(f"VERBOSE: After {key}!= filter: {len(filtered_sites)} sites")
                    
                    # Handle other contains filters
                    elif '~' in filter_part and not (filter_part.startswith('cat') or filter_part.startswith('name')):
                        key, value = filter_part.split('~', 1)
                        filtered_sites = [
                            s for s in filtered_sites 
                            if value.lower() in str(s.get(key, '')).lower()
                        ]
                        if config.verbose:
                            print(f"VERBOSE: After {key}~ filter: {len(filtered_sites)} sites")
                    
                    # Handle comparison operators (>, <, >=, <=)
                    elif '>' in filter_part and '=' not in filter_part:
                        key, value = filter_part.split('>', 1)
                        try:
                            num_value = int(value)
                            filtered_sites = [
                                s for s in filtered_sites 
                                if int(s.get(key, 0)) > num_value
                            ]
                        except ValueError:
                            # If not a number, treat as string comparison
                            filtered_sites = [
                                s for s in filtered_sites 
                                if str(s.get(key, '')) > value
                            ]
                        if config.verbose:
                            print(f"VERBOSE: After {key}> filter: {len(filtered_sites)} sites")
                    
                    elif '<' in filter_part and '=' not in filter_part:
                        key, value = filter_part.split('<', 1)
                        try:
                            num_value = int(value)
                            filtered_sites = [
                                s for s in filtered_sites 
                                if int(s.get(key, 0)) < num_value
                            ]
                        except ValueError:
                            filtered_sites = [
                                s for s in filtered_sites 
                                if str(s.get(key, '')) < value
                            ]
                        if config.verbose:
                            print(f"VERBOSE: After {key}< filter: {len(filtered_sites)} sites")
                    
                    elif '>=' in filter_part:
                        key, value = filter_part.split('>=', 1)
                        try:
                            num_value = int(value)
                            filtered_sites = [
                                s for s in filtered_sites 
                                if int(s.get(key, 0)) >= num_value
                            ]
                        except ValueError:
                            filtered_sites = [
                                s for s in filtered_sites 
                                if str(s.get(key, '')) >= value
                            ]
                        if config.verbose:
                            print(f"VERBOSE: After {key}>= filter: {len(filtered_sites)} sites")
                    
                    elif '<=' in filter_part:
                        key, value = filter_part.split('<=', 1)
                        try:
                            num_value = int(value)
                            filtered_sites = [
                                s for s in filtered_sites 
                                if int(s.get(key, 0)) <= num_value
                            ]
                        except ValueError:
                            filtered_sites = [
                                s for s in filtered_sites 
                                if str(s.get(key, '')) <= value
                            ]
                        if config.verbose:
                            print(f"VERBOSE: After {key}<= filter: {len(filtered_sites)} sites")
                    
                    # Handle logical operators (and, or)
                    elif filter_part.lower() == 'and':
                        # 'and' is handled by sequential filtering
                        continue
                    elif filter_part.lower() == 'or':
                        # 'or' logic needs more complex handling
                        # For simplicity, we'll implement basic OR logic
                        if config.verbose:
                            print(f"VERBOSE: OR operator found - complex filters not fully supported in web interface")
                        continue
                    
                    else:
                        # Simple text search across multiple fields
                        search_term = filter_part.lower()
                        filtered_sites = [
                            s for s in filtered_sites 
                            if (search_term in str(s.get('name', '')).lower() or
                                search_term in str(s.get('cat', '')).lower() or
                                search_term in str(s.get('uri_check', '')).lower())
                        ]
                        if config.verbose:
                            print(f"VERBOSE: After text search: {len(filtered_sites)} sites")
            
            if config.verbose:
                print(f"VERBOSE: Final filtered sites: {len(filtered_sites)}")
                
                # Log some sample sites for debugging
                if filtered_sites:
                    print(f"VERBOSE: Sample sites after filtering:")
                    for i, site in enumerate(filtered_sites[:5]):
                        print(f"VERBOSE:   {i+1}. {site.get('name', 'unknown')} - cat: {site.get('cat', 'unknown')}")
            
            return filtered_sites
        
        # Use the appropriate readlist function
        if use_blackbird_modules:
            readlist_func = readlist
        else:
            readlist_func = fallback_readlist
        
        # Load site data
        data = readlist_func("username", config)
        if config.verbose:
            print(f"VERBOSE: Loaded {len(data.get('sites', []))} sites from {config.USERNAME_list_PATH}")
        
        # Apply filters - ALWAYS use web_applyFilters to ensure category filters work
        sites_to_search = data.get("sites", [])
        config.username_sites = web_applyFilters(sites_to_search, config)
        if config.verbose:
            print(f"VERBOSE: After filtering: {len(config.username_sites)} sites")
        
        # Load metadata
        metadata_data = readlist_func("metadata", config)
        config.metadata_params = metadata_data
        
        # Perform search
        result = await simple_fetch_results(username, config)
        
        # Filter to only found accounts
        found_accounts = [
            r for r in result.get("results", []) 
            if r.get("status") == "FOUND"
        ]
        
        if config.verbose:
            end_time = time.time()
            duration = end_time - start_time
            print(f"VERBOSE: Search completed in {duration:.2f} seconds. Found {len(found_accounts)} accounts")
        
        return found_accounts
        
    except Exception as e:
        if config.verbose:
            print(f"VERBOSE: Error in search_username_blackbird: {e}")
            traceback.print_exc()
        return []

async def search_email_blackbird(email, config):
    """Use Blackbird's actual email verification function with Live display workaround"""
    try:
        if config.verbose:
            print(f"VERBOSE: Starting email search for: {email}")
            start_time = time.time()
        
        # Import required modules
        from modules.core.email import verifyEmail
        from modules.whatsmyname.list_operations import readlist
        from modules.utils.filter import applyFilters
        import asyncio
        import aiohttp
        import time
        
        # Load email data
        data = readlist("email", config)
        sitesToSearch = data["sites"]
        config.email_sites = applyFilters(sitesToSearch, config)
        
        if config.verbose:
            print(f"VERBOSE: Loaded {len(config.email_sites)} email sites to check")
        
        # We need to run the actual email verification but without the Live display
        # Let's create a simplified version of fetchResults that doesn't use Live
        async def simple_email_fetch(email, config):
            """Simplified version of fetchResults without Live display"""
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
                    
                    # Import the actual checkSite function
                    from modules.core.email import checkSite
                    from modules.utils.input import processInput
                    
                    # Process input if needed
                    if site.get("input_operation") is not None:
                        email_processed = processInput(email, site["input_operation"], config)
                        if email_processed is None:
                            email_processed = email
                        elif not isinstance(email_processed, str):
                            email_processed = str(email_processed)
                    else:
                        email_processed = email
                    
                    # Build URL
                    url = site["uri_check"].replace("{account}", email_processed)
                    data = site["data"].replace("{account}", email_processed) if site["data"] else None
                    headers = site["headers"] if site["headers"] else None
                    
                    if config.verbose and completed % 10 == 0:
                        print(f"VERBOSE: Checking email site {completed+1}/{total_sites}: {site.get('name', 'unknown')}")
                    
                    # Call the actual checkSite function
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
                
                # Create tasks for all sites
                tasks = [check_site_wrapper(site) for site in config.email_sites]
                
                # Process all tasks
                for task in asyncio.as_completed(tasks):
                    result = await task
                    results.append(result)
                
                return {"results": results, "email": email}
        
        # Run the simplified email fetch
        if config.verbose:
            print(f"VERBOSE: Starting to check {len(config.email_sites)} email sites...")
        
        results = await simple_email_fetch(email, config)
        
        if config.verbose:
            end_time = time.time()
            print(f"VERBOSE: Email check completed in {round(end_time - start_time, 1)} seconds")
        
        # Filter to only found accounts
        from modules.utils.filter import filterFoundAccounts
        found_accounts = [acc for acc in results.get('results', []) if filterFoundAccounts(acc)]
        
        if config.verbose:
            print(f"VERBOSE: Found {len(found_accounts)} email accounts")
        
        # Convert to the same format as username results
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
        if config.verbose:
            print(f"VERBOSE: Error in Blackbird email search for {email}: {str(e)}")
            traceback.print_exc()
        return []

async def check_site_simplified(site, email_processed, session, config):
    """Simplified version of checkSite for email search"""
    try:
        from modules.utils.http_client import do_async_request
        from modules.utils.parse import extractMetadata
        
        url = site["uri_check"].replace("{account}", email_processed)
        
        if config.verbose:
            print(f"\nVERBOSE: Checking email site: {site.get('name', 'unknown')}")
            print(f"VERBOSE: URL: {url}")
            print(f"VERBOSE: e_string: {site.get('e_string', 'N/A')}")
            print(f"VERBOSE: e_code: {site.get('e_code', 'N/A')}")
        
        # Make request
        response = await do_async_request(
            site.get("method", "GET"),
            url,
            session,
            config,
            data=site.get("data"),
            headers=site.get("headers")
        )
        
        if response is None:
            if config.verbose:
                print(f"VERBOSE: No response for {site.get('name', 'unknown')}")
            return {
                "name": site.get("name", "unknown"),
                "url": url,
                "category": site.get("cat", "unknown"),
                "status": "ERROR",
                "metadata": None
            }
        
        # Check if email exists
        e_string = site.get("e_string", "")
        e_code = site.get("e_code", 200)
        m_string = site.get("m_string", "")
        m_code = site.get("m_code", 404)
        
        content = response.get("content", "")
        status_code = response.get("status_code", 0)
        
        if config.verbose:
            print(f"VERBOSE: Status code: {status_code}")
            print(f"VERBOSE: Response length: {len(content)}")
        
        # Check if e_string is in content
        account_found = (
            e_string in content and 
            (e_code == status_code or e_code == 0)
        )
        
        if config.verbose:
            print(f"VERBOSE: e_string in content: {e_string in content}")
            print(f"VERBOSE: Status code matches e_code: {status_code == e_code}")
            print(f"VERBOSE: Account found: {account_found}")
        
        if account_found:
            # Check for non-match string/code
            account_not_found = (
                m_string in content or
                (m_code == status_code and m_code != e_code)
            )
            
            if config.verbose:
                print(f"VERBOSE: m_string in content: {m_string in content}")
                print(f"VERBOSE: Status code matches m_code: {status_code == m_code}")
                print(f"VERBOSE: Account not found: {account_not_found}")
            
            if not account_not_found:
                result = {
                    "name": site.get("name", "unknown"),
                    "url": response.get("url", url),
                    "category": site.get("cat", "unknown"),
                    "status": "FOUND",
                    "metadata": None
                }
                
                if config.verbose:
                    print(f"VERBOSE: ✓ FOUND account on {site.get('name', 'unknown')}")
                return result
        
        if config.verbose:
            print(f"VERBOSE: ✗ NOT FOUND on {site.get('name', 'unknown')}")
        return {
            "name": site.get("name", "unknown"),
            "url": response.get("url", url),
            "category": site.get("cat", "unknown"),
            "status": "NOT-FOUND",
            "metadata": None
        }
        
    except Exception as e:
        if config.verbose:
            print(f"VERBOSE: Error checking email site {site.get('name', 'unknown')}: {e}")
        return {
            "name": site.get("name", "unknown"),
            "url": url,
            "category": site.get("cat", "unknown"),
            "status": "ERROR",
            "metadata": None
        }

async def simple_email_search_fallback(email, config):
    """Simple fallback email search without Rich dependencies"""
    async with aiohttp.ClientSession() as session:
        results = []
        
        # Common email verification endpoints
        email_check_endpoints = [
            {
                "name": "Have I Been Pwned",
                "url": f"https://haveibeenpwned.com/unifiedsearch/{email}",
                "category": "security",
                "method": "GET"
            },
            {
                "name": "EmailRep",
                "url": f"https://emailrep.io/{email}",
                "category": "security",
                "method": "GET"
            },
            {
                "name": "Hunter.io Email Verifier",
                "url": f"https://api.hunter.io/v2/email-verifier?email={email}&api_key=demo",
                "category": "professional",
                "method": "GET"
            },
            {
                "name": "DeHashed",
                "url": f"https://dehashed.com/search?query={email}",
                "category": "security",
                "method": "GET"
            }
        ]
        
        for site in email_check_endpoints:
            try:
                if config.verbose:
                    print(f"VERBOSE: Checking: {site['name']}")
                
                async with session.request(
                    method=site.get("method", "GET"),
                    url=site["url"],
                    headers={"User-Agent": config.userAgent},
                    timeout=config.timeout
                ) as response:
                    status = response.status
                    content = await response.text()
                    
                    # Simple check - if we get a 200, consider it found
                    if status == 200:
                        results.append({
                            "name": site["name"],
                            "url": site["url"],
                            "category": site["category"],
                            "status": "FOUND",
                            "metadata": None
                        })
                        if config.verbose:
                            print(f"VERBOSE: ✓ Found on {site['name']}")
                    else:
                        results.append({
                            "name": site["name"],
                            "url": site["url"],
                            "category": site["category"],
                            "status": "NOT-FOUND",
                            "metadata": None
                        })
            except Exception as e:
                if config.verbose:
                    print(f"VERBOSE: Error checking {site['name']}: {e}")
                results.append({
                    "name": site["name"],
                    "url": site["url"],
                    "category": site["category"],
                    "status": "ERROR",
                    "metadata": None
                })
        
        return results

def create_web_config(options):
    """Create a Blackbird config object for web interface"""
    config = BlackbirdConfig()
    
    # Set options from web form
    config.verbose = options.get('verbose', False)
    config.proxy = options.get('proxy')
    config.timeout = int(options.get('timeout', 30))
    config.max_concurrent_requests = int(options.get('max_concurrent', 30))
    
    # Set the filter (already combined in search route)
    config.filter = options.get('filter')
    
    # Store category filters for debugging
    config.include_categories = options.get('include_categories', '')
    config.exclude_categories = options.get('exclude_categories', '')
    
    # Set other options
    config.no_nsfw = options.get('no_nsfw', False)
    config.dump = options.get('dump', False)
    config.csv = options.get('save_csv', True)
    config.json = options.get('save_json', True)
    config.pdf = options.get('save_pdf', False)
    config.ai = options.get('ai', False)
    
    # Add email-specific configuration
    config.email_sites = []  # Will be populated when loading email sites
    
    # Create console
    config.console = WebConsole()
    
    if config.verbose:
        print(f"VERBOSE: Creating config with options:")
        print(f"  - Verbose mode: {config.verbose}")
        print(f"  - Timeout: {config.timeout}")
        print(f"  - Concurrent requests: {config.max_concurrent_requests}")
        print(f"  - Filter: {config.filter}")
        print(f"  - Include categories: {config.include_categories}")
        print(f"  - Exclude categories: {config.exclude_categories}")
        print(f"  - NSFW filter: {config.no_nsfw}")
        print(f"  - Export formats: CSV={config.csv}, JSON={config.json}, PDF={config.pdf}")
        print(f"  - Proxy: {config.proxy}")
        print(f"  - AI analysis: {config.ai}")
    
    return config

def save_reports(found_accounts, identifier, session_folder, config, search_type="username"):
    """Save reports using Blackbird's export modules"""
    try:
        if config.verbose:
            print(f"VERBOSE: Saving reports for {identifier} in {session_folder}")
            start_time = time.time()
        
        # Ensure the session folder exists
        os.makedirs(session_folder, exist_ok=True)
        
        # Set current user/email for file naming
        if search_type == "username":
            config.currentUser = identifier
            config.currentEmail = None
            prefix = f"{identifier}_{config.dateRaw}_blackbird"
        else:
            config.currentEmail = identifier
            config.currentUser = None
            prefix = f"{identifier}_{config.dateRaw}_blackbird"
        
        config.saveDirectory = session_folder
        
        reports = {}
        
        # Save JSON - Match CLI format
        if config.json and found_accounts:
            try:
                json_file = f"{prefix}.json"
                json_path = os.path.join(session_folder, json_file)
                
                # Prepare data for JSON - use simpler format like CLI
                json_data = []
                for account in found_accounts:
                    account_data = {
                        'name': account.get('name', 'Unknown'),
                        'url': account.get('url', '#'),
                        'category': account.get('category', 'unknown'),
                        'status': account.get('status', 'UNKNOWN')
                    }
                    
                    # Add metadata if available - format it like CLI
                    metadata = account.get('metadata')
                    if metadata:
                        # Format metadata to match CLI output
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
                
                # Save as pretty JSON like the CLI does
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(json_data, f, indent=4, ensure_ascii=False)
                
                reports['json_file'] = json_file
                if config.verbose:
                    print(f"VERBOSE: Saved JSON: {json_file}")
            except Exception as e:
                if config.verbose:
                    print(f"VERBOSE: Error saving JSON: {e}")
        
        # Save CSV if enabled
        if config.csv and found_accounts:
            try:
                csv_file = f"{prefix}.csv"
                csv_path = os.path.join(session_folder, csv_file)
                
                with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    # Write headers
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
                    print(f"VERBOSE: Saved CSV: {csv_file}")
            except Exception as e:
                if config.verbose:
                    print(f"VERBOSE: Error saving CSV: {e}")
        
        # Save PDF if enabled
        if config.pdf and found_accounts:
            try:
                pdf_file = f"{prefix}.pdf"
                pdf_path = os.path.join(session_folder, pdf_file)
                
                # Create a simple PDF
                from reportlab.lib.pagesizes import letter
                from reportlab.pdfgen import canvas
                from reportlab.lib.units import inch
                
                c = canvas.Canvas(pdf_path, pagesize=letter)
                width, height = letter
                
                # Title
                c.setFont("Helvetica-Bold", 16)
                title = f"Blackbird Report - {identifier}"
                c.drawString(1*inch, height - 1*inch, title)
                
                # Subtitle
                c.setFont("Helvetica", 10)
                c.drawString(1*inch, height - 1.3*inch, f"Generated: {config.datePretty}")
                c.drawString(1*inch, height - 1.6*inch, f"Found {len(found_accounts)} accounts")
                
                # Results
                y_position = height - 2*inch
                c.setFont("Helvetica-Bold", 12)
                c.drawString(1*inch, y_position, "Results:")
                
                y_position -= 0.3*inch
                c.setFont("Helvetica", 10)
                
                # Table headers
                c.setFont("Helvetica-Bold", 10)
                c.drawString(1*inch, y_position, "Site Name")
                c.drawString(3*inch, y_position, "URL")
                c.drawString(6*inch, y_position, "Category")
                c.drawString(7.2*inch, y_position, "Status")
                
                y_position -= 0.2*inch
                c.setFont("Helvetica", 10)
                
                # Draw a line
                c.line(1*inch, y_position, 7.5*inch, y_position)
                y_position -= 0.3*inch
                
                for account in found_accounts[:30]:  # Limit to first 30
                    if y_position < 1*inch:  # New page if needed
                        c.showPage()
                        y_position = height - 1*inch
                        # Redraw headers on new page
                        c.setFont("Helvetica-Bold", 10)
                        c.drawString(1*inch, y_position, "Site Name")
                        c.drawString(3*inch, y_position, "URL")
                        c.drawString(6*inch, y_position, "Category")
                        c.drawString(7.2*inch, y_position, "Status")
                        y_position -= 0.2*inch
                        c.line(1*inch, y_position, 7.5*inch, y_position)
                        y_position -= 0.3*inch
                        c.setFont("Helvetica", 10)
                    
                    # Site name
                    site_name = account.get('name', 'Unknown')
                    if len(site_name) > 25:
                        site_name = site_name[:22] + "..."
                    c.drawString(1*inch, y_position, site_name)
                    
                    # URL
                    url = account.get('url', '#')
                    if len(url) > 40:
                        url = url[:37] + "..."
                    c.drawString(3*inch, y_position, url)
                    
                    # Category
                    category = account.get('category', 'unknown')
                    c.drawString(6*inch, y_position, category)
                    
                    # Status with color indicator
                    status = account.get('status', 'UNKNOWN')
                    status_color = {
                        'FOUND': 'green',
                        'NOT-FOUND': 'gray',
                        'ERROR': 'red'
                    }.get(status, 'black')
                    
                    # Draw status with colored box
                    c.setFillColor(status_color)
                    c.rect(7.2*inch, y_position - 0.05*inch, 0.3*inch, 0.15*inch, fill=1, stroke=0)
                    c.setFillColorRGB(1, 1, 1)  # White text
                    c.drawString(7.25*inch, y_position, status[:1])  # Just first letter
                    c.setFillColorRGB(0, 0, 0)  # Reset to black
                    
                    y_position -= 0.2*inch
                
                # Footer
                c.showPage()
                c.setFont("Helvetica", 8)
                c.drawString(1*inch, 0.5*inch, f"Generated by Blackbird on {config.datePretty}")
                
                c.save()
                reports['pdf_file'] = pdf_file
                if config.verbose:
                    print(f"VERBOSE: Created PDF: {pdf_file}")
                
            except Exception as e:
                if config.verbose:
                    print(f"VERBOSE: Error saving PDF: {e}")
                reports['pdf_file'] = None
        
        # Reset config
        config.currentUser = None
        config.currentEmail = None
        config.saveDirectory = None
        
        if config.verbose:
            end_time = time.time()
            duration = end_time - start_time
            print(f"VERBOSE: Reports saved in {duration:.2f} seconds")
        
        return reports
        
    except Exception as e:
        if config.verbose:
            print(f"VERBOSE: Error in save_reports: {str(e)}")
            traceback.print_exc()
        return {}

async def process_single_search(item, search_type, config):
    """Process a single search item"""
    try:
        if config.verbose:
            print(f"VERBOSE: Processing {search_type}: {item}")
            start_time = time.time()
        
        if search_type == "username":
            found_accounts = await search_username_blackbird(item, config)
        elif search_type == "email":
            found_accounts = await search_email_blackbird(item, config)
        else:
            return None
        
        if config.verbose:
            end_time = time.time()
            duration = end_time - start_time
            print(f"VERBOSE: Found {len(found_accounts)} accounts for {item} in {duration:.2f} seconds")
        
        # Convert to display format
        claimed_profiles = []
        for account in found_accounts:
            profile = {
                'site_name': account.get('name', 'Unknown'),
                'url': account.get('url', '#'),
                'category': account.get('category', 'unknown'),
                'status': account.get('status', 'UNKNOWN')
            }
            
            # Add metadata if available
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
            print(f"VERBOSE: Error processing {item}: {str(e)}")
            traceback.print_exc()
        return None

def create_session_folder(username, search_type):
    """Create session folder in username_mm_dd_yyyy_blackbird format"""
    date_str = datetime.now().strftime("%m_%d_%Y")
    if search_type == "email":
        folder_name = f"{username}_{date_str}_blackbird"
    else:
        folder_name = f"{username}_{date_str}_blackbird"
    
    # Create the folder in the results directory
    session_folder = os.path.join(app.config["REPORTS_FOLDER"], folder_name)
    return folder_name, session_folder

def process_search_task(search_items, search_type, options, timestamp, enable_frequency=False):
    """Background task to process search using actual Blackbird code"""
    try:
        print(f"Starting search task for {len(search_items)} items")
        
        # Create a new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Process all searches
        tasks = []
        for item in search_items:
            # Create session folder for each username/email
            folder_name, session_folder = create_session_folder(item, search_type)
            
            # Create config
            config = create_web_config(options)
            config.saveDirectory = session_folder
            
            task = process_single_search(item, search_type, config)
            tasks.append(task)
        
        # Run all tasks concurrently
        results = loop.run_until_complete(asyncio.gather(*tasks))
        
        individual_reports = []
        
        # Process results and save reports
        for result in results:
            if result is None:
                continue
                
            item = result['item']
            found_accounts = result['found_accounts']
            claimed_profiles = result['claimed_profiles']
            
            # Get the session folder for this username/email
            folder_name, session_folder = create_session_folder(item, search_type)
            
            # Create folder
            os.makedirs(session_folder, exist_ok=True)
            
            # Create config for saving
            config = create_web_config(options)
            config.saveDirectory = session_folder
            config.currentUser = item if search_type == "username" else None
            config.currentEmail = item if search_type == "email" else None
            
            # Save reports
            reports = save_reports(found_accounts, item, session_folder, config, search_type)
            
            report_data = {
                'username': item,
                'search_type': search_type,
                'folder_name': folder_name,
                'csv_file': reports.get('csv_file'),
                'json_file': reports.get('json_file'),
                'pdf_file': reports.get('pdf_file'),
                'claimed_profiles': claimed_profiles,
                'total_found': result['total_found']
            }
            
            # Add frequency data if enabled
            if enable_frequency and frequency_analyzer:
                print(f"Adding frequency analysis for {item}...")
                
                # Scan reports to ensure fresh data
                frequency_analyzer.scan_reports()
                
                # Get frequency data for this user
                freq_data = frequency_analyzer.get_username_frequency(item)
                
                # Calculate frequency percentage
                total_reports = frequency_analyzer.frequency_cache.get('total_reports', 1)
                user_reports = len(freq_data.get('search_history', []))
                frequency_percentage = (user_reports / total_reports * 100) if total_reports > 0 else 0
                
                # Get most common sites for this user
                common_sites = []
                for site in freq_data.get('sites_found', []):
                    site_freq = frequency_analyzer.get_site_frequency(site)
                    common_sites.append({
                        'site': site,
                        'count': site_freq.get('total_found', 0),
                        'username_count': site_freq.get('username_count', 0)
                    })
                
                # Sort by count
                common_sites.sort(key=lambda x: x['count'], reverse=True)
                
                report_data['frequency_data'] = {
                    'username': item,
                    'search_type': search_type,
                    'total_occurrences': user_reports,
                    'site_count': freq_data.get('site_count', 0),
                    'first_seen': freq_data.get('first_seen'),
                    'last_seen': freq_data.get('last_seen'),
                    'common_sites': common_sites[:5],  # Top 5 sites
                    'frequency_percentage': frequency_percentage
                }
            
            individual_reports.append(report_data)
        
        # Get overall common sites if frequency analysis is enabled
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
        
        # Save job results
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
        
        print(f"Search completed successfully for session {timestamp}")
        
    except Exception as e:
        print(f"Error in search task: {str(e)}")
        traceback.print_exc()
        job_results[timestamp] = {
            'status': 'failed',
            'error': str(e)
        }
    finally:
        background_jobs[timestamp]['completed'] = True
        print(f"Marked job {timestamp} as completed")

@app.route('/')
def index():
    """Main page with search form"""
    try:
        print("Loading index page...")
        
        # Try to load site names and categories from Blackbird's data
        site_names = []
        tag_options = []
        categories = []
        
        try:
            config = BlackbirdConfig()
            print(f"Config created, looking for data at: {config.USERNAME_list_PATH}")
            
            if os.path.exists(config.USERNAME_list_PATH):
                with open(config.USERNAME_list_PATH, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Load site names
                site_names = sorted(set([
                    site.get('name', '') for site in data.get('sites', []) 
                    if site.get('name')
                ]))
                
                # Extract tags
                for site in data.get('sites', []):
                    tags = site.get('tags', [])
                    if isinstance(tags, list):
                        tag_options.extend(tags)
                    elif isinstance(tags, str):
                        tag_options.append(tags)
                
                tag_options = sorted(set(tag_options))
                
                # Extract categories from the JSON data
                # First check if there's a "categories" key in the JSON
                if 'categories' in data:
                    categories = data['categories']
                else:
                    # If no categories array, extract unique categories from sites
                    categories = sorted(set([
                        site.get('cat', '').strip() for site in data.get('sites', [])
                        if site.get('cat', '').strip()
                    ]))
                
                print(f"Loaded {len(site_names)} sites, {len(tag_options)} tags, and {len(categories)} categories")
                print(f"Categories found: {categories}")
                
            else:
                print(f"Data file not found: {config.USERNAME_list_PATH}")
                # Try alternative path: ../blackbird/data/wmn-data.json
                alt_path = os.path.join(CURRENT_DIR, '..', 'blackbird', 'data', 'wmn-data.json')
                if os.path.exists(alt_path):
                    print(f"Found data at alternative path: {alt_path}")
                    with open(alt_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # Load site names
                    site_names = sorted(set([
                        site.get('name', '') for site in data.get('sites', []) 
                        if site.get('name')
                    ]))
                    
                    # Extract tags
                    for site in data.get('sites', []):
                        tags = site.get('tags', [])
                        if isinstance(tags, list):
                            tag_options.extend(tags)
                        elif isinstance(tags, str):
                            tag_options.append(tags)
                    
                    tag_options = sorted(set(tag_options))
                    
                    # Extract categories
                    if 'categories' in data:
                        categories = data['categories']
                    else:
                        categories = sorted(set([
                            site.get('cat', '').strip() for site in data.get('sites', [])
                            if site.get('cat', '').strip()
                        ]))
                    
                    print(f"Loaded {len(site_names)} sites, {len(tag_options)} tags, and {len(categories)} categories from alternative path")
                else:
                    print("Data file not found at alternative path either")
                    # Create sample data for testing
                    site_names = ["Twitter", "Facebook", "Instagram", "GitHub", "LinkedIn"]
                    tag_options = ["social", "tech", "coding", "professional"]
                    categories = ["social", "tech", "business", "coding", "gaming", "art", "misc"]
                
        except Exception as e:
            print(f"Error loading data: {str(e)}")
            traceback.print_exc()
            # Fallback to sample data
            site_names = ["Twitter", "Facebook", "Instagram", "GitHub", "LinkedIn"]
            tag_options = ["social", "tech", "coding", "professional"]
            categories = ["social", "tech", "business", "coding", "gaming", "art", "misc"]
        
        # Try to load email site names and categories
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
                
                # Extract email categories
                email_categories = sorted(set([
                    site.get('cat', '').strip() for site in email_data.get('sites', [])
                    if site.get('cat', '').strip()
                ]))
                
                print(f"Loaded {len(email_site_names)} email sites and {len(email_categories)} email categories")
            else:
                print(f"Email data file not found: {config.EMAIL_list_PATH}")
                # Create sample email data for testing
                email_site_names = ["Have I Been Pwned", "DeHashed", "Hunter.io", "EmailRep", "BreachDirectory"]
                email_categories = ["security", "professional", "verification"]
        except Exception as e:
            print(f"Error loading email data: {str(e)}")
            traceback.print_exc()
            # Fallback to sample email data
            email_site_names = ["Have I Been Pwned", "DeHashed", "Hunter.io", "EmailRep", "BreachDirectory"]
            email_categories = ["security", "professional", "verification"]
        
        # Map categories to icons for the UI
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
        
        # Create category data for template - combine username and email categories
        all_categories = sorted(set(categories + email_categories))
        category_data = []
        for category in all_categories:
            # Skip NSFW category entirely
            if category == "xx NSFW xx":
                continue
                
            icon = category_icons.get(category, "📁")
            display_name = category
            
            # Add source indicator
            source = []
            if category in categories:
                source.append("username")
            if category in email_categories:
                source.append("email")
            
            category_data.append({
                'id': category,
                'name': display_name,
                'icon': icon,
                'source': '|'.join(source)  # e.g., "username|email"
            })
        
        # Prepare email-specific data for the template
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
        print(f"Error loading index: {str(e)}")
        traceback.print_exc()
        return render_template('index.html', 
                             site_options=[], 
                             tag_options=[], 
                             categories=[],
                             email_site_options=[],
                             email_categories=[])

@app.route('/search', methods=['POST'])
def search():
    """Handle search request"""
    try:
        print("Processing search request...")
        
        # Check if frequency analysis is enabled
        enable_frequency = 'enable_frequency' in request.form
        show_common_sites = 'show_common_sites' in request.form
        
        # Determine search type
        search_type = 'username'  # Default to username search
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
        
        # Parse search items
        search_items = [
            item.strip() for item in search_input.replace(',', ' ').split() 
            if item.strip()
        ]
        
        print(f"Search items: {search_items}")
        
        # Create timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Get options from form including category filters
        selected_tags = request.form.getlist('tags')
        site_list = [
            s.strip() for s in request.form.get('site', '').split(',') 
            if s.strip()
        ]
        
        # Get category filter data
        include_categories = request.form.get('include_categories', '')
        exclude_categories = request.form.get('exclude_categories', '')
        custom_filter = request.form.get('filter', '')
        
        # Build the complete filter string for Blackbird
        filter_parts = []
        
        # Add included categories using = (exact match)
        if include_categories:
            included = [c for c in include_categories.split(',') if c]
            if included:
                # Use OR operator | for multiple included categories
                filter_parts.append(f'cat={("|".join(included))}')
        
        # Add excluded categories using != (not equal)
        if exclude_categories:
            excluded = [c for c in exclude_categories.split(',') if c]
            if excluded:
                filter_parts.append(f'cat!=({"|".join(excluded)})')
        
        # Add custom filter if provided
        if custom_filter and custom_filter.strip():
            # Check if custom filter already has category filters
            # We'll let Blackbird handle the combination
            filter_parts.append(custom_filter.strip())
        
        # Combine all filter parts
        final_filter = ' '.join(filter_parts) if filter_parts else None
        
        options = {
            'top_sites': request.form.get('top_sites', '500'),
            'timeout': request.form.get('timeout', '30'),
            'max_concurrent': request.form.get('max_concurrent', '30'),
            'proxy': request.form.get('proxy'),
            'tor_proxy': request.form.get('tor_proxy'),
            'i2p_proxy': request.form.get('i2p_proxy'),
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
            'filter': final_filter,  # Pass combined filter to Blackbird
            'include_categories': include_categories,  # Keep raw for reference
            'exclude_categories': exclude_categories,  # Keep raw for reference
            'enable_frequency': enable_frequency,
            'show_common_sites': show_common_sites
        }
        
        print(f"Category filters - Included: {include_categories}, Excluded: {exclude_categories}")
        print(f"Final filter string: '{final_filter}'")
        print(f"Frequency analysis enabled: {enable_frequency}")
        
        # Start background job
        background_jobs[timestamp] = {
            'completed': False,
            'thread': Thread(
                target=process_search_task,
                args=(search_items, search_type, options, timestamp, enable_frequency)
            ),
            'enable_frequency': enable_frequency,
            'show_common_sites': show_common_sites
        }
        background_jobs[timestamp]['thread'].start()
        
        print(f"Started {search_type} search job {timestamp} for {len(search_items)} items")
        flash(f'Search started! Your search ID is: {timestamp}', 'info')
        
        # Redirect directly to results page
        return redirect(url_for('results', session_id=timestamp))
        
    except Exception as e:
        print(f"Error in search route: {str(e)}")
        traceback.print_exc()
        flash(f'Error starting search: {str(e)}', 'danger')
        return redirect(url_for('index'))

@app.route('/status/<timestamp>')
def status(timestamp):
    """Check search status - Simplified to redirect to results"""
    print(f"Checking status for timestamp: {timestamp}")
    
    if timestamp not in background_jobs:
        flash('Invalid search session', 'danger')
        return redirect(url_for('index'))
    
    # Check if job is completed
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
    
    # Job is still running, show a simple waiting page
    return render_template('status.html', timestamp=timestamp)

@app.route('/results/<session_id>')
def results(session_id):
    """Display search results"""
    try:
        # IMPORTANT: Clear all flash messages first
        from flask import get_flashed_messages
        get_flashed_messages()  # Clears the flash queue
        
        print(f"Displaying results for session: {session_id}")
        
        # Find results for this session
        result_data = job_results.get(session_id)
        
        if not result_data:
            # Check if job is still running
            if session_id in background_jobs and not background_jobs[session_id]['completed']:
                # Use a simple return without flash to prevent spamming
                return render_template('status.html', timestamp=session_id)
            else:
                # Show error but only once
                flash('No results found for this session', 'danger')
                return redirect(url_for('index'))
        if result_data.get('status') != 'completed':
            error_msg = result_data.get('error', 'Unknown error')
            flash(f'Search failed: {error_msg}', 'danger')
            return redirect(url_for('index'))
        
        print(f"Found result data: {result_data.get('search_type')}")
        
        # Prepare reports for template
        adapted_reports = []
        for report in result_data.get('individual_reports', []):
            adapted_report = {
                'username': report['username'],
                'search_type': report.get('search_type', 'username'),
                'folder_name': report.get('folder_name'),
                'claimed_profiles': report.get('claimed_profiles', []),
                'total_found': report.get('total_found', 0)
            }
            
            # Add file links if they exist
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
        print(f"Error displaying results: {str(e)}")
        traceback.print_exc()
        flash(f'Error loading results: {str(e)}', 'danger')
        return redirect(url_for('index'))

@app.route('/reports/<path:filename>')
def download_report(filename):
    """Download report files"""
    try:
        print(f"Download request for: {filename}")
        
        # Split the path to get folder and file
        path_parts = filename.split('/')
        if len(path_parts) == 1:
            # If just filename, search in all subdirectories
            file_path = None
            for root, dirs, files in os.walk(app.config["REPORTS_FOLDER"]):
                if filename in files:
                    file_path = os.path.join(root, filename)
                    break
            
            if not file_path:
                raise Exception(f"File not found: {filename}")
        else:
            # Full path provided
            file_path = os.path.normpath(
                os.path.join(app.config["REPORTS_FOLDER"], filename)
            )
        
        print(f"Looking for file at: {file_path}")
        
        # Security check
        if not file_path.startswith(app.config["REPORTS_FOLDER"]):
            raise Exception("Invalid file path")
        
        if not os.path.exists(file_path):
            raise Exception(f"File not found: {file_path}")
        
        return send_file(file_path, as_attachment=True)
        
    except Exception as e:
        print(f"Error serving file {filename}: {str(e)}")
        traceback.print_exc()
        return "File not found", 404

@app.route('/api/site-tags')
def get_site_tags():
    """API endpoint to get tags for site filtering"""
    try:
        print("Getting site tags...")
        
        config = BlackbirdConfig()
        
        if not os.path.exists(config.USERNAME_list_PATH):
            print(f"Data file not found: {config.USERNAME_list_PATH}")
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
        print(f"Returning {len(tags_list)} tags")
        
        return {
            'tags': tags_list, 
            'total_sites': len(data.get('sites', [])),
            'status': 'success'
        }
        
    except Exception as e:
        print(f"Error getting site tags: {str(e)}")
        traceback.print_exc()
        return {'tags': [], 'error': str(e), 'status': 'error'}

@app.route('/api/stats')
def get_stats():
    """Get statistics about the Blackbird installation"""
    try:
        print("Getting stats...")
        
        stats = {
            'active_jobs': len([j for j in background_jobs.values() if not j.get('completed', True)]),
            'completed_jobs': len(job_results),
            'reports_folder': app.config["REPORTS_FOLDER"],
            'username_sites': 0,
            'email_sites': 0,
        }
        
        # Try to get site counts
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
            print(f"Error getting site counts: {e}")
        
        print(f"Stats: {stats}")
        return stats
        
    except Exception as e:
        print(f"Error getting stats: {str(e)}")
        traceback.print_exc()
        return {'error': str(e)}

@app.route('/api/search-types')
def get_search_types():
    """Get available search types"""
    return {
        'search_types': [
            {'id': 'username', 'name': 'Username Search', 'description': 'Search for usernames across social networks'},
            {'id': 'email', 'name': 'Email Search', 'description': 'Search for email addresses across platforms'},
        ]
    }

@app.route('/api/frequency/overview')
def get_frequency_overview():
    """Get overview of frequency analysis"""
    try:
        if not frequency_analyzer:
            return {'error': 'Frequency analyzer not initialized', 'status': 'error'}
        
        data = frequency_analyzer.scan_reports()
        
        # Prepare response
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
        
        # Get top 10 sites
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
    """Search historical frequency data"""
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

@app.route('/api/frequency/username/<username>')
def get_username_frequency(username):
    """Get frequency data for specific username"""
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
    """Get frequency data for specific site"""
    try:
        if not frequency_analyzer:
            return {'error': 'Frequency analyzer not initialized'}
        
        freq_data = frequency_analyzer.get_site_frequency(site_name)
        freq_data['status'] = 'success'
        return freq_data
        
    except Exception as e:
        return {'error': str(e), 'status': 'error'}

@app.route('/health')
def health():
    """Health check endpoint"""
    return {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'jobs': len(background_jobs),
        'completed_jobs': len(job_results),
    }

if __name__ == '__main__':
    # Load Blackbird modules
    print("=" * 60)
    print("Starting Blackbird Web Interface")
    print("=" * 60)
    
    # Find and setup blackbird
    print("\n[1] Setting up Blackbird environment...")
    blackbird_root = find_blackbird_root()
    
    if blackbird_root:
        print(f"✓ Blackbird root: {blackbird_root}")
        
        # Add to sys.path
        src_dir = os.path.join(blackbird_root, 'src')
        if os.path.exists(src_dir):
            sys.path.insert(0, src_dir)
            print(f"✓ Added to sys.path: {src_dir}")
        
        # Also add the parent directory
        sys.path.insert(0, blackbird_root)
        print(f"✓ Added to sys.path: {blackbird_root}")
    else:
        print("✗ Could not find Blackbird root")
    
    print("\n[2] Loading Blackbird modules...")
    load_blackbird_modules()
    
    print("\n[3] Initializing frequency analyzer...")
    init_frequency_analyzer()
    
    # Test data files
    print("\n[4] Checking data files...")
    config = BlackbirdConfig()
    print(f"  Username list: {config.USERNAME_list_PATH} - {'✓' if os.path.exists(config.USERNAME_list_PATH) else '✗'}")
    print(f"  Email list: {config.EMAIL_list_PATH} - {'✓' if os.path.exists(config.EMAIL_list_PATH) else '✗'}")
    print(f"  Metadata: {config.USERNAME_METADATA_list_PATH} - {'✓' if os.path.exists(config.USERNAME_METADATA_list_PATH) else '✗'}")
    
    # Check assets
    if BLACKBIRD_ASSETS_DIR:
        print(f"  Assets directory: {BLACKBIRD_ASSETS_DIR} - {'✓' if os.path.exists(BLACKBIRD_ASSETS_DIR) else '✗'}")
    
    # Run the app
    debug_mode = os.getenv('FLASK_DEBUG', 'True').lower() in ['true', '1', 't']
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', '5000'))
    
    print(f"\n[5] Starting server on {host}:{port} (debug={debug_mode})")
    print("=" * 60)
    
    # app.run(debug=debug_mode, host=host, port=port)
    app.run(host=host, port=port)