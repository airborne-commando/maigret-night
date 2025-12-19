"""
Maigret Night - Modular Components
This package contains all modular components for Maigret Night GUI.
"""

from .breach_vip import (
    process_single_email,
    process_email_file,
    is_enabled as is_breach_email_enabled,
    check_breach_vip_status
)

from .breach_vip_username import (
    process_single_username,
    process_username_file,
    is_enabled as is_breach_username_enabled
)

from .workers import CrowWorker, MaigretWorker, MaigretWebWorker
from .tor_spoofing import TORSpoofer
from .crow_header import create_crow_tab
from .crow_tabs import CrowTabMethods
from .command_builder import build_blackbird_command

__all__ = [
    'process_single_email',
    'process_email_file',
    'is_breach_email_enabled',
    'check_breach_vip_status',
    'process_single_username',
    'process_username_file',
    'is_breach_username_enabled',
    'CrowWorker',
    'MaigretWorker',
    'MaigretWebWorker',
    'TORSpoofer',
    'create_crow_tab',
    'CrowTabMethods',
    'build_blackbird_command'
]