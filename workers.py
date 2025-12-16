import os
import subprocess
from PyQt6.QtCore import QThread, pyqtSignal
import ssl
from datetime import datetime
import re

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
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def auto_save_ai_results(self):
        """Automatically save AI results to file (from crow.py)"""
        if not self.ai_results_buffer:
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
    
    def terminate(self):
        if self.process:
            self.process.terminate()
            self.process.wait()