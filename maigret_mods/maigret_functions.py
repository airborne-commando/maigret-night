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

# Import from workers module
try:
    from .workers import CrowWorker, MaigretWorker, MaigretWebWorker, DashboardWorker
except ImportError:
    # Fallback for when running directly
    from workers import CrowWorker, MaigretWorker, MaigretWebWorker, DashboardWorker

# Remove the indentation from all function definitions

def run_crow_search(gui_instance):
    """Run the Crow (Blackbird) search"""
    # Clear output area
    gui_instance.output_area.clear()
    
    # Get username and email for AI analysis
    username = gui_instance.crow_username_input.text().strip()
    email = gui_instance.crow_email_input.text().strip()
    
    # Check if AI is enabled but no API key
    if gui_instance.crow_ai_checkbox.isChecked():
        if not gui_instance.check_crow_ai_api_key():
            return
    
    # Initialize TOR if enabled
    if gui_instance.crow_tor_checkbox.isChecked():
        try:
            from .tor_spoofing import TORSpoofer
        except ImportError:
            from tor_spoofing import TORSpoofer
            
        if not gui_instance.crow_tor_spoofer:
            gui_instance.crow_tor_spoofer = TORSpoofer(gui_instance)
        
        # Set TOR environment variables
        proxy_url = f"socks5://127.0.0.1:{gui_instance.crow_tor_spoofer.tor_port}"
        os.environ["HTTP_PROXY"] = proxy_url
        os.environ["HTTPS_PROXY"] = proxy_url
        os.environ["ALL_PROXY"] = proxy_url
        
        # Verify TOR is working
        if not gui_instance.verify_tor_connection():
            gui_instance.output_area.append("⚠️  TOR verification failed, but proceeding...")
    
    # ================================================================
    # BREACH.VIP USERNAME SEARCH HOOK
    # ================================================================
    if gui_instance.crow_breach_username_checkbox.isChecked() and username:
        gui_instance.output_area.append("\n" + "=" * 60)
        gui_instance.output_area.append("🔍 BREACH.VIP USERNAME SEARCH HOOK")
        gui_instance.output_area.append("=" * 60)
        
        if username.startswith("file:"):
            file_path = username[5:]
            if os.path.exists(file_path):
                gui_instance.output_area.append(f"Searching Breach.vip for usernames from file: {os.path.basename(file_path)}")
                try:
                    from .breach_vip_username import process_username_file
                except ImportError:
                    from breach_vip_username import process_username_file
                process_username_file(file_path, gui_instance.output_area)
            else:
                gui_instance.output_area.append(f"❌ File not found: {file_path}")
        else:
            usernames = [u.strip() for u in username.split(',') if u.strip()]
            if len(usernames) == 1:
                gui_instance.output_area.append(f"Searching Breach.vip for username: {usernames[0]}")
                try:
                    from .breach_vip_username import process_single_username
                except ImportError:
                    from breach_vip_username import process_single_username
                process_single_username(usernames[0], gui_instance.output_area)
            else:
                gui_instance.output_area.append(f"Searching Breach.vip for {len(usernames)} usernames")
                for username_item in usernames:
                    gui_instance.output_area.append(f"  • Processing: {username_item}")
                    try:
                        from .breach_vip_username import process_single_username
                    except ImportError:
                        from breach_vip_username import process_single_username
                    process_single_username(username_item, gui_instance.output_area)
        
        gui_instance.output_area.append("=" * 60 + "\n")

    # ================================================================
    # BREACH.VIP EMAIL SEARCH HOOK
    # ================================================================
    if gui_instance.crow_breach_email_checkbox.isChecked() and email:
        gui_instance.output_area.append("\n" + "=" * 60)
        gui_instance.output_area.append("📧 BREACH.VIP EMAIL SEARCH HOOK")
        gui_instance.output_area.append("=" * 60)
        
        if email.startswith("file:"):
            file_path = email[5:]
            if os.path.exists(file_path):
                gui_instance.output_area.append(f"Searching Breach.vip for emails from file: {os.path.basename(file_path)}")
                try:
                    from .breach_vip import process_email_file
                except ImportError:
                    from breach_vip import process_email_file
                process_email_file(file_path, gui_instance.output_area)
            else:
                gui_instance.output_area.append(f"❌ File not found: {file_path}")
        else:
            emails = [e.strip() for e in email.split(',') if e.strip()]
            if len(emails) == 1:
                gui_instance.output_area.append(f"Searching Breach.vip for email: {emails[0]}")
                try:
                    from .breach_vip import process_single_email
                except ImportError:
                    from breach_vip import process_single_email
                process_single_email(emails[0], gui_instance.output_area)
            else:
                gui_instance.output_area.append(f"Searching Breach.vip for {len(emails)} emails")
                for email_item in emails:
                    gui_instance.output_area.append(f"  • Processing: {email_item}")
                    try:
                        from .breach_vip import process_single_email
                    except ImportError:
                        from breach_vip import process_single_email
                    process_single_email(email_item, gui_instance.output_area)
        
        gui_instance.output_area.append("=" * 60 + "\n")
    
    # Build Blackbird command
    try:
        # Need to import build_blackbird_command
        try:
            from .command_builder import build_blackbird_command
        except ImportError:
            from command_builder import build_blackbird_command
        
        # Update the command building in run_crow_search method:
        command = build_blackbird_command(
            username_input=username,
            email_input=email,
            username_file_input="",
            email_file_input="",
            permute_checkbox=gui_instance.crow_permute_checkbox.isChecked(),
            permuteall_checkbox=gui_instance.crow_permuteall_checkbox.isChecked(),  # ADDED
            AI_checkbox=gui_instance.crow_ai_checkbox.isChecked(),
            no_nsfw_checkbox=gui_instance.crow_no_nsfw_checkbox.isChecked(),
            no_update_checkbox=gui_instance.crow_no_update_checkbox.isChecked(),  # ADDED
            csv_checkbox=gui_instance.crow_csv_checkbox.isChecked(),
            pdf_checkbox=gui_instance.crow_pdf_checkbox.isChecked(),
            json_checkbox=gui_instance.crow_json_checkbox.isChecked(),
            verbose_checkbox=gui_instance.crow_verbose_checkbox.isChecked(),
            dump_checkbox=gui_instance.crow_dump_checkbox.isChecked(),
            proxy_input="",
            timeout_spinbox=30,
            max_concurrent_requests=gui_instance.crow_max_concurrent_spinbox.value(),  # ADDED
            filter_input=gui_instance.crow_filter_input.text(),
            instagram_session_id=""
        )
        
        # Show AI info if enabled
        if gui_instance.crow_ai_checkbox.isChecked():
            gui_instance.output_area.append("🤖 AI Analysis Enabled")
            gui_instance.output_area.append("Note: AI analysis will be automatically saved to text file")
            gui_instance.output_area.append("")
        
        # Create and start the worker
        gui_instance.crow_worker = CrowWorker(
            " ".join(command), 
            needs_ai_confirmation=gui_instance.crow_ai_checkbox.isChecked(),
            is_setup_ai=False,
            tor_spoofer=gui_instance.crow_tor_spoofer if gui_instance.crow_tor_checkbox.isChecked() else None,
            username=username.split('file:')[0] if username.startswith('file:') else username,
            email=email.split('file:')[0] if email.startswith('file:') else email
        )
        gui_instance.crow_worker.output_signal.connect(gui_instance.update_crow_output)
        gui_instance.crow_worker.finished_signal.connect(gui_instance.on_crow_search_finished)
        gui_instance.crow_worker.ai_file_saved.connect(gui_instance.on_ai_file_saved)
        gui_instance.crow_worker.start()
        
        gui_instance.crow_run_btn.setEnabled(False)
        gui_instance.crow_stop_btn.setEnabled(True)
        
    except Exception as e:
        gui_instance.output_area.append(f"❌ Error building command: {e}")

def create_save_load_actions(gui_instance, layout):
    save_load_layout = QHBoxLayout()

    gui_instance.save_button = QPushButton("Save Maigret Settings")
    gui_instance.save_button.clicked.connect(gui_instance.save_settings_dialog)
    save_load_layout.addWidget(gui_instance.save_button)

    gui_instance.load_button = QPushButton("Load Maigret Settings")
    gui_instance.load_button.clicked.connect(gui_instance.load_settings_dialog)
    save_load_layout.addWidget(gui_instance.load_button)

    layout.addLayout(save_load_layout)

def save_settings_dialog(gui_instance):
    file_path, _ = QFileDialog.getSaveFileName(gui_instance, "Save Settings", "", "JSON Files (*.json)")
    
    if file_path:
        if not file_path.lower().endswith('.json'):
            file_path += '.json'
        save_settings(gui_instance, file_path)

def save_settings(gui_instance, file_path):
    # Parse multiple sites from text area
    sites_text = gui_instance.site_textedit.toPlainText()
    sites_list = []
    if sites_text:
        # Split by lines and filter out empty lines
        sites_list = [site.strip() for site in sites_text.split('\n') if site.strip()]
    
    settings = {
        'web_port': gui_instance.web_port_input.text() if gui_instance.web_port_input.text() else "5000",
        'username': gui_instance.username_input.text(),
        'timeout': gui_instance.timeout_spinbox.value(),
        'retries': gui_instance.retries_spinbox.value(),
        'max_connections': gui_instance.max_connections_spinbox.value(),
        'recursive_search': not gui_instance.no_recursion_checkbox.isChecked(),
        'info_extracting': not gui_instance.no_extracting_checkbox.isChecked(),
        'permute': gui_instance.permute_checkbox.isChecked(),
        'proxy_url': gui_instance.proxy_input.text() if gui_instance.proxy_input.text() else None,
        'tor_proxy_url': gui_instance.tor_proxy_input.text() if gui_instance.tor_proxy_input.text() else "socks5://127.0.0.1:9050",
        'i2p_proxy_url': gui_instance.i2p_proxy_input.text() if gui_instance.i2p_proxy_input.text() else None,
        'scan_all_sites': gui_instance.all_sites_checkbox.isChecked(),
        'top_sites_count': gui_instance.top_sites_input.value() if gui_instance.top_sites_checkbox.isChecked() else 500,
        'tags': gui_instance.tags_input.text(),
        'scan_sites_list': sites_list,
        'scan_disabled_sites': gui_instance.use_disabled_sites_checkbox.isChecked(),
        'parse_url': gui_instance.parse_url_input.text(),
        'submit_url': gui_instance.submit_url_input.text(),
        'self_check_enabled': gui_instance.self_check_checkbox.isChecked(),
        'print_not_found': gui_instance.print_not_found_checkbox.isChecked(),
        'print_check_errors': gui_instance.print_errors_checkbox.isChecked(),
        'report_sorting': gui_instance.report_sorting_combobox.currentText() if gui_instance.report_sorting_checkbox.isChecked() else "default",
        'csv_report': gui_instance.csv_checkbox.isChecked(),
        'pdf_report': gui_instance.pdf_checkbox.isChecked(),
        'txt_report': gui_instance.txt_checkbox.isChecked(),
        'json_report_simple': gui_instance.json_checkbox_simple.isChecked(),
        'json_report_ndjson': gui_instance.json_checkbox_ndjson.isChecked(),
        'graph_report': gui_instance.G_checkbox.isChecked(),
        'html_report': gui_instance.html_checkbox.isChecked(),
        'verbose': gui_instance.verbose_checkbox.isChecked(),
        'info': gui_instance.info_checkbox.isChecked(),
        'debug': gui_instance.debug_checkbox.isChecked(),
    }

    # Remove None values to match JSON structure
    settings = {k: v for k, v in settings.items() if v is not None}

    with open(file_path, 'w') as json_file:
        json.dump(settings, json_file, indent=4)

    gui_instance.output_area.append(f"Settings saved to {file_path}.")

def load_settings_dialog(gui_instance):
    file_path, _ = QFileDialog.getOpenFileName(gui_instance, "Load Settings", "", "JSON Files (*.json)")

    if file_path:
        load_settings(gui_instance, file_path)

def load_settings(gui_instance, file_path):
    try:
        with open(file_path, 'r') as json_file:
            settings = json.load(json_file)

        gui_instance.web_port_input.setText(settings.get('web_port', '5000'))
        gui_instance.username_input.setText(settings.get('username', ''))
        gui_instance.timeout_spinbox.setValue(settings.get('timeout', 30))
        gui_instance.retries_spinbox.setValue(settings.get('retries', 0))
        gui_instance.max_connections_spinbox.setValue(settings.get('max_connections', 100))
        gui_instance.no_recursion_checkbox.setChecked(not settings.get('recursive_search', True))
        gui_instance.no_extracting_checkbox.setChecked(not settings.get('info_extracting', True))
        gui_instance.permute_checkbox.setChecked(settings.get('permute', False))
        gui_instance.proxy_input.setText(settings.get('proxy_url', ''))
        gui_instance.tor_proxy_input.setText(settings.get('tor_proxy_url', 'socks5://127.0.0.1:9050'))
        gui_instance.i2p_proxy_input.setText(settings.get('i2p_proxy_url', ''))
        gui_instance.all_sites_checkbox.setChecked(settings.get('scan_all_sites', False))
        top_sites_count = settings.get('top_sites_count', 500)
        gui_instance.top_sites_checkbox.setChecked(top_sites_count != 500)
        gui_instance.top_sites_input.setValue(top_sites_count)
        gui_instance.tags_input.setText(settings.get('tags', ''))
        
        # Load multiple sites from list
        sites_list = settings.get('scan_sites_list', [])
        gui_instance.site_textedit.setPlainText('\n'.join(sites_list))
        
        gui_instance.use_disabled_sites_checkbox.setChecked(settings.get('scan_disabled_sites', False))
        gui_instance.parse_url_input.setText(settings.get('parse_url', ''))
        gui_instance.submit_url_input.setText(settings.get('submit_url', ''))
        gui_instance.self_check_checkbox.setChecked(settings.get('self_check_enabled', False))
        gui_instance.print_not_found_checkbox.setChecked(settings.get('print_not_found', False))
        gui_instance.print_errors_checkbox.setChecked(settings.get('print_check_errors', False))
        report_sorting = settings.get('report_sorting', 'default')
        gui_instance.report_sorting_checkbox.setChecked(report_sorting != 'default')
        gui_instance.report_sorting_combobox.setCurrentText(report_sorting)
        gui_instance.csv_checkbox.setChecked(settings.get('csv_report', False))
        gui_instance.pdf_checkbox.setChecked(settings.get('pdf_report', False))
        gui_instance.txt_checkbox.setChecked(settings.get('txt_report', False))
        gui_instance.json_checkbox_simple.setChecked(settings.get('json_report_simple', False))
        gui_instance.json_checkbox_ndjson.setChecked(settings.get('json_report_ndjson', False))
        gui_instance.G_checkbox.setChecked(settings.get('graph_report', False))
        gui_instance.html_checkbox.setChecked(settings.get('html_report', False))
        gui_instance.verbose_checkbox.setChecked(settings.get('verbose', False))
        gui_instance.info_checkbox.setChecked(settings.get('info', False))
        gui_instance.debug_checkbox.setChecked(settings.get('debug', False))

        gui_instance.output_area.append(f"Settings loaded from {file_path}.")
    except FileNotFoundError:
        gui_instance.output_area.append("No settings file found.")
    except json.JSONDecodeError:
        gui_instance.output_area.append("Error decoding settings file.")

def create_options_tab(gui_instance, tab_widget):
    options_group = QWidget()
    options_layout = QVBoxLayout()

    # Username input
    username_layout = QHBoxLayout()
    gui_instance.username_input = QLineEdit()
    username_layout.addWidget(QLabel("Username:"))
    username_layout.addWidget(gui_instance.username_input)
    options_layout.addLayout(username_layout)

    # Timeout input
    timeout_layout = QHBoxLayout()
    timeout_layout.addWidget(QLabel("Timeout (seconds):"))
    gui_instance.timeout_spinbox = QSpinBox()
    gui_instance.timeout_spinbox.setRange(15, 300)
    gui_instance.timeout_spinbox.setValue(30)
    timeout_layout.addWidget(gui_instance.timeout_spinbox)
    options_layout.addLayout(timeout_layout)

    # Retries input
    retries_layout = QHBoxLayout()
    retries_layout.addWidget(QLabel("Retries:"))
    gui_instance.retries_spinbox = QSpinBox()
    gui_instance.retries_spinbox.setRange(0, 10)
    gui_instance.retries_spinbox.setValue(0)
    retries_layout.addWidget(gui_instance.retries_spinbox)
    options_layout.addLayout(retries_layout)

    # Max connections input
    max_connections_layout = QHBoxLayout()
    max_connections_layout.addWidget(QLabel("Max Connections:"))
    gui_instance.max_connections_spinbox = QSpinBox()
    gui_instance.max_connections_spinbox.setRange(1, 200)
    gui_instance.max_connections_spinbox.setValue(100)
    max_connections_layout.addWidget(gui_instance.max_connections_spinbox)
    options_layout.addLayout(max_connections_layout)

    # Checkboxes row 1
    checkbox_layout_1 = QHBoxLayout()
    gui_instance.no_recursion_checkbox = QCheckBox("No Recursion")
    checkbox_layout_1.addWidget(gui_instance.no_recursion_checkbox)
    gui_instance.no_extracting_checkbox = QCheckBox("No Extracting")
    checkbox_layout_1.addWidget(gui_instance.no_extracting_checkbox)
    gui_instance.permute_checkbox = QCheckBox("Permute")
    checkbox_layout_1.addWidget(gui_instance.permute_checkbox)
    gui_instance.all_sites_checkbox = QCheckBox("All Sites")
    checkbox_layout_1.addWidget(gui_instance.all_sites_checkbox)
    options_layout.addLayout(checkbox_layout_1)

    # Checkboxes row 2
    checkbox_layout_2 = QHBoxLayout()
    gui_instance.self_check_checkbox = QCheckBox("Self Check")
    checkbox_layout_2.addWidget(gui_instance.self_check_checkbox)
    gui_instance.use_disabled_sites_checkbox = QCheckBox("Use Disabled Sites")
    checkbox_layout_2.addWidget(gui_instance.use_disabled_sites_checkbox)
    gui_instance.report_sorting_checkbox = QCheckBox("Enable Report Sorting")
    checkbox_layout_2.addWidget(gui_instance.report_sorting_checkbox)
    options_layout.addLayout(checkbox_layout_2)

    # Report Sorting
    gui_instance.report_sorting_combobox = QComboBox()
    gui_instance.report_sorting_combobox.addItems(["default", "data"])
    gui_instance.report_sorting_combobox.setEnabled(False)
    options_layout.addWidget(QLabel("Report Sorting:"))
    options_layout.addWidget(gui_instance.report_sorting_combobox)
    gui_instance.report_sorting_checkbox.toggled.connect(gui_instance.toggle_report_sorting_input)

    # Top Sites
    top_sites_layout = QHBoxLayout()
    gui_instance.top_sites_checkbox = QCheckBox("Top Sites Count:")
    gui_instance.top_sites_checkbox.toggled.connect(gui_instance.toggle_top_sites_input)
    top_sites_layout.addWidget(gui_instance.top_sites_checkbox)
    gui_instance.top_sites_input = QSpinBox()
    gui_instance.top_sites_input.setRange(1, 1000)
    gui_instance.top_sites_input.setValue(500)
    gui_instance.top_sites_input.setEnabled(False)
    top_sites_layout.addWidget(gui_instance.top_sites_input)
    options_layout.addLayout(top_sites_layout)

    # Proxy settings
    proxy_layout = QHBoxLayout()
    
    proxy_widget = QWidget()
    proxy_sub_layout = QVBoxLayout()
    proxy_sub_layout.addWidget(QLabel("Proxy URL:"))
    gui_instance.proxy_input = QLineEdit()
    gui_instance.proxy_input.setPlaceholderText("e.g., socks5://127.0.0.1:1080")
    proxy_sub_layout.addWidget(gui_instance.proxy_input)
    proxy_widget.setLayout(proxy_sub_layout)
    proxy_layout.addWidget(proxy_widget)

    tor_proxy_widget = QWidget()
    tor_proxy_sub_layout = QVBoxLayout()
    tor_proxy_sub_layout.addWidget(QLabel("Tor Proxy:"))
    gui_instance.tor_proxy_input = QLineEdit()
    gui_instance.tor_proxy_input.setText("socks5://127.0.0.1:9050")
    tor_proxy_sub_layout.addWidget(gui_instance.tor_proxy_input)
    tor_proxy_widget.setLayout(tor_proxy_sub_layout)
    proxy_layout.addWidget(tor_proxy_widget)

    i2p_proxy_widget = QWidget()
    i2p_proxy_sub_layout = QVBoxLayout()
    i2p_proxy_sub_layout.addWidget(QLabel("I2P Proxy:"))
    gui_instance.i2p_proxy_input = QLineEdit()
    gui_instance.i2p_proxy_input.setPlaceholderText("http://127.0.0.1:4444")
    i2p_proxy_sub_layout.addWidget(gui_instance.i2p_proxy_input)
    i2p_proxy_widget.setLayout(i2p_proxy_sub_layout)
    proxy_layout.addWidget(i2p_proxy_widget)

    options_layout.addLayout(proxy_layout)

    # Tags input
    tags_layout = QHBoxLayout()
    tags_layout.addWidget(QLabel("Tags (comma-separated):"))
    gui_instance.tags_input = QLineEdit()
    tags_layout.addWidget(gui_instance.tags_input)
    options_layout.addLayout(tags_layout)

    # Sites section with text area and load button
    sites_section_widget = QWidget()
    sites_section_layout = QVBoxLayout()
    
    sites_label_layout = QHBoxLayout()
    sites_label_layout.addWidget(QLabel("Sites (one per line, each as separate --site parameter):"))
    
    # Add Load Sites File button
    gui_instance.load_sites_button = QPushButton("Load Sites from File")
    gui_instance.load_sites_button.clicked.connect(gui_instance.load_sites_from_file)
    sites_label_layout.addWidget(gui_instance.load_sites_button)
    
    sites_section_layout.addLayout(sites_label_layout)
    
    gui_instance.site_textedit = QTextEdit()
    gui_instance.site_textedit.setMaximumHeight(100)
    gui_instance.site_textedit.setPlaceholderText("Enter site URLs, one per line\nExample:\ntwitter.com\ngithub.com\ninstagram.com\n\nOr use the 'Load Sites from File' button to load from a text file.")
    sites_section_layout.addWidget(gui_instance.site_textedit)
    
    sites_section_widget.setLayout(sites_section_layout)
    options_layout.addWidget(sites_section_widget)

    # Parse and Submit URLs
    parse_layout = QHBoxLayout()
    parse_layout.addWidget(QLabel("Parse URL:"))
    gui_instance.parse_url_input = QLineEdit()
    parse_layout.addWidget(gui_instance.parse_url_input)
    options_layout.addLayout(parse_layout)

    submit_layout = QHBoxLayout()
    submit_layout.addWidget(QLabel("Submit URL:"))
    gui_instance.submit_url_input = QLineEdit()
    submit_layout.addWidget(gui_instance.submit_url_input)
    options_layout.addLayout(submit_layout)

    # Output formats row
    format_layout = QHBoxLayout()
    format_layout.addWidget(QLabel("Output Formats:"))
    gui_instance.csv_checkbox = QCheckBox("CSV")
    format_layout.addWidget(gui_instance.csv_checkbox)
    gui_instance.pdf_checkbox = QCheckBox("PDF")
    format_layout.addWidget(gui_instance.pdf_checkbox)
    gui_instance.txt_checkbox = QCheckBox("TXT")
    format_layout.addWidget(gui_instance.txt_checkbox)
    gui_instance.json_checkbox_simple = QCheckBox("JSON Simple")
    format_layout.addWidget(gui_instance.json_checkbox_simple)
    gui_instance.json_checkbox_ndjson = QCheckBox("JSON ndjson")
    format_layout.addWidget(gui_instance.json_checkbox_ndjson)
    gui_instance.G_checkbox = QCheckBox("Graph")
    format_layout.addWidget(gui_instance.G_checkbox)
    gui_instance.html_checkbox = QCheckBox("HTML")
    format_layout.addWidget(gui_instance.html_checkbox)
    options_layout.addLayout(format_layout)

    # Verbosity row
    verbosity_layout = QHBoxLayout()
    verbosity_layout.addWidget(QLabel("Verbosity:"))
    gui_instance.print_not_found_checkbox = QCheckBox("Print Not Found")
    verbosity_layout.addWidget(gui_instance.print_not_found_checkbox)
    gui_instance.print_errors_checkbox = QCheckBox("Print Errors")
    verbosity_layout.addWidget(gui_instance.print_errors_checkbox)
    gui_instance.verbose_checkbox = QCheckBox("Verbose")
    verbosity_layout.addWidget(gui_instance.verbose_checkbox)
    gui_instance.info_checkbox = QCheckBox("Info")
    verbosity_layout.addWidget(gui_instance.info_checkbox)
    gui_instance.debug_checkbox = QCheckBox("Debug")
    verbosity_layout.addWidget(gui_instance.debug_checkbox)
    options_layout.addLayout(verbosity_layout)

    options_group.setLayout(options_layout)
    tab_widget.addTab(options_group, "Options")

def load_sites_from_file(gui_instance):
    """Load sites from a text file, one per line"""
    file_path, _ = QFileDialog.getOpenFileName(
        gui_instance, 
        "Load Sites from File", 
        "", 
        "Text Files (*.txt);;All Files (*.*)"
    )
    
    if file_path:
        try:
            with open(file_path, 'r') as file:
                sites_content = file.read()
            
            # Set the content to the text edit
            gui_instance.site_textedit.setPlainText(sites_content)
            gui_instance.output_area.append(f"Loaded sites from {file_path}")
            
            # Count and display number of sites
            sites_list = [site.strip() for site in sites_content.split('\n') if site.strip()]
            gui_instance.output_area.append(f"Found {len(sites_list)} site(s) in the file.")
            
        except Exception as e:
            gui_instance.output_area.append(f"Error loading sites file: {str(e)}")
            QMessageBox.critical(gui_instance, "Error", f"Failed to load sites file:\n{str(e)}")

def toggle_top_sites_input(gui_instance):
    gui_instance.top_sites_input.setEnabled(gui_instance.top_sites_checkbox.isChecked())

def toggle_report_sorting_input(gui_instance):
    gui_instance.report_sorting_combobox.setEnabled(gui_instance.report_sorting_checkbox.isChecked())

def create_buttons(gui_instance, layout):
    button_layout = QHBoxLayout()
    
    # Existing buttons...
    gui_instance.run_button = QPushButton("Run Maigret")
    gui_instance.run_button.clicked.connect(gui_instance.run_maigret)
    button_layout.addWidget(gui_instance.run_button)
    
    gui_instance.stop_button = QPushButton("Stop Maigret")
    gui_instance.stop_button.clicked.connect(gui_instance.stop_maigret)
    gui_instance.stop_button.setEnabled(False)
    button_layout.addWidget(gui_instance.stop_button)
    
    # Add web interface button
    gui_instance.web_button = QPushButton("Start Web Interface")
    gui_instance.web_button.clicked.connect(gui_instance.toggle_web_interface)
    button_layout.addWidget(gui_instance.web_button)
    
    # Add Dashboard button
    gui_instance.dashboard_button = QPushButton("Generate Dashboard")
    gui_instance.dashboard_button.clicked.connect(gui_instance.generate_dashboard)
    button_layout.addWidget(gui_instance.dashboard_button)
    
    # Add port input for web interface
    web_port_layout = QHBoxLayout()
    web_port_layout.addWidget(QLabel("Web Port:"))
    gui_instance.web_port_input = QLineEdit()
    gui_instance.web_port_input.setPlaceholderText("5000")
    gui_instance.web_port_input.setMaximumWidth(80)
    web_port_layout.addWidget(gui_instance.web_port_input)
    button_layout.addLayout(web_port_layout)
    
    layout.addLayout(button_layout)

    gui_instance.output_area = QTextEdit()
    gui_instance.output_area.setReadOnly(True)
    layout.addWidget(gui_instance.output_area)

def generate_dashboard(gui_instance):
    """Generate and display the data dashboard"""
    # Check if there are any reports to display
    reports_dir = "reports"
    results_dir = "results"
    
    if not os.path.exists(reports_dir) and not os.path.exists(results_dir):
        reply = QMessageBox.question(
            gui_instance, 
            "No Reports Found", 
            "No reports or results directories found. Generate empty dashboard?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.No:
            return
    
    # Ask if user wants to open in browser
    open_browser = QMessageBox.question(
        gui_instance,
        "Open Dashboard?",
        "Generate dashboard and open in browser?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.Yes
    )
    
    open_browser = (open_browser == QMessageBox.StandardButton.Yes)
    
    # Create and start dashboard worker
    try:
        from .workers import DashboardWorker
    except ImportError:
        from workers import DashboardWorker
        
    gui_instance.dashboard_worker = DashboardWorker(open_browser=open_browser)
    gui_instance.dashboard_worker.output_signal.connect(gui_instance.append_output)
    gui_instance.dashboard_worker.finished_signal.connect(gui_instance.on_dashboard_finished)
    gui_instance.dashboard_worker.start()
    
    # Disable button while generating
    gui_instance.dashboard_button.setEnabled(False)

def on_dashboard_finished(gui_instance, success, message):
    """Called when dashboard generation finishes"""
    gui_instance.dashboard_button.setEnabled(True)
    
    if success:
        gui_instance.output_area.append(f"✅ {message}")
    else:
        gui_instance.output_area.append(f"❌ {message}")
        QMessageBox.warning(gui_instance, "Dashboard Error", message)

def toggle_web_interface(gui_instance):
    """Toggle the Maigret web interface on/off"""
    if gui_instance.maigret_web_worker and gui_instance.maigret_web_worker.isRunning():
        # Stop web interface
        stop_web_interface(gui_instance)
        gui_instance.run_button.setEnabled(True)
    else:
        # TERMINATE EXISTING MAIGRET WORKER IF RUNNING
        if gui_instance.maigret_worker and gui_instance.maigret_worker.isRunning():
            gui_instance.output_area.append("⚠️  Stopping existing Maigret search to start web interface...")
            gui_instance.maigret_worker.terminate()
            gui_instance.maigret_worker = None
            # Also update button states
            gui_instance.run_button.setEnabled(False)  # Keep run disabled
            gui_instance.stop_button.setEnabled(False)  # Disable stop button
        
        # TERMINATE EXISTING CROW WORKER IF RUNNING
        if gui_instance.crow_worker and gui_instance.crow_worker.isRunning():
            gui_instance.output_area.append("⚠️  Stopping existing Crow search to start web interface...")
            gui_instance.crow_worker.terminate()
            gui_instance.crow_worker = None
            # Also update Crow button states
            gui_instance.crow_run_btn.setEnabled(True)  # Re-enable Crow run
            gui_instance.crow_stop_btn.setEnabled(False)  # Disable Crow stop
        
        # Start web interface
        start_web_interface(gui_instance)
        gui_instance.run_button.setEnabled(False)  # Disable run button since web is running

def start_web_interface(gui_instance):
    """Start the Maigret web interface"""
    port = gui_instance.web_port_input.text().strip()
    if not port:
        port = "5000"
    
    # Validate port number
    try:
        port_int = int(port)
        if not (1 <= port_int <= 65535):
            raise ValueError("Port must be between 1 and 65535")
    except ValueError as e:
        gui_instance.output_area.append(f"Invalid port number: {e}")
        QMessageBox.warning(gui_instance, "Invalid Port", f"Please enter a valid port number (1-65535).\nError: {e}")
        return
    
    gui_instance.output_area.append(f"Starting Maigret web interface on port {port}...")
    gui_instance.output_area.append(f"Access at: http://localhost:{port}")
    
    try:
        from .workers import MaigretWebWorker
    except ImportError:
        from workers import MaigretWebWorker
        
    gui_instance.maigret_web_worker = MaigretWebWorker(port)
    gui_instance.maigret_web_worker.output_signal.connect(gui_instance.append_web_output)
    gui_instance.maigret_web_worker.finished_signal.connect(gui_instance.on_web_interface_finished)
    gui_instance.maigret_web_worker.start()
    
    gui_instance.web_button.setText("Stop Web Interface")
    gui_instance.web_port_input.setEnabled(False)
    
    # Open browser option (optional)
    open_browser = QMessageBox.question(
        gui_instance,
        "Open Browser?",
        "Would you like to open the web interface in your default browser?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.Yes
    )
    
    if open_browser == QMessageBox.StandardButton.Yes:
        import webbrowser
        webbrowser.open(f"http://localhost:{port}")

def stop_web_interface(gui_instance):
    """Stop the Maigret web interface"""
    if gui_instance.maigret_web_worker:
        gui_instance.output_area.append("Stopping Maigret web interface...")
        gui_instance.maigret_web_worker.terminate()
        gui_instance.maigret_web_worker = None
        gui_instance.web_button.setText("Start Web Interface")
        gui_instance.web_port_input.setEnabled(True)
        gui_instance.output_area.append("Web interface stopped.")
        
        # RE-ENABLE THE RUN BUTTON WHEN WEB INTERFACE STOPS
        gui_instance.run_button.setEnabled(True)

def on_web_interface_finished(gui_instance):
    """Called when web interface process finishes"""
    gui_instance.web_button.setText("Start Web Interface")
    gui_instance.web_port_input.setEnabled(True)
    gui_instance.output_area.append("Web interface process finished.")

def append_web_output(gui_instance, text):
    """Append web interface output to the text area"""
    gui_instance.output_area.append(f"[Web Interface] {text}")

def run_maigret(gui_instance):
    """Run the Maigret search"""
    
    # STOP WEB INTERFACE IF RUNNING
    if gui_instance.maigret_web_worker and gui_instance.maigret_web_worker.isRunning():
        gui_instance.output_area.append("⚠️  Stopping web interface to run Maigret search...")
        stop_web_interface(gui_instance)
    
    # STOP CROW WORKER IF RUNNING
    if gui_instance.crow_worker and gui_instance.crow_worker.isRunning():
        gui_instance.output_area.append("⚠️  Stopping Crow search to run Maigret...")
        gui_instance.stop_crow_search()
    
    gui_instance.output_area.clear()

    command = f"maigret {gui_instance.username_input.text()}"

    command += f" --timeout {gui_instance.timeout_spinbox.value()}"
    command += f" --retries {gui_instance.retries_spinbox.value()}"
    command += f" --max-connections {gui_instance.max_connections_spinbox.value()}"
 
    if gui_instance.no_recursion_checkbox.isChecked():
        command += " --no-recursion"
    if gui_instance.no_extracting_checkbox.isChecked():
        command += " --no-extracting"
    if gui_instance.permute_checkbox.isChecked():
        command += " --permute"
    
    proxy = gui_instance.proxy_input.text()
    if proxy:
        command += f" --proxy {proxy}"
    
    tor_proxy = gui_instance.tor_proxy_input.text()
    if tor_proxy and tor_proxy != "socks5://127.0.0.1:9050":
        command += f" --tor-proxy {tor_proxy}"
    
    i2p_proxy = gui_instance.i2p_proxy_input.text()
    if i2p_proxy:
        command += f" --i2p-proxy {i2p_proxy}"
    
    if gui_instance.all_sites_checkbox.isChecked():
        command += " --all-sites"
    
    if gui_instance.top_sites_checkbox.isChecked():
        command += f" --top-sites {gui_instance.top_sites_input.value()}"
    
    tags = gui_instance.tags_input.text()
    if tags:
        command += f" --tags {tags}"
    
    # Handle multiple sites as separate --site parameters
    sites_text = gui_instance.site_textedit.toPlainText()
    if sites_text:
        # Split by lines and filter out empty lines
        sites_list = [site.strip() for site in sites_text.split('\n') if site.strip()]
        if sites_list:
            # Add each site as a separate --site parameter
            for site in sites_list:
                command += f" --site {site}"
            gui_instance.output_area.append(f"Using {len(sites_list)} site(s): {', '.join(sites_list)}")
    
    if gui_instance.use_disabled_sites_checkbox.isChecked():
        command += " --use-disabled-sites"
    
    parse_url = gui_instance.parse_url_input.text()
    if parse_url:
        command += f" --parse {parse_url}"
    
    submit_url = gui_instance.submit_url_input.text()
    if submit_url:
        command += f" --submit {submit_url}"
    
    if gui_instance.self_check_checkbox.isChecked():
        command += " --self-check"
    
    # Output formats
    if gui_instance.csv_checkbox.isChecked():
        command += " --csv"
    if gui_instance.pdf_checkbox.isChecked():
        command += " --pdf"
    if gui_instance.txt_checkbox.isChecked():
        command += " --txt"
    if gui_instance.json_checkbox_simple.isChecked():
        command += " --json simple"
    if gui_instance.json_checkbox_ndjson.isChecked():
        command += " --json ndjson"
    if gui_instance.G_checkbox.isChecked():
        command += " --graph"
    if gui_instance.html_checkbox.isChecked():
        command += " --html"
    
    if gui_instance.report_sorting_checkbox.isChecked():
        command += f" --reports-sorting {gui_instance.report_sorting_combobox.currentText()}"
    
    if gui_instance.print_not_found_checkbox.isChecked():
        command += " --print-not-found"
    if gui_instance.print_errors_checkbox.isChecked():
        command += " --print-errors"
    if gui_instance.verbose_checkbox.isChecked():
        command += " --verbose"
    if gui_instance.info_checkbox.isChecked():
        command += " --info"
    if gui_instance.debug_checkbox.isChecked():
        command += " --debug"
    
    gui_instance.output_area.append(f"Running command: {command}")

    if gui_instance.self_check_checkbox.isChecked():
        # Prepend with echo 'y' | to auto-respond
        command = f"echo 'y' | {command}"
    
    gui_instance.maigret_worker = MaigretWorker(command)
    gui_instance.maigret_worker.output_signal.connect(gui_instance.append_output)
    gui_instance.maigret_worker.finished_signal.connect(gui_instance.on_maigret_finished)
    gui_instance.maigret_worker.start()

    gui_instance.run_button.setEnabled(False)
    gui_instance.stop_button.setEnabled(True)

def on_maigret_finished(gui_instance):
    gui_instance.stop_button.setEnabled(False)
    gui_instance.run_button.setEnabled(True)

def stop_maigret(gui_instance):
    if gui_instance.maigret_worker:
        gui_instance.maigret_worker.terminate()
        gui_instance.maigret_worker = None
        gui_instance.output_area.append("Maigret process terminated.")
    
    # Also stop web interface if running
    if gui_instance.maigret_web_worker and gui_instance.maigret_web_worker.isRunning():
        stop_web_interface(gui_instance)
    
    gui_instance.run_button.setEnabled(True)
    gui_instance.stop_button.setEnabled(False)

def append_output(gui_instance, text):
    gui_instance.output_area.append(text)