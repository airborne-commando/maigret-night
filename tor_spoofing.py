import requests
import time
import os
import subprocess
import socket
from PyQt6.QtWidgets import QMessageBox

class TORSpoofer:
    def __init__(self, gui_instance=None):
        self.gui_instance = gui_instance
        self.tor_enabled = False
        self.tor_session = None
        self.tor_port = 9050  # Default TOR port
        self.control_port = 9051  # Default control port
        self.tor_password = "hashbrownyummy"  # Set your password here, change it
    
    def log_message(self, message):
        """Log messages to GUI output area if available"""
        if self.gui_instance and hasattr(self.gui_instance, 'output_area'):
            self.gui_instance.output_area.append(f"🔒 TOR: {message}")
        else:
            print(f"TOR: {message}")
    
    def check_tor_connection(self):
        """Check if TOR is running and accessible via multiple endpoints with better error handling."""
        test_urls = [
            "https://httpbin.org/ip",          # Returns JSON - Primary
            "https://api.ipify.org?format=json",  # Returns JSON - Secondary
            "https://icanhazip.com",           # Returns plain text - Tertiary
            "https://checkip.amazonaws.com",   # Returns plain text - Quaternary
            "http://checkip.dyndns.org",       # Simple HTTP endpoint
            "https://ipinfo.io/ip",            # Another reliable endpoint
            "https://api.myip.com",            # JSON endpoint
            "http://ip-api.com/json"           # JSON endpoint with location info
        ]

        session = requests.Session()
        session.proxies = {
            'http': f'socks5h://127.0.0.1:{self.tor_port}',
            'https': f'socks5h://127.0.0.1:{self.tor_port}'
        }
        
        successful_connections = 0
        last_error = None
        
        for url in test_urls:
            try:
                # Add headers to avoid being blocked
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': 'application/json, text/plain, */*'
                }
                
                response = session.get(url, headers=headers, timeout=5)
                
                # Handle 503 and other non-200 responses
                if response.status_code != 200:
                    self.log_message(f"⚠️  {url} returned {response.status_code}, trying next...")
                    last_error = f"HTTP {response.status_code}"
                    continue  # Try next endpoint
                
                # Try to extract IP from response
                try:
                    # Try parsing JSON response first
                    if 'application/json' in response.headers.get('Content-Type', ''):
                        ip_data = response.json()
                        # Extract IP from various possible JSON structures
                        ip = (ip_data.get("origin") or 
                              ip_data.get("ip") or 
                              ip_data.get("query") or
                              ip_data.get("addr"))
                    else:
                        # Parse plain text response
                        ip_text = response.text.strip()
                        # Extract IP address using regex for safety
                        import re
                        ip_match = re.search(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', ip_text)
                        ip = ip_match.group(0) if ip_match else ip_text
                    
                    if ip:
                        self.log_message(f"✅ Connected via TOR - Current IP: {ip} (via {url.split('/')[2]})")
                        successful_connections += 1
                        
                        # If we have at least 2 successful connections, consider TOR working
                        if successful_connections >= 2:
                            return True
                        
                except (ValueError, KeyError, AttributeError) as e:
                    self.log_message(f"⚠️  Could not parse response from {url}: {e}")
                    continue
                    
            except requests.exceptions.Timeout:
                self.log_message(f"⚠️  Timeout connecting to {url}, trying next...")
                last_error = "Timeout"
                continue
            except requests.exceptions.ConnectionError:
                self.log_message(f"⚠️  Connection error to {url}, trying next...")
                last_error = "Connection error"
                continue
            except Exception as e:
                self.log_message(f"⚠️  Error with {url}: {e}")
                last_error = str(e)
                continue
        
        # If we get here, we didn't get enough successful connections
        if successful_connections > 0:
            self.log_message(f"⚠️  Partial TOR connectivity: {successful_connections}/8 endpoints")
            return True  # Still return True if we have at least some connectivity
        
        self.log_message(f"❌ TOR connection failed. Last error: {last_error}")
        return False

    def test_tor_circuit(self):
        """Test TOR circuit with multiple requests to ensure it's working properly."""
        endpoints = [
            ("https://httpbin.org/headers", "headers"),
            ("https://api.ipify.org?format=json", "ipify"),
            ("https://ipinfo.io/json", "ipinfo"),
        ]
        
        session = requests.Session()
        session.proxies = {
            'http': f'socks5h://127.0.0.1:{self.tor_port}',
            'https': f'socks5h://127.0.0.1:{self.tor_port}'
        }
        
        successful_tests = 0
        for url, name in endpoints:
            try:
                response = session.get(url, timeout=5)
                if response.status_code == 200:
                    self.log_message(f"✅ TOR circuit test {name}: OK")
                    successful_tests += 1
                else:
                    self.log_message(f"⚠️  TOR circuit test {name}: HTTP {response.status_code}")
            except Exception as e:
                self.log_message(f"⚠️  TOR circuit test {name}: Failed - {e}")
        
        return successful_tests >= 2  # Need at least 2 successful tests
    
    def renew_tor_connection(self):
        """Renew TOR circuit using raw socket authentication"""
        try:
            # Use raw socket connection
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            sock.connect(('127.0.0.1', self.control_port))
            
            # Try authentication with password
            if self.tor_password:
                auth_cmd = f'AUTHENTICATE "{self.tor_password}"\r\n'
                sock.send(auth_cmd.encode())
                response = sock.recv(1024).decode()
                
                if '250 OK' in response:
                    self.log_message("🔐 Authenticated with password")
                else:
                    # Try without password
                    auth_cmd = 'AUTHENTICATE\r\n'
                    sock.send(auth_cmd.encode())
                    response = sock.recv(1024).decode()
            else:
                # Try without password
                auth_cmd = 'AUTHENTICATE\r\n'
                sock.send(auth_cmd.encode())
                response = sock.recv(1024).decode()
            
            if '250 OK' not in response:
                self.log_message(f"❌ Authentication failed: {response}")
                sock.close()
                return False
            
            # Send NEWNYM signal
            sock.send(b'SIGNAL NEWNYM\r\n')
            response = sock.recv(1024).decode()
            
            if '250 OK' not in response:
                self.log_message(f"❌ NEWNYM failed: {response}")
                sock.close()
                return False
            
            self.log_message("🔄 Renewed TOR circuit - New IP address")
            sock.send(b'QUIT\r\n')
            sock.close()
            
            # Wait for circuit to establish and test
            time.sleep(3)
            
            # Test the new circuit
            if self.test_tor_circuit():
                self.log_message("✅ New TOR circuit working properly")
                return True
            else:
                self.log_message("⚠️  New circuit test failed, but renewal succeeded")
                return True  # Still return True as renewal worked
            
        except Exception as e:
            self.log_message(f"❌ TOR renewal failed: {e}")
            return False
            
    def setup_tor_session(self):
        """Set up a requests session that routes through TOR with better validation"""
        if not self.check_tor_connection():
            self.log_message("TOR not available. Please ensure TOR is running.")
            return None
        
        # Test circuit quality
        if not self.test_tor_circuit():
            self.log_message("⚠️  TOR circuit quality test failed, but continuing...")
        
        self.tor_session = requests.Session()
        self.tor_session.proxies = {
            'http': f'socks5h://127.0.0.1:{self.tor_port}',
            'https': f'socks5h://127.0.0.1:{self.tor_port}'
        }
        
        # Add headers to avoid detection
        self.tor_session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        })
        
        self.tor_enabled = True
        self.log_message("✅ TOR session configured successfully")
        return self.tor_session
    
    def get_current_ip(self, retry_count=3):
        """Get current public IP address through TOR with retry logic"""
        if not self.tor_session:
            if not self.setup_tor_session():
                return None
        
        for attempt in range(retry_count):
            try:
                # Try multiple endpoints
                endpoints = [
                    'https://httpbin.org/ip',
                    'https://api.ipify.org?format=json',
                    'https://icanhazip.com'
                ]
                
                for url in endpoints:
                    try:
                        response = self.tor_session.get(url, timeout=5)
                        if response.status_code == 200:
                            if 'application/json' in response.headers.get('Content-Type', ''):
                                ip_data = response.json()
                                return ip_data.get('origin') or ip_data.get('ip')
                            else:
                                return response.text.strip()
                    except Exception:
                        continue  # Try next endpoint
                
                self.log_message(f"⚠️  IP check attempt {attempt + 1} failed")
                if attempt < retry_count - 1:
                    time.sleep(2)  # Wait before retry
                    
            except Exception as e:
                self.log_message(f"❌ Failed to get current IP (attempt {attempt + 1}): {e}")
                if attempt < retry_count - 1:
                    time.sleep(2)
        
        return None
    
    def enable_tor_for_ai(self, tor_port=9050, control_port=9051):
        """Enable TOR spoofing for AI requests with comprehensive testing"""
        self.tor_port = tor_port
        self.control_port = control_port
        
        # First, ensure TOR is running
        if not self.ensure_tor_running():
            self.log_message("❌ Failed to start TOR service")
            return False
        
        if self.setup_tor_session():
            self.tor_enabled = True
            
            # Test IP renewal and circuit quality
            try:
                # Get initial IP
                initial_ip = self.get_current_ip()
                if initial_ip:
                    self.log_message(f"🔍 Initial TOR IP: {initial_ip}")
                
                # Test renewal
                if self.renew_tor_connection():
                    new_ip = self.get_current_ip()
                    if new_ip and new_ip != initial_ip:
                        self.log_message(f"✅ TOR IP changed from {initial_ip} to {new_ip}")
                    elif new_ip:
                        self.log_message(f"⚠️  TOR IP unchanged: {new_ip}")
                    else:
                        self.log_message("✅ TOR renewal succeeded (IP check failed)")
                else:
                    self.log_message("⚠️  TOR renewal failed, but base connection working")
                    
            except Exception as e:
                self.log_message(f"✅ TOR enabled with testing issues: {e}")
            
            return True
        else:
            self.tor_enabled = False
            self.log_message("❌ Failed to enable TOR spoofing")
            return False
    
    def ensure_tor_running(self):
        """Ensure TOR service is running with multiple checks"""
        try:
            # First check if TOR is already running
            if self.check_tor_connection():
                return True
            
            # Try alternative methods to start TOR
            methods = [
                # Method 1: systemctl
                (['sudo', 'systemctl', 'start', 'tor'], "systemctl"),
                # Method 2: service command
                (['sudo', 'service', 'tor', 'start'], "service"),
                # Method 3: direct TOR binary (if installed)
                (['tor', '--quiet'], "tor binary"),
            ]
            
            for command, method_name in methods:
                try:
                    self.log_message(f"🔄 Attempting to start TOR via {method_name}...")
                    result = subprocess.run(command, 
                                          capture_output=True, 
                                          text=True, 
                                          timeout=5)
                    
                    if result.returncode == 0:
                        self.log_message(f"✅ TOR started via {method_name}")
                        # Wait for TOR to initialize
                        time.sleep(5)
                        
                        # Verify it's working
                        if self.check_tor_connection():
                            return True
                    else:
                        self.log_message(f"⚠️  {method_name} failed: {result.stderr}")
                        
                except (subprocess.TimeoutExpired, FileNotFoundError) as e:
                    self.log_message(f"⚠️  {method_name} unavailable: {e}")
                    continue
            
            self.log_message("❌ All TOR startup methods failed")
            return False
                
        except Exception as e:
            self.log_message(f"❌ TOR service management failed: {e}")
            return False
    
    def disable_tor(self):
        """Disable TOR spoofing"""
        self.tor_enabled = False
        self.tor_session = None
        self.log_message("TOR spoofing disabled")