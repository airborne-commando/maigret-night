#!/usr/bin/env python3
#!~/.local/bin/venv/bin/activate python3
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
from workers import CrowWorker
from tor_spoofing import TORSpoofer
from breach_vip import process_single_email, process_email_file, is_enabled as is_breach_email_enabled
from breach_vip_username import process_single_username, process_username_file, is_enabled as is_breach_username_enabled
from crow_header import create_crow_tab
from crow_tabs import CrowTabMethods

# Worker class that handles executing the Maigret command in a separate thread

class MaigretWebWorker(QThread):
    output_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()
    
    def __init__(self, port="5000"):
        super().__init__()
        self.port = port
        self.process = None
        
    def run(self):
        self.process = subprocess.Popen(
            f"maigret --web {self.port}",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            shell=True
        )
        for line in self.process.stdout:
            self.output_signal.emit(line.strip())
        self.process.wait()
        self.finished_signal.emit()
        
    def terminate(self):
        if self.process:
            self.process.terminate()
            self.process.wait()

class MaigretWorker(QThread):
    output_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, command):
        super().__init__()
        self.command = command
        self.process = None
        self.maigret_web_worker = None  # Add this line

    def run(self):
        self.process = subprocess.Popen(self.command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, shell=True)
        for line in self.process.stdout:
            self.output_signal.emit(line.strip())
        self.process.wait()
        self.finished_signal.emit()

    def terminate(self):
        if self.process:
            self.process.terminate()
            self.process.wait()

class MaigretGUI(QMainWindow, CrowTabMethods):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Maigret Night")
        self.setGeometry(100, 100, 1200, 800)
        self.maigret_worker = None
        self.crow_worker = None
        self.crow_tor_spoofer = None
        self.crow_ai_api_key = None
        self.maigret_web_worker = None  # Add this line

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        tab_widget = QTabWidget()
        layout.addWidget(tab_widget)

        # Create tabs for different sections
        self.create_options_tab(tab_widget)
        
        # Create the Crow tab
        create_crow_tab(tab_widget, self)

        # Buttons and output area
        self.create_buttons(layout)

        # Add Save and Load actions
        self.create_save_load_actions(layout)

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
        # Parse multiple sites from text area
        sites_text = self.site_textedit.toPlainText()
        sites_list = []
        if sites_text:
            # Split by lines and filter out empty lines
            sites_list = [site.strip() for site in sites_text.split('\n') if site.strip()]
        
        settings = {
            'web_port': self.web_port_input.text() if self.web_port_input.text() else "5000",
            'username': self.username_input.text(),
            'timeout': self.timeout_spinbox.value(),
            'retries': self.retries_spinbox.value(),
            'max_connections': self.max_connections_spinbox.value(),
            'recursive_search': not self.no_recursion_checkbox.isChecked(),
            'info_extracting': not self.no_extracting_checkbox.isChecked(),
            'permute': self.permute_checkbox.isChecked(),
            'proxy_url': self.proxy_input.text() if self.proxy_input.text() else None,
            'tor_proxy_url': self.tor_proxy_input.text() if self.tor_proxy_input.text() else "socks5://127.0.0.1:9050",
            'i2p_proxy_url': self.i2p_proxy_input.text() if self.i2p_proxy_input.text() else None,
            'scan_all_sites': self.all_sites_checkbox.isChecked(),
            'top_sites_count': self.top_sites_input.value() if self.top_sites_checkbox.isChecked() else 500,
            'tags': self.tags_input.text(),
            'scan_sites_list': sites_list,
            'scan_disabled_sites': self.use_disabled_sites_checkbox.isChecked(),
            'parse_url': self.parse_url_input.text(),
            'submit_url': self.submit_url_input.text(),
            'self_check_enabled': self.self_check_checkbox.isChecked(),
            'print_not_found': self.print_not_found_checkbox.isChecked(),
            'print_check_errors': self.print_errors_checkbox.isChecked(),
            'report_sorting': self.report_sorting_combobox.currentText() if self.report_sorting_checkbox.isChecked() else "default",
            'csv_report': self.csv_checkbox.isChecked(),
            'pdf_report': self.pdf_checkbox.isChecked(),
            'txt_report': self.txt_checkbox.isChecked(),
            'json_report_simple': self.json_checkbox_simple.isChecked(),
            'json_report_ndjson': self.json_checkbox_ndjson.isChecked(),
            'graph_report': self.G_checkbox.isChecked(),
            'html_report': self.html_checkbox.isChecked(),
            'verbose': self.verbose_checkbox.isChecked(),
            'info': self.info_checkbox.isChecked(),
            'debug': self.debug_checkbox.isChecked(),
        }

        # Remove None values to match JSON structure
        settings = {k: v for k, v in settings.items() if v is not None}

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

            self.web_port_input.setText(settings.get('web_port', '5000'))
            self.username_input.setText(settings.get('username', ''))
            self.timeout_spinbox.setValue(settings.get('timeout', 30))
            self.retries_spinbox.setValue(settings.get('retries', 0))
            self.max_connections_spinbox.setValue(settings.get('max_connections', 100))
            self.no_recursion_checkbox.setChecked(not settings.get('recursive_search', True))
            self.no_extracting_checkbox.setChecked(not settings.get('info_extracting', True))
            self.permute_checkbox.setChecked(settings.get('permute', False))
            self.proxy_input.setText(settings.get('proxy_url', ''))
            self.tor_proxy_input.setText(settings.get('tor_proxy_url', 'socks5://127.0.0.1:9050'))
            self.i2p_proxy_input.setText(settings.get('i2p_proxy_url', ''))
            self.all_sites_checkbox.setChecked(settings.get('scan_all_sites', False))
            top_sites_count = settings.get('top_sites_count', 500)
            self.top_sites_checkbox.setChecked(top_sites_count != 500)
            self.top_sites_input.setValue(top_sites_count)
            self.tags_input.setText(settings.get('tags', ''))
            
            # Load multiple sites from list
            sites_list = settings.get('scan_sites_list', [])
            self.site_textedit.setPlainText('\n'.join(sites_list))
            
            self.use_disabled_sites_checkbox.setChecked(settings.get('scan_disabled_sites', False))
            self.parse_url_input.setText(settings.get('parse_url', ''))
            self.submit_url_input.setText(settings.get('submit_url', ''))
            self.self_check_checkbox.setChecked(settings.get('self_check_enabled', False))
            self.print_not_found_checkbox.setChecked(settings.get('print_not_found', False))
            self.print_errors_checkbox.setChecked(settings.get('print_check_errors', False))
            report_sorting = settings.get('report_sorting', 'default')
            self.report_sorting_checkbox.setChecked(report_sorting != 'default')
            self.report_sorting_combobox.setCurrentText(report_sorting)
            self.csv_checkbox.setChecked(settings.get('csv_report', False))
            self.pdf_checkbox.setChecked(settings.get('pdf_report', False))
            self.txt_checkbox.setChecked(settings.get('txt_report', False))
            self.json_checkbox_simple.setChecked(settings.get('json_report_simple', False))
            self.json_checkbox_ndjson.setChecked(settings.get('json_report_ndjson', False))
            self.G_checkbox.setChecked(settings.get('graph_report', False))
            self.html_checkbox.setChecked(settings.get('html_report', False))
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

        # Username input
        username_layout = QHBoxLayout()
        self.username_input = QLineEdit()
        username_layout.addWidget(QLabel("Username:"))
        username_layout.addWidget(self.username_input)
        options_layout.addLayout(username_layout)

        # Timeout input
        timeout_layout = QHBoxLayout()
        timeout_layout.addWidget(QLabel("Timeout (seconds):"))
        self.timeout_spinbox = QSpinBox()
        self.timeout_spinbox.setRange(15, 300)
        self.timeout_spinbox.setValue(30)
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
        self.max_connections_spinbox.setRange(1, 200)
        self.max_connections_spinbox.setValue(100)
        max_connections_layout.addWidget(self.max_connections_spinbox)
        options_layout.addLayout(max_connections_layout)

        # Checkboxes row 1
        checkbox_layout_1 = QHBoxLayout()
        self.no_recursion_checkbox = QCheckBox("No Recursion")
        checkbox_layout_1.addWidget(self.no_recursion_checkbox)
        self.no_extracting_checkbox = QCheckBox("No Extracting")
        checkbox_layout_1.addWidget(self.no_extracting_checkbox)
        self.permute_checkbox = QCheckBox("Permute")
        checkbox_layout_1.addWidget(self.permute_checkbox)
        self.all_sites_checkbox = QCheckBox("All Sites")
        checkbox_layout_1.addWidget(self.all_sites_checkbox)
        options_layout.addLayout(checkbox_layout_1)

        # Checkboxes row 2
        checkbox_layout_2 = QHBoxLayout()
        self.self_check_checkbox = QCheckBox("Self Check")
        checkbox_layout_2.addWidget(self.self_check_checkbox)
        self.use_disabled_sites_checkbox = QCheckBox("Use Disabled Sites")
        checkbox_layout_2.addWidget(self.use_disabled_sites_checkbox)
        self.report_sorting_checkbox = QCheckBox("Enable Report Sorting")
        checkbox_layout_2.addWidget(self.report_sorting_checkbox)
        options_layout.addLayout(checkbox_layout_2)

        # Report Sorting
        self.report_sorting_combobox = QComboBox()
        self.report_sorting_combobox.addItems(["default", "data"])
        self.report_sorting_combobox.setEnabled(False)
        options_layout.addWidget(QLabel("Report Sorting:"))
        options_layout.addWidget(self.report_sorting_combobox)
        self.report_sorting_checkbox.toggled.connect(self.toggle_report_sorting_input)

        # Top Sites
        top_sites_layout = QHBoxLayout()
        self.top_sites_checkbox = QCheckBox("Top Sites Count:")
        self.top_sites_checkbox.toggled.connect(self.toggle_top_sites_input)
        top_sites_layout.addWidget(self.top_sites_checkbox)
        self.top_sites_input = QSpinBox()
        self.top_sites_input.setRange(1, 1000)
        self.top_sites_input.setValue(500)
        self.top_sites_input.setEnabled(False)
        top_sites_layout.addWidget(self.top_sites_input)
        options_layout.addLayout(top_sites_layout)

        # Proxy settings
        proxy_layout = QHBoxLayout()
        
        proxy_widget = QWidget()
        proxy_sub_layout = QVBoxLayout()
        proxy_sub_layout.addWidget(QLabel("Proxy URL:"))
        self.proxy_input = QLineEdit()
        self.proxy_input.setPlaceholderText("e.g., socks5://127.0.0.1:1080")
        proxy_sub_layout.addWidget(self.proxy_input)
        proxy_widget.setLayout(proxy_sub_layout)
        proxy_layout.addWidget(proxy_widget)

        tor_proxy_widget = QWidget()
        tor_proxy_sub_layout = QVBoxLayout()
        tor_proxy_sub_layout.addWidget(QLabel("Tor Proxy:"))
        self.tor_proxy_input = QLineEdit()
        self.tor_proxy_input.setText("socks5://127.0.0.1:9050")
        tor_proxy_sub_layout.addWidget(self.tor_proxy_input)
        tor_proxy_widget.setLayout(tor_proxy_sub_layout)
        proxy_layout.addWidget(tor_proxy_widget)

        i2p_proxy_widget = QWidget()
        i2p_proxy_sub_layout = QVBoxLayout()
        i2p_proxy_sub_layout.addWidget(QLabel("I2P Proxy:"))
        self.i2p_proxy_input = QLineEdit()
        self.i2p_proxy_input.setPlaceholderText("http://127.0.0.1:4444")
        i2p_proxy_sub_layout.addWidget(self.i2p_proxy_input)
        i2p_proxy_widget.setLayout(i2p_proxy_sub_layout)
        proxy_layout.addWidget(i2p_proxy_widget)

        options_layout.addLayout(proxy_layout)

        # Tags input
        tags_layout = QHBoxLayout()
        tags_layout.addWidget(QLabel("Tags (comma-separated):"))
        self.tags_input = QLineEdit()
        tags_layout.addWidget(self.tags_input)
        options_layout.addLayout(tags_layout)

        # Sites section with text area and load button
        sites_section_widget = QWidget()
        sites_section_layout = QVBoxLayout()
        
        sites_label_layout = QHBoxLayout()
        sites_label_layout.addWidget(QLabel("Sites (one per line, each as separate --site parameter):"))
        
        # Add Load Sites File button
        self.load_sites_button = QPushButton("Load Sites from File")
        self.load_sites_button.clicked.connect(self.load_sites_from_file)
        sites_label_layout.addWidget(self.load_sites_button)
        
        sites_section_layout.addLayout(sites_label_layout)
        
        self.site_textedit = QTextEdit()
        self.site_textedit.setMaximumHeight(100)
        self.site_textedit.setPlaceholderText("Enter site URLs, one per line\nExample:\ntwitter.com\ngithub.com\ninstagram.com\n\nOr use the 'Load Sites from File' button to load from a text file.")
        sites_section_layout.addWidget(self.site_textedit)
        
        sites_section_widget.setLayout(sites_section_layout)
        options_layout.addWidget(sites_section_widget)

        # Parse and Submit URLs
        parse_layout = QHBoxLayout()
        parse_layout.addWidget(QLabel("Parse URL:"))
        self.parse_url_input = QLineEdit()
        parse_layout.addWidget(self.parse_url_input)
        options_layout.addLayout(parse_layout)

        submit_layout = QHBoxLayout()
        submit_layout.addWidget(QLabel("Submit URL:"))
        self.submit_url_input = QLineEdit()
        submit_layout.addWidget(self.submit_url_input)
        options_layout.addLayout(submit_layout)

        # Output formats row
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("Output Formats:"))
        self.csv_checkbox = QCheckBox("CSV")
        format_layout.addWidget(self.csv_checkbox)
        self.pdf_checkbox = QCheckBox("PDF")
        format_layout.addWidget(self.pdf_checkbox)
        self.txt_checkbox = QCheckBox("TXT")
        format_layout.addWidget(self.txt_checkbox)
        self.json_checkbox_simple = QCheckBox("JSON Simple")
        format_layout.addWidget(self.json_checkbox_simple)
        self.json_checkbox_ndjson = QCheckBox("JSON ndjson")
        format_layout.addWidget(self.json_checkbox_ndjson)
        self.G_checkbox = QCheckBox("Graph")
        format_layout.addWidget(self.G_checkbox)
        self.html_checkbox = QCheckBox("HTML")
        format_layout.addWidget(self.html_checkbox)
        options_layout.addLayout(format_layout)

        # Verbosity row
        verbosity_layout = QHBoxLayout()
        verbosity_layout.addWidget(QLabel("Verbosity:"))
        self.print_not_found_checkbox = QCheckBox("Print Not Found")
        verbosity_layout.addWidget(self.print_not_found_checkbox)
        self.print_errors_checkbox = QCheckBox("Print Errors")
        verbosity_layout.addWidget(self.print_errors_checkbox)
        self.verbose_checkbox = QCheckBox("Verbose")
        verbosity_layout.addWidget(self.verbose_checkbox)
        self.info_checkbox = QCheckBox("Info")
        verbosity_layout.addWidget(self.info_checkbox)
        self.debug_checkbox = QCheckBox("Debug")
        verbosity_layout.addWidget(self.debug_checkbox)
        options_layout.addLayout(verbosity_layout)

        options_group.setLayout(options_layout)
        tab_widget.addTab(options_group, "Options")

    def load_sites_from_file(self):
        """Load sites from a text file, one per line"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Load Sites from File", 
            "", 
            "Text Files (*.txt);;All Files (*.*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r') as file:
                    sites_content = file.read()
                
                # Set the content to the text edit
                self.site_textedit.setPlainText(sites_content)
                self.output_area.append(f"Loaded sites from {file_path}")
                
                # Count and display number of sites
                sites_list = [site.strip() for site in sites_content.split('\n') if site.strip()]
                self.output_area.append(f"Found {len(sites_list)} site(s) in the file.")
                
            except Exception as e:
                self.output_area.append(f"Error loading sites file: {str(e)}")
                QMessageBox.critical(self, "Error", f"Failed to load sites file:\n{str(e)}")

    def toggle_top_sites_input(self):
        self.top_sites_input.setEnabled(self.top_sites_checkbox.isChecked())

    def toggle_report_sorting_input(self):
        self.report_sorting_combobox.setEnabled(self.report_sorting_checkbox.isChecked())

    def create_buttons(self, layout):
        button_layout = QHBoxLayout()
        
        # Existing buttons...
        self.run_button = QPushButton("Run Maigret")
        self.run_button.clicked.connect(self.run_maigret)
        button_layout.addWidget(self.run_button)
        
        self.stop_button = QPushButton("Stop Maigret")
        self.stop_button.clicked.connect(self.stop_maigret)
        self.stop_button.setEnabled(False)
        button_layout.addWidget(self.stop_button)
        
        # Add web interface button
        self.web_button = QPushButton("Start Web Interface")
        self.web_button.clicked.connect(self.toggle_web_interface)
        button_layout.addWidget(self.web_button)
        
        # Add port input for web interface
        web_port_layout = QHBoxLayout()
        web_port_layout.addWidget(QLabel("Web Port:"))
        self.web_port_input = QLineEdit()
        self.web_port_input.setPlaceholderText("5000")
        self.web_port_input.setMaximumWidth(80)
        web_port_layout.addWidget(self.web_port_input)
        button_layout.addLayout(web_port_layout)
        
        layout.addLayout(button_layout)

        self.output_area = QTextEdit()
        self.output_area.setReadOnly(True)
        layout.addWidget(self.output_area)

    def toggle_web_interface(self):
        """Toggle the Maigret web interface on/off"""
        if self.maigret_web_worker and self.maigret_web_worker.isRunning():
            # Stop web interface
            self.stop_web_interface()
        else:
            # Start web interface
            self.start_web_interface()

    def start_web_interface(self):
        """Start the Maigret web interface"""
        port = self.web_port_input.text().strip()
        if not port:
            port = "5000"
        
        # Validate port number
        try:
            port_int = int(port)
            if not (1 <= port_int <= 65535):
                raise ValueError("Port must be between 1 and 65535")
        except ValueError as e:
            self.output_area.append(f"Invalid port number: {e}")
            QMessageBox.warning(self, "Invalid Port", f"Please enter a valid port number (1-65535).\nError: {e}")
            return
        
        self.output_area.append(f"Starting Maigret web interface on port {port}...")
        self.output_area.append(f"Access at: http://localhost:{port}")
        
        self.maigret_web_worker = MaigretWebWorker(port)
        self.maigret_web_worker.output_signal.connect(self.append_web_output)
        self.maigret_web_worker.finished_signal.connect(self.on_web_interface_finished)
        self.maigret_web_worker.start()
        
        self.web_button.setText("Stop Web Interface")
        self.web_port_input.setEnabled(False)
        
        # Open browser option (optional)
        open_browser = QMessageBox.question(
            self,
            "Open Browser?",
            "Would you like to open the web interface in your default browser?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        
        if open_browser == QMessageBox.StandardButton.Yes:
            import webbrowser
            webbrowser.open(f"http://localhost:{port}")

    def stop_web_interface(self):
        """Stop the Maigret web interface"""
        if self.maigret_web_worker:
            self.output_area.append("Stopping Maigret web interface...")
            self.maigret_web_worker.terminate()
            self.maigret_web_worker = None
            self.web_button.setText("Start Web Interface")
            self.web_port_input.setEnabled(True)
            self.output_area.append("Web interface stopped.")

    def on_web_interface_finished(self):
        """Called when web interface process finishes"""
        self.web_button.setText("Start Web Interface")
        self.web_port_input.setEnabled(True)
        self.output_area.append("Web interface process finished.")

    def append_web_output(self, text):
        """Append web interface output to the text area"""
        self.output_area.append(f"[Web Interface] {text}")

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
        
        proxy = self.proxy_input.text()
        if proxy:
            command += f" --proxy {proxy}"
        
        tor_proxy = self.tor_proxy_input.text()
        if tor_proxy and tor_proxy != "socks5://127.0.0.1:9050":
            command += f" --tor-proxy {tor_proxy}"
        
        i2p_proxy = self.i2p_proxy_input.text()
        if i2p_proxy:
            command += f" --i2p-proxy {i2p_proxy}"
        
        if self.all_sites_checkbox.isChecked():
            command += " --all-sites"
        
        if self.top_sites_checkbox.isChecked():
            command += f" --top-sites {self.top_sites_input.value()}"
        
        tags = self.tags_input.text()
        if tags:
            command += f" --tags {tags}"
        
        # Handle multiple sites as separate --site parameters
        sites_text = self.site_textedit.toPlainText()
        if sites_text:
            # Split by lines and filter out empty lines
            sites_list = [site.strip() for site in sites_text.split('\n') if site.strip()]
            if sites_list:
                # Add each site as a separate --site parameter
                for site in sites_list:
                    command += f" --site {site}"
                self.output_area.append(f"Using {len(sites_list)} site(s): {', '.join(sites_list)}")
        
        if self.use_disabled_sites_checkbox.isChecked():
            command += " --use-disabled-sites"
        
        parse_url = self.parse_url_input.text()
        if parse_url:
            command += f" --parse {parse_url}"
        
        submit_url = self.submit_url_input.text()
        if submit_url:
            command += f" --submit {submit_url}"
        
        if self.self_check_checkbox.isChecked():
            command += " --self-check"
        
        # Output formats
        if self.csv_checkbox.isChecked():
            command += " --csv"
        if self.pdf_checkbox.isChecked():
            command += " --pdf"
        if self.txt_checkbox.isChecked():
            command += " --txt"
        if self.json_checkbox_simple.isChecked():
            command += " --json simple"
        if self.json_checkbox_ndjson.isChecked():
            command += " --json ndjson"
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
        
        # Also stop web interface if running
        if self.maigret_web_worker and self.maigret_web_worker.isRunning():
            self.stop_web_interface()
        
        self.run_button.setEnabled(True)
        self.stop_button.setEnabled(False)

    def append_output(self, text):
        self.output_area.append(text)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MaigretGUI()
    window.show()
    sys.exit(app.exec())