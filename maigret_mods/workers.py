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
    
    def terminate(self):
        """Stop the multi-search operation"""
        self.should_stop = True
        super().terminate()