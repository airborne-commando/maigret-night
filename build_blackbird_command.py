# build_blackbird_command.py
import os

def build_blackbird_command(username_input, email_input, username_file_input, email_file_input, 
                            permute_checkbox, permuteall_checkbox, AI_checkbox, no_nsfw_checkbox, 
                            no_update_checkbox, csv_checkbox, pdf_checkbox, json_checkbox, verbose_checkbox, 
                            dump_checkbox, proxy_input, timeout_spinbox, filter_input, 
                            instagram_session_id):
    command = ["python", "blackbird.py"]

    # Function to handle appending parameters if text is present
    def add_params(param, text, cmd_list):
        if text:
            items = [item.strip() for item in text.split(',')]
            for item in items:
                cmd_list.extend([param, item])

    # Handle username input (could be direct input or file: prefix)
    if username_input:
        if username_input.startswith("file:"):
            # Extract file path from the "file:" prefix
            file_path = username_input[5:].strip()
            if os.path.exists(file_path):
                command.extend(["--username-file", file_path])
            else:
                # File doesn't exist, fall back to treating as regular input
                print(f"Warning: File not found: {file_path}. Treating as username input.")
                add_params("-u", username_input.replace("file:", ""), command)
        else:
            # Regular username input
            add_params("-u", username_input, command)
    
    # Handle email input (could be direct input or file: prefix)
    if email_input:
        if email_input.startswith("file:"):
            # Extract file path from the "file:" prefix
            file_path = email_input[5:].strip()
            if os.path.exists(file_path):
                command.extend(["--email-file", file_path])
            else:
                # File doesn't exist, fall back to treating as regular input
                print(f"Warning: File not found: {file_path}. Treating as email input.")
                add_params("-e", email_input.replace("file:", ""), command)
        else:
            # Regular email input
            add_params("-e", email_input, command)

    # Note: username_file_input and email_file_input parameters are kept for backward compatibility
    # but we're now using the "file:" prefix system instead
    if username_file_input and os.path.exists(username_file_input):
        command.extend(["--username-file", username_file_input])
    if email_file_input and os.path.exists(email_file_input):
        command.extend(["--email-file", email_file_input])

    # Check if we have any username input for permute options
    # Extract actual username from input (remove file: prefix if present)
    actual_username_input = username_input
    if username_input and username_input.startswith("file:"):
        # If it's a file, we can't permute it
        actual_username_input = ""
    elif username_input:
        actual_username_input = username_input

    # Add permute options if selected and exactly one username is provided
    if actual_username_input and len(actual_username_input.split(',')) == 1:
        if permute_checkbox:
            command.append("--permute")
        elif permuteall_checkbox:
            command.append("--permuteall")

    # Add other options based on checkbox states
    checkboxes = {
        "--ai": AI_checkbox,
        "--no-nsfw": no_nsfw_checkbox,
        "--no-update": no_update_checkbox,
        "--csv": csv_checkbox,
        "--pdf": pdf_checkbox,
        "--json": json_checkbox,
        "--verbose": verbose_checkbox,
        "--dump": dump_checkbox
    }
    command.extend([param for param, checked in checkboxes.items() if checked])

    # Add proxy and timeout options
    if proxy_input:
        command.extend(["--proxy", proxy_input])

    command.extend(["--timeout", str(timeout_spinbox)])

    # Add filter option if text is present
    if filter_input:
        command.extend(["--filter", filter_input])

    # Set the Instagram session ID environment variable if entered
    if instagram_session_id:
        os.environ["INSTAGRAM_SESSION_ID"] = instagram_session_id

    return command