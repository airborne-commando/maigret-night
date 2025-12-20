# crow_tabs.py - Updated with relative imports
from .workers import CrowWorker
from .tor_spoofing import TORSpoofer
from .command_builder import build_blackbird_command
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit, 
                            QLabel, QDialogButtonBox, QMessageBox, QFileDialog)
import json
import os
import sys
import subprocess

class CrowTabMethods:
    """Mixin class containing all Crow tab methods"""
    
    def __init__(self):
        # Initialize Crow-specific attributes
        self.crow_worker = None
        self.crow_tor_spoofer = None
        self.crow_ai_api_key = None
    
    # Note: The breach functions (process_single_email, process_single_username, etc.)
    # will be passed in from the main file, so we don't need to import them here

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
                "crow_permuteall_checkbox": self.crow_permuteall_checkbox.isChecked(),  # ADDED
                "crow_no_update_checkbox": self.crow_no_update_checkbox.isChecked(),    # ADDED
                "crow_max_concurrent_spinbox": self.crow_max_concurrent_spinbox.value(),  # ADDED
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
                self.crow_permuteall_checkbox.setChecked(settings.get("crow_permuteall_checkbox", False))  # ADDED
                self.crow_no_update_checkbox.setChecked(settings.get("crow_no_update_checkbox", False))    # ADDED
                self.crow_max_concurrent_spinbox.setValue(settings.get("crow_max_concurrent_spinbox", 30))  # ADDED
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

    # This method needs to be updated in the main file, not here
    # The breach functions will be called from the main file

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