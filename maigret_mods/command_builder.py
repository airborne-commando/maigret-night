"""
Command builder for Blackbird OSINT tool
"""

import os

def combine_filters(filter_list):
    """Combine multiple filters into a single filter string"""
    if not filter_list:
        return ""
    
    # First, process each filter (could be file or direct)
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
    
    # Combine all processed filters with "and"
    if len(processed_filters) == 1:
        return processed_filters[0]
    else:
        return " and ".join(processed_filters)

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
            usernames = username_input.split(',')
            for username in usernames:
                username = username.strip()
                if username:
                    command.extend(["-u", username])
    
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
            emails = email_input.split(',')
            for email in emails:
                email = email.strip()
                if email:
                    command.extend(["-e", email])
    
    # Handle filters - always use interactive filters now (if provided)
    filter_to_use = ""
    
    if interactive_filters:
        # Use interactive filters
        filter_to_use = combine_filters(interactive_filters)
    
    if filter_to_use:
        if filter_to_use.startswith("file:"):
            file_path = filter_to_use[5:]
            if os.path.exists(file_path):
                try:
                    # Read the filter file
                    with open(file_path, 'r') as f:
                        filters_content = f.read().strip()
                    
                    if filters_content:
                        # Process multiple lines
                        lines = [line.strip() for line in filters_content.split('\n') if line.strip()]
                        if lines:
                            if len(lines) == 1:
                                filter_value = lines[0]
                            else:
                                # Combine with "and"
                                combined_filters = " and ".join(lines)
                                filter_value = combined_filters
                            
                            command.extend(["--filter", filter_value])
                except FileNotFoundError:
                    print(f"❌ Filter file not found: {file_path}")
                    return None
                except Exception as e:
                    print(f"❌ Error reading filter file: {e}")
                    return None
            else:
                print(f"❌ Filter file not found: {file_path}")
                return None
        else:
            # Direct filter text
            command.extend(["--filter", filter_to_use])
    else:
        # No filters specified - this is OK, Blackbird will search all sites
        pass
    
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