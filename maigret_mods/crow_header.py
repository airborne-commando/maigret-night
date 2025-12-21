# crow_header.py
# ================================================================
# CROW (Blackbird Integration) Section - MODULAR VERSION
# ================================================================

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QLineEdit, QPushButton, QCheckBox, QGroupBox, 
                            QFileDialog, QSpinBox, QGridLayout, QScrollArea, 
                            QFrame, QSizePolicy)  # Added QScrollArea, QFrame, QSizePolicy
from PyQt6.QtCore import Qt

def create_crow_tab(tab_widget, parent):
    """Create the Crow tab modularly"""
    crow_group = QWidget()
    crow_layout = QVBoxLayout()

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
    parent.crow_username_input = QLineEdit()
    parent.crow_username_input.setPlaceholderText("Enter username(s) or 'file:path/to/file.txt'")
    username_layout.addWidget(parent.crow_username_input)

    # Username file button
    username_file_btn = QPushButton("📁")
    username_file_btn.setToolTip("Select username file")
    username_file_btn.clicked.connect(parent.select_crow_username_file)
    username_file_btn.setFixedWidth(40)
    username_layout.addWidget(username_file_btn)
    parent.crow_breach_username_checkbox = QCheckBox("Search usernames on Breach.vip")
    username_layout.addWidget(parent.crow_breach_username_checkbox)

    input_layout.addLayout(username_layout)

    # Email input
    email_layout = QHBoxLayout()
    email_layout.addWidget(QLabel("Email(s):"))
    parent.crow_email_input = QLineEdit()
    parent.crow_email_input.setPlaceholderText("Enter email(s) or 'file:path/to/file.txt'")
    email_layout.addWidget(parent.crow_email_input)

    # Email file button
    email_file_btn = QPushButton("📁")
    email_file_btn.setToolTip("Select email file")
    email_file_btn.clicked.connect(parent.select_crow_email_file)
    email_file_btn.setFixedWidth(40)
    email_layout.addWidget(email_file_btn)
    parent.crow_breach_email_checkbox = QCheckBox("Search emails on Breach.vip")
    email_layout.addWidget(parent.crow_breach_email_checkbox)

    input_layout.addLayout(email_layout)

    input_group.setLayout(input_layout)
    crow_layout.addWidget(input_group)

    crow_layout.addSpacing(10)

    # Options section
    options_group = QGroupBox("Options")
    options_layout = QVBoxLayout()

    # AI Analysis
    ai_layout = QHBoxLayout()
    parent.crow_ai_checkbox = QCheckBox("AI Metadata Extraction")
    ai_layout.addWidget(parent.crow_ai_checkbox)

    # AI Setup button
    parent.crow_ai_setup_btn = QPushButton("Setup AI Key")
    parent.crow_ai_setup_btn.clicked.connect(parent.setup_crow_ai_api_key)
    ai_layout.addWidget(parent.crow_ai_setup_btn)

    options_layout.addLayout(ai_layout)

    # TOR Spoofing
    tor_layout = QHBoxLayout()
    parent.crow_tor_checkbox = QCheckBox("Use TOR for AI requests")
    tor_layout.addWidget(parent.crow_tor_checkbox)

    # TOR Settings button
    parent.crow_tor_settings_btn = QPushButton("TOR Settings")
    parent.crow_tor_settings_btn.clicked.connect(parent.configure_crow_tor_settings)
    tor_layout.addWidget(parent.crow_tor_settings_btn)

    options_layout.addLayout(tor_layout)

    # Additional options in a grid
    options_grid = QGridLayout()  # Define the grid layout

    # Left column items (column 0)
    parent.crow_permute_checkbox = QCheckBox("Permute username")
    options_grid.addWidget(parent.crow_permute_checkbox, 0, 0)

    parent.crow_permuteall_checkbox = QCheckBox("Permute all variations")
    options_grid.addWidget(parent.crow_permuteall_checkbox, 1, 0)

    parent.crow_no_nsfw_checkbox = QCheckBox("Exclude NSFW sites")
    options_grid.addWidget(parent.crow_no_nsfw_checkbox, 2, 0)

    # ADDED: Max concurrent requests input
    max_concurrent_layout = QHBoxLayout()
    max_concurrent_layout.addWidget(QLabel("Max Concurrent:"))
    parent.crow_max_concurrent_spinbox = QSpinBox()
    parent.crow_max_concurrent_spinbox.setRange(1, 100)
    parent.crow_max_concurrent_spinbox.setValue(30)
    max_concurrent_layout.addWidget(parent.crow_max_concurrent_spinbox)
    options_grid.addLayout(max_concurrent_layout, 3, 0)

    # Right column items (column 1)
    parent.crow_verbose_checkbox = QCheckBox("Verbose logging")
    options_grid.addWidget(parent.crow_verbose_checkbox, 0, 1)

    parent.crow_no_update_checkbox = QCheckBox("Disable updates")
    options_grid.addWidget(parent.crow_no_update_checkbox, 1, 1)

    # Add the grid to the options layout
    options_layout.addLayout(options_grid)

    # INTERACTIVE FILTER SYSTEM
    filter_group = QGroupBox("Search Filters")
    filter_group_layout = QVBoxLayout()
    
    # Interactive filters section header
    interactive_filter_label = QLabel("📋 Interactive Filters (Check to enable, uncheck to disable):")
    interactive_filter_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
    filter_group_layout.addWidget(interactive_filter_label)
    
    # Create a scroll area for interactive filters
    parent.crow_interactive_filters_scroll = QScrollArea()
    parent.crow_interactive_filters_scroll.setWidgetResizable(True)
    parent.crow_interactive_filters_scroll.setMaximumHeight(200)
    parent.crow_interactive_filters_scroll.setFrameShape(QFrame.Shape.NoFrame)
    
    # Container widget for interactive filters
    parent.crow_interactive_filters_container = QWidget()
    parent.crow_interactive_filters_layout = QVBoxLayout()
    parent.crow_interactive_filters_layout.setContentsMargins(5, 5, 5, 5)
    parent.crow_interactive_filters_layout.setSpacing(5)
    
    # Store the filter widgets in a list
    parent.crow_interactive_filter_widgets = []
    
    # Create first filter widget
    parent._create_interactive_filter_widget()
    
    parent.crow_interactive_filters_container.setLayout(parent.crow_interactive_filters_layout)
    parent.crow_interactive_filters_scroll.setWidget(parent.crow_interactive_filters_container)
    filter_group_layout.addWidget(parent.crow_interactive_filters_scroll)
    
    # Interactive filter buttons
    interactive_buttons_layout = QHBoxLayout()
    
    parent.crow_add_filter_btn = QPushButton("➕ Add Filter")
    parent.crow_add_filter_btn.setToolTip("Add another filter input")
    parent.crow_add_filter_btn.clicked.connect(parent.add_interactive_filter)
    interactive_buttons_layout.addWidget(parent.crow_add_filter_btn)
    
    parent.crow_remove_filter_btn = QPushButton("➖ Remove Last Filter")
    parent.crow_remove_filter_btn.setToolTip("Remove the last filter input")
    parent.crow_remove_filter_btn.clicked.connect(parent.remove_last_interactive_filter)
    interactive_buttons_layout.addWidget(parent.crow_remove_filter_btn)
    
    parent.crow_clear_filters_btn = QPushButton("🗑️ Clear All Filters")
    parent.crow_clear_filters_btn.setToolTip("Remove all interactive filters")
    parent.crow_clear_filters_btn.clicked.connect(parent.clear_interactive_filters)
    interactive_buttons_layout.addWidget(parent.crow_clear_filters_btn)
    
    # Filter help button
    parent.crow_filter_help_btn = QPushButton("Filter Help ?")
    parent.crow_filter_help_btn.setFixedWidth(100)
    parent.crow_filter_help_btn.clicked.connect(parent.show_crow_filter_help)
    interactive_buttons_layout.addWidget(parent.crow_filter_help_btn)
    
    interactive_buttons_layout.addStretch()
    
    filter_group_layout.addLayout(interactive_buttons_layout)
    
    filter_group.setLayout(filter_group_layout)
    options_layout.addWidget(filter_group)

    options_group.setLayout(options_layout)
    crow_layout.addWidget(options_group)

    crow_layout.addSpacing(10)

    # Output options
    output_group = QGroupBox("Output Options")
    output_layout = QHBoxLayout()

    parent.crow_csv_checkbox = QCheckBox("CSV output")
    parent.crow_pdf_checkbox = QCheckBox("PDF")
    parent.crow_json_checkbox = QCheckBox("JSON")
    parent.crow_dump_checkbox = QCheckBox("Dump HTML")

    output_layout.addWidget(parent.crow_csv_checkbox)
    output_layout.addWidget(parent.crow_pdf_checkbox)
    output_layout.addWidget(parent.crow_json_checkbox)
    output_layout.addWidget(parent.crow_dump_checkbox)

    output_group.setLayout(output_layout)
    crow_layout.addWidget(output_group)

    crow_layout.addSpacing(10)

    # Action buttons
    button_layout = QHBoxLayout()

    # Save/Load buttons
    parent.crow_save_btn = QPushButton("💾 Save")
    parent.crow_save_btn.clicked.connect(parent.save_crow_settings)
    button_layout.addWidget(parent.crow_save_btn)

    parent.crow_load_btn = QPushButton("📂 Load")
    parent.crow_load_btn.clicked.connect(parent.load_crow_settings)
    button_layout.addWidget(parent.crow_load_btn)

    button_layout.addStretch()

    # Run/Stop buttons
    parent.crow_run_btn = QPushButton("▶ Run Crow")
    parent.crow_run_btn.clicked.connect(parent.run_crow_search)
    parent.crow_run_btn.setStyleSheet("font-weight: bold; background-color: #4CAF50; color: white;")
    button_layout.addWidget(parent.crow_run_btn)

    parent.crow_stop_btn = QPushButton("⏹ Stop")
    parent.crow_stop_btn.clicked.connect(parent.stop_crow_search)
    parent.crow_stop_btn.setEnabled(False)
    parent.crow_stop_btn.setStyleSheet("background-color: #f44336; color: white;")
    button_layout.addWidget(parent.crow_stop_btn)

    crow_layout.addLayout(button_layout)

    crow_layout.addSpacing(10)

    crow_layout.addStretch()

    crow_group.setLayout(crow_layout)
    tab_widget.addTab(crow_group, "🦅 Crow")
    
    return crow_group