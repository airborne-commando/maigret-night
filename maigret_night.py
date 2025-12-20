#!/usr/bin/env python3
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
# Import from modular directory
from maigret_mods.workers import CrowWorker, MaigretWorker, MaigretWebWorker, DashboardWorker
from maigret_mods.tor_spoofing import TORSpoofer
from maigret_mods.crow_header import create_crow_tab
from maigret_mods.crow_tabs import CrowTabMethods
from maigret_mods.breach_vip import process_single_email, process_email_file
from maigret_mods.breach_vip_username import process_single_username, process_username_file
from maigret_mods.command_builder import build_blackbird_command
# Import functions from maigret_functions
from maigret_mods.maigret_functions import (
    run_crow_search,
    create_save_load_actions,
    save_settings_dialog,
    save_settings,
    load_settings_dialog,
    load_settings,
    create_options_tab,
    load_sites_from_file,
    toggle_top_sites_input,
    toggle_report_sorting_input,
    create_buttons,
    generate_dashboard,
    on_dashboard_finished,
    toggle_web_interface,
    start_web_interface,
    stop_web_interface,
    on_web_interface_finished,
    append_web_output,
    run_maigret,
    on_maigret_finished,
    stop_maigret,
    append_output
)

class MaigretGUI(QMainWindow, CrowTabMethods):
    def __init__(self):
        super().__init__()
        # Initialize the parent classes
        QMainWindow.__init__(self)
        CrowTabMethods.__init__(self)
        
        self.setWindowTitle("Maigret Night")
        self.setGeometry(100, 100, 1200, 800)
        self.maigret_worker = None
        self.crow_worker = None
        self.crow_tor_spoofer = None
        self.crow_ai_api_key = None
        self.maigret_web_worker = None
        self.dashboard_worker = None

        # Initialize UI components needed by the imported functions
        self.initialize_ui_components()
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        tab_widget = QTabWidget()
        layout.addWidget(tab_widget)

        # Create tabs for different sections using imported function
        create_options_tab(self, tab_widget)
        
        # Create the Crow tab
        create_crow_tab(tab_widget, self)

        # Create buttons and output area using imported function
        create_buttons(self, layout)

        # Add Save and Load actions using imported function
        create_save_load_actions(self, layout)

    def initialize_ui_components(self):
        """Initialize UI components that will be used by imported functions"""
        # These will be properly initialized in create_options_tab and create_buttons
        # but we need to declare them here for the imported functions to work
        self.output_area = None
        self.username_input = None
        self.username_file_btn = None  # ADDED: For the username file button
        self.timeout_spinbox = None
        self.retries_spinbox = None
        self.max_connections_spinbox = None
        self.no_recursion_checkbox = None
        self.no_extracting_checkbox = None
        self.permute_checkbox = None
        self.all_sites_checkbox = None
        self.self_check_checkbox = None
        self.use_disabled_sites_checkbox = None
        self.report_sorting_checkbox = None
        self.report_sorting_combobox = None
        self.top_sites_checkbox = None
        self.top_sites_input = None
        self.proxy_input = None
        self.tor_proxy_input = None
        self.i2p_proxy_input = None
        self.tags_input = None
        self.site_textedit = None
        self.load_sites_button = None
        self.parse_url_input = None
        self.submit_url_input = None
        self.csv_checkbox = None
        self.pdf_checkbox = None
        self.txt_checkbox = None
        self.json_checkbox_simple = None
        self.json_checkbox_ndjson = None
        self.G_checkbox = None
        self.html_checkbox = None
        self.print_not_found_checkbox = None
        self.print_errors_checkbox = None
        self.verbose_checkbox = None
        self.info_checkbox = None
        self.debug_checkbox = None
        self.web_port_input = None
        self.run_button = None
        self.stop_button = None
        self.web_button = None
        self.dashboard_button = None
        
        # Crow tab components
        self.crow_username_input = None
        self.crow_email_input = None
        self.crow_ai_checkbox = None
        self.crow_tor_checkbox = None
        self.crow_breach_username_checkbox = None
        self.crow_breach_email_checkbox = None
        self.crow_permute_checkbox = None
        self.crow_permuteall_checkbox = None
        self.crow_no_nsfw_checkbox = None
        self.crow_no_update_checkbox = None
        self.crow_csv_checkbox = None
        self.crow_pdf_checkbox = None
        self.crow_json_checkbox = None
        self.crow_verbose_checkbox = None
        self.crow_dump_checkbox = None
        self.crow_max_concurrent_spinbox = None
        self.crow_filter_input = None
        self.crow_run_btn = None
        self.crow_stop_btn = None

    def select_maigret_username_file(self):
        """Select a file containing usernames for Maigret"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Select Username File", 
            "", 
            "Text Files (*.txt);;All Files (*.*)"
        )
        
        if file_path:
            # Update the username input with file: prefix
            self.username_input.setText(f"file:{file_path}")
            self.output_area.append(f"Username file selected: {os.path.basename(file_path)}")
            
            # Optional: Count and display number of usernames in file
            try:
                with open(file_path, 'r') as f:
                    usernames = [line.strip() for line in f if line.strip()]
                self.output_area.append(f"Found {len(usernames)} username(s) in file")
            except Exception as e:
                self.output_area.append(f"Note: Could not read file - {str(e)}")

    # Define methods that will use the imported functions
    # These methods will be called from the UI components
    
    def run_crow_search_wrapper(self):
        """Wrapper method for run_crow_search"""
        run_crow_search(self)
    
    def save_settings_dialog_wrapper(self):
        """Wrapper method for save_settings_dialog"""
        save_settings_dialog(self)
    
    def load_settings_dialog_wrapper(self):
        """Wrapper method for load_settings_dialog"""
        load_settings_dialog(self)
    
    def save_settings_wrapper(self, file_path):
        """Wrapper method for save_settings"""
        save_settings(self, file_path)
    
    def load_settings_wrapper(self, file_path):
        """Wrapper method for load_settings"""
        load_settings(self, file_path)
    
    def load_sites_from_file_wrapper(self):
        """Wrapper method for load_sites_from_file"""
        load_sites_from_file(self)
    
    def toggle_top_sites_input_wrapper(self):
        """Wrapper method for toggle_top_sites_input"""
        toggle_top_sites_input(self)
    
    def toggle_report_sorting_input_wrapper(self):
        """Wrapper method for toggle_report_sorting_input"""
        toggle_report_sorting_input(self)
    
    def generate_dashboard_wrapper(self):
        """Wrapper method for generate_dashboard"""
        generate_dashboard(self)
    
    def on_dashboard_finished_wrapper(self, success, message):
        """Wrapper method for on_dashboard_finished"""
        on_dashboard_finished(self, success, message)
    
    def toggle_web_interface_wrapper(self):
        """Wrapper method for toggle_web_interface"""
        toggle_web_interface(self)
    
    def start_web_interface_wrapper(self):
        """Wrapper method for start_web_interface"""
        start_web_interface(self)
    
    def stop_web_interface_wrapper(self):
        """Wrapper method for stop_web_interface"""
        stop_web_interface(self)
    
    def on_web_interface_finished_wrapper(self):
        """Wrapper method for on_web_interface_finished"""
        on_web_interface_finished(self)
    
    def append_web_output_wrapper(self, text):
        """Wrapper method for append_web_output"""
        append_web_output(self, text)
    
    def run_maigret_wrapper(self):
        """Wrapper method for run_maigret"""
        run_maigret(self)
    
    def on_maigret_finished_wrapper(self):
        """Wrapper method for on_maigret_finished"""
        on_maigret_finished(self)
    
    def stop_maigret_wrapper(self):
        """Wrapper method for stop_maigret"""
        stop_maigret(self)
    
    def append_output_wrapper(self, text):
        """Wrapper method for append_output"""
        append_output(self, text)

    # Connect the wrapper methods to the actual imported functions
    # by overriding the methods in the parent class
    def run_crow_search(self):
        self.run_crow_search_wrapper()
    
    def save_settings_dialog(self):
        self.save_settings_dialog_wrapper()
    
    def load_settings_dialog(self):
        self.load_settings_dialog_wrapper()
    
    def save_settings(self, file_path):
        self.save_settings_wrapper(file_path)
    
    def load_settings(self, file_path):
        self.load_settings_wrapper(file_path)
    
    def load_sites_from_file(self):
        self.load_sites_from_file_wrapper()
    
    def toggle_top_sites_input(self):
        self.toggle_top_sites_input_wrapper()
    
    def toggle_report_sorting_input(self):
        self.toggle_report_sorting_input_wrapper()
    
    def generate_dashboard(self):
        self.generate_dashboard_wrapper()
    
    def on_dashboard_finished(self, success, message):
        self.on_dashboard_finished_wrapper(success, message)
    
    def toggle_web_interface(self):
        self.toggle_web_interface_wrapper()
    
    def start_web_interface(self):
        self.start_web_interface_wrapper()
    
    def stop_web_interface(self):
        self.stop_web_interface_wrapper()
    
    def on_web_interface_finished(self):
        self.on_web_interface_finished_wrapper()
    
    def append_web_output(self, text):
        self.append_web_output_wrapper(text)
    
    def run_maigret(self):
        self.run_maigret_wrapper()
    
    def on_maigret_finished(self):
        self.on_maigret_finished_wrapper()
    
    def stop_maigret(self):
        self.stop_maigret_wrapper()
    
    def append_output(self, text):
        self.append_output_wrapper(text)

    # ================================================================
    # IMPORTANT: ADD THESE METHODS FOR PROPER THREAD CLEANUP
    # ================================================================
    
    def closeEvent(self, event):
        """Handle application close event - clean up threads before exiting"""
        # Stop all running workers
        self.cleanup_workers()
        
        # Accept the close event
        event.accept()
    
    def cleanup_workers(self):
        """Clean up all worker threads before exiting"""
        # Stop Maigret web interface if running
        if self.maigret_web_worker and self.maigret_web_worker.isRunning():
            self.output_area.append("Stopping web interface...")
            self.stop_web_interface()
        
        # Stop Maigret search if running
        if self.maigret_worker and self.maigret_worker.isRunning():
            self.output_area.append("Stopping Maigret search...")
            self.stop_maigret()
        
        # Stop Crow search if running
        if self.crow_worker and self.crow_worker.isRunning():
            self.output_area.append("Stopping Crow search...")
            self.stop_crow_search()
        
        # Stop Dashboard generation if running
        if self.dashboard_worker and self.dashboard_worker.isRunning():
            self.output_area.append("Stopping dashboard generation...")
            self.dashboard_worker.terminate()
            self.dashboard_worker.wait()
        
        # Give threads time to finish
        import time
        time.sleep(0.5)
        
        # Disconnect all signals
        if self.maigret_worker:
            try:
                self.maigret_worker.output_signal.disconnect()
                self.maigret_worker.finished_signal.disconnect()
            except:
                pass
        
        if self.crow_worker:
            try:
                self.crow_worker.output_signal.disconnect()
                self.crow_worker.finished_signal.disconnect()
                if hasattr(self.crow_worker, 'ai_file_saved'):
                    self.crow_worker.ai_file_saved.disconnect()
            except:
                pass
        
        if self.maigret_web_worker:
            try:
                self.maigret_web_worker.output_signal.disconnect()
                self.maigret_web_worker.finished_signal.disconnect()
            except:
                pass
        
        if self.dashboard_worker:
            try:
                self.dashboard_worker.output_signal.disconnect()
                self.dashboard_worker.finished_signal.disconnect()
            except:
                pass
        
        self.output_area.append("All workers cleaned up. Safe to exit.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MaigretGUI()
    window.show()
    
    # Set up proper application exit handling
    try:
        result = app.exec()
        # Ensure cleanup happens on exit
        window.cleanup_workers()
        sys.exit(result)
    except KeyboardInterrupt:
        window.cleanup_workers()
        sys.exit(0)
    except Exception as e:
        print(f"Application error: {e}")
        window.cleanup_workers()
        sys.exit(1)