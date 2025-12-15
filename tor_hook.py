# tor_hook.py

import sys
import os
import requests
import json
import re
from stem import Signal
from stem.control import Controller

class TORHook:
    def __init__(self, tor_port=9050, control_port=9051, tor_password=None):
        self.tor_port = tor_port
        self.control_port = control_port
        self.tor_password = tor_password
        self.tor_enabled = False
        self.tor_session = None
        
    def enable_tor(self):
        """Enable TOR connection with redundant IP checking"""
        ip_services = [
            'http://httpbin.org/ip',
            'https://icanhazip.com/',
            'https://checkip.amazonaws.com/'
        ]
        try:
            session = requests.Session()
            session.proxies = {
                'http': f'socks5h://127.0.0.1:{self.tor_port}',
                'https': f'socks5h://127.0.0.1:{self.tor_port}'
            }

            ip = None
            for url in ip_services:
                try:
                    response = session.get(url, timeout=10)
                    if response.status_code == 200:
                        if 'httpbin.org' in url:
                            ip = response.json().get('origin')
                        else:
                            ip = response.text.strip()
                        print(f"🔒 TOR enabled - Current IP from {url}: {ip}")
                        break
                except Exception as e:
                    print(f"❌ Failed to get IP from {url}: {e}")

            if ip:
                self.tor_session = session
                self.tor_enabled = True
                return True
            else:
                print("❌ All IP checks failed, TOR enable unsuccessful")
                return False

        except Exception as e:
            print(f"❌ TOR connection failed: {e}")
            return False
    
    def renew_tor_ip(self):
        """Renew TOR circuit for new IP"""
        if not self.tor_enabled:
            return False
            
        try:
            with Controller.from_port(port=self.control_port) as controller:
                if self.tor_password:
                    controller.authenticate(password=self.tor_password)
                else:
                    controller.authenticate()
                
                controller.signal(Signal.NEWNYM)
                print("🔒 TOR circuit renewed - New IP address")
                return True
        except Exception as e:
            print(f"❌ Failed to renew TOR circuit: {e}")
            return False
    
    def intercept_ai_requests(self, command):
        """Intercept and modify Blackbird command to use TOR for AI requests"""
        if not self.tor_enabled or '--ai' not in command:
            return command
            
        # Renew IP before starting AI analysis
        self.renew_tor_ip()
        
        # We'll handle the interception in the output processing
        # For now, just return the original command
        return command
    
    def process_ai_output(self, line):
        """Process Blackbird output to intercept AI API calls"""
        if not self.tor_enabled:
            return line
            
        # Look for AI analysis starting
        if 'analyzing with ai' in line.lower():
            print("🔒 Intercepting AI requests through TOR...")
            # Renew IP for each new AI analysis
            self.renew_tor_ip()
            
        return line

def create_tor_proxy_command(original_command, tor_port=9050):
    """Create a command that routes through TOR proxy"""
    # This is a simplified version - in practice you'd use a more sophisticated approach
    tor_command = f"torify {original_command}"
    return tor_command

# Standalone TOR interceptor for command-line use
def intercept_blackbird_command():
    """Main interceptor function"""
    if len(sys.argv) < 2:
        print("Usage: python tor_hook.py <blackbird_command>")
        sys.exit(1)
    
    original_command = ' '.join(sys.argv[1:])
    
    # Check if TOR should be enabled
    use_tor = os.environ.get('BLACKBIRD_USE_TOR') == '1'
    tor_port = int(os.environ.get('TOR_PORT', 9050))
    
    if use_tor and '--ai' in original_command:
        print("🔒 TOR Interceptor: AI analysis will be routed through TOR")
        hook = TORHook(tor_port=tor_port)
        if hook.enable_tor():
            # For now, just print the command - in practice you'd execute it
            print(f"Executing with TOR: {original_command}")
            # Here you would actually execute the command with TOR routing
            os.system(create_tor_proxy_command(original_command, tor_port))
        else:
            print("❌ TOR failed, running without TOR")
            os.system(original_command)
    else:
        # Run original command
        os.system(original_command)

if __name__ == "__main__":
    intercept_blackbird_command()