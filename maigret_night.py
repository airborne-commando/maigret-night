import sys
import subprocess
import json
import os
import re
import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QPushButton, QTextEdit, QCheckBox, 
                             QGroupBox, QFormLayout, QSpinBox, QComboBox, QTabWidget, 
                             QFileDialog, QMessageBox, QDialog, QDialogButtonBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

# Import Blackbird modules
from build_blackbird_command import build_blackbird_command
from tor_spoofing import TORSpoofer
from breach_vip import process_single_email, process_email_file, is_enabled as is_breach_email_enabled
from breach_vip_username import process_single_username, process_username_file, is_enabled as is_breach_username_enabled

# Worker class that handles executing the Maigret command in a separate thread
class MaigretWorker(QThread):
    output_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()  # Add this signal to indicate completion

    def __init__(self, command):
        super().__init__()
        self.command = command
        self.process = None

    def run(self):
        self.process = subprocess.Popen(self.command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, shell=True)
        for line in self.process.stdout:
            self.output_signal.emit(line.strip())
        self.process.wait()

        self.finished_signal.emit()  # Emit when the process finishes

    def terminate(self):
        if self.process:
            self.process.terminate()
            self.process.wait()

# Worker class for Crow (Blackbird) commands
class CrowWorker(QThread):
    output_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()
    ai_file_saved = pyqtSignal(str)  # Signal when AI file is saved
    
    def __init__(self, command, needs_ai_confirmation=False, is_setup_ai=False, tor_spoofer=None, username="", email=""):
        super().__init__()
        self.command = command
        self.process = None
        self.needs_ai_confirmation = needs_ai_confirmation
        self.is_setup_ai = is_setup_ai
        self.tor_spoofer = tor_spoofer
        self.username = username
        self.email = email
        
        # AI analysis state
        self.ai_results_started = False
        self.ai_results_buffer = []
    
    def run(self):
        # Set up TOR environment at the beginning
        if self.tor_spoofer and self.tor_spoofer.tor_enabled:
            # Set comprehensive proxy environment
            proxy_url = f"socks5://127.0.0.1:{self.tor_spoofer.tor_port}"
            os.environ["HTTP_PROXY"] = proxy_url
            os.environ["HTTPS_PROXY"] = proxy_url
            os.environ["ALL_PROXY"] = proxy_url
            os.environ["BLACKBIRD_USE_TOR"] = "1"
            os.environ["TOR_PORT"] = str(self.tor_spoofer.tor_port)
            
            # Clear SSL verification warnings
            os.environ["PYTHONHTTPSVERIFY"] = "0"
            import ssl
            ssl._create_default_https_context = ssl._create_unverified_context
        
        self.process = subprocess.Popen(
            self.command, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT, 
            stdin=subprocess.PIPE,
            text=True, 
            shell=True,
            bufsize=1
        )
        
        if self.is_setup_ai:
            import time
            time.sleep(2)
            try:
                self.process.stdin.write('Y\n')
                self.process.stdin.flush()
                self.output_signal.emit("✓ Sent confirmation for API key setup")
            except Exception as e:
                self.output_signal.emit(f"Setup confirmation error: {e}")
        
        # Process output line by line
        confirmation_sent = False
        for line in self.process.stdout:
            text = line.rstrip()  # Keep original formatting
            
            # Handle AI confirmation if needed
            if (self.needs_ai_confirmation and not confirmation_sent and 
                ('analyzing with ai' in text.lower() or 'consent' in text.lower())):
                try:
                    self.process.stdin.write('Y\n')
                    self.process.stdin.flush()
                    confirmation_sent = True
                    self.output_signal.emit("✓ Automatically confirmed AI analysis")
                except Exception as e:
                    self.output_signal.emit(f"AI confirmation error: {e}")
            
            # Process AI analysis output (similar to crow.py logic)
            self.process_ai_output(text)
            
            # Emit formatted text to GUI
            formatted_text = self.format_ai_text_for_gui(text)
            self.output_signal.emit(formatted_text)
        
        # Save any remaining AI results
        if self.ai_results_started:
            self.auto_save_ai_results()
        
        self.process.stdout.close()
        self.process.wait()

    def process_ai_output(self, text):
        """Process AI analysis output similar to crow.py"""
        # Check if AI analysis is starting
        if 'analyzing with ai' in text.lower() or '✨ analyzing with ai' in text.lower():
            self.ai_results_started = True
            self.ai_results_buffer = [
                "🤖 BLACKBIRD AI ANALYSIS REPORT",
                "=" * 60,
                f"Generated: {self.get_current_timestamp()}",
                "=" * 60,
                ""
            ]
            
            # Add search context
            if self.username:
                self.ai_results_buffer.append(f"Target Username: {self.username}")
            if self.email:
                self.ai_results_buffer.append(f"Target Email: {self.email}")
            if self.username or self.email:
                self.ai_results_buffer.append("")
        
        # Buffer AI results
        if self.ai_results_started:
            # Clean and format the text for file output
            clean_text = text.replace('🤖', '').replace('📊', '').strip()
            if clean_text:  # Only add non-empty lines
                self.ai_results_buffer.append(clean_text)
            
            # Check if AI analysis is complete
            if 'ai queries left' in text.lower() or 'analysis complete' in text.lower():
                self.ai_results_buffer.extend([
                    "",
                    "=" * 60,
                    f"Analysis complete - {self.get_current_timestamp()}",
                    "=" * 60
                ])
                self.auto_save_ai_results()
                self.ai_results_started = False
    
    def format_ai_text_for_gui(self, text):
        """Format AI text for GUI display with emojis (from crow.py)"""
        if any(keyword in text.lower() for keyword in ['analyzing with ai', 'ai queries left', '✨']):
            return f"🤖 {text}"
        elif text.startswith('[Summary]'):
            return f"📋 {text}"
        elif text.startswith('[Profile Type]'):
            return f"🎯 {text}"
        elif text.startswith('[Insights]'):
            return f"💡 {text}"
        elif text.startswith('[Risk Flags]'):
            return f"⚠️  {text}"
        elif text.startswith('[Tags]'):
            return f"🏷️  {text}"
        else:
            return text
    
    def get_current_timestamp(self):
        """Get current timestamp for file naming and reports"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def auto_save_ai_results(self):
        """Automatically save AI results to file (from crow.py)"""
        if not self.ai_results_buffer:
            return
        
        try:
            import re
            import os
            from datetime import datetime
            
            # Generate filename with timestamp and target info
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Create descriptive filename
            if self.username:
                base_name = self.username
            elif self.email:
                base_name = self.email.split('@')[0]
            else:
                base_name = "analysis"

            # Clean filename
            safe_name = re.sub(r'[^\w\-_.]', '_', base_name)
            filename = f"blackbird_ai_{safe_name}_{timestamp}.txt"

            # Directory path where you want to save the file
            directory_path = "results"

            # Create directory if it doesn't exist
            if not os.path.exists(directory_path):
                os.makedirs(directory_path)

            # Full file path with directory
            full_path = os.path.join(directory_path, filename)

            # Save to file
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(self.ai_results_buffer))
            
            # Emit signal that file was saved
            self.ai_file_saved.emit(full_path)
            
        except Exception as e:
            self.output_signal.emit(f"❌ Error auto-saving AI results: {e}")
    
    def terminate(self):
        if self.process:
            self.process.terminate()
            self.process.wait()

# Main GUI class for the Maigret OSINT tool
class MaigretGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Maigret Night")
        self.setGeometry(100, 100, 1200, 800)  # Increased window size for Crow tab
        self.maigret_worker = None
        self.crow_worker = None
        self.crow_tor_spoofer = None
        self.crow_ai_api_key = None

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        tab_widget = QTabWidget()
        layout.addWidget(tab_widget)

        # Create tabs for different sections
        self.create_options_tab(tab_widget)
        self.create_crow_tab(tab_widget)

        # Buttons and output area
        self.create_buttons(layout)

        # Add Save and Load actions
        self.create_save_load_actions(layout)

    # ================================================================
    # CROW TAB METHODS
    # ================================================================

    def verify_tor_connection(self):
        """Verify TOR connection status"""
        if not self.crow_tor_spoofer:
            return False
        
        try:
            import requests
            
            # Test connection through TOR
            proxy_url = f"socks5://127.0.0.1:{self.crow_tor_spoofer.tor_port}"
            proxies = {
                'http': proxy_url,
                'https': proxy_url
            }
            
            # Try to access a TOR check service
            response = requests.get("https://check.torproject.org/api/ip", 
                                   proxies=proxies, 
                                   timeout=10)
            
            data = response.json()
            if data.get('IsTor', False):
                self.output_area.append("✅ TOR connection verified and masking active")
                return True
            else:
                self.output_area.append("⚠️  Connected but not using TOR exit node")
                return False
                
        except Exception as e:
            self.output_area.append(f"❌ TOR connection test failed: {e}")
            return False

    def select_crow_username_file(self):
        """Select username file for Crow search"""
        file_name, _ = QFileDialog.getOpenFileName(self, "Select Username File")
        if file_name:
            self.crow_username_input.setText(f"file:{file_name}")

    def select_crow_email_file(self):
        """Select email file for Crow search"""
        file_name, _ = QFileDialog.getOpenFileName(self, "Select Email File")
        if file_name:
            self.crow_email_input.setText(f"file:{file_name}")

    def setup_crow_ai_api_key(self):
        """Setup AI API key for Crow with proper TOR masking"""
        self.output_area.clear()
        self.output_area.append("🔧 Starting API Key setup for Crow...")
        
        # Delete existing API key for fresh registration
        self.delete_crow_api_key()
        
        # Check if TOR is enabled
        if self.crow_tor_checkbox.isChecked():
            self.output_area.append("🕶️  TOR enabled - ensuring anonymous registration...")
            
            # Initialize TOR spoofer if not already done
            if not self.crow_tor_spoofer:
                self.crow_tor_spoofer = TORSpoofer(self)
            
            # Test TOR connection first
            if not self.crow_tor_spoofer.enable_tor_for_ai():
                self.output_area.append("❌ TOR connection failed. Retrying...")
                
                # Try to restart TOR service
                if not self.restart_tor_service():
                    self.output_area.append("❌ TOR setup failed. Using fallback method...")
                    self.setup_with_proxychains()
                    return
                else:
                    self.output_area.append("✅ TOR restarted successfully")
            
            # Set environment variables for TOR proxying
            os.environ["BLACKBIRD_USE_TOR"] = "1"
            os.environ["TOR_PORT"] = str(self.crow_tor_spoofer.tor_port)
            
            # Set HTTP/HTTPS proxy environment variables for all connections
            proxy_url = f"socks5://127.0.0.1:{self.crow_tor_spoofer.tor_port}"
            os.environ["HTTP_PROXY"] = proxy_url
            os.environ["HTTPS_PROXY"] = proxy_url
            os.environ["ALL_PROXY"] = proxy_url
            
            # Also set for Python requests/urllib
            os.environ["REQUESTS_CA_BUNDLE"] = ""
            
            self.output_area.append(f"✅ TOR proxy configured: {proxy_url}")
            self.output_area.append("🔒 TOR masking active for API registration")
            
            # Verify TOR IP
            if not self.verify_tor_ip():
                self.output_area.append("⚠️  TOR IP verification failed, but proceeding...")
        else:
            self.output_area.append("🔗 Setting up direct connection (TOR not enabled)")
            # Clear any proxy environment variables
            self.clear_proxy_env_vars()
        
        # Run the setup
        self.run_crow_setup_ai()

    def clear_proxy_env_vars(self):
        """Clear proxy environment variables"""
        for var in ["HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "BLACKBIRD_USE_TOR", "TOR_PORT"]:
            if var in os.environ:
                del os.environ[var]

    def verify_tor_ip(self):
        """Verify that TOR is masking the IP address"""
        try:
            import requests
            
            # Use requests with TOR proxy if enabled
            proxies = None
            if self.crow_tor_spoofer and self.crow_tor_spoofer.tor_enabled:
                proxy_url = f"socks5://127.0.0.1:{self.crow_tor_spoofer.tor_port}"
                proxies = {
                    'http': proxy_url,
                    'https': proxy_url
                }
            
            response = requests.get("https://api.ipify.org?format=json", 
                                   proxies=proxies, 
                                   timeout=10)
            ip_data = response.json()
            
            # Get original IP for comparison
            original_response = requests.get("https://api.ipify.org?format=json", timeout=10)
            original_ip = original_response.json()['ip']
            
            tor_ip = ip_data['ip']
            
            if tor_ip != original_ip:
                self.output_area.append(f"✅ TOR IP verified: {tor_ip}")
                self.output_area.append(f"   Original IP: {original_ip}")
                return True
            else:
                self.output_area.append(f"⚠️  TOR IP same as original: {tor_ip}")
                return False
                
        except Exception as e:
            self.output_area.append(f"⚠️  Could not verify TOR IP: {e}")
            return False

    def restart_tor_service(self):
        """Attempt to restart TOR service"""
        try:
            import subprocess
            
            # Try to restart TOR service (platform specific)
            if sys.platform == "win32":
                subprocess.run(["net", "stop", "tor"], capture_output=True)
                subprocess.run(["net", "start", "tor"], capture_output=True)
            else:
                subprocess.run(["sudo", "systemctl", "restart", "tor"], capture_output=True)
            
            # Wait a moment for TOR to restart
            import time
            time.sleep(3)
            
            return True
        except Exception as e:
            self.output_area.append(f"⚠️  Could not restart TOR: {e}")
            return False

    def setup_with_proxychains(self):
        """Alternative setup using proxychains"""
        self.output_area.append("🔄 Attempting setup with proxychains...")
        
        try:
            # Try to use proxychains if available
            command = ["proxychains", "python", "blackbird.py", "--setup-ai"]
            
            self.crow_worker = CrowWorker(" ".join(command), is_setup_ai=True)
            self.crow_worker.output_signal.connect(self.update_crow_output)
            self.crow_worker.finished_signal.connect(self.on_crow_setup_finished)
            self.crow_worker.start()
            
            self.crow_run_btn.setEnabled(False)
            self.crow_stop_btn.setEnabled(True)
            
        except Exception as e:
            self.output_area.append(f"❌ Proxychains method failed: {e}")
            self.output_area.append("🔄 Falling back to direct connection...")
            self.clear_proxy_env_vars()
            self.run_crow_setup_ai()

    def delete_crow_api_key(self):
        """Delete existing API key file for fresh registration"""
        import json
        
        config_paths = [
            os.path.expanduser("~/.ai_key.json"),
            ".ai_key.json"
        ]
        
        for config_path in config_paths:
            if os.path.exists(config_path):
                try:
                    os.remove(config_path)
                    self.output_area.append(f"🗑️  Deleted existing API key: {config_path}")
                    break
                except Exception as e:
                    self.output_area.append(f"⚠️  Could not delete {config_path}: {e}")

    def setup_crow_ai_direct(self):
        """Fallback direct setup without TOR"""
        self.output_area.append("🔄 Starting direct API setup...")
        self.run_crow_setup_ai()

    def run_crow_setup_ai(self):
        """Run the blackbird setup-ai command"""
        try:
            command = ["python", "blackbird.py", "--setup-ai"]
            
            # Create and start the worker for setup
            self.crow_worker = CrowWorker(" ".join(command), is_setup_ai=True)
            self.crow_worker.output_signal.connect(self.update_crow_output)
            self.crow_worker.finished_signal.connect(self.on_crow_setup_finished)
            self.crow_worker.start()
            
            self.crow_run_btn.setEnabled(False)
            self.crow_stop_btn.setEnabled(True)
            
        except Exception as e:
            self.output_area.append(f"❌ Error starting setup: {e}")

    def on_crow_setup_finished(self):
        """Handle completion of Crow AI setup"""
        self.crow_run_btn.setEnabled(True)
        self.crow_stop_btn.setEnabled(False)
        
        # Check if setup was successful
        self.check_crow_api_key()

    def check_crow_api_key(self):
        """Check if API key was successfully configured"""
        import json
        
        api_key_found = False
        config_paths = [
            os.path.expanduser("~/.ai_key.json"),
            ".ai_key.json"
        ]
        
        for config_path in config_paths:
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r') as f:
                        config = json.load(f)
                        if config.get("ai_api_key"):
                            api_key_found = True
                            self.crow_ai_api_key = config["ai_api_key"]
                            os.environ["BLACKBIRD_AI_API_KEY"] = config["ai_api_key"]
                            self.output_area.append("✅ AI API Key configured and loaded!")
                            break
                        elif config.get("api_key"):
                            api_key_found = True
                            self.crow_ai_api_key = config["api_key"]
                            os.environ["BLACKBIRD_AI_API_KEY"] = config["api_key"]
                            self.output_area.append("✅ AI API Key configured and loaded!")
                            break
                except (json.JSONDecodeError, KeyError):
                    continue
        
        if not api_key_found:
            self.output_area.append("⚠️  API key setup completed, but couldn't automatically detect the key.")

    def configure_crow_tor_settings(self):
        """Configure TOR settings for Crow"""
        dialog = QDialog(self)
        dialog.setWindowTitle("TOR Configuration for Crow")
        layout = QVBoxLayout()
        
        form_layout = QFormLayout()
        
        # Initialize TOR spoofer if not already done
        if not self.crow_tor_spoofer:
            self.crow_tor_spoofer = TORSpoofer(self)
        
        tor_port_input = QLineEdit(str(self.crow_tor_spoofer.tor_port))
        control_port_input = QLineEdit(str(self.crow_tor_spoofer.control_port))
        
        password_info = QLabel(f"Current password: {'*' * 20} (hardcoded for testing)")
        password_info.setWordWrap(True)
        
        form_layout.addRow("TOR Port:", tor_port_input)
        form_layout.addRow("Control Port:", control_port_input)
        form_layout.addRow("Password:", password_info)
        
        help_label = QLabel("Note: Using hardcoded password for testing. Port changes will be applied.")
        help_label.setWordWrap(True)
        form_layout.addRow("", help_label)
        
        layout.addLayout(form_layout)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | 
                                 QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        dialog.setLayout(layout)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                self.crow_tor_spoofer.tor_port = int(tor_port_input.text())
                self.crow_tor_spoofer.control_port = int(control_port_input.text())
                
                # Test new configuration if TOR is enabled
                if self.crow_tor_checkbox.isChecked():
                    if not self.crow_tor_spoofer.enable_tor_for_ai():
                        QMessageBox.warning(self, "TOR Configuration Failed", 
                                          "New TOR settings are invalid.")
                        self.crow_tor_checkbox.setChecked(False)
                    else:
                        QMessageBox.information(self, "Success", "TOR configuration updated successfully!")
                            
            except ValueError:
                QMessageBox.warning(self, "Invalid Input", "Port numbers must be integers.")

    def show_crow_filter_help(self):
        """Show filter help for Crow"""
        QMessageBox.information(self, "Crow Filter Help",
                              "Create custom search filters for Crow:\n\n"
                              "Properties: name, cat, uri_check, e_code, e_string, m_string, m_code\n"
                              "Operators: =, ~, >, <, >=, <=, !=\n\n"
                              "Examples:\n"
                              "• name~twitter\n"
                              "• cat=social\n"
                              "• e_code>200 and name~facebook")

    def save_crow_settings(self):
        """Save Crow-specific settings"""
        file_name, _ = QFileDialog.getSaveFileName(self, "Save Crow Settings", "", "JSON Files (*.json)")
        if file_name:
            if not file_name.endswith('.json'):
                file_name += '.json'

            settings = {
                "crow_username_input": self.crow_username_input.text(),
                "crow_email_input": self.crow_email_input.text(),
                "crow_ai_checkbox": self.crow_ai_checkbox.isChecked(),
                "crow_tor_checkbox": self.crow_tor_checkbox.isChecked(),
                "crow_permute_checkbox": self.crow_permute_checkbox.isChecked(),
                "crow_no_nsfw_checkbox": self.crow_no_nsfw_checkbox.isChecked(),
                "crow_csv_checkbox": self.crow_csv_checkbox.isChecked(),
                "crow_verbose_checkbox": self.crow_verbose_checkbox.isChecked(),
                "crow_pdf_checkbox": self.crow_pdf_checkbox.isChecked(),
                "crow_json_checkbox": self.crow_json_checkbox.isChecked(),
                "crow_dump_checkbox": self.crow_dump_checkbox.isChecked(),
                "crow_filter_input": self.crow_filter_input.text(),
                "crow_breach_username_checkbox": self.crow_breach_username_checkbox.isChecked(),
                "crow_breach_email_checkbox": self.crow_breach_email_checkbox.isChecked(),
                "crow_ai_api_key": self.crow_ai_api_key if hasattr(self, 'crow_ai_api_key') else ''
            }

            with open(file_name, 'w') as f:
                json.dump(settings, f, indent=4)
            
            self.output_area.append(f"💾 Crow settings saved to: {file_name}")

    def load_crow_settings(self):
        """Load Crow-specific settings"""
        file_name, _ = QFileDialog.getOpenFileName(self, "Load Crow Settings", "", "JSON Files (*.json)")
        if file_name:
            try:
                with open(file_name, 'r') as f:
                    settings = json.load(f)

                self.crow_username_input.setText(settings.get("crow_username_input", ""))
                self.crow_email_input.setText(settings.get("crow_email_input", ""))
                self.crow_ai_checkbox.setChecked(settings.get("crow_ai_checkbox", False))
                self.crow_tor_checkbox.setChecked(settings.get("crow_tor_checkbox", False))
                self.crow_permute_checkbox.setChecked(settings.get("crow_permute_checkbox", False))
                self.crow_no_nsfw_checkbox.setChecked(settings.get("crow_no_nsfw_checkbox", False))
                self.crow_csv_checkbox.setChecked(settings.get("crow_csv_checkbox", False))
                self.crow_verbose_checkbox.setChecked(settings.get("crow_verbose_checkbox", False))
                self.crow_pdf_checkbox.setChecked(settings.get("crow_pdf_checkbox", False))
                self.crow_json_checkbox.setChecked(settings.get("crow_json_checkbox", False))
                self.crow_dump_checkbox.setChecked(settings.get("crow_dump_checkbox", False))
                self.crow_filter_input.setText(settings.get("crow_filter_input", ""))
                self.crow_breach_username_checkbox.setChecked(settings.get("crow_breach_username_checkbox", False))
                self.crow_breach_email_checkbox.setChecked(settings.get("crow_breach_email_checkbox", False))
                
                if settings.get("crow_ai_api_key"):
                    self.crow_ai_api_key = settings["crow_ai_api_key"]
                    os.environ["BLACKBIRD_AI_API_KEY"] = settings["crow_ai_api_key"]
                
                self.output_area.append(f"📂 Crow settings loaded from: {file_name}")
                
            except Exception as e:
                self.output_area.append(f"❌ Error loading settings: {e}")

    def run_crow_search(self):
        """Run the Crow (Blackbird) search"""
        # Clear output area
        self.output_area.clear()
        
        # Get username and email for AI analysis
        username = self.crow_username_input.text().strip()  # ADD THIS LINE
        email = self.crow_email_input.text().strip()        # ADD THIS LINE
        
        # Check if AI is enabled but no API key
        if self.crow_ai_checkbox.isChecked():
            if not self.check_crow_ai_api_key():
                return
        
        # Initialize TOR if enabled
        if self.crow_tor_checkbox.isChecked():
            if not self.crow_tor_spoofer:
                self.crow_tor_spoofer = TORSpoofer(self)
            
            # Set TOR environment variables
            proxy_url = f"socks5://127.0.0.1:{self.crow_tor_spoofer.tor_port}"
            os.environ["HTTP_PROXY"] = proxy_url
            os.environ["HTTPS_PROXY"] = proxy_url
            os.environ["ALL_PROXY"] = proxy_url
            
            # Verify TOR is working
            if not self.verify_tor_connection():
                self.output_area.append("⚠️  TOR verification failed, but proceeding...")
        
        # ================================================================
        # BREACH.VIP USERNAME SEARCH HOOK
        # ================================================================
        if self.crow_breach_username_checkbox.isChecked() and username:
            self.output_area.append("\n" + "=" * 60)
            self.output_area.append("🔍 BREACH.VIP USERNAME SEARCH HOOK")
            self.output_area.append("=" * 60)
            
            if username.startswith("file:"):
                file_path = username[5:]
                if os.path.exists(file_path):
                    self.output_area.append(f"Searching Breach.vip for usernames from file: {os.path.basename(file_path)}")
                    process_username_file(file_path, self.output_area)
                else:
                    self.output_area.append(f"❌ File not found: {file_path}")
            else:
                usernames = [u.strip() for u in username.split(',') if u.strip()]
                if len(usernames) == 1:
                    self.output_area.append(f"Searching Breach.vip for username: {usernames[0]}")
                    process_single_username(usernames[0], self.output_area)
                else:
                    self.output_area.append(f"Searching Breach.vip for {len(usernames)} usernames")
                    for username_item in usernames:
                        self.output_area.append(f"  • Processing: {username_item}")
                        process_single_username(username_item, self.output_area)
            
            self.output_area.append("=" * 60 + "\n")

        # ================================================================
        # BREACH.VIP EMAIL SEARCH HOOK
        # ================================================================
        if self.crow_breach_email_checkbox.isChecked() and email:
            self.output_area.append("\n" + "=" * 60)
            self.output_area.append("📧 BREACH.VIP EMAIL SEARCH HOOK")
            self.output_area.append("=" * 60)
            
            if email.startswith("file:"):
                file_path = email[5:]
                if os.path.exists(file_path):
                    self.output_area.append(f"Searching Breach.vip for emails from file: {os.path.basename(file_path)}")
                    process_email_file(file_path, self.output_area)
                else:
                    self.output_area.append(f"❌ File not found: {file_path}")
            else:
                emails = [e.strip() for e in email.split(',') if e.strip()]
                if len(emails) == 1:
                    self.output_area.append(f"Searching Breach.vip for email: {emails[0]}")
                    process_single_email(emails[0], self.output_area)
                else:
                    self.output_area.append(f"Searching Breach.vip for {len(emails)} emails")
                    for email_item in emails:
                        self.output_area.append(f"  • Processing: {email_item}")
                        process_single_email(email_item, self.output_area)
            
            self.output_area.append("=" * 60 + "\n")
        
        # Build Blackbird command
        try:
            command = build_blackbird_command(
                username_input=username,
                email_input=email,
                username_file_input="",
                email_file_input="",
                permute_checkbox=self.crow_permute_checkbox.isChecked(),
                permuteall_checkbox=False,
                AI_checkbox=self.crow_ai_checkbox.isChecked(),
                no_nsfw_checkbox=self.crow_no_nsfw_checkbox.isChecked(),
                no_update_checkbox=False,
                csv_checkbox=self.crow_csv_checkbox.isChecked(),
                pdf_checkbox=self.crow_pdf_checkbox.isChecked(),
                json_checkbox=self.crow_json_checkbox.isChecked(),
                verbose_checkbox=self.crow_verbose_checkbox.isChecked(),
                dump_checkbox=self.crow_dump_checkbox.isChecked(),
                proxy_input="",
                timeout_spinbox=30,
                filter_input=self.crow_filter_input.text(),
                instagram_session_id=""
            )
            
            # Show AI info if enabled
            if self.crow_ai_checkbox.isChecked():
                self.output_area.append("🤖 AI Analysis Enabled")
                self.output_area.append("Note: AI analysis will be automatically saved to text file")
                self.output_area.append("")
            
            # Create and start the worker
            self.crow_worker = CrowWorker(
                " ".join(command), 
                needs_ai_confirmation=self.crow_ai_checkbox.isChecked(),
                is_setup_ai=False,
                tor_spoofer=self.crow_tor_spoofer if self.crow_tor_checkbox.isChecked() else None,
                username=username.split('file:')[0] if username.startswith('file:') else username,
                email=email.split('file:')[0] if email.startswith('file:') else email
            )
            self.crow_worker.output_signal.connect(self.update_crow_output)
            self.crow_worker.finished_signal.connect(self.on_crow_search_finished)
            self.crow_worker.ai_file_saved.connect(self.on_ai_file_saved)
            self.crow_worker.start()
            
            self.crow_run_btn.setEnabled(False)
            self.crow_stop_btn.setEnabled(True)
            
        except Exception as e:
            self.output_area.append(f"❌ Error building command: {e}")

    def on_ai_file_saved(self, file_path):
        """Handle when AI analysis file is saved"""
        self.output_area.append(f"💾 AI results saved to: {file_path}")
        
        # Optional: Ask if user wants to open the file
        reply = QMessageBox.question(
            self,
            "AI Analysis Saved",
            f"AI analysis has been saved to:\n{file_path}\n\nWould you like to open it?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                if sys.platform == "win32":
                    os.startfile(file_path)
                elif sys.platform == "darwin":
                    subprocess.run(["open", file_path])
                else:
                    subprocess.run(["xdg-open", file_path])
            except Exception as e:
                self.output_area.append(f"⚠️ Could not open file: {e}")

    def check_crow_ai_api_key(self):
        """Check if AI API key is available for Crow"""
        import json
        
        # Check environment variable
        if os.environ.get("BLACKBIRD_AI_API_KEY"):
            return True
        
        # Check config files
        config_paths = [
            os.path.expanduser("~/.ai_key.json"),
            ".ai_key.json",
        ]
        
        for config_path in config_paths:
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r') as f:
                        config = json.load(f)
                        if config.get("ai_api_key") or config.get("api_key"):
                            return True
                except (json.JSONDecodeError, KeyError):
                    continue
        
        # Check stored API key
        if hasattr(self, 'crow_ai_api_key') and self.crow_ai_api_key:
            return True
        
        # Ask user to setup
        reply = QMessageBox.question(
            self, 
            "AI API Key Required",
            "AI analysis requires an API key. Would you like to configure it now?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.setup_crow_ai_api_key()
            return False  # Don't proceed yet
        else:
            QMessageBox.warning(self, "Warning", "AI analysis disabled - no API key configured.")
            self.crow_ai_checkbox.setChecked(False)
            return True  # Proceed without AI

    def stop_crow_search(self):
        """Stop the Crow search"""
        if self.crow_worker and self.crow_worker.isRunning():
            self.crow_worker.terminate()
            self.crow_worker.wait()
        
        self.crow_run_btn.setEnabled(True)
        self.crow_stop_btn.setEnabled(False)
        self.output_area.append("⏹️ Crow search stopped.")

    def update_crow_output(self, text):
        """Update Crow output area with text"""
        self.output_area.append(text)

    def on_crow_search_finished(self):
        """Handle completion of Crow search"""
        self.crow_run_btn.setEnabled(True)
        self.crow_stop_btn.setEnabled(False)
        self.output_area.append("✅ Crow search completed!")

    # ================================================================
    # ORIGINAL MAIGRET METHODS
    # ================================================================

    def create_save_load_actions(self, layout):
        save_load_layout = QHBoxLayout()

        self.save_button = QPushButton("Save Maigret Settings")
        self.save_button.clicked.connect(self.save_settings_dialog)
        save_load_layout.addWidget(self.save_button)

        self.load_button = QPushButton("Load Maigret Settings")
        self.load_button.clicked.connect(self.load_settings_dialog)
        save_load_layout.addWidget(self.load_button)

        layout.addLayout(save_load_layout)

    def save_settings_dialog(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Settings", "", "JSON Files (*.json)")
        
        if file_path:
            if not file_path.lower().endswith('.json'):
                file_path += '.json'
            self.save_settings(file_path)

    def save_settings(self, file_path):
        settings = {
            'username': self.username_input.text(),
            'timeout': self.timeout_spinbox.value(),
            'retries': self.retries_spinbox.value(),
            'max_connections': self.max_connections_spinbox.value(),
            'no_recursion': self.no_recursion_checkbox.isChecked(),
            'no_extracting': self.no_extracting_checkbox.isChecked(),
            'permute': self.permute_checkbox.isChecked(),
            'proxy': self.proxy_input.text(),
            'tor_proxy': self.tor_proxy_input.text(),
            'i2p_proxy': self.i2p_proxy_input.text(),
            'all_sites': self.all_sites_checkbox.isChecked(),
            'top_sites': self.top_sites_checkbox.isChecked(),
            'top_sites_count': self.top_sites_input.value(),
            'tags': self.tags_input.text(),
            'site': self.site_input.text(),
            'use_disabled_sites': self.use_disabled_sites_checkbox.isChecked(),
            'parse_url': self.parse_url_input.text(),
            'submit_url': self.submit_url_input.text(),
            'self_check': self.self_check_checkbox.isChecked(),
            'stats': self.stats_checkbox.isChecked(),
            'csv': self.csv_checkbox.isChecked(),
            'pdf': self.pdf_checkbox.isChecked(),
            'txt': self.txt_checkbox.isChecked(),
            'html': self.html_checkbox.isChecked(),
            'report_sorting': self.report_sorting_checkbox.isChecked(),
            'report_sorting_type': self.report_sorting_combobox.currentText(),
            'print_not_found': self.print_not_found_checkbox.isChecked(),
            'print_errors': self.print_errors_checkbox.isChecked(),
            'verbose': self.verbose_checkbox.isChecked(),
            'info': self.info_checkbox.isChecked(),
            'debug': self.debug_checkbox.isChecked(),
        }

        with open(file_path, 'w') as json_file:
            json.dump(settings, json_file, indent=4)

        self.output_area.append(f"Settings saved to {file_path}.")

    def load_settings_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Load Settings", "", "JSON Files (*.json)")

        if file_path:
            self.load_settings(file_path)

    def load_settings(self, file_path):
        try:
            with open(file_path, 'r') as json_file:
                settings = json.load(json_file)

            self.username_input.setText(settings.get('username', ''))
            self.timeout_spinbox.setValue(settings.get('timeout', 30))
            self.retries_spinbox.setValue(settings.get('retries', 3))
            self.max_connections_spinbox.setValue(settings.get('max_connections', 10))
            self.no_recursion_checkbox.setChecked(settings.get('no_recursion', False))
            self.no_extracting_checkbox.setChecked(settings.get('no_extracting', False))
            self.permute_checkbox.setChecked(settings.get('permute', False))
            self.proxy_input.setText(settings.get('proxy', ''))
            self.tor_proxy_input.setText(settings.get('tor_proxy', ''))
            self.i2p_proxy_input.setText(settings.get('i2p_proxy', ''))
            self.all_sites_checkbox.setChecked(settings.get('all_sites', False))
            self.top_sites_checkbox.setChecked(settings.get('top_sites', False))
            self.top_sites_input.setValue(settings.get('top_sites_count', 10))
            self.tags_input.setText(settings.get('tags', ''))
            self.site_input.setText(settings.get('site', ''))
            self.use_disabled_sites_checkbox.setChecked(settings.get('use_disabled_sites', False))
            self.parse_url_input.setText(settings.get('parse_url', ''))
            self.submit_url_input.setText(settings.get('submit_url', ''))
            self.self_check_checkbox.setChecked(settings.get('self_check', False))
            self.stats_checkbox.setChecked(settings.get('stats', False))
            self.csv_checkbox.setChecked(settings.get('csv', False))
            self.pdf_checkbox.setChecked(settings.get('pdf', False))
            self.txt_checkbox.setChecked(settings.get('txt', False))
            self.html_checkbox.setChecked(settings.get('html', False))
            self.report_sorting_checkbox.setChecked(settings.get('report_sorting', False))
            self.report_sorting_combobox.setCurrentText(settings.get('report_sorting_type', 'default'))
            self.print_not_found_checkbox.setChecked(settings.get('print_not_found', False))
            self.print_errors_checkbox.setChecked(settings.get('print_errors', False))
            self.verbose_checkbox.setChecked(settings.get('verbose', False))
            self.info_checkbox.setChecked(settings.get('info', False))
            self.debug_checkbox.setChecked(settings.get('debug', False))

            self.output_area.append(f"Settings loaded from {file_path}.")
        except FileNotFoundError:
            self.output_area.append("No settings file found.")
        except json.JSONDecodeError:
            self.output_area.append("Error decoding settings file.")

    def create_options_tab(self, tab_widget):
        options_group = QWidget()
        options_layout = QVBoxLayout()

        # Create a horizontal layout for the Username and No Recursion checkbox
        username_layout = QHBoxLayout()
        
        self.username_input = QLineEdit()
        username_layout.addWidget(QLabel("Username:"))
        username_layout.addWidget(self.username_input)

        self.no_recursion_checkbox = QCheckBox("No Recursion")
        username_layout.addWidget(self.no_recursion_checkbox)

        options_layout.addLayout(username_layout)

        # Timeout input
        timeout_layout = QHBoxLayout()
        timeout_layout.addWidget(QLabel("Timeout (seconds):"))
        self.timeout_spinbox = QSpinBox()
        self.timeout_spinbox.setRange(15, 300)
        timeout_layout.addWidget(self.timeout_spinbox)
        options_layout.addLayout(timeout_layout)

        # Retries input
        retries_layout = QHBoxLayout()
        retries_layout.addWidget(QLabel("Retries:"))
        self.retries_spinbox = QSpinBox()
        self.retries_spinbox.setRange(0, 10)
        self.retries_spinbox.setValue(0)
        retries_layout.addWidget(self.retries_spinbox)
        options_layout.addLayout(retries_layout)

        # Max connections input
        max_connections_layout = QHBoxLayout()
        max_connections_layout.addWidget(QLabel("Max Connections:"))
        self.max_connections_spinbox = QSpinBox()
        self.max_connections_spinbox.setRange(1, 50)
        self.max_connections_spinbox.setValue(10)
        max_connections_layout.addWidget(self.max_connections_spinbox)
        options_layout.addLayout(max_connections_layout)

        # Create a horizontal layout for the checkboxes: No Extracting, Permute, All Sites
        checkbox_layout_1 = QHBoxLayout()

        self.no_extracting_checkbox = QCheckBox("No Extracting")
        checkbox_layout_1.addWidget(self.no_extracting_checkbox)

        self.permute_checkbox = QCheckBox("Permute")
        checkbox_layout_1.addWidget(self.permute_checkbox)

        self.all_sites_checkbox = QCheckBox("All Sites")
        checkbox_layout_1.addWidget(self.all_sites_checkbox)

        options_layout.addLayout(checkbox_layout_1)

        # Create a horizontal layout for the checkboxes: Self Check, Stats, Report Sorting
        checkbox_layout_2 = QHBoxLayout()

        self.self_check_checkbox = QCheckBox("Self Check")
        checkbox_layout_2.addWidget(self.self_check_checkbox)

        self.stats_checkbox = QCheckBox("Stats")
        checkbox_layout_2.addWidget(self.stats_checkbox)

        self.report_sorting_checkbox = QCheckBox("Enable Report Sorting")
        checkbox_layout_2.addWidget(self.report_sorting_checkbox)

        options_layout.addLayout(checkbox_layout_2)

        # Report Sorting input
        self.report_sorting_combobox = QComboBox()
        self.report_sorting_combobox.addItems(["default", "data"])
        self.report_sorting_combobox.setEnabled(False)
        options_layout.addWidget(QLabel("Report Sort:"))
        options_layout.addWidget(self.report_sorting_combobox)

        self.report_sorting_checkbox.toggled.connect(self.toggle_report_sorting_input)

        # Add Top Sites checkbox
        self.top_sites_checkbox = QCheckBox("Enable Top Sites")
        options_layout.addWidget(self.top_sites_checkbox)

        # Top sites input
        self.top_sites_input = QSpinBox()
        self.top_sites_input.setRange(1, 100)
        self.top_sites_input.setValue(10)
        self.top_sites_input.setEnabled(False)
        options_layout.addWidget(QLabel("Top Sites Count:"))
        options_layout.addWidget(self.top_sites_input)

        self.top_sites_checkbox.toggled.connect(self.toggle_top_sites_input)

        # Create a horizontal layout for Tags and Proxy inputs
        proxy_layout_horizontal = QHBoxLayout()

        # Tags input
        tags_widget = QWidget()
        tags_sub_layout = QVBoxLayout()
        tags_sub_layout.addWidget(QLabel("Tags (comma-separated):"))
        self.tags_input = QLineEdit()
        tags_sub_layout.addWidget(self.tags_input)
        tags_widget.setLayout(tags_sub_layout)
        proxy_layout_horizontal.addWidget(tags_widget)

        # Proxy URL input
        proxy_widget = QWidget()
        proxy_sub_layout = QVBoxLayout()
        proxy_sub_layout.addWidget(QLabel("Proxy URL:"))
        self.proxy_input = QLineEdit()
        self.proxy_input.setPlaceholderText("e.g., socks5://127.0.0.1:1080")
        proxy_sub_layout.addWidget(self.proxy_input)
        proxy_widget.setLayout(proxy_sub_layout)
        proxy_layout_horizontal.addWidget(proxy_widget)

        # Tor Proxy input
        tor_proxy_widget = QWidget()
        tor_proxy_sub_layout = QVBoxLayout()
        tor_proxy_sub_layout.addWidget(QLabel("Tor Proxy URL:"))
        self.tor_proxy_input = QLineEdit()
        tor_proxy_sub_layout.addWidget(self.tor_proxy_input)
        tor_proxy_widget.setLayout(tor_proxy_sub_layout)
        proxy_layout_horizontal.addWidget(tor_proxy_widget)

        # I2P Proxy input
        i2p_proxy_widget = QWidget()
        i2p_proxy_sub_layout = QVBoxLayout()
        i2p_proxy_sub_layout.addWidget(QLabel("I2P Proxy URL:"))
        self.i2p_proxy_input = QLineEdit()
        i2p_proxy_sub_layout.addWidget(self.i2p_proxy_input)
        i2p_proxy_widget.setLayout(i2p_proxy_sub_layout)
        proxy_layout_horizontal.addWidget(i2p_proxy_widget)

        options_layout.addLayout(proxy_layout_horizontal)

        # Site input
        self.site_input = QLineEdit()
        options_layout.addWidget(QLabel("Site URL:"))
        options_layout.addWidget(self.site_input)

        # Disabled sites checkbox
        self.use_disabled_sites_checkbox = QCheckBox("Use Disabled Sites")
        options_layout.addWidget(self.use_disabled_sites_checkbox)

        # Parse URL input
        self.parse_url_input = QLineEdit()
        options_layout.addWidget(QLabel("Parse URL:"))
        options_layout.addWidget(self.parse_url_input)

        # Submit URL input
        self.submit_url_input = QLineEdit()
        options_layout.addWidget(QLabel("Submit URL:"))
        options_layout.addWidget(self.submit_url_input)

        # Create a horizontal layout for the new checkboxes
        additional_checkbox_layout = QHBoxLayout()

        self.print_not_found_checkbox = QCheckBox("Print Sites Not Found")
        additional_checkbox_layout.addWidget(self.print_not_found_checkbox)

        self.print_errors_checkbox = QCheckBox("Print Errors")
        additional_checkbox_layout.addWidget(self.print_errors_checkbox)

        self.verbose_checkbox = QCheckBox("Verbose (-v)")
        additional_checkbox_layout.addWidget(self.verbose_checkbox)

        self.info_checkbox = QCheckBox("Info (-vv)")
        additional_checkbox_layout.addWidget(self.info_checkbox)

        self.debug_checkbox = QCheckBox("Debug (-vvv, -d)")
        additional_checkbox_layout.addWidget(self.debug_checkbox)

        # Also add the output format checkboxes to the SAME horizontal layout
        self.csv_checkbox = QCheckBox("CSV")
        additional_checkbox_layout.addWidget(self.csv_checkbox)

        self.pdf_checkbox = QCheckBox("PDF")
        additional_checkbox_layout.addWidget(self.pdf_checkbox)

        self.txt_checkbox = QCheckBox("TXT")
        additional_checkbox_layout.addWidget(self.txt_checkbox)

        self.G_checkbox = QCheckBox("G")
        additional_checkbox_layout.addWidget(self.G_checkbox)

        self.html_checkbox = QCheckBox("HTML")
        additional_checkbox_layout.addWidget(self.html_checkbox)

        options_layout.addLayout(additional_checkbox_layout)

        options_group.setLayout(options_layout)
        tab_widget.addTab(options_group, "Options")

    def toggle_top_sites_input(self):
        self.top_sites_input.setEnabled(self.top_sites_checkbox.isChecked())

    def toggle_report_sorting_input(self):
        self.report_sorting_combobox.setEnabled(self.report_sorting_checkbox.isChecked())

    def create_crow_tab(self, tab_widget):
        crow_group = QWidget()
        crow_layout = QVBoxLayout()

        # ================================================================
        # CROW (Blackbird Integration) Section
        # ================================================================

        # Header label
        crow_header = QLabel("🦅 CROW - Blackbird OSINT Integration")
        crow_header.setStyleSheet("font-weight: bold; font-size: 14px; margin: 10px;")
        crow_layout.addWidget(crow_header)
        crow_layout.addSpacing(10)

        # Input section
        input_group = QGroupBox("Search Parameters")
        input_layout = QVBoxLayout()

        # Username input
        username_layout = QHBoxLayout()
        username_layout.addWidget(QLabel("Username(s):"))
        self.crow_username_input = QLineEdit()
        self.crow_username_input.setPlaceholderText("Enter username(s) or 'file:path/to/file.txt'")
        username_layout.addWidget(self.crow_username_input)

        # Username file button
        username_file_btn = QPushButton("📁")
        username_file_btn.setToolTip("Select username file")
        username_file_btn.clicked.connect(self.select_crow_username_file)
        username_file_btn.setFixedWidth(40)
        username_layout.addWidget(username_file_btn)
        self.crow_breach_username_checkbox = QCheckBox("Search usernames on Breach.vip")
        username_layout.addWidget(self.crow_breach_username_checkbox)


        input_layout.addLayout(username_layout)

        # Email input
        email_layout = QHBoxLayout()
        email_layout.addWidget(QLabel("Email(s):"))
        self.crow_email_input = QLineEdit()
        self.crow_email_input.setPlaceholderText("Enter email(s) or 'file:path/to/file.txt'")
        email_layout.addWidget(self.crow_email_input)

        # Email file button
        email_file_btn = QPushButton("📁")
        email_file_btn.setToolTip("Select email file")
        email_file_btn.clicked.connect(self.select_crow_email_file)
        email_file_btn.setFixedWidth(40)
        email_layout.addWidget(email_file_btn)
        self.crow_breach_email_checkbox = QCheckBox("Search emails on Breach.vip")
        email_layout.addWidget(self.crow_breach_email_checkbox)

        input_layout.addLayout(email_layout)

        input_group.setLayout(input_layout)
        crow_layout.addWidget(input_group)

        crow_layout.addSpacing(10)

        # Options section
        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout()

        # AI Analysis
        ai_layout = QHBoxLayout()
        self.crow_ai_checkbox = QCheckBox("AI Metadata Extraction")
        ai_layout.addWidget(self.crow_ai_checkbox)

        # AI Setup button
        self.crow_ai_setup_btn = QPushButton("Setup AI Key")
        self.crow_ai_setup_btn.clicked.connect(self.setup_crow_ai_api_key)
        ai_layout.addWidget(self.crow_ai_setup_btn)

        options_layout.addLayout(ai_layout)

        # TOR Spoofing
        tor_layout = QHBoxLayout()
        self.crow_tor_checkbox = QCheckBox("Use TOR for AI requests")
        tor_layout.addWidget(self.crow_tor_checkbox)

        # TOR Settings button
        self.crow_tor_settings_btn = QPushButton("TOR Settings")
        self.crow_tor_settings_btn.clicked.connect(self.configure_crow_tor_settings)
        tor_layout.addWidget(self.crow_tor_settings_btn)

        options_layout.addLayout(tor_layout)

        # Additional options in a grid
        options_grid = QHBoxLayout()

        # Left column
        left_col = QVBoxLayout()
        self.crow_permute_checkbox = QCheckBox("Permute username")
        left_col.addWidget(self.crow_permute_checkbox)

        self.crow_no_nsfw_checkbox = QCheckBox("Exclude NSFW sites")
        left_col.addWidget(self.crow_no_nsfw_checkbox)

        # Right column
        right_col = QVBoxLayout()
        self.crow_verbose_checkbox = QCheckBox("Verbose logging")
        right_col.addWidget(self.crow_verbose_checkbox)

        options_grid.addLayout(left_col)
        options_grid.addSpacing(20)
        options_grid.addLayout(right_col)

        options_layout.addLayout(options_grid)

        # Filter input
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filter:"))
        self.crow_filter_input = QLineEdit()
        self.crow_filter_input.setPlaceholderText("e.g., name~twitter or cat=social")
        filter_layout.addWidget(self.crow_filter_input)

        # Filter help button
        filter_help_btn = QPushButton("?")
        filter_help_btn.setFixedSize(30, 30)
        filter_help_btn.clicked.connect(self.show_crow_filter_help)
        filter_layout.addWidget(filter_help_btn)

        options_layout.addLayout(filter_layout)

        options_group.setLayout(options_layout)
        crow_layout.addWidget(options_group)

        crow_layout.addSpacing(10)

        # Output options
        output_group = QGroupBox("Output Options")
        output_layout = QHBoxLayout()


        self.crow_csv_checkbox = QCheckBox("CSV output")
        self.crow_pdf_checkbox = QCheckBox("PDF")
        self.crow_json_checkbox = QCheckBox("JSON")
        self.crow_dump_checkbox = QCheckBox("Dump HTML")

        output_layout.addWidget(self.crow_csv_checkbox)
        output_layout.addWidget(self.crow_pdf_checkbox)
        output_layout.addWidget(self.crow_json_checkbox)
        output_layout.addWidget(self.crow_dump_checkbox)

        output_group.setLayout(output_layout)
        crow_layout.addWidget(output_group)

        crow_layout.addSpacing(10)

        # Breach.vip integration
        # breach_group = QGroupBox("Breach.vip Integration")
        # breach_layout = QVBoxLayout()

        # breach_note = QLabel("Search for breached data associated with targets:")
        # breach_note.setStyleSheet("color: #666; margin-bottom: 10px;")
        # breach_layout.addWidget(breach_note)

        # breach_check_layout = QHBoxLayout()
        # self.crow_breach_username_checkbox = QCheckBox("Search usernames on Breach.vip")
        # breach_check_layout.addWidget(self.crow_breach_username_checkbox)

        # self.crow_breach_email_checkbox = QCheckBox("Search emails on Breach.vip")
        # breach_check_layout.addWidget(self.crow_breach_email_checkbox)

        # breach_layout.addLayout(breach_check_layout)
        # breach_group.setLayout(breach_layout)
        # crow_layout.addWidget(breach_group)

        crow_layout.addSpacing(10)

        # Action buttons
        button_layout = QHBoxLayout()

        # Save/Load buttons
        self.crow_save_btn = QPushButton("💾 Save")
        self.crow_save_btn.clicked.connect(self.save_crow_settings)
        button_layout.addWidget(self.crow_save_btn)

        self.crow_load_btn = QPushButton("📂 Load")
        self.crow_load_btn.clicked.connect(self.load_crow_settings)
        button_layout.addWidget(self.crow_load_btn)

        button_layout.addStretch()

        # Run/Stop buttons
        self.crow_run_btn = QPushButton("▶ Run Crow")
        self.crow_run_btn.clicked.connect(self.run_crow_search)
        self.crow_run_btn.setStyleSheet("font-weight: bold; background-color: #4CAF50; color: white;")
        button_layout.addWidget(self.crow_run_btn)

        self.crow_stop_btn = QPushButton("⏹ Stop")
        self.crow_stop_btn.clicked.connect(self.stop_crow_search)
        self.crow_stop_btn.setEnabled(False)
        self.crow_stop_btn.setStyleSheet("background-color: #f44336; color: white;")
        button_layout.addWidget(self.crow_stop_btn)

        crow_layout.addLayout(button_layout)

        crow_layout.addSpacing(10)

        # Output area specific for Crow
        # output_label = QLabel("Crow Output:")
        # output_label.setStyleSheet("font-weight: bold;")
        # crow_layout.addWidget(output_label)

        # self.output_area = QTextEdit()
        # self.output_area.setReadOnly(True)
        # crow_layout.addWidget(self.output_area)

        # Add stretch to push everything up
        crow_layout.addStretch()

        crow_group.setLayout(crow_layout)
        tab_widget.addTab(crow_group, "🦅 Crow")

    def create_buttons(self, layout):
        button_layout = QHBoxLayout()
        self.run_button = QPushButton("Run Maigret")
        self.run_button.clicked.connect(self.run_maigret)
        button_layout.addWidget(self.run_button)

        self.stop_button = QPushButton("Stop Maigret")
        self.stop_button.clicked.connect(self.stop_maigret)
        self.stop_button.setEnabled(False)
        button_layout.addWidget(self.stop_button)

        layout.addLayout(button_layout)

        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        layout.addWidget(self.output_area)

    def run_maigret(self):
        self.output_area.clear()

        command = f"maigret {self.username_input.text()}"

        command += f" --timeout {self.timeout_spinbox.value()}"
        command += f" --retries {self.retries_spinbox.value()}"
        command += f" --max-connections {self.max_connections_spinbox.value()}"
        if self.no_recursion_checkbox.isChecked():
            command += " --no-recursion"
        if self.no_extracting_checkbox.isChecked():
            command += " --no-extracting"
        if self.permute_checkbox.isChecked():
            command += " --permute"
        if self.proxy_input.text():
            command += f" --proxy {self.proxy_input.text()}"
        if self.tor_proxy_input.text():
            command += f" --tor-proxy {self.tor_proxy_input.text()}"
        if self.i2p_proxy_input.text():
            command += f" --i2p-proxy {self.i2p_proxy_input.text()}"
        if self.all_sites_checkbox.isChecked():
            command += " --all-sites"
        if self.top_sites_checkbox.isChecked():
            command += f" --top-sites {self.top_sites_input.value()}"
        if self.tags_input.text():
            command += f" --tags {self.tags_input.text()}"
        if self.site_input.text():
            command += f" --site {self.site_input.text()}"
        if self.use_disabled_sites_checkbox.isChecked():
            command += " --use-disabled-sites"
        
        if self.parse_url_input.text():
            command += f" --parse {self.parse_url_input.text()}"
        if self.submit_url_input.text():
            command += f" --submit {self.submit_url_input.text()}"
        if self.self_check_checkbox.isChecked():
            command += " --self-check"
        if self.stats_checkbox.isChecked():
            command += " --stats"
        
        if self.csv_checkbox.isChecked():
            command += " --csv"
        if self.pdf_checkbox.isChecked():
            command += " --pdf"
        if self.txt_checkbox.isChecked():
            command += " --txt"
        if self.G_checkbox.isChecked():
            command += " --graph"
        if self.html_checkbox.isChecked():
            command += " --html"
        
        if self.report_sorting_checkbox.isChecked():
            command += f" --reports-sorting {self.report_sorting_combobox.currentText()}"

        if self.print_not_found_checkbox.isChecked():
            command += " --print-not-found"
        if self.print_errors_checkbox.isChecked():
            command += " --print-errors"
        if self.verbose_checkbox.isChecked():
            command += " --verbose"
        if self.info_checkbox.isChecked():
            command += " --info"
        if self.debug_checkbox.isChecked():
            command += " --debug"
        
        self.output_area.append(f"Running command: {command}")

        self.maigret_worker = MaigretWorker(command)
        self.maigret_worker.output_signal.connect(self.append_output)
        self.maigret_worker.finished_signal.connect(self.on_maigret_finished)
        self.maigret_worker.start()

        self.run_button.setEnabled(False)
        self.stop_button.setEnabled(True)

    def on_maigret_finished(self):
        self.stop_button.setEnabled(False)
        self.run_button.setEnabled(True)

    def stop_maigret(self):
        if self.maigret_worker:
            self.maigret_worker.terminate()
            self.maigret_worker = None
            self.output_area.append("Maigret process terminated.")

        self.run_button.setEnabled(True)
        self.stop_button.setEnabled(False)

    def append_output(self, text):
        self.output_area.append(text)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MaigretGUI()
    window.show()
    sys.exit(app.exec())