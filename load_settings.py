# load_settings.py

import json
import os
from PyQt6.QtWidgets import QFileDialog

def load_settings(gui_instance):
    # Open a file dialog to select a JSON file to load
    file_name, _ = QFileDialog.getOpenFileName(gui_instance, "Open Settings", "", "JSON Files (*.json);;All Files (*)")
    if file_name:
        # Load the settings from the JSON file
        with open(file_name, 'r') as f:
            settings = json.load(f)

        # Define a mapping of setting keys to widget methods and types
        setting_mappings = {
            "username_input": (gui_instance.username_input.setText, str),
            # "username_file_input": (gui_instance.username_file_input.setText, str),
            "email_input": (gui_instance.email_input.setText, str),
            # "hudson_email_input": (gui_instance.hudson_email_input.setText, str),
            # "email_file_input": (gui_instance.email_file_input.setText, str),
            # "breach_email_file_input": (gui_instance.breach_email_file_input.setText, str),
            "tor_checkbox": (gui_instance.tor_checkbox.setChecked, bool),
            "permute_checkbox": (gui_instance.permute_checkbox.setChecked, bool),
            "enable_breach_username_checkbox": (gui_instance.enable_breach_username_checkbox.setChecked, bool),
            "enable_breach_email_checkbox": (gui_instance.enable_breach_email_checkbox.setChecked, bool),
            "permuteall_checkbox": (gui_instance.permuteall_checkbox.setChecked, bool),
            "no_nsfw_checkbox": (gui_instance.no_nsfw_checkbox.setChecked, bool),
            "proxy_input": (gui_instance.proxy_input.setText, str),
            "timeout_spinbox": (gui_instance.timeout_spinbox.setValue, int),
            "no_update_checkbox": (gui_instance.no_update_checkbox.setChecked, bool),
            "csv_checkbox": (gui_instance.csv_checkbox.setChecked, bool),
            "pdf_checkbox": (gui_instance.pdf_checkbox.setChecked, bool),
            "json_checkbox": (gui_instance.json_checkbox.setChecked, bool),
            "verbose_checkbox": (gui_instance.verbose_checkbox.setChecked, bool),
            "dump_checkbox": (gui_instance.dump_checkbox.setChecked, bool),
            "instagram_session_id": (gui_instance.instagram_session_id.setText, str),
            "AI_checkbox": (gui_instance.AI_checkbox.setChecked, bool),
            "filter": (gui_instance.filter_input.setText, str)
        }

        # Apply the loaded settings
        for key, (set_method, value_type) in setting_mappings.items():
            if key in settings:
                set_method(value_type(settings[key]))

        # Special handling for ai_api_key
        if "ai_api_key" in settings and settings["ai_api_key"]:
            gui_instance.ai_api_key = settings["ai_api_key"]
            os.environ["BLACKBIRD_AI_API_KEY"] = settings["ai_api_key"]