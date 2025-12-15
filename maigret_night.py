import sys
import subprocess
import json
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QLineEdit, QPushButton, QTextEdit, QCheckBox, 
                             QGroupBox, QFormLayout, QSpinBox, QComboBox, QTabWidget, QToolButton,QFileDialog, QMessageBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

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

# Main GUI class for the Maigret OSINT tool
class MaigretGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Maigret Night")
        self.setGeometry(100, 100, 1000, 600)  # Reduced window size
        self.worker = None

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        tab_widget = QTabWidget()
        layout.addWidget(tab_widget)

        # Create tabs for different sections
        self.create_options_tab(tab_widget)
        # self.create_proxy_tab(tab_widget)
        # self.create_output_tab(tab_widget)

        # Buttons and output area
        self.create_buttons(layout)

        # Add Save and Load actions
        self.create_save_load_actions(layout)

    def create_save_load_actions(self, layout):
        save_load_layout = QHBoxLayout()

        self.save_button = QPushButton("Save Settings")
        self.save_button.clicked.connect(self.save_settings_dialog)
        save_load_layout.addWidget(self.save_button)

        self.load_button = QPushButton("Load Settings")
        self.load_button.clicked.connect(self.load_settings_dialog)
        save_load_layout.addWidget(self.load_button)

        layout.addLayout(save_load_layout)

    def save_settings_dialog(self):
        # Open a save file dialog
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Settings", "", "JSON Files (*.json)")
        
        if file_path:
            # Ensure the file has a .json extension
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
        # Open a file dialog to load settings
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
        self.retries_spinbox.setValue(0)  # Default retries is 3
        retries_layout.addWidget(self.retries_spinbox)
        options_layout.addLayout(retries_layout)

        # Max connections input
        max_connections_layout = QHBoxLayout()
        max_connections_layout.addWidget(QLabel("Max Connections:"))
        self.max_connections_spinbox = QSpinBox()
        self.max_connections_spinbox.setRange(1, 50) # Max connections, up to 50
        self.max_connections_spinbox.setValue(10)  # Default max connections is 10 now
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

        # Report Sorting input (only enabled if checkbox is checked)
        self.report_sorting_combobox = QComboBox()
        self.report_sorting_combobox.addItems(["default", "data"])
        self.report_sorting_combobox.setEnabled(False)  # Disable initially
        options_layout.addWidget(QLabel("Report Sort:"))
        options_layout.addWidget(self.report_sorting_combobox)

        # Enable/Disable report sorting input based on checkbox state
        self.report_sorting_checkbox.toggled.connect(self.toggle_report_sorting_input)

        # Add Top Sites checkbox
        self.top_sites_checkbox = QCheckBox("Enable Top Sites")
        options_layout.addWidget(self.top_sites_checkbox)

        # Top sites input (only enabled if Top Sites checkbox is checked)
        self.top_sites_input = QSpinBox()
        self.top_sites_input.setRange(1, 100)
        self.top_sites_input.setValue(10)  # Default to 10 top sites
        self.top_sites_input.setEnabled(False)  # Disable initially
        options_layout.addWidget(QLabel("Top Sites Count:"))
        options_layout.addWidget(self.top_sites_input)

        # Enable/Disable top sites count input based on checkbox state
        self.top_sites_checkbox.toggled.connect(self.toggle_top_sites_input)

        # Create a horizontal layout for Tags and Proxy inputs
        proxy_layout_horizontal = QHBoxLayout()

        # Tags input (first column)
        tags_widget = QWidget()
        tags_sub_layout = QVBoxLayout()
        tags_sub_layout.addWidget(QLabel("Tags (comma-separated):"))
        self.tags_input = QLineEdit()
        tags_sub_layout.addWidget(self.tags_input)
        tags_widget.setLayout(tags_sub_layout)
        proxy_layout_horizontal.addWidget(tags_widget)

        # Proxy URL input (second column)
        proxy_widget = QWidget()
        proxy_sub_layout = QVBoxLayout()
        proxy_sub_layout.addWidget(QLabel("Proxy URL:"))
        self.proxy_input = QLineEdit()
        self.proxy_input.setPlaceholderText("e.g., socks5://127.0.0.1:1080")
        proxy_sub_layout.addWidget(self.proxy_input)
        proxy_widget.setLayout(proxy_sub_layout)
        proxy_layout_horizontal.addWidget(proxy_widget)

        # Tor Proxy input (third column)
        tor_proxy_widget = QWidget()
        tor_proxy_sub_layout = QVBoxLayout()
        tor_proxy_sub_layout.addWidget(QLabel("Tor Proxy URL:"))
        self.tor_proxy_input = QLineEdit()
        tor_proxy_sub_layout.addWidget(self.tor_proxy_input)
        tor_proxy_widget.setLayout(tor_proxy_sub_layout)
        proxy_layout_horizontal.addWidget(tor_proxy_widget)

        # I2P Proxy input (fourth column)
        i2p_proxy_widget = QWidget()
        i2p_proxy_sub_layout = QVBoxLayout()
        i2p_proxy_sub_layout.addWidget(QLabel("I2P Proxy URL:"))
        self.i2p_proxy_input = QLineEdit()
        i2p_proxy_sub_layout.addWidget(self.i2p_proxy_input)
        i2p_proxy_widget.setLayout(i2p_proxy_sub_layout)
        proxy_layout_horizontal.addWidget(i2p_proxy_widget)

        # Add the horizontal layout to the main options layout
        options_layout.addLayout(proxy_layout_horizontal)

        # Site input (below them)
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

        self.html_checkbox = QCheckBox("HTML")
        additional_checkbox_layout.addWidget(self.html_checkbox)

        # Add the horizontal layout of additional checkboxes to the main layout
        options_layout.addLayout(additional_checkbox_layout)

        options_group.setLayout(options_layout)
        tab_widget.addTab(options_group, "Options")

    def toggle_top_sites_input(self):
        # Enable or disable the top sites input based on checkbox
        self.top_sites_input.setEnabled(self.top_sites_checkbox.isChecked())

    def toggle_report_sorting_input(self):
        # Enable or disable the report sorting input based on checkbox
        self.report_sorting_combobox.setEnabled(self.report_sorting_checkbox.isChecked())

    # def create_proxy_tab(self, tab_widget):
    #     proxy_group = QWidget()
    #     proxy_layout = QVBoxLayout()

    #     self.proxy_input = QLineEdit()
    #     proxy_layout.addWidget(QLabel("Proxy URL (e.g., socks5://127.0.0.1:1080):"))
    #     proxy_layout.addWidget(self.proxy_input)

    #     self.tor_proxy_input = QLineEdit()
    #     proxy_layout.addWidget(QLabel("Tor Proxy URL:"))
    #     proxy_layout.addWidget(self.tor_proxy_input)

    #     self.i2p_proxy_input = QLineEdit()
    #     proxy_layout.addWidget(QLabel("I2P Proxy URL:"))
    #     proxy_layout.addWidget(self.i2p_proxy_input)

    #     proxy_group.setLayout(proxy_layout)
    #     tab_widget.addTab(proxy_group, "Proxy")

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
        # Clear the output area before starting a new search
        self.output_area.clear()

        # Construct the command for running Maigret
        command = f"maigret {self.username_input.text()}"

        # Add additional flags for settings
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
        
        # Add more specific URLs
        if self.parse_url_input.text():
            command += f" --parse {self.parse_url_input.text()}"
        if self.submit_url_input.text():
            command += f" --submit {self.submit_url_input.text()}"
        if self.self_check_checkbox.isChecked():
            command += " --self-check"
        if self.stats_checkbox.isChecked():
            command += " --stats"
        
        # Output file options
        if self.csv_checkbox.isChecked():
            command += " --csv"
        if self.pdf_checkbox.isChecked():
            command += " --pdf"
        if self.txt_checkbox.isChecked():
            command += " --txt"
        if self.html_checkbox.isChecked():
            command += " --html"
        
        # Add report sorting if checkbox is checked
        if self.report_sorting_checkbox.isChecked():
            command += f" --reports-sorting {self.report_sorting_combobox.currentText()}"

        # New flags for the additional options
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

        # Run the Maigret command in a separate thread
        self.worker = MaigretWorker(command)
        self.worker.output_signal.connect(self.append_output)
        self.worker.finished_signal.connect(self.on_maigret_finished)  # Connect to the finished signal
        self.worker.start()

        self.run_button.setEnabled(False)
        self.stop_button.setEnabled(True)

    def on_maigret_finished(self):
        # Disable the stop button when Maigret finishes
        self.stop_button.setEnabled(False)
        self.run_button.setEnabled(True)  # Re-enable the run button

    def stop_maigret(self):
        if self.worker:
            self.worker.terminate()
            self.worker = None
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
