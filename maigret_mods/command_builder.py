"""
Command builder for Blackbird OSINT tool
"""

import os

def combine_filters(filter_list):
    """Combine multiple filters with smart AND/OR operator selection"""
    if not filter_list:
        return ""
    
    # Process each filter
    processed_filters = []
    
    for filter_item in filter_list:
        if filter_item.startswith("file:"):
            file_path = filter_item[5:]
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r') as f:
                        content = f.read().strip()
                    if content:
                        # Split by lines and add each as separate filter
                        lines = [line.strip() for line in content.split('\n') if line.strip()]
                        processed_filters.extend(lines)
                except:
                    # If can't read file, use the file reference as-is
                    processed_filters.append(filter_item)
            else:
                processed_filters.append(filter_item)
        else:
            processed_filters.append(filter_item)
    
    if len(processed_filters) == 1:
        return processed_filters[0]
    
    # Group filters by type for smart combination
    name_contains_or_equals = []
    name_not_equals = []
    cat_not_equals = []
    cat_equals = []
    other_filters = []
    
    for filter_expr in processed_filters:
        if 'name~' in filter_expr or 'name=' in filter_expr:
            name_contains_or_equals.append(filter_expr)
        elif 'name!=' in filter_expr:
            name_not_equals.append(filter_expr)
        elif 'cat!=' in filter_expr:
            cat_not_equals.append(filter_expr)
        elif 'cat=' in filter_expr:
            cat_equals.append(filter_expr)
        else:
            other_filters.append(filter_expr)
    
    # Build combined filter
    combined_parts = []
    
    # 1. Combine name~ and name= with OR (lowercase 'or' for Blackbird)
    if name_contains_or_equals:
        if len(name_contains_or_equals) == 1:
            combined_parts.append(name_contains_or_equals[0])
        else:
            # Use lowercase 'or' without parentheses
            combined_parts.append(" or ".join(name_contains_or_equals))
    
    # 2. Combine name!= with AND (lowercase 'and' for Blackbird)
    if name_not_equals:
        if len(name_not_equals) == 1:
            combined_parts.append(name_not_equals[0])
        else:
            # Use lowercase 'and' without parentheses
            combined_parts.append(" and ".join(name_not_equals))
    
    # 3. Combine cat!= with AND (lowercase 'and' for Blackbird)
    if cat_not_equals:
        if len(cat_not_equals) == 1:
            combined_parts.append(cat_not_equals[0])
        else:
            # Use lowercase 'and' without parentheses
            combined_parts.append(" and ".join(cat_not_equals))
    
    # 4. Combine cat= with OR (lowercase 'or' for Blackbird)
    if cat_equals:
        if len(cat_equals) == 1:
            combined_parts.append(cat_equals[0])
        else:
            # Use lowercase 'or' without parentheses
            combined_parts.append(" or ".join(cat_equals))
    
    # 5. Add other filters
    combined_parts.extend(other_filters)
    
    # Combine all parts with AND (lowercase 'and' for Blackbird)
    if len(combined_parts) == 1:
        return combined_parts[0]
    else:
        return " and ".join(combined_parts)


def auto_detect_and_append_operators(filter_text):
    """Automatically append the right operators to filter text"""
    lines = [line.strip() for line in filter_text.split('\n') if line.strip()]
    
    if len(lines) <= 1:
        return filter_text
    
    # Analyze each line to determine operator
    result_lines = []
    for i, line in enumerate(lines):
        result_lines.append(line)
        
        # Only add operator if not the last line
        if i < len(lines) - 1:
            current_line = line
            next_line = lines[i + 1]
            
            # Determine operator based on patterns (use lowercase)
            if 'name~' in current_line or 'name=' in current_line:
                if 'name~' in next_line or 'name=' in next_line:
                    result_lines.append("or")  # lowercase
                else:
                    result_lines.append("and")  # lowercase
            elif 'name!=' in current_line:
                result_lines.append("and")  # lowercase
            elif 'cat!=' in current_line:
                result_lines.append("and")  # lowercase
            elif 'cat=' in current_line:
                result_lines.append("or")   # lowercase
            else:
                result_lines.append("and")  # lowercase
    
    return " ".join(result_lines)


def auto_detect_and_append_operators(filter_text):
    """Automatically append the right operators to filter text"""
    lines = [line.strip() for line in filter_text.split('\n') if line.strip()]
    
    if len(lines) <= 1:
        return filter_text
    
    # Analyze each line to determine operator
    result_lines = []
    for i, line in enumerate(lines):
        result_lines.append(line)
        
        # Only add operator if not the last line
        if i < len(lines) - 1:
            current_line = line
            next_line = lines[i + 1]
            
            # Determine operator based on patterns
            if 'name~' in current_line or 'name=' in current_line:
                if 'name~' in next_line or 'name=' in next_line:
                    result_lines.append("or")
                else:
                    result_lines.append("and")
            elif 'name!=' in current_line:
                result_lines.append("and")
            elif 'cat!=' in current_line:
                result_lines.append("and")  # cat!= uses AND
            elif 'cat=' in current_line:
                result_lines.append("or")   # cat= uses OR
            else:
                result_lines.append("and")
    
    return " ".join(result_lines)

# Update the build_blackbird_command function in command_builder.py
# In command_builder.py, update the build_blackbird_command function:
def build_blackbird_command(
    username_input="",
    email_input="",
    username_file_input="",
    email_file_input="",
    permute_checkbox=False,
    permuteall_checkbox=False,
    AI_checkbox=False,
    no_nsfw_checkbox=False,
    no_update_checkbox=False,
    csv_checkbox=False,
    pdf_checkbox=False,
    json_checkbox=False,
    verbose_checkbox=False,
    dump_checkbox=False,
    proxy_input="",
    timeout_spinbox=30,
    max_concurrent_requests=30,
    filter_input="",
    interactive_filters=None,  # Now always used
    use_interactive_filters=True,  # Always true now, but keep for compatibility
    instagram_session_id=""
):
    """
    Build Blackbird command based on input parameters
    
    Args:
        username_input (str): Username(s) to search
        email_input (str): Email(s) to search
        username_file_input (str): Path to username file
        email_file_input (str): Path to email file
        permute_checkbox (bool): Enable username permutation
        permuteall_checkbox (bool): Enable all permutations
        AI_checkbox (bool): Enable AI analysis
        no_nsfw_checkbox (bool): Exclude NSFW sites
        no_update_checkbox (bool): Disable updates
        csv_checkbox (bool): Generate CSV output
        pdf_checkbox (bool): Generate PDF output
        json_checkbox (bool): Generate JSON output
        verbose_checkbox (bool): Enable verbose output
        dump_checkbox (bool): Dump HTML output
        proxy_input (str): Proxy URL
        timeout_spinbox (int): Timeout in seconds
        max_concurrent_requests (int): Max concurrent requests
        filter_input (str): Original filter input (deprecated)
        interactive_filters (list): List of interactive filter strings
        use_interactive_filters (bool): Whether to use interactive filters
        instagram_session_id (str): Instagram session ID
    
    Returns:
        list: Command as list of arguments or None if error
    """
    
    command = ["python", "blackbird.py"]
    
    # Add username or username file
    if username_input:
        if username_input.startswith("file:"):
            file_path = username_input[5:]
            if os.path.exists(file_path):
                command.extend(["-uf", file_path])
            else:
                print(f"❌ Username file not found: {file_path}")
                return None
        else:
            # Handle multiple usernames separated by commas
            usernames = [u.strip() for u in username_input.split(',') if u.strip()]
            if usernames:
                command.extend(["-u"] + usernames)
    
    # Add email or email file
    if email_input:
        if email_input.startswith("file:"):
            file_path = email_input[5:]
            if os.path.exists(file_path):
                command.extend(["-ef", file_path])
            else:
                print(f"❌ Email file not found: {file_path}")
                return None
        else:
            # Handle multiple emails separated by commas
            emails = [e.strip() for e in email_input.split(',') if e.strip()]
            if emails:
                command.extend(["-e"] + emails)
    
    # Handle filters - always use interactive filters now (if provided)
    filter_string = ""
    
    if interactive_filters:
        # Process all interactive filters
        all_filter_parts = []
        
        for filter_item in interactive_filters:
            if filter_item.startswith("file:"):
                file_path = filter_item[5:]
                if os.path.exists(file_path):
                    try:
                        with open(file_path, 'r') as f:
                            content = f.read().strip()
                        if content:
                            lines = [line.strip() for line in content.split('\n') if line.strip()]
                            all_filter_parts.extend(lines)
                    except Exception as e:
                        print(f"❌ Error reading filter file {file_path}: {e}")
                        # If can't read, skip this filter
                        continue
                else:
                    print(f"❌ Filter file not found: {file_path}")
                    continue
            else:
                # Direct filter expression
                all_filter_parts.append(filter_item)
        
        # Combine all filter parts
        if all_filter_parts:
            if len(all_filter_parts) == 1:
                filter_string = all_filter_parts[0]
            else:
                filter_string = combine_filters(all_filter_parts)
    
    # Add the filter to command if we have one
    if filter_string:
        command.extend(["--filter", filter_string])
    
    # Add options
    if permute_checkbox:
        command.append("--permute")
    if permuteall_checkbox:
        command.append("--permuteall")
    if AI_checkbox:
        command.append("--ai")
    if no_nsfw_checkbox:
        command.append("--no-nsfw")
    if no_update_checkbox:
        command.append("--no-update")
    if csv_checkbox:
        command.append("--csv")
    if pdf_checkbox:
        command.append("--pdf")
    if json_checkbox:
        command.append("--json")
    if verbose_checkbox:
        command.append("-v")
    if dump_checkbox:
        command.append("--dump")
    
    # Add proxy if specified
    if proxy_input:
        command.extend(["--proxy", proxy_input])
    
    # Add timeout
    command.extend(["--timeout", str(timeout_spinbox)])
    
    # Max concurrent requests
    command.extend(["--max-concurrent-requests", str(max_concurrent_requests)])
    
    # Add Instagram session ID if specified
    if instagram_session_id:
        pass
    
    return command