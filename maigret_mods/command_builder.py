"""
Command builder for Blackbird OSINT tool
"""

import os

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
    max_concurrent_requests=30,  # ADDED: New parameter
    filter_input="",
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
        csv_checkbox (bool): Generate CSV output
        pdf_checkbox (bool): Generate PDF output
        json_checkbox (bool): Generate JSON output
        verbose_checkbox (bool): Enable verbose output
        dump_checkbox (bool): Dump HTML output
        proxy_input (str): Proxy URL
        timeout_spinbox (int): Timeout in seconds
        max_concurrent_requests (int): Max concurrent requests (default: 30)
        filter_input (str): Search filter (can be direct filter or file:path/to/filters.txt)
        instagram_session_id (str): Instagram session ID
    
    Returns:
        list: Command as list of arguments
    """
    
    command = ["python", "blackbird.py"]
    
    # Add username or username file
    if username_input:
        if username_input.startswith("file:"):
            file_path = username_input[5:]
            if os.path.exists(file_path):
                command.extend(["-uf", file_path])
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
            # Handle multiple emails separated by commas
            emails = email_input.split(',')
            for email in emails:
                email = email.strip()
                if email:
                    command.extend(["-e", email])
    
    # Handle filter input - can be direct filter or file
    if filter_input:
        if filter_input.startswith("file:"):
            file_path = filter_input[5:]
            if os.path.exists(file_path):
                try:
                    # Read the filter file
                    with open(file_path, 'r') as f:
                        filters_content = f.read().strip()
                    
                    if filters_content:
                        # Process multiple lines - join with " and " or keep as is
                        lines = [line.strip() for line in filters_content.split('\n') if line.strip()]
                        if lines:
                            if len(lines) == 1:
                                # Single filter line
                                filter_value = lines[0]
                            else:
                                # Multiple filter lines - join with " and "
                                # But first check if each line already contains "and"
                                combined_filters = " and ".join(lines)
                                filter_value = combined_filters
                            
                            command.extend(["--filter", filter_value])
                except FileNotFoundError:
                    print(f"❌ Filter file not found: {file_path}")
                    # Return None to indicate error
                    return None
                except Exception as e:
                    print(f"❌ Error reading filter file: {e}")
                    return None
        else:
            # Direct filter text
            command.extend(["--filter", filter_input])
    
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
        # Blackbird doesn't have Instagram session ID parameter
        # This would need to be set as environment variable or config
        pass
    
    return command