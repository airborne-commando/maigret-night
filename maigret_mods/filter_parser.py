# filter_parser.py
"""
Filter Parser for Blackbird OSINT tool with comment support
Supports:
- # as single-line comments
- Simple and efficient parsing
"""

import re
import os

class FilterParser:
    """Parser for filter files with # comment support"""
    
    def __init__(self):
        self.single_line_comment = re.compile(r'^\s*#.*$')
    
    def parse_filter_file(self, file_path):
        """
        Parse a filter file and return clean filters
        
        Args:
            file_path (str): Path to filter file
        
        Returns:
            list: Clean filter strings without comments
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Filter file not found: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return self.parse_filter_content(content)
    
    def parse_filter_content(self, content):
        """
        Parse filter content string and remove # comments
        
        Args:
            content (str): Filter content with # comments
        
        Returns:
            list: Clean filter strings
        """
        lines = content.split('\n')
        clean_lines = []
        
        for line in lines:
            # Remove inline # comments
            line = self._remove_inline_comments(line)
            
            # Skip if whole line is a comment or empty
            line = line.strip()
            if line and not self.single_line_comment.match(line):
                clean_lines.append(line)
        
        return clean_lines
    
    def _remove_inline_comments(self, line):
        """Remove inline # comments"""
        if '#' in line:
            # Find the first # that's not inside quotes
            in_quotes = False
            quote_char = None
            for i, char in enumerate(line):
                if char in ['"', "'"]:
                    if in_quotes and char == quote_char:
                        in_quotes = False
                        quote_char = None
                    elif not in_quotes:
                        in_quotes = True
                        quote_char = char
                elif char == '#' and not in_quotes:
                    return line[:i].rstrip()
        return line
    
    def validate_filter(self, filter_string):
        """
        Validate a filter string format
        
        Args:
            filter_string (str): Filter expression
        
        Returns:
            bool: True if valid, False otherwise
        """
        if not filter_string:
            return False
        
        # Basic pattern validation
        # Check for valid filter patterns
        patterns = [
            r'^(name|cat|uri_check|e_code|e_string|m_string|m_code)',
            r'[=~><!]+',
            r'[^=\s]+$'
        ]
        
        for pattern in patterns:
            if not re.search(pattern, filter_string):
                return False
        
        return True

    def validate_filters(self, filters):
        """
        Validate a list of filter strings
        
        Args:
            filters (list): List of filter strings
        
        Returns:
            tuple: (valid_filters, invalid_filters)
        """
        valid_filters = []
        invalid_filters = []
        
        for filter_str in filters:
            if self.validate_filter(filter_str):
                valid_filters.append(filter_str)
            else:
                invalid_filters.append(filter_str)
        
        return valid_filters, invalid_filters
    
    def create_example_filter_file(self, file_path):
        """
        Create an example filter file with # comments
        
        Args:
            file_path (str): Path to create example file
        """
        example_content = """# Example Blackbird Filter File with # Comments
# ============================================
# Use # for single-line comments

# Some users internet footprint - These sites will be excluded
uri_check!=https://api.tracker.gg/api/v2/apex/standard/profile/origin/{account}
uri_check!=https://gitlab.archlinux.org/api/v4/users?username={account}
uri_check!=https://archiveofourown.org/users/{account}

# Sites to comment out for now
# uri_check!=https://some.site/{account}
name!=weebly
name!=Etoro
name!=Lemon8
# name!=gumroad  # Temporarily disabled (inline comment)
name!=Bandcamp

# Multiple filters can be combined
name~twitter  # This finds sites with "twitter" in the name
cat=social and e_code=200  # Only social sites that return 200

# Complex filter example
(name~facebook or name~meta) and cat!=adult and e_code<400

# End of filter file
"""
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(example_content)
        
        return file_path

# Global parser instance
parser = FilterParser()

def parse_filters_from_file(file_path):
    """Parse filters from a file with comment support"""
    return parser.parse_filter_file(file_path)

def parse_filters_from_string(filter_string):
    """Parse filters from a string with comment support"""
    return parser.parse_filter_content(filter_string)

def validate_filters(filters):
    """Validate a list of filter strings"""
    return parser.validate_filters(filters)