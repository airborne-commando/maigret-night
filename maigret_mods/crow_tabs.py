# crow_tabs.py - Updated with relative imports and proper Qt imports
from .workers import CrowWorker
from .tor_spoofing import TORSpoofer
from .command_builder import build_blackbird_command
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit, 
                            QLabel, QDialogButtonBox, QMessageBox, QFileDialog,
                            QWidget, QCheckBox, QHBoxLayout, QPushButton)  # Added missing imports
from PyQt6.QtCore import Qt
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
        self.crow_interactive_filter_widgets = []  # Initialize the list
    
    # Note: The breach functions (process_single_email, process_single_username, etc.)
    # will be passed in from the main file, so we don't need to import them here

    # ================================================================
    # CROW TAB METHODS
    # ================================================================


    def preview_filter_parsing(self):
        """Preview how filters will be parsed (shows what gets included/excluded)"""
        from filter_parser import parse_filters_from_string, validate_filters
        
        # Get all filter texts
        all_filter_texts = []
        for widget in self.crow_interactive_filter_widgets:
            if widget.checkbox.isChecked():
                filter_text = widget.input.text().strip()
                if filter_text:
                    all_filter_texts.append(filter_text)
        
        if not all_filter_texts:
            QMessageBox.information(self, "No Filters", "No active filters to preview.")
            return
        
        # Parse and validate
        preview_dialog = QDialog(self)
        preview_dialog.setWindowTitle("Filter Parser Preview")
        preview_dialog.setMinimumWidth(600)
        
        layout = QVBoxLayout()
        
        # Results text area
        results_text = QTextEdit()
        results_text.setReadOnly(True)
        results_text.setFont(QFont("Courier", 10))
        
        # Process each filter
        total_included = 0
        total_excluded = 0
        
        for i, filter_item in enumerate(all_filter_texts, 1):
            results_text.append(f"\n{'='*60}")
            results_text.append(f"Filter {i}: {filter_item}")
            results_text.append(f"{'='*60}")
            
            try:
                if filter_item.startswith("file:"):
                    file_path = filter_item[5:]
                    if os.path.exists(file_path):
                        with open(file_path, 'r') as f:
                            content = f.read()
                        parsed = parse_filters_from_string(content)
                    else:
                        results_text.append(f"❌ File not found: {file_path}")
                        continue
                else:
                    parsed = parse_filters_from_string(filter_item)
                
                valid, invalid = validate_filters(parsed)
                
                results_text.append(f"📊 Results:")
                results_text.append(f"  ✅ Included: {len(valid)} filter(s)")
                results_text.append(f"  ❌ Excluded: {len(invalid)} filter(s)")
                
                if valid:
                    results_text.append("\n  Active filters:")
                    for j, filt in enumerate(valid, 1):
                        results_text.append(f"    {j}. {filt}")
                
                if invalid:
                    results_text.append("\n  Excluded (invalid/comment):")
                    for j, filt in enumerate(invalid, 1):
                        results_text.append(f"    {j}. {filt}")
                
                total_included += len(valid)
                total_excluded += len(invalid)
                
            except Exception as e:
                results_text.append(f"❌ Error parsing: {e}")
        
        # Summary
        results_text.append(f"\n{'='*60}")
        results_text.append(f"📈 SUMMARY")
        results_text.append(f"  Total active filters: {total_included}")
        results_text.append(f"  Total excluded filters: {total_excluded}")
        
        if total_included > 0:
            from command_builder import combine_filters
            combined_filters = []
            for filter_item in all_filter_texts:
                parsed = parse_filters_from_string(filter_item)
                valid, _ = validate_filters(parsed)
                combined_filters.extend(valid)
            
            combined = combine_filters(combined_filters)
            results_text.append(f"\n  Final combined filter:")
            results_text.append(f"  \"{combined}\"")
        
        layout.addWidget(results_text)
        
        # Close button
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        btn_box.rejected.connect(preview_dialog.reject)
        layout.addWidget(btn_box)
        
        preview_dialog.setLayout(layout)
        preview_dialog.exec()


    def _create_interactive_filter_widget(self, filter_text="", enabled=False):
        """Create a single interactive filter widget"""
        filter_widget = QWidget()
        filter_layout = QHBoxLayout()
        filter_layout.setContentsMargins(0, 0, 0, 0)
        
        # Checkbox to enable/disable this filter
        filter_checkbox = QCheckBox()
        filter_checkbox.setChecked(enabled)
        filter_checkbox.setToolTip("Check to include this filter in the search")
        filter_layout.addWidget(filter_checkbox)
        
        # Filter input field
        filter_input = QLineEdit()
        filter_input.setPlaceholderText("e.g., name~twitter, cat=social, or file:path/to/filters.txt")
        filter_input.setText(filter_text)
        filter_input.setToolTip("Enter filter expression or file path")
        filter_layout.addWidget(filter_input)
        
        # File button for this filter
        filter_file_btn = QPushButton("📁")
        filter_file_btn.setToolTip("Select filter file for this filter")
        filter_file_btn.setFixedWidth(40)
        filter_file_btn.clicked.connect(lambda: self._select_filter_file_for_widget(filter_input))
        filter_layout.addWidget(filter_file_btn)
        
        # Remove button for this specific filter
        remove_btn = QPushButton("✖")
        remove_btn.setToolTip("Remove this filter")
        remove_btn.setFixedSize(30, 30)
        remove_btn.clicked.connect(lambda: self._remove_specific_filter_widget(filter_widget))
        filter_layout.addWidget(remove_btn)
        
        filter_widget.setLayout(filter_layout)
        
        # Store references
        filter_widget.checkbox = filter_checkbox
        filter_widget.input = filter_input
        filter_widget.file_btn = filter_file_btn
        filter_widget.remove_btn = remove_btn
        
        self.crow_interactive_filter_widgets.append(filter_widget)
        self.crow_interactive_filters_layout.addWidget(filter_widget)
        
        return filter_widget

    def _select_filter_file_for_widget(self, filter_input):
        """Select filter file for a specific filter widget"""
        file_name, _ = QFileDialog.getOpenFileName(
            self, 
            "Select Filter File", 
            "", 
            "Text Files (*.txt);;JSON Files (*.json);;All Files (*)"
        )
        if file_name:
            if self.validate_filter_file(file_name):
                filter_input.setText(f"file:{file_name}")

    def _remove_specific_filter_widget(self, widget):
        """Remove a specific filter widget"""
        if widget in self.crow_interactive_filter_widgets:
            self.crow_interactive_filter_widgets.remove(widget)
            widget.setParent(None)
            widget.deleteLater()
            
            # Update UI if no filters left
            if not self.crow_interactive_filter_widgets:
                self._create_interactive_filter_widget()

    def add_interactive_filter(self):
        """Add a new interactive filter widget"""
        self._create_interactive_filter_widget()

    def remove_last_interactive_filter(self):
        """Remove the last interactive filter widget"""
        if self.crow_interactive_filter_widgets:
            last_widget = self.crow_interactive_filter_widgets[-1]
            self._remove_specific_filter_widget(last_widget)

    def clear_interactive_filters(self):
        """Clear all interactive filters"""
        # Remove all widgets
        for widget in self.crow_interactive_filter_widgets[:]:
            self._remove_specific_filter_widget(widget)
        
        # Add one empty filter widget back
        self._create_interactive_filter_widget()

    def get_interactive_filters(self):
        """Get all enabled interactive filters as a list"""
        filters = []
        for widget in self.crow_interactive_filter_widgets:
            if widget.checkbox.isChecked():
                filter_text = widget.input.text().strip()
                if filter_text:
                    filters.append(filter_text)
        return filters

    def combine_interactive_filters(self):
        """Combine all enabled interactive filters into a single filter string"""
        filters = self.get_interactive_filters()
        if not filters:
            return ""
        
        # Combine filters with "and"
        combined = " and ".join(filters)
        return combined

    # In crow_tabs.py, update the validate_interactive_filters method:
    def validate_interactive_filters(self):
        """Validate all interactive filters and return any errors"""
        errors = []
        enabled_count = 0
        
        for i, widget in enumerate(self.crow_interactive_filter_widgets):
            if widget.checkbox.isChecked():
                filter_text = widget.input.text().strip()
                if not filter_text:
                    errors.append(f"Filter #{i+1} is enabled but empty")
                else:
                    # Check if it's a file and validate it
                    if filter_text.startswith("file:"):
                        file_path = filter_text[5:]
                        if not os.path.exists(file_path):
                            errors.append(f"Filter #{i+1}: File not found: {file_path}")
                enabled_count += 1
        
        # REMOVED: No longer require at least one filter
        # Filters are optional
        
        return errors, enabled_count

    def validate_filter_file(self, file_path):
        """Validate filter file format"""
        try:
            with open(file_path, 'r') as f:
                content = f.read().strip()
                
            if not content:
                self.output_area.append("⚠️ Filter file is empty")
                return False
            
            lines = [line.strip() for line in content.split('\n') if line.strip()]
            self.output_area.append(f"✅ Loaded {len(lines)} filter(s) from file")
            
            # Show preview of filters
            for i, line in enumerate(lines[:3]):  # Show first 3 filters as preview
                self.output_area.append(f"   Filter {i+1}: {line}")
            if len(lines) > 3:
                self.output_area.append(f"   ... and {len(lines)-3} more filter(s)")
            
            return True
            
        except FileNotFoundError:
            self.output_area.append(f"❌ Filter file not found: {file_path}")
            return False
        except Exception as e:
            self.output_area.append(f"❌ Error reading filter file: {e}")
            return False

    # Update the save_crow_settings method to save interactive filters:
    def save_crow_settings(self):
        """Save Crow-specific settings including interactive filters"""
        file_name, _ = QFileDialog.getSaveFileName(self, "Save Crow Settings", "", "JSON Files (*.json)")
        if file_name:
            if not file_name.endswith('.json'):
                file_name += '.json'

            # Save interactive filters
            interactive_filters_data = []
            for widget in self.crow_interactive_filter_widgets:
                interactive_filters_data.append({
                    "text": widget.input.text(),
                    "enabled": widget.checkbox.isChecked()
                })

            settings = {
                "crow_username_input": self.crow_username_input.text(),
                "crow_email_input": self.crow_email_input.text(),
                "crow_ai_checkbox": self.crow_ai_checkbox.isChecked(),
                "crow_tor_checkbox": self.crow_tor_checkbox.isChecked(),
                "crow_permuteall_checkbox": self.crow_permuteall_checkbox.isChecked(),
                "crow_no_update_checkbox": self.crow_no_update_checkbox.isChecked(),
                "crow_max_concurrent_spinbox": self.crow_max_concurrent_spinbox.value(),
                "crow_permute_checkbox": self.crow_permute_checkbox.isChecked(),
                "crow_no_nsfw_checkbox": self.crow_no_nsfw_checkbox.isChecked(),
                "crow_csv_checkbox": self.crow_csv_checkbox.isChecked(),
                "crow_verbose_checkbox": self.crow_verbose_checkbox.isChecked(),
                "crow_pdf_checkbox": self.crow_pdf_checkbox.isChecked(),
                "crow_json_checkbox": self.crow_json_checkbox.isChecked(),
                "crow_dump_checkbox": self.crow_dump_checkbox.isChecked(),
                "crow_breach_username_checkbox": self.crow_breach_username_checkbox.isChecked(),
                "crow_breach_email_checkbox": self.crow_breach_email_checkbox.isChecked(),
                "crow_interactive_filters": interactive_filters_data,
                "crow_ai_api_key": self.crow_ai_api_key if hasattr(self, 'crow_ai_api_key') else ''
            }

            with open(file_name, 'w') as f:
                json.dump(settings, f, indent=4)
            
            self.output_area.append(f"💾 Crow settings saved to: {file_name}")

    # Update the load_crow_settings method to load interactive filters:
    def load_crow_settings(self):
        """Load Crow-specific settings including interactive filters"""
        file_name, _ = QFileDialog.getOpenFileName(self, "Load Crow Settings", "", "JSON Files (*.json)")
        if file_name:
            try:
                with open(file_name, 'r') as f:
                    settings = json.load(f)

                # Load basic settings
                self.crow_username_input.setText(settings.get("crow_username_input", ""))
                self.crow_email_input.setText(settings.get("crow_email_input", ""))
                self.crow_ai_checkbox.setChecked(settings.get("crow_ai_checkbox", False))
                self.crow_tor_checkbox.setChecked(settings.get("crow_tor_checkbox", False))
                self.crow_permute_checkbox.setChecked(settings.get("crow_permute_checkbox", False))
                self.crow_no_nsfw_checkbox.setChecked(settings.get("crow_no_nsfw_checkbox", False))
                self.crow_csv_checkbox.setChecked(settings.get("crow_csv_checkbox", False))
                self.crow_verbose_checkbox.setChecked(settings.get("crow_verbose_checkbox", False))
                self.crow_pdf_checkbox.setChecked(settings.get("crow_pdf_checkbox", False))
                self.crow_permuteall_checkbox.setChecked(settings.get("crow_permuteall_checkbox", False))
                self.crow_no_update_checkbox.setChecked(settings.get("crow_no_update_checkbox", False))
                self.crow_max_concurrent_spinbox.setValue(settings.get("crow_max_concurrent_spinbox", 30))
                self.crow_json_checkbox.setChecked(settings.get("crow_json_checkbox", False))
                self.crow_dump_checkbox.setChecked(settings.get("crow_dump_checkbox", False))
                self.crow_breach_username_checkbox.setChecked(settings.get("crow_breach_username_checkbox", False))
                self.crow_breach_email_checkbox.setChecked(settings.get("crow_breach_email_checkbox", False))
                
                if settings.get("crow_ai_api_key"):
                    self.crow_ai_api_key = settings["crow_ai_api_key"]
                    os.environ["BLACKBIRD_AI_API_KEY"] = settings["crow_ai_api_key"]
                
                # Clear existing interactive filters
                for widget in self.crow_interactive_filter_widgets[:]:
                    self._remove_specific_filter_widget(widget)
                
                # Load interactive filters
                interactive_filters = settings.get("crow_interactive_filters", [])
                for filter_data in interactive_filters:
                    self._create_interactive_filter_widget(
                        filter_text=filter_data.get("text", ""),
                        enabled=filter_data.get("enabled", True)
                    )
                
                self.output_area.append(f"📂 Crow settings loaded from: {file_name}")
                self.output_area.append(f"📋 Loaded {len(interactive_filters)} interactive filter(s)")
                
            except Exception as e:
                self.output_area.append(f"❌ Error loading settings: {e}")

    def show_crow_filter_help(self):
        """Show filter help for Crow with interactive filter instructions"""
        help_text = """
        FILTER HELP - CROW SEARCH FILTERS
        ==================================
        
        FILTER SYNTAX:
        --------------
        Properties: name, cat, uri_check, e_code, e_string, m_string, m_code
        Operators: =, ~, >, <, >=, <=, !=
        
        Examples:
        • name~twitter
        • cat=social
        • e_code>200 and name~facebook
        • cat!=adult
        
        FILE FILTERS:
        -------------
        Use 'file:/path/to/filters.txt' to load filters from a file
        File format: One filter per line
        Multiple filters on same line: Separate with 'and'
        
        INTERACTIVE FILTERS:
        --------------------
        1. Check/uncheck each filter's checkbox to enable/disable it
        2. Click "➕ Add Filter" to add more filter inputs
        3. Use 📁 button on each filter to load from file
        4. Use ✖ button to remove specific filters
        
        FILTER COMBINATION:
        -------------------
        • When multiple filters are enabled, they are combined with "and"
        • Example: Filter1: name~twitter, Filter2: cat=social
          Result: name~twitter and cat=social
        
        OPTIONAL FILTERS:
        -----------------
        • Filters are completely optional - you can run searches without any filters
        • Leave all filters unchecked to search without filtering
        • Empty filters (enabled but no text) will cause an error
        
        TIPS:
        -----
        • Leave filters unchecked to temporarily disable them
        • Use file filters for complex or frequently used filters
        • Save your filter setups for later use
        """
        
        QMessageBox.information(self, "Crow Filter Help", help_text)

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

            
            self.crow_worker = CrowWorker(command, is_setup_ai=True)
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
            self.crow_worker = CrowWorker(command, is_setup_ai=True)
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

    def on_ai_file_saved(self, file_path):
        """Handle when AI analysis file is saved - MODIFIED: No longer asks to open file"""
        self.output_area.append(f"💾 AI results saved to: {file_path}")
        # Just notify user, don't ask to open

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
        """Stop the Crow search and prevent file creation"""
        if self.crow_worker and self.crow_worker.isRunning():
            # First, terminate the worker thread
            self.crow_worker.terminate()
            
            # Also terminate the underlying subprocess if it exists
            if hasattr(self.crow_worker, 'process') and self.crow_worker.process:
                try:
                    # Forcefully terminate the Blackbird subprocess
                    self.crow_worker.process.terminate()
                    
                    # On some systems, we might need to kill it
                    import signal
                    self.crow_worker.process.send_signal(signal.SIGTERM)
                    
                    # Wait a bit for process to terminate
                    import time
                    time.sleep(0.5)
                    
                    # Force kill if still running
                    if self.crow_worker.process.poll() is None:
                        self.crow_worker.process.kill()
                        
                except Exception as e:
                    self.output_area.append(f"⚠️ Error stopping process: {e}")
            
            # Wait for thread to finish
            self.crow_worker.wait()
        
        self.crow_run_btn.setEnabled(True)
        self.crow_stop_btn.setEnabled(False)
        self.output_area.append("⏹️ Crow search stopped (process terminated, files not created).")

    def update_crow_output(self, text):
        """Update Crow output area with text"""
        self.output_area.append(text)

    def on_crow_search_finished(self):
        """Handle completion of Crow search"""
        self.crow_run_btn.setEnabled(True)
        self.crow_stop_btn.setEnabled(False)
        self.output_area.append("✅ Crow search completed!")