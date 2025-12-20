import os
import sys
import subprocess
import webbrowser
import signal  # ADD THIS IMPORT
from PyQt6.QtCore import QThread, pyqtSignal
import ssl
from datetime import datetime
import re

class DashboardWorker(QThread):
    output_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)  # success, message
    
    def __init__(self, open_browser=True):
        super().__init__()
        self.open_browser = open_browser
        self.dashboard_path = None
        
    def run(self):
        try:
            self.output_signal.emit("🔄 Generating dashboard...")
            
            # Import dashboard functions
            try:
                from maigret_mods.gen_dashboard import generate_dashboard
                
                # Generate the dashboard
                dashboard_file = generate_dashboard()
                self.dashboard_path = os.path.abspath(dashboard_file)
                
                self.output_signal.emit(f"✅ Dashboard generated: {dashboard_file}")
                self.output_signal.emit(f"📁 Location: {self.dashboard_path}")
                
                # Open in browser if requested
                if self.open_browser:
                    webbrowser.open(f"file://{self.dashboard_path}")
                    self.output_signal.emit("🌐 Opening dashboard in browser...")
                
                self.finished_signal.emit(True, f"Dashboard generated successfully: {dashboard_file}")
                
            except ImportError as e:
                self.output_signal.emit(f"❌ Error importing dashboard module: {e}")
                self.finished_signal.emit(False, f"Import error: {e}")
                
            except Exception as e:
                self.output_signal.emit(f"❌ Error generating dashboard: {e}")
                self.finished_signal.emit(False, f"Generation error: {e}")
                
        except Exception as e:
            self.output_signal.emit(f"❌ Unexpected error: {e}")
            self.finished_signal.emit(False, f"Unexpected error: {e}")

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
        
        # Termination flag
        self._terminate_requested = False
    
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
            ssl._create_default_https_context = ssl._create_unverified_context
        
        # Create process with proper signal handling
        try:
            self.process = subprocess.Popen(
                self.command, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT, 
                stdin=subprocess.PIPE,
                text=True, 
                shell=True,
                bufsize=1,
                preexec_fn=os.setsid if hasattr(os, 'setsid') else None  # Create process group
            )
        except Exception as e:
            self.output_signal.emit(f"❌ Failed to start process: {e}")
            self.finished_signal.emit()
            return
        
        if self.is_setup_ai:
            import time
            time.sleep(2)
            try:
                if self.process.stdin and not self._terminate_requested:
                    self.process.stdin.write('Y\n')
                    self.process.stdin.flush()
                    self.output_signal.emit("✓ Sent confirmation for API key setup")
            except Exception as e:
                self.output_signal.emit(f"Setup confirmation error: {e}")
        
        # Process output line by line
        confirmation_sent = False
        for line in self.process.stdout:
            if self._terminate_requested:
                break
                
            text = line.rstrip()  # Keep original formatting
            
            # Handle AI confirmation if needed
            if (self.needs_ai_confirmation and not confirmation_sent and 
                ('analyzing with ai' in text.lower() or 'consent' in text.lower())):
                try:
                    if self.process.stdin and not self._terminate_requested:
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
        if self.ai_results_started and not self._terminate_requested:
            self.auto_save_ai_results()
        
        # Clean up process
        try:
            if self.process.stdout:
                self.process.stdout.close()
            if self.process.stdin:
                self.process.stdin.close()
        except:
            pass
        
        # Wait for process
        try:
            if not self._terminate_requested:
                self.process.wait()
        except:
            pass
        
        if not self._terminate_requested:
            self.finished_signal.emit()

    def terminate(self):
        """Properly terminate the thread and process"""
        self._terminate_requested = True
        
        if self.process:
            try:
                # Kill the entire process group
                if hasattr(os, 'setsid'):
                    os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
                else:
                    self.process.terminate()
                
                # Wait for clean termination
                self.process.wait(timeout=2)
            except:
                try:
                    # Force kill if still running
                    if self.process.poll() is None:
                        if hasattr(os, 'setsid'):
                            os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                        else:
                            self.process.kill()
                        self.process.wait(timeout=1)
                except:
                    pass
        
        # Call parent's terminate
        super().terminate()
    
    def process_ai_output(self, text):
        """Process AI analysis output similar to crow.py"""
        if self._terminate_requested:
            return
            
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
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def auto_save_ai_results(self):
        """Automatically save AI results to file (from crow.py)"""
        if not self.ai_results_buffer or self._terminate_requested:
            return
        
        try:
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

class MaigretWorker(QThread):
    output_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()
    
    def __init__(self, command, auto_confirm_self_check=False):
        super().__init__()
        self.command = command
        self.process = None
        self.auto_confirm_self_check = auto_confirm_self_check
        self._terminate_requested = False  # ADD THIS

    def run(self):
        # Start process with proper signal handling
        self.process = subprocess.Popen(
            self.command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.PIPE,
            text=True,
            bufsize=1,
            preexec_fn=os.setsid if hasattr(os, 'setsid') else None  # Create process group
        )
        
        # If auto-confirm is enabled, send 'y' immediately
        if self.auto_confirm_self_check and not self._terminate_requested:
            try:
                if self.process.stdin:
                    self.process.stdin.write('y\n')
                    self.process.stdin.flush()
            except:
                pass
        
        # Read output
        for line in self.process.stdout:
            if self._terminate_requested:
                break
                
            cleaned_line = line.strip()
            # Clean ANSI escape sequences
            import re
            ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
            cleaned_line = ansi_escape.sub('', cleaned_line)
            
            if cleaned_line:
                self.output_signal.emit(cleaned_line)
                
                # Log that we auto-responded if we see the prompt
                if "Do you want to save changes permanently?" in cleaned_line:
                    if self.auto_confirm_self_check and not self._terminate_requested:
                        self.output_signal.emit("✓ Already auto-responded 'y'")
        
        # Clean up
        try:
            if self.process.stdout:
                self.process.stdout.close()
            if self.process.stdin:
                self.process.stdin.close()
        except:
            pass
        
        # Wait for process to finish
        if not self._terminate_requested:
            self.process.wait()
        
        if not self._terminate_requested:
            self.finished_signal.emit()
    
    def terminate(self):
        """Properly terminate the process to avoid zombies"""
        self._terminate_requested = True
        
        if self.process:
            try:
                # Try to send SIGTERM first
                if hasattr(os, 'setsid'):
                    # Kill the entire process group
                    os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
                else:
                    self.process.terminate()
                
                # Wait a bit for clean termination
                self.process.wait(timeout=2)
            except:
                try:
                    # Force kill if still running
                    if self.process.poll() is None:
                        if hasattr(os, 'setsid'):
                            os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                        else:
                            self.process.kill()
                        
                        # Wait and reap
                        self.process.wait(timeout=1)
                except:
                    pass
        
        # Call parent's terminate
        super().terminate()

class MaigretWebWorker(QThread):
    output_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()
    
    def __init__(self, port="5000"):
        super().__init__()
        self.port = port
        self.process = None
        self._terminate_requested = False  # ADD THIS
        
    def run(self):
        try:
            self.process = subprocess.Popen(
                f"maigret --web {self.port}",
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                shell=True,
                preexec_fn=os.setsid if hasattr(os, 'setsid') else None  # Create process group
            )
            
            for line in self.process.stdout:
                if self._terminate_requested:
                    break
                self.output_signal.emit(line.strip())
                
            # Clean up
            try:
                if self.process.stdout:
                    self.process.stdout.close()
            except:
                pass
            
            if not self._terminate_requested:
                self.process.wait()
                self.finished_signal.emit()
        except Exception as e:
            self.output_signal.emit(f"Error: {e}")
            self.finished_signal.emit()
        
    def terminate(self):
        """Terminate the web interface process"""
        self._terminate_requested = True
        
        if self.process:
            try:
                if hasattr(os, 'setsid'):
                    os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
                else:
                    self.process.terminate()
                self.process.wait(timeout=2)
            except:
                try:
                    if self.process.poll() is None:
                        if hasattr(os, 'setsid'):
                            os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                        else:
                            self.process.kill()
                        self.process.wait(timeout=1)
                except:
                    pass
        
class MaigretMultiSearchWorker(QThread):
    """Worker thread for running multiple Maigret searches"""
    output_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()
    progress_signal = pyqtSignal(int, int)  # (current, total)
    
    def __init__(self, usernames, gui_instance):
        super().__init__()
        self.usernames = usernames
        self.gui_instance = gui_instance
        self.should_stop = False
        
        # Store command parts from gui_instance
        self.timeout = None
        self.retries = None
        self.max_connections = None
        self.no_recursion = None
        self.no_extracting = None
        self.permute = None
        self.proxy = None
        self.tor_proxy = None
        self.i2p_proxy = None
        self.all_sites = None
        self.top_sites = None
        self.top_sites_count = None
        self.tags = None
        self.sites_list = None
        self.use_disabled_sites = None
        self.parse_url = None
        self.submit_url = None
        self.self_check = None
        self.csv_output = None
        self.pdf_output = None
        self.txt_output = None
        self.json_simple = None
        self.json_ndjson = None
        self.graph_output = None
        self.html_output = None
        self.report_sorting = None
        self.report_sorting_type = None
        self.print_not_found = None
        self.print_errors = None
        self.verbose = None
        self.info = None
        self.debug = None
        
        # Cache GUI values to avoid thread safety issues
        self.cache_gui_values()
    
    def cache_gui_values(self):
        """Cache GUI values to avoid accessing GUI from worker thread"""
        try:
            self.timeout = self.gui_instance.timeout_spinbox.value()
            self.retries = self.gui_instance.retries_spinbox.value()
            self.max_connections = self.gui_instance.max_connections_spinbox.value()
            self.no_recursion = self.gui_instance.no_recursion_checkbox.isChecked()
            self.no_extracting = self.gui_instance.no_extracting_checkbox.isChecked()
            self.permute = self.gui_instance.permute_checkbox.isChecked()
            self.proxy = self.gui_instance.proxy_input.text().strip()
            self.tor_proxy = self.gui_instance.tor_proxy_input.text().strip()
            self.i2p_proxy = self.gui_instance.i2p_proxy_input.text().strip()
            self.all_sites = self.gui_instance.all_sites_checkbox.isChecked()
            self.top_sites = self.gui_instance.top_sites_checkbox.isChecked()
            self.top_sites_count = self.gui_instance.top_sites_input.value()
            self.tags = self.gui_instance.tags_input.text().strip()
            
            # Sites list
            sites_text = self.gui_instance.site_textedit.toPlainText()
            self.sites_list = [site.strip() for site in sites_text.split('\n') if site.strip()]
            
            self.use_disabled_sites = self.gui_instance.use_disabled_sites_checkbox.isChecked()
            self.parse_url = self.gui_instance.parse_url_input.text().strip()
            self.submit_url = self.gui_instance.submit_url_input.text().strip()
            self.self_check = self.gui_instance.self_check_checkbox.isChecked()
            self.csv_output = self.gui_instance.csv_checkbox.isChecked()
            self.pdf_output = self.gui_instance.pdf_checkbox.isChecked()
            self.txt_output = self.gui_instance.txt_checkbox.isChecked()
            self.json_simple = self.gui_instance.json_checkbox_simple.isChecked()
            self.json_ndjson = self.gui_instance.json_checkbox_ndjson.isChecked()
            self.graph_output = self.gui_instance.G_checkbox.isChecked()
            self.html_output = self.gui_instance.html_checkbox.isChecked()
            self.report_sorting = self.gui_instance.report_sorting_checkbox.isChecked()
            self.report_sorting_type = self.gui_instance.report_sorting_combobox.currentText()
            self.print_not_found = self.gui_instance.print_not_found_checkbox.isChecked()
            self.print_errors = self.gui_instance.print_errors_checkbox.isChecked()
            self.verbose = self.gui_instance.verbose_checkbox.isChecked()
            self.info = self.gui_instance.info_checkbox.isChecked()
            self.debug = self.gui_instance.debug_checkbox.isChecked()
            
        except Exception as e:
            self.output_signal.emit(f"⚠️  Error caching GUI values: {e}")
    
    def run(self):
        """Run Maigret searches for each username"""
        total_users = len(self.usernames)
        
        for i, username in enumerate(self.usernames, 1):
            if self.should_stop:
                self.output_signal.emit("⚠️  Maigret search stopped by user")
                break
            
            self.output_signal.emit(f"\n{'='*60}")
            self.output_signal.emit(f"🔍 SEARCHING USERNAME {i}/{total_users}: {username}")
            self.output_signal.emit(f"{'='*60}")
            
            # Emit progress
            self.progress_signal.emit(i, total_users)
            
            # Build command for this username
            command = f"maigret {username}"
            
            # Add cached options
            command += f" --timeout {self.timeout}"
            command += f" --retries {self.retries}"
            command += f" --max-connections {self.max_connections}"
            
            if self.no_recursion:
                command += " --no-recursion"
            if self.no_extracting:
                command += " --no-extracting"
            if self.permute:
                command += " --permute"
            
            if self.proxy:
                command += f" --proxy {self.proxy}"
            
            if self.tor_proxy and self.tor_proxy != "socks5://127.0.0.1:9050":
                command += f" --tor-proxy {self.tor_proxy}"
            
            if self.i2p_proxy:
                command += f" --i2p-proxy {self.i2p_proxy}"
            
            if self.all_sites:
                command += " --all-sites"
            
            if self.top_sites:
                command += f" --top-sites {self.top_sites_count}"
            
            if self.tags:
                command += f" --tags {self.tags}"
            
            # Add sites as separate --site parameters
            if self.sites_list:
                for site in self.sites_list:
                    command += f" --site {site}"
                self.output_signal.emit(f"Using {len(self.sites_list)} site(s) for this search")
            
            if self.use_disabled_sites:
                command += " --use-disabled-sites"
            
            if self.parse_url:
                command += f" --parse {self.parse_url}"
            
            if self.submit_url:
                command += f" --submit {self.submit_url}"
            
            if self.self_check:
                command += " --self-check"
            
            # Output formats
            if self.csv_output:
                command += " --csv"
            if self.pdf_output:
                command += " --pdf"
            if self.txt_output:
                command += " --txt"
            if self.json_simple:
                command += " --json simple"
            if self.json_ndjson:
                command += " --json ndjson"
            if self.graph_output:
                command += " --graph"
            if self.html_output:
                command += " --html"
            
            if self.report_sorting:
                command += f" --reports-sorting {self.report_sorting_type}"
            
            if self.print_not_found:
                command += " --print-not-found"
            if self.print_errors:
                command += " --print-errors"
            if self.verbose:
                command += " --verbose"
            if self.info:
                command += " --info"
            if self.debug:
                command += " --debug"
            
            self.output_signal.emit(f"Running command for '{username}': {command}")
            
            if self.self_check:
                # Prepend with echo 'y' | to auto-respond
                command = f"echo 'y' | {command}"
            
            # Run the command
            try:
                process = subprocess.Popen(
                    command,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True,
                    preexec_fn=os.setsid if hasattr(os, 'setsid') else None
                )
                
                # Capture output in real-time
                for line in process.stdout:
                    if self.should_stop:
                        # Kill the process if we're stopping
                        if hasattr(os, 'setsid'):
                            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                        else:
                            process.terminate()
                        break
                    
                    # Clean ANSI escape sequences
                    import re
                    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
                    clean_line = ansi_escape.sub('', line.rstrip())
                    
                    if clean_line:
                        self.output_signal.emit(clean_line)
                
                if not self.should_stop:
                    process.wait()
                    
                    if process.returncode == 0:
                        self.output_signal.emit(f"✅ Search completed for '{username}'")
                    else:
                        self.output_signal.emit(f"❌ Search failed for '{username}' (exit code: {process.returncode})")
                        
            except Exception as e:
                self.output_signal.emit(f"❌ Error running Maigret for '{username}': {str(e)}")
            
            # Brief pause between searches (optional)
            if i < total_users and not self.should_stop:
                import time
                time.sleep(1)
        
        self.output_signal.emit(f"\n{'='*60}")
        if self.should_stop:
            self.output_signal.emit(f"⚠️  Maigret multi-search stopped. Processed {i-1}/{total_users} users.")
        else:
            self.output_signal.emit(f"✅ Maigret multi-search completed! Processed {total_users} users.")
        self.output_signal.emit(f"{'='*60}")
        
        self.finished_signal.emit()
    
    def terminate(self):
        """Stop the multi-search operation"""
        self.should_stop = True
        super().terminate()