"""
Maigret Night - Modular Components
This package contains all modular components for Maigret Night GUI.
"""

from .gen_dashboard import (
    load_css,
    load_js,
    process_file,
    load_dir,
    generate_dashboard
)

from .breach_vip import (
    process_single_email,
    process_email_file,
    is_enabled as is_breach_email_enabled,
    check_breach_vip_status  # Fixed typo from "check_breath_vip_status"
)

from .breach_vip_username import (
    process_single_username,
    process_username_file,
    is_enabled as is_breach_username_enabled
)

from .maigret_functions import (
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

from .workers import CrowWorker, MaigretWorker, MaigretWebWorker, DashboardWorker
from .tor_spoofing import TORSpoofer
from .crow_header import create_crow_tab
from .crow_tabs import CrowTabMethods
from .command_builder import build_blackbird_command, combine_filters  # ADDED combine_filters

__all__ = [
    'load_css',
    'load_js',
    'process_file',
    'load_dir',
    'generate_dashboard',
    'process_single_email',
    'process_email_file',
    'is_breach_email_enabled',
    'check_breach_vip_status',  # Fixed typo
    'process_single_username',
    'process_username_file',
    'is_breach_username_enabled',
    'CrowWorker',
    'MaigretWorker',
    'MaigretWebWorker',
    'DashboardWorker',
    'TORSpoofer',
    'create_crow_tab',
    'CrowTabMethods',
    'run_crow_search',
    'create_save_load_actions',
    'save_settings_dialog',
    'save_settings',
    'load_settings_dialog',
    'load_settings',
    'create_options_tab',
    'load_sites_from_file',
    'toggle_top_sites_input',
    'toggle_report_sorting_input',
    'create_buttons',
    'generate_dashboard',
    'on_dashboard_finished',
    'toggle_web_interface',
    'start_web_interface',
    'stop_web_interface',
    'on_web_interface_finished',
    'append_web_output',
    'run_maigret',
    'on_maigret_finished',
    'stop_maigret',
    'append_output',
    'build_blackbird_command',
    'combine_filters'  # ADDED
]