from flask import (
    Flask,
    render_template,
    request,
    send_file,
    flash,
    redirect,
    url_for,
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
        self.USERNAME_LIST_PATH = self._find_data_file('wmn-data.json')
        self.EMAIL_LIST_PATH = self._find_data_file('email-data.json')
        self.USERNAME_METADATA_LIST_PATH = self._find_data_file('wmn-metadata.json')
        self.USERNAME_LIST_URL = "https://raw.githubusercontent.com/WebBreacher/WhatsMyName/main/wmn-data.json"
        
        # Initialize lists
        self.username_sites = []
        self.metadata_params = {}
        self.include_categories = []
        self.exclude_categories = []
        
        print(f"Username list path: {self.USERNAME_LIST_PATH}")
        print(f"Email list path: {self.EMAIL_LIST_PATH}")
        print(f"Metadata path: {self.USERNAME_METADATA_LIST_PATH}")
    
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
    """Find the Blackbird installation root directory"""
    possible_paths = [
        # Current project structure
        os.path.join(CURRENT_DIR, '..', 'blackbird'),
        os.path.join(CURRENT_DIR, 'blackbird'),
        
        # Common installation locations
        os.path.join('/usr', 'local', 'lib', 'blackbird'),
        os.path.join('/usr', 'lib', 'blackbird'),
        os.path.join('/opt', 'blackbird'),
        
        # User installations
        os.path.join(os.path.expanduser('~'), '.local', 'lib', 'blackbird'),
        os.path.join(os.path.expanduser('~'), 'blackbird'),
        os.path.join(os.path.expanduser('~'), '.blackbird'),
        
        # Your specific location based on data files
        os.path.dirname(os.path.dirname(CURRENT_DIR)),  # Go up two levels from venvs/blackbird/blackbird_web
        CURRENT_DIR,  # Current directory itself
        
        # Check data directory's parent
        os.path.dirname(os.path.dirname(BLACKBIRD_ASSETS_DIR)) if BLACKBIRD_ASSETS_DIR else None,
    ]
    
    # Filter out None values
    possible_paths = [p for p in possible_paths if p]
    
    print("Searching for Blackbird in the following locations:")
    for path in possible_paths:
        abs_path = os.path.abspath(path)
        print(f"  - {abs_path}")
        if os.path.exists(abs_path):
            # Check for Blackbird structure
            src_path = os.path.join(abs_path, 'src')
            if os.path.exists(src_path):
                print(f"✓ Found Blackbird at: {abs_path}")
                return abs_path
            
            # Also check if it's the src directory itself
            if abs_path.endswith('src'):
                parent_path = os.path.dirname(abs_path)
                print(f"✓ Found Blackbird src, using parent: {parent_path}")
                return parent_path
    
    print("✗ Could not find Blackbird root directory")
    
    # Try to find by searching for specific files
    print("\nSearching for Blackbird files...")
    search_dirs = [
        os.path.dirname(CURRENT_DIR),
        os.path.expanduser('~'),
        '/',
    ]
    
    for search_dir in search_dirs:
        print(f"Searching in {search_dir}...")
        try:
            for root, dirs, files in os.walk(search_dir, topdown=True):
                # Limit depth
                if root.count(os.sep) - search_dir.count(os.sep) > 3:
                    dirs[:] = []  # Don't go deeper
                    continue
                
                # Check for Blackbird files
                if 'blackbird.py' in files or 'requirements.txt' in files:
                    if 'src' in dirs:
                        print(f"✓ Found Blackbird-like structure at: {root}")
                        return root
        except Exception as e:
            print(f"  Error searching {search_dir}: {e}")
            continue
    
    return None

def load_blackbird_modules():
    """Try to load Blackbird modules with multiple strategies"""
    
    # Strategy 1: Try direct import from installed package
    try:
        import modules
        print("✓ Successfully imported Blackbird modules directly")
        return True
    except ImportError:
        print("✗ Direct import failed")
    
    # Strategy 2: Find and add to sys.path
    blackbird_root = find_blackbird_root()
    if blackbird_root:
        src_path = os.path.join(blackbird_root, 'src')
        if os.path.exists(src_path) and src_path not in sys.path:
            sys.path.insert(0, src_path)
            print(f"✓ Added Blackbird src to path: {src_path}")
            
            # Try import again
            try:
                import modules
                print("✓ Successfully imported after adding to path")
                return True
            except ImportError as e:
                print(f"✗ Import still failed: {e}")
    
    # Strategy 3: Check if we're in the blackbird directory
    current_files = os.listdir(CURRENT_DIR)
    parent_files = os.listdir(os.path.dirname(CURRENT_DIR))
    
    if 'modules' in current_files or 'modules' in parent_files:
        print("✓ Found modules directory nearby")
        # Add parent directory
        parent_dir = os.path.dirname(CURRENT_DIR)
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
        
        # Try to find src directory
        possible_src_dirs = [
            os.path.join(parent_dir, 'src'),
            os.path.join(CURRENT_DIR, 'src'),
            os.path.join(parent_dir, '..', 'src'),
        ]
        
        for src_dir in possible_src_dirs:
            if os.path.exists(src_dir) and src_dir not in sys.path:
                sys.path.insert(0, src_dir)
                print(f"✓ Added src directory: {src_dir}")
    
    # Strategy 4: Create minimal mock modules
    print("⚠ Creating minimal mock modules for basic functionality")
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
    
    mock_utils.filter = type(sys)('filter')
    mock_utils.filter.applyFilters = MockFilter.applyFilters
    
    # Add log mock
    class MockLog:
        @staticmethod
        def logError(e, msg, config):
            print(f"[ERROR] {msg}: {e}")
    
    mock_utils.log = type(sys)('log')
    mock_utils.log.logError = MockLog.logError
    
    # Create mock whatsmyname module
    mock_whatsmyname = type(sys)('modules.whatsmyname')
    
    class MockListOperations:
        @staticmethod
        def readList(list_type, config):
            if list_type == "username":
                path = config.USERNAME_LIST_PATH
            elif list_type == "metadata":
                path = config.USERNAME_METADATA_LIST_PATH
            else:
                return {"sites": []}
            
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {"sites": []}
    
    mock_whatsmyname.list_operations = type(sys)('list_operations')
    mock_whatsmyname.list_operations.readList = MockListOperations.readList
    
    # Add to sys.modules
    sys.modules['modules'] = mock_modules
    sys.modules['modules.utils'] = mock_utils
    sys.modules['modules.utils.http_client'] = mock_utils.http_client
    sys.modules['modules.utils.parse'] = mock_utils.parse
    sys.modules['modules.utils.filter'] = mock_utils.filter
    sys.modules['modules.utils.log'] = mock_utils.log
    sys.modules['modules.whatsmyname'] = mock_whatsmyname
    sys.modules['modules.whatsmyname.list_operations'] = mock_whatsmyname.list_operations
    
    print("✓ Created minimal mock modules")

def setup_blackbird_module_system():
    """Set up the module system to load Blackbird modules properly"""
    
    blackbird_root = find_blackbird_root()
    
    if blackbird_root:
        # Add to sys.path
        src_path = os.path.join(blackbird_root, 'src')
        if src_path not in sys.path:
            sys.path.insert(0, src_path)
            print(f"Added to sys.path: {src_path}")
        
        return src_path
    
    print("Warning: Could not find Blackbird installation")
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
        self._width = 80
        self._height = 24
        self.encoding = "utf-8"
    
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
        print(f"Starting fetch for username: {username}")
        
        # Import required utils or create fallbacks
        try:
            # Try to import the actual modules
            from modules.utils.http_client import do_async_request
            from modules.utils.parse import extractMetadata, remove_duplicates
            print("Successfully imported Blackbird utils")
        except ImportError as e:
            print(f"Import failed, using fallbacks: {e}")
            do_async_request = create_simple_async_request()
            extractMetadata = create_simple_extract_metadata()
            remove_duplicates = simple_remove_duplicates
        
        async with aiohttp.ClientSession() as session:
            results = []
            
            async def check_site(site):
                try:
                    # Build URL
                    url = site["uri_check"].replace("{account}", username)
                    
                    print(f"  Checking: {site.get('name', 'unknown')} -> {url}")
                    
                    # Make request
                    response = await do_async_request(
                        "GET",
                        url,
                        session,
                        config
                    )
                    
                    if response is None:
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
                                print(f"Metadata extraction failed: {e}")
                            
                            print(f"  ✓ Found on {site.get('name', 'unknown')}")
                            return result
                    
                    return {
                        "name": site.get("name", "unknown"),
                        "url": response.get("url", url),
                        "category": site.get("cat", "unknown"),
                        "status": "NOT-FOUND",
                        "metadata": None
                    }
                    
                except Exception as e:
                    print(f"Error checking site {site.get('name', 'unknown')}: {e}")
                    return {
                        "name": site.get("name", "unknown"),
                        "url": url,
                        "category": site.get("cat", "unknown"),
                        "status": "ERROR",
                        "metadata": None
                    }
            
            # Process sites concurrently
            tasks = []
            for site in config.username_sites:
                task = asyncio.create_task(check_site(site))
                tasks.append(task)
            
            # Wait for all tasks
            results = await asyncio.gather(*tasks)
            
            return {
                "results": results,
                "username": username,
                "total_checked": len(results)
            }
            
    except Exception as e:
        print(f"Error in simple_fetch_results: {e}")
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

# Update the search_username_blackbird function to use category filters
async def search_username_blackbird(username, config):
    """Use Blackbird's modules to search for username"""
    try:
        print(f"Starting Blackbird search for: {username}")
        
        # Import list operations
        try:
            from modules.whatsmyname.list_operations import readList
            from modules.utils.filter import applyFilters as blackbird_applyFilters
            print("Successfully imported Blackbird core modules")
            use_blackbird_modules = True
        except ImportError as e:
            print(f"Import error: {e}, using fallback functions")
            use_blackbird_modules = False
        
        # Define fallback functions
        def fallback_readList(list_type, config):
            print(f"Fallback readList for {list_type}")
            if list_type == "username":
                path = config.USERNAME_LIST_PATH
            elif list_type == "metadata":
                path = config.USERNAME_METADATA_LIST_PATH
            else:
                return {"sites": []}
            
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {"sites": []}
        
        def web_applyFilters(sites, config):
            """Web interface filter implementation that understands Blackbird syntax"""
            print(f"Applying filters to {len(sites)} sites")
            print(f"DEBUG: Filter string: '{config.filter}'")
            
            # Start with all sites
            filtered_sites = sites
            
            # Remove NSFW sites by default when category is filtered out
            # We'll handle this via category exclusion instead of separate no_nsfw flag
            # if config.no_nsfw:
            #     filtered_sites = [s for s in filtered_sites if s.get("cat") != "xx NSFW xx"]
            #     print(f"After NSFW filter: {len(filtered_sites)} sites")
            
            # Always check if we have a filter string from the web interface
            if hasattr(config, 'filter') and config.filter:
                # Parse the filter string
                filter_parts = config.filter.split()
                
                for filter_part in filter_parts:
                    print(f"DEBUG: Processing filter part: '{filter_part}'")
                    
                    # Handle category filters
                    if filter_part.startswith('cat='):
                        # Include categories: cat=social|tech
                        categories = filter_part[4:].split('|')
                        print(f"DEBUG: Including categories: {categories}")
                        
                        filtered_sites = [
                            s for s in filtered_sites 
                            if s.get('cat', '') in categories
                        ]
                        print(f"After cat= filter: {len(filtered_sites)} sites")
                        
                    elif filter_part.startswith('cat!='):
                        # Exclude categories: cat!=gaming|shopping
                        categories = filter_part[5:].split('|')
                        print(f"DEBUG: Excluding categories: {categories}")
                        
                        filtered_sites = [
                            s for s in filtered_sites 
                            if s.get('cat', '') not in categories
                        ]
                        print(f"After cat!= filter: {len(filtered_sites)} sites")
                        
                    elif filter_part.startswith('cat~'):
                        # Contains filter: cat~social (category contains "social")
                        search_term = filter_part[4:]
                        print(f"DEBUG: Category contains: '{search_term}'")
                        
                        filtered_sites = [
                            s for s in filtered_sites 
                            if search_term.lower() in s.get('cat', '').lower()
                        ]
                        print(f"After cat~ filter: {len(filtered_sites)} sites")
                        
                    elif '=' in filter_part and not filter_part.startswith('cat'):
                        # Other equality filters: name=twitter
                        key, value = filter_part.split('=', 1)
                        filtered_sites = [
                            s for s in filtered_sites 
                            if str(s.get(key, '')).lower() == value.lower()
                        ]
                        print(f"After {key}= filter: {len(filtered_sites)} sites")
                        
                    elif '!=' in filter_part and not filter_part.startswith('cat'):
                        # Other inequality filters: name!=twitter
                        key, value = filter_part.split('!=', 1)
                        filtered_sites = [
                            s for s in filtered_sites 
                            if str(s.get(key, '')).lower() != value.lower()
                        ]
                        print(f"After {key}!= filter: {len(filtered_sites)} sites")
                        
                    elif '~' in filter_part and not filter_part.startswith('cat'):
                        # Other contains filters: name~twitter
                        key, value = filter_part.split('~', 1)
                        filtered_sites = [
                            s for s in filtered_sites 
                            if value.lower() in str(s.get(key, '')).lower()
                        ]
                        print(f"After {key}~ filter: {len(filtered_sites)} sites")
                        
                    else:
                        # Simple text search
                        search_term = filter_part.lower()
                        filtered_sites = [
                            s for s in filtered_sites 
                            if (search_term in str(s.get('name', '')).lower() or
                                search_term in str(s.get('cat', '')).lower() or
                                search_term in str(s.get('uri_check', '')).lower())
                        ]
                        print(f"After text search: {len(filtered_sites)} sites")
            
            print(f"DEBUG: Final filtered sites: {len(filtered_sites)}")
            
            # Log some sample sites for debugging
            if filtered_sites:
                print(f"DEBUG: Sample sites after filtering:")
                for i, site in enumerate(filtered_sites[:5]):
                    print(f"  {i+1}. {site.get('name', 'unknown')} - cat: {site.get('cat', 'unknown')}")
            
            return filtered_sites
        
        # Use the appropriate readList function
        if use_blackbird_modules:
            readList_func = readList
        else:
            readList_func = fallback_readList
        
        # Load site data
        data = readList_func("username", config)
        print(f"Loaded {len(data.get('sites', []))} sites from {config.USERNAME_LIST_PATH}")
        
        # Apply filters - ALWAYS use web_applyFilters to ensure category filters work
        sites_to_search = data.get("sites", [])
        config.username_sites = web_applyFilters(sites_to_search, config)
        print(f"After filtering: {len(config.username_sites)} sites")
        
        # Load metadata
        metadata_data = readList_func("metadata", config)
        config.metadata_params = metadata_data
        
        # Perform search
        result = await simple_fetch_results(username, config)
        
        # Filter to only found accounts
        found_accounts = [
            r for r in result.get("results", []) 
            if r.get("status") == "FOUND"
        ]
        
        print(f"Search completed. Found {len(found_accounts)} accounts")
        
        return found_accounts
        
    except Exception as e:
        print(f"Error in search_username_blackbird: {e}")
        traceback.print_exc()
        return []

async def search_email_blackbird(email, config):
    """Use Blackbird's actual verifyEmail function with proper async handling"""
    try:
        print(f"Starting email search for: {email}")
        
        # For now, return empty results for email search
        # You can implement similar logic to username search if needed
        print("Email search not fully implemented yet")
        return []
        
    except Exception as e:
        print(f"Error in Blackbird email search for {email}: {str(e)}")
        traceback.print_exc()
        return []

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
    
    # Debug the filter
    if config.filter:
        print(f"DEBUG: Config filter set to: '{config.filter}'")
    
    config.no_nsfw = options.get('no_nsfw', False)
    config.dump = options.get('dump', False)
    config.csv = options.get('save_csv', True)
    config.json = options.get('save_json', True)
    config.pdf = options.get('save_pdf', False)
    config.ai = options.get('ai', False)
    
    # Store category filters for debugging
    config.include_categories = options.get('include_categories', '')
    config.exclude_categories = options.get('exclude_categories', '')
    
    # Create console
    config.console = WebConsole()
    
    return config

def save_reports(found_accounts, username, session_folder, config, search_type="username"):
    """Save reports using Blackbird's export modules"""
    try:
        print(f"Saving reports for {username} in {session_folder}")
        
        # Ensure the session folder exists
        os.makedirs(session_folder, exist_ok=True)
        
        # Set current user/email for file naming
        if search_type == "username":
            config.currentUser = username
            config.currentEmail = None
            identifier = username
        else:
            config.currentEmail = username
            config.currentUser = None
            identifier = username
        
        config.saveDirectory = session_folder
        
        reports = {}
        
        # Save CSV
        if config.csv and found_accounts:
            try:
                csv_file = f"{identifier}_{config.dateRaw}_blackbird.csv"
                csv_path = os.path.join(session_folder, csv_file)
                
                with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['name', 'url', 'category', 'status'])
                    for account in found_accounts:
                        writer.writerow([
                            account.get('name', 'Unknown'),
                            account.get('url', '#'),
                            account.get('category', 'unknown'),
                            account.get('status', 'UNKNOWN')
                        ])
                
                reports['csv_file'] = csv_file
                print(f"Saved CSV: {csv_file}")
            except Exception as e:
                print(f"Error saving CSV: {e}")
        
        # Save JSON
        if config.json and found_accounts:
            try:
                json_file = f"{identifier}_{config.dateRaw}_blackbird.json"
                json_path = os.path.join(session_folder, json_file)
                
                # Prepare data for JSON
                json_data = []
                for account in found_accounts:
                    account_data = {
                        'name': account.get('name', 'Unknown'),
                        'url': account.get('url', '#'),
                        'category': account.get('category', 'unknown'),
                        'status': account.get('status', 'UNKNOWN')
                    }
                    
                    # Add metadata if available
                    metadata = account.get('metadata')
                    if metadata:
                        account_data['metadata'] = metadata
                    
                    json_data.append(account_data)
                
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(json_data, f, indent=2, ensure_ascii=False)
                
                reports['json_file'] = json_file
                print(f"Saved JSON: {json_file}")
            except Exception as e:
                print(f"Error saving JSON: {e}")
        
        # Save PDF
        if config.pdf and found_accounts:
            try:
                pdf_file = f"{identifier}_{config.dateRaw}_blackbird.pdf"
                pdf_path = os.path.join(session_folder, pdf_file)
                
                # Create a simple PDF
                from reportlab.lib.pagesizes import letter
                from reportlab.pdfgen import canvas
                from reportlab.lib.units import inch
                
                c = canvas.Canvas(pdf_path, pagesize=letter)
                width, height = letter
                
                # Title
                c.setFont("Helvetica-Bold", 16)
                c.drawString(1*inch, height - 1*inch, f"Blackbird Report - {identifier}")
                
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
                
                for account in found_accounts[:30]:  # Limit to first 30
                    if y_position < 1*inch:  # New page if needed
                        c.showPage()
                        y_position = height - 1*inch
                    
                    # Site name
                    c.setFont("Helvetica-Bold", 10)
                    site_name = account.get('name', 'Unknown')
                    if len(site_name) > 30:
                        site_name = site_name[:27] + "..."
                    c.drawString(1*inch, y_position, site_name)
                    
                    # URL
                    c.setFont("Helvetica", 8)
                    url = account.get('url', '#')
                    if len(url) > 60:
                        url = url[:57] + "..."
                    c.drawString(3*inch, y_position, url)
                    
                    # Category
                    category = account.get('category', 'unknown')
                    c.drawString(6.5*inch, y_position, category)
                    
                    y_position -= 0.2*inch
                
                c.save()
                reports['pdf_file'] = pdf_file
                print(f"Created PDF: {pdf_file}")
                
            except Exception as e:
                print(f"Error saving PDF: {e}")
                reports['pdf_file'] = None
        
        # Reset config
        config.currentUser = None
        config.currentEmail = None
        config.saveDirectory = None
        
        return reports
        
    except Exception as e:
        print(f"Error in save_reports: {str(e)}")
        traceback.print_exc()
        return {}

async def process_single_search(item, search_type, config):
    """Process a single search item"""
    try:
        print(f"Processing {search_type}: {item}")
        
        if search_type == "username":
            found_accounts = await search_username_blackbird(item, config)
        elif search_type == "email":
            found_accounts = await search_email_blackbird(item, config)
        else:
            return None
        
        print(f"Found {len(found_accounts)} accounts for {item}")
        
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
        print(f"Error processing {item}: {str(e)}")
        traceback.print_exc()
        return None

def create_session_folder(username, search_type):
    """Create session folder in username_mm_dd_yyyy_blackbird format"""
    date_str = datetime.now().strftime("%m_%d_%Y")
    folder_name = f"{username}_{date_str}_blackbird"
    session_folder = os.path.join(app.config["REPORTS_FOLDER"], folder_name)
    return folder_name, session_folder

def process_search_task(search_items, search_type, options, timestamp):
    """Background task to process search using actual Blackbird code"""
    try:
        print(f"Starting search task for {len(search_items)} items")
        
        # Create a new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Process all searches
        tasks = []
        for item in search_items:
            # Create session folder for each username
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
            
            # Get the session folder for this username
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
            
            individual_reports.append({
                'username': item,
                'search_type': search_type,
                'folder_name': folder_name,
                'csv_file': reports.get('csv_file'),
                'json_file': reports.get('json_file'),
                'pdf_file': reports.get('pdf_file'),
                'claimed_profiles': claimed_profiles,
                'total_found': result['total_found']
            })
        
        # Save job results
        job_results[timestamp] = {
            'status': 'completed',
            'search_items': search_items,
            'search_type': search_type,
            'individual_reports': individual_reports,
            'timestamp': timestamp
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
            print(f"Config created, looking for data at: {config.USERNAME_LIST_PATH}")
            
            if os.path.exists(config.USERNAME_LIST_PATH):
                with open(config.USERNAME_LIST_PATH, 'r', encoding='utf-8') as f:
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
                print(f"Data file not found: {config.USERNAME_LIST_PATH}")
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
            "shopping": "🛒",
            "social": "💬",
            "tech": "💻",
            "video": "🎥"
            # "xx NSFW xx": "🔞"
        }
        
        # Create category data for template
        category_data = []
        for category in categories:
            # Skip NSFW category entirely
            if category == "xx NSFW xx":
                continue
                
            icon = category_icons.get(category, "📁")
            display_name = category
            
            category_data.append({
                'id': category,
                'name': display_name,
                'icon': icon
            })
        
        return render_template('index.html', 
                             site_options=site_names,
                             tag_options=tag_options,
                             categories=category_data)
        
    except Exception as e:
        print(f"Error loading index: {str(e)}")
        traceback.print_exc()
        return render_template('index.html', site_options=[], tag_options=[], categories=[])

@app.route('/search', methods=['POST'])
def search():
    """Handle search request"""
    try:
        print("Processing search request...")
        
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
        }
        
        print(f"Category filters - Included: {include_categories}, Excluded: {exclude_categories}")
        print(f"Final filter string: '{final_filter}'")
        
        # Start background job
        background_jobs[timestamp] = {
            'completed': False,
            'thread': Thread(
                target=process_search_task,
                args=(search_items, search_type, options, timestamp)
            ),
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
        print(f"Displaying results for session: {session_id}")
        
        # Find results for this session
        result_data = job_results.get(session_id)
        
        if not result_data:
            # Check if job is still running
            if session_id in background_jobs and not background_jobs[session_id]['completed']:
                # Job is still running, show waiting page
                flash('Search is still in progress. Please wait...', 'info')
                return render_template('status.html', timestamp=session_id)
            else:
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
        
        if not os.path.exists(config.USERNAME_LIST_PATH):
            print(f"Data file not found: {config.USERNAME_LIST_PATH}")
            return {'tags': [], 'total_sites': 0, 'status': 'no_data'}
        
        with open(config.USERNAME_LIST_PATH, 'r', encoding='utf-8') as f:
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
            
            if os.path.exists(config.USERNAME_LIST_PATH):
                with open(config.USERNAME_LIST_PATH, 'r', encoding='utf-8') as f:
                    username_data = json.load(f)
                stats['username_sites'] = len(username_data.get('sites', []))
            
            if os.path.exists(config.EMAIL_LIST_PATH):
                with open(config.EMAIL_LIST_PATH, 'r', encoding='utf-8') as f:
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
    print("Loading Blackbird modules...")
    load_blackbird_modules()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('blackbird-web.log'),
            logging.StreamHandler()
        ]
    )
    
    # Print startup info
    print("=" * 60)
    print("Starting Blackbird Web Interface")
    print("=" * 60)
    
    # Test data files
    config = BlackbirdConfig()
    print(f"\nData files:")
    print(f"  Username list: {config.USERNAME_LIST_PATH} - {'✓' if os.path.exists(config.USERNAME_LIST_PATH) else '✗'}")
    print(f"  Email list: {config.EMAIL_LIST_PATH} - {'✓' if os.path.exists(config.EMAIL_LIST_PATH) else '✗'}")
    print(f"  Metadata: {config.USERNAME_METADATA_LIST_PATH} - {'✓' if os.path.exists(config.USERNAME_METADATA_LIST_PATH) else '✗'}")
    
    # Check assets
    if BLACKBIRD_ASSETS_DIR:
        print(f"  Assets directory: {BLACKBIRD_ASSETS_DIR} - {'✓' if os.path.exists(BLACKBIRD_ASSETS_DIR) else '✗'}")
    
    # Test module imports
    print(f"\nModule status:")
    
    test_imports = [
        ('modules.utils.http_client', 'HTTP Client'),
        ('modules.utils.parse', 'Parse'),
        ('modules.utils.filter', 'Filter'),
        ('modules.whatsmyname.list_operations', 'List Operations'),
    ]
    
    for module_name, display_name in test_imports:
        try:
            __import__(module_name)
            print(f"  {display_name}: ✓")
        except ImportError:
            print(f"  {display_name}: ✗ (using mock)")
    
    # Run the app
    debug_mode = os.getenv('FLASK_DEBUG', 'True').lower() in ['true', '1', 't']
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', '5000'))
    
    print(f"\nStarting server on {host}:{port} (debug={debug_mode})")
    print("=" * 60)
    
    app.run(debug=debug_mode, host=host, port=port)