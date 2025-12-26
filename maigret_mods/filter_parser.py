# filter_parser.py
"""
Filter Parser for Blackbird OSINT tool with comment support
Supports:
- # as single-line comments
- /* ... */ as multi-line comment blocks
- Filter validation and cleaning
"""

import re
import os

class FilterParser:
    """Parser for filter files with comment support"""
    
    def __init__(self):
        self.single_line_comment = re.compile(r'^\s*#.*$')
        self.multi_line_start = re.compile(r'/\*')
        self.multi_line_end = re.compile(r'\*/')
    
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
        Parse filter content string and remove comments
        
        Args:
            content (str): Filter content with comments
        
        Returns:
            list: Clean filter strings
        """
        lines = content.split('\n')
        clean_lines = []
        in_comment_block = False
        
        for line in lines:
            # Remove inline comments
            line = self._remove_inline_comments(line, in_comment_block)
            
            # Check for single-line comment
            if self.single_line_comment.match(line):
                continue
            
            # Check for multi-line comment blocks
            line, in_comment_block = self._process_multi_line_comments(line, in_comment_block)
            
            # Skip empty lines and comment-only lines
            if line.strip() and not in_comment_block:
                clean_lines.append(line.strip())
        
        return clean_lines
    
    def _remove_inline_comments(self, line, in_comment_block):
        """Remove inline # comments when not in a block comment"""
        if not in_comment_block and '#' in line:
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
    
    def _process_multi_line_comments(self, line, in_comment_block):
        """Process /* ... */ comment blocks"""
        result_line = ""
        i = 0
        
        while i < len(line):
            if in_comment_block:
                # Look for end of comment block
                end_match = self.multi_line_end.search(line[i:])
                if end_match:
                    i += end_match.end()  # Skip past */
                    in_comment_block = False
                else:
                    i = len(line)  # Skip rest of line
            else:
                # Look for start of comment block
                start_match = self.multi_line_start.search(line[i:])
                if start_match:
                    # Add text before comment
                    result_line += line[i:start_match.start() + i]
                    i += start_match.end()  # Skip past /*
                    in_comment_block = True
                else:
                    # No comment block, add remaining text
                    result_line += line[i:]
                    break
        
        return result_line, in_comment_block
    
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
    
    def create_example_filter_file(self, file_path):
        """
        Create an example filter file with comments
        
        Args:
            file_path (str): Path to create example file
        """
        example_content = """# Example Blackbird Filter File with Comments
# ============================================
# Use # for single-line comments
# Use /* ... */ for comment blocks

# Some users internet footprint - These sites will be excluded
uri_check!=https://api.tracker.gg/api/v2/apex/standard/profile/origin/{account}
uri_check!=https://gitlab.archlinux.org/api/v4/users?username={account}
uri_check!=https://archiveofourown.org/users/{account}

# Sites to comment out for now (using single-line comments)
# uri_check!=https://some.site/{account}
name!=weebly
name!=Etoro
name!=Lemon8
# name!=gumroad  # Temporarily disabled
name!=Bandcamp

/*
Will check these sites later - This is a comment block
Everything between /* and */ is ignored
Useful for disabling large sections temporarily
*/

uri_check!=https://hometech.social/api/v1/accounts/lookup?acct={account}
uri_check!=https://hostux.social/api/v1/accounts/lookup?acct={account}

/*
Another comment block - You can nest single-line comments inside:
# This single-line comment is also ignored inside the block
uri_check!=https://independent.academia.edu/{account}
uri_check!=https://imginn.com/{account}/
*/

# Back to active filters - Mixed with comments
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
    valid_filters = []
    invalid_filters = []
    
    for filter_str in filters:
        if parser.validate_filter(filter_str):
            valid_filters.append(filter_str)
        else:
            invalid_filters.append(filter_str)
    
    return valid_filters, invalid_filters