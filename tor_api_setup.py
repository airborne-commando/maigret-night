import sys
import os
import subprocess
import requests
import socket
import time
import re
from PyQt6.QtCore import QThread, pyqtSignal

class TORAPISetup(QThread):
    """Thread to handle API setup through TOR with robust error handling"""
    output_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool)
    
    def __init__(self, tor_port=9050, control_port=9051, tor_password=None):
        super().__init__()
        self.tor_port = tor_port
        self.control_port = control_port
        self.tor_password = tor_password
        self.process = None
        self.tor_session = None
    
    def create_tor_session(self):
        """Create a TOR session with proper configuration"""
        session = requests.Session()
        session.proxies = {
            'http': f'socks5h://127.0.0.1:{self.tor_port}',
            'https': f'socks5h://127.0.0.1:{self.tor_port}'
        }
        
        # Add headers to avoid detection
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        })
        
        session.timeout = 15
        return session
    
    def check_tor_connection(self, retries=3):
        """Check TOR connection with multiple endpoints and retries"""
        if not self.tor_session:
            self.tor_session = self.create_tor_session()
        
        test_urls = [
            ("https://httpbin.org/ip", "httpbin"),
            ("https://api.ipify.org?format=json", "ipify"),
            ("https://icanhazip.com", "icanhazip"),
            ("https://checkip.amazonaws.com", "aws"),
            ("https://ipinfo.io/ip", "ipinfo"),
            ("http://checkip.dyndns.org", "dyndns"),
        ]
        
        successful_tests = 0
        last_ip = None
        
        for url, service_name in test_urls:
            for attempt in range(retries):
                try:
                    self.output_signal.emit(f"🔍 Testing TOR via {service_name}...")
                    response = self.tor_session.get(url, timeout=10)
                    
                    if response.status_code == 200:
                        # Extract IP from response
                        try:
                            if 'application/json' in response.headers.get('Content-Type', ''):
                                ip_data = response.json()
                                ip = ip_data.get("origin") or ip_data.get("ip") or ip_data.get("query")
                            else:
                                # Parse plain text
                                text = response.text.strip()
                                ip_match = re.search(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', text)
                                ip = ip_match.group(0) if ip_match else text
                            
                            if ip:
                                if last_ip is None:
                                    last_ip = ip
                                
                                # Check if IPs are consistent (should be same TOR exit node)
                                if ip == last_ip:
                                    self.output_signal.emit(f"✅ {service_name}: IP {ip}")
                                    successful_tests += 1
                                else:
                                    self.output_signal.emit(f"⚠️  {service_name}: Different IP {ip} (expected {last_ip})")
                                    # Still count as successful if we got an IP
                                    successful_tests += 1
                                    last_ip = ip
                                
                                # If we have at least 2 successful tests, TOR is working
                                if successful_tests >= 2:
                                    self.output_signal.emit(f"🔒 TOR connection established - Current IP: {last_ip}")
                                    return True
                                
                                break  # Success, move to next endpoint
                        except Exception as e:
                            self.output_signal.emit(f"⚠️  Could not parse {service_name} response: {e}")
                    else:
                        self.output_signal.emit(f"⚠️  {service_name}: HTTP {response.status_code}")
                        
                except requests.exceptions.Timeout:
                    self.output_signal.emit(f"⚠️  {service_name}: Timeout (attempt {attempt + 1}/{retries})")
                    if attempt < retries - 1:
                        time.sleep(2)
                except requests.exceptions.ConnectionError:
                    self.output_signal.emit(f"⚠️  {service_name}: Connection error (attempt {attempt + 1}/{retries})")
                    if attempt < retries - 1:
                        time.sleep(2)
                except Exception as e:
                    self.output_signal.emit(f"⚠️  {service_name}: Error {e}")
                    if attempt < retries - 1:
                        time.sleep(2)
            
            # Small delay between endpoints
            time.sleep(0.5)
        
        if successful_tests > 0:
            self.output_signal.emit(f"⚠️  Partial TOR connectivity: {successful_tests}/6 endpoints")
            return True
        
        self.output_signal.emit("❌ TOR connection failed across all endpoints")
        return False

    def renew_tor_ip(self):
        """Get fresh TOR IP with robust error handling"""
        try:
            self.output_signal.emit("🔄 Renewing TOR IP address...")
            
            # Connect to TOR control port
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(15)
            sock.connect(('127.0.0.1', self.control_port))
            
            # Authenticate
            if self.tor_password:
                auth_cmd = f'AUTHENTICATE "{self.tor_password}"\r\n'
                sock.send(auth_cmd.encode())
                response = sock.recv(1024).decode()
                
                if '250 OK' in response:
                    self.output_signal.emit("🔐 Authenticated with password")
                else:
                    # Try without password
                    auth_cmd = 'AUTHENTICATE\r\n'
                    sock.send(auth_cmd.encode())
                    response = sock.recv(1024).decode()
            else:
                auth_cmd = 'AUTHENTICATE\r\n'
                sock.send(auth_cmd.encode())
                response = sock.recv(1024).decode()
            
            if '250 OK' not in response:
                self.output_signal.emit(f"❌ Authentication failed: {response}")
                sock.close()
                return False
            
            # Request new circuit
            sock.send(b'SIGNAL NEWNYM\r\n')
            response = sock.recv(1024).decode()
            
            if '250 OK' not in response:
                self.output_signal.emit(f"❌ NEWNYM failed: {response}")
                sock.close()
                return False
            
            sock.send(b'QUIT\r\n')
            sock.close()
            
            self.output_signal.emit("✅ TOR circuit renewed")
            
            # Wait for circuit to establish and verify
            time.sleep(5)
            
            # Verify new IP
            if self.check_tor_connection(retries=2):
                self.output_signal.emit("✅ Fresh TOR IP ready for API registration")
                return True
            else:
                self.output_signal.emit("⚠️  TOR renewal succeeded but IP verification failed")
                return True  # Still continue with setup
                
        except socket.timeout:
            self.output_signal.emit("❌ TOR control port timeout - is TOR running?")
            return False
        except ConnectionRefusedError:
            self.output_signal.emit("❌ TOR control port refused - check TOR configuration")
            return False
        except Exception as e:
            self.output_signal.emit(f"❌ TOR renewal error: {e}")
            # Don't fail entirely, continue with current IP
            return True
    
    def verify_api_connectivity(self):
        """Verify connectivity to Blackbird AI API through TOR"""
        test_endpoints = [
            "https://api.blackbird.ai/status",  # If there's a status endpoint
            "https://api.blackbird.ai/",        # Base API endpoint
        ]
        
        for endpoint in test_endpoints:
            try:
                response = self.tor_session.get(endpoint, timeout=10)
                if response.status_code < 500:  # Anything other than server errors
                    self.output_signal.emit(f"✅ API connectivity test passed: {endpoint}")
                    return True
                else:
                    self.output_signal.emit(f"⚠️  API endpoint {endpoint}: HTTP {response.status_code}")
            except Exception as e:
                self.output_signal.emit(f"⚠️  API endpoint {endpoint}: {e}")
        
        self.output_signal.emit("⚠️  API connectivity tests inconclusive - proceeding anyway")
        return True  # Proceed even if we can't reach API
    
    def run_blackbird_setup(self):
        """Run blackbird setup command with proper environment"""
        try:
            # Set up environment variables for TOR
            env = os.environ.copy()
            env['ALL_PROXY'] = f'socks5h://127.0.0.1:{self.tor_port}'
            env['HTTP_PROXY'] = f'socks5h://127.0.0.1:{self.tor_port}'
            env['HTTPS_PROXY'] = f'socks5h://127.0.0.1:{self.tor_port}'
            env['BLACKBIRD_USE_TOR'] = '1'  # Signal to blackbird.py to use TOR
            
            # Run the setup command
            cmd = ['python', 'blackbird.py', '--setup-ai']
            self.output_signal.emit(f"🚀 Starting: {' '.join(cmd)}")
            
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.PIPE,
                text=True,
                env=env,
                bufsize=1,
                universal_newlines=True
            )
            
            # Monitor output and handle prompts
            confirmation_sent = False
            for line in iter(self.process.stdout.readline, ''):
                if not line:
                    break
                    
                text = line.strip()
                self.output_signal.emit(text)
                
                # Look for registration prompt
                if not confirmation_sent:
                    if any(prompt in text.lower() for prompt in ['ip is registered', '[y/n]', 'register this ip', 'confirm']):
                        try:
                            # Send confirmation
                            self.process.stdin.write('Y\n')
                            self.process.stdin.flush()
                            confirmation_sent = True
                            self.output_signal.emit("✅ Sent confirmation for TOR IP registration")
                        except Exception as e:
                            self.output_signal.emit(f"⚠️  Could not send confirmation: {e}")
                
                # Check for success indicators
                if any(success in text.lower() for success in ['success', 'api key saved', 'registered', 'setup complete']):
                    self.output_signal.emit("✅ API setup appears successful")
            
            # Wait for process to complete
            return_code = self.process.wait()
            
            if return_code == 0:
                self.output_signal.emit("✅ Blackbird AI setup completed successfully")
                return True
            else:
                self.output_signal.emit(f"⚠️  Blackbird setup returned code {return_code}")
                # Still might be successful if API key was saved
                return self.check_api_key_saved()
                
        except Exception as e:
            self.output_signal.emit(f"❌ Setup process failed: {e}")
            return False
    
    def check_api_key_saved(self):
        """Check if API key was saved to file"""
        config_paths = [
            os.path.expanduser("~/.ai_key.json"),
            ".ai_key.json",
            "ai_key.json"
        ]
        
        for config_path in config_paths:
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r') as f:
                        import json
                        config = json.load(f)
                        if config.get("ai_api_key") or config.get("api_key"):
                            self.output_signal.emit(f"✅ API key found in {config_path}")
                            return True
                except Exception as e:
                    self.output_signal.emit(f"⚠️  Could not read {config_path}: {e}")
        
        self.output_signal.emit("⚠️  No API key found in expected locations")
        return False
    
    def run(self):
        """Execute API setup through TOR with comprehensive error handling"""
        self.output_signal.emit("=" * 60)
        self.output_signal.emit("🚀 BLACKBIRD AI API SETUP THROUGH TOR")
        self.output_signal.emit("=" * 60)
        
        # Step 1: Establish TOR connection
        self.output_signal.emit("🔧 Step 1: Testing TOR connectivity...")
        if not self.check_tor_connection():
            self.output_signal.emit("❌ Cannot proceed without TOR connection")
            self.finished_signal.emit(False)
            return
        
        # Step 2: Renew IP for fresh registration
        self.output_signal.emit("🔧 Step 2: Getting fresh TOR IP for registration...")
        if not self.renew_tor_ip():
            self.output_signal.emit("⚠️  IP renewal failed, continuing with current IP...")
        
        # Step 3: Verify API connectivity
        self.output_signal.emit("🔧 Step 3: Testing API connectivity...")
        self.verify_api_connectivity()
        
        # Step 4: Run the setup
        self.output_signal.emit("🔧 Step 4: Running Blackbird AI setup...")
        success = self.run_blackbird_setup()
        
        # Step 5: Final verification
        if success:
            self.output_signal.emit("🔧 Step 5: Verifying setup...")
            if self.check_api_key_saved():
                self.output_signal.emit("=" * 60)
                self.output_signal.emit("✅ API SETUP COMPLETE THROUGH TOR")
                self.output_signal.emit("=" * 60)
                self.finished_signal.emit(True)
                return
        
        self.output_signal.emit("=" * 60)
        self.output_signal.emit("⚠️  API SETUP MAY NOT HAVE COMPLETED SUCCESSFULLY")
        self.output_signal.emit("=" * 60)
        self.finished_signal.emit(False)
    
    def stop(self):
        """Stop the setup process"""
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
            self.output_signal.emit("⏹️  Setup process stopped")