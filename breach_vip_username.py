# breach_vip_username.py
import os
import json
import re
import time
import requests
from datetime import datetime
from PyQt6.QtWidgets import QMessageBox

def is_enabled(parent):
    """Check if username search is enabled"""
    return hasattr(parent, 'enable_breach_username_checkbox') and parent.enable_breach_username_checkbox.isChecked()

def check_breach_vip_status():
    """Check if Breach.vip is accessible with multiple endpoints"""
    test_endpoints = [
        "https://breach.vip/",
        "https://breach.vip/api/status",
        "https://breach.vip/api/search",  # Main API endpoint
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json, text/html, */*'
    }
    
    for endpoint in test_endpoints:
        try:
            response = requests.get(endpoint, headers=headers, timeout=10)
            if response.status_code < 500:  # Not a server error
                return True
            else:
                print(f"⚠️  {endpoint}: HTTP {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"⚠️  {endpoint}: {e}")
    
    return False

def process_single_username(username, output_area):
    """Process a single username for Breach.vip search"""
    if not output_area:
        return
        
    output_area.append(f"🔍 Searching Breach.vip for username: {username}")
    
    # Check if Breach.vip is accessible
    if not check_breach_vip_status():
        output_area.append("⚠️  Breach.vip appears to be down or unreachable")
        output_area.append("💡 Trying alternative methods...")
        
        # Try alternative check methods
        result = search_single_username_fallback(username)
        if result.get('success', False):
            data = result['data']
            display_username_results(data, username, output_area, source="Alternative")
        else:
            output_area.append("❌ All search methods failed")
            output_area.append("Please try again later or check your internet connection")
        return
    
    try:
        result = search_single_username_api(username)
        
        if result.get('success', False):
            data = result['data']
            display_username_results(data, username, output_area)
        else:
            error_msg = result.get('error', 'Unknown error')
            output_area.append(f"❌ Search failed: {error_msg}")
            
            # If API returns 503/500, try fallback
            if '503' in error_msg or '500' in error_msg:
                output_area.append("🔄 Trying fallback method...")
                result = search_single_username_fallback(username)
                if result.get('success', False):
                    data = result['data']
                    display_username_results(data, username, output_area, source="Fallback")
            
    except Exception as e:
        output_area.append(f"❌ Error searching {username}: {e}")
        output_area.append("🔄 Trying fallback method...")
        result = search_single_username_fallback(username)
        if result.get('success', False):
            data = result['data']
            display_username_results(data, username, output_area, source="Fallback")

def search_single_username_fallback(username):
    """Fallback method for username search when API is down"""
    try:
        # Basic username validation
        is_valid = 2 <= len(username) <= 30
        
        # Check for common username patterns
        has_special_chars = bool(re.search(r'[^a-zA-Z0-9_]', username))
        
        return {
            'success': True,
            'data': {
                'results': [],
                'status': 'fallback',
                'message': f'API unavailable. Username analysis complete.',
                'username_valid': is_valid,
                'has_special_chars': has_special_chars,
                'length': len(username),
                'suggestions': [
                    'Try searching on other platforms like social media',
                    'Check if username appears in public data breaches elsewhere'
                ] if is_valid else ['Username appears invalid']
            },
            'source': 'fallback'
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'Fallback failed: {str(e)[:100]}',
            'source': 'fallback'
        }

def process_username_file(file_path, output_area):
    """Process a file containing multiple usernames for Breach.vip search"""
    if not output_area:
        return
    
    # Check service status before processing file
    if not check_breach_vip_status():
        output_area.append("❌ Breach.vip appears to be down or unreachable")
        output_area.append("⚠️  Cannot process file while service is unavailable")
        output_area.append("💡 Please try again later")
        return
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            usernames = [line.strip() for line in f if line.strip()]
            
        if not usernames:
            QMessageBox.warning(None, "File Error", "The file is empty or contains no valid usernames.")
            return
            
        valid_usernames = []
        invalid_usernames = []
        
        # Validate usernames
        for username in usernames:
            if username and len(username) >= 2:
                valid_usernames.append(username)
            else:
                invalid_usernames.append(username)
                
        if not valid_usernames:
            QMessageBox.warning(None, "File Error", "No valid usernames found in the file.")
            return
            
        # Show confirmation dialog for multiple usernames
        if len(valid_usernames) > 1:
            reply = QMessageBox.question(
                None,
                "Multiple Usernames Found",
                f"Found {len(valid_usernames)} valid username(s) and {len(invalid_usernames)} invalid entry(s).\n\n"
                f"Do you want to search all {len(valid_usernames)} usernames? This may take a while due to rate limits.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
                
        # Process all valid usernames
        output_area.append(f"📁 Processing {len(valid_usernames)} username(s) from file: {os.path.basename(file_path)}")
        if invalid_usernames:
            output_area.append(f"⚠️  Skipped {len(invalid_usernames)} invalid entries")
            
        output_area.append("=" * 60)
    
        # Create results directory if it doesn't exist
        results_dir = "results"
        if not os.path.exists(results_dir):
            os.makedirs(results_dir)
            
        # Generate batch filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        batch_filename = f"breach_vip_usernames_{timestamp}.txt"
        batch_filepath = os.path.join(results_dir, batch_filename)
        
        all_results = []
        service_down = False
        
        for i, username in enumerate(valid_usernames, 1):
            if service_down:
                output_area.append(f"⚠️  Skipping remaining usernames - service unavailable")
                break
                
            output_area.append(f"\n🔍 [{i}/{len(valid_usernames)}] Searching: {username}")
            
            try:
                # Re-check service status periodically
                if i % 5 == 0 and not check_breach_vip_status():
                    output_area.append("❌ Breach.vip service became unavailable")
                    service_down = True
                    break
                
                result = search_single_username_api(username)
                all_results.append({
                    'username': username,
                    'result': result,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
                
                # Display brief result
                if result.get('success', False) and result.get('data'):
                    data = result['data']
                    if data.get('results') and len(data['results']) > 0:
                        record_count = len(data['results'])
                        unique_breaches = len(set(r.get('source', '') for r in data['results']))
                        output_area.append(f"   🚨 Found {record_count} records across {unique_breaches} breaches")
                    else:
                        output_area.append(f"   ✅ No breach records found")
                else:
                    error_msg = result.get('error', 'Unknown error')
                    output_area.append(f"   ❌ Search failed: {error_msg}")
                    
                    # Check if it's a service error
                    if any(code in error_msg for code in ['503', '500', '429']):
                        output_area.append("   ⚠️  Service error detected")
                        if '429' in error_msg:
                            output_area.append("   💤 Rate limited, waiting 60 seconds...")
                            time.sleep(60)
                
                # Respect rate limit - wait between requests
                if i < len(valid_usernames):  # Don't wait after the last one
                    time.sleep(4)  # 4 seconds between requests to stay under 15/minute
                    
            except Exception as e:
                output_area.append(f"   ❌ Error searching {username}: {e}")
                all_results.append({
                    'username': username,
                    'result': {'success': False, 'error': str(e)},
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
                
                # Check for network errors
                if 'Connection' in str(e) or 'Timeout' in str(e):
                    output_area.append("   ⚠️  Network error - service may be down")
                    if not check_breach_vip_status():
                        service_down = True
                        break
                
        # Save batch results
        if all_results:
            save_batch_results(all_results, batch_filepath, output_area)
            output_area.append(f"\n💾 Batch results saved to: {batch_filepath}")
            
            if service_down:
                output_area.append(f"⚠️  Search interrupted - {len(all_results)}/{len(valid_usernames)} usernames processed")
            else:
                output_area.append("🎉 Batch search completed!")
        else:
            output_area.append("❌ No results to save")
        
    except Exception as e:
        output_area.append(f"❌ Error processing file: {e}")

def search_single_username_api(username):
    """Make API call to Breach.vip for a single username with better error handling"""
    try:
        url = "https://breach.vip/api/search"
        
        payload = {
            "term": username,
            "fields": ["username", "name"],  # Search in username and name fields
            "categories": None,
            "wildcard": False,
            "case_sensitive": False
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        # Add timeout and retry logic
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            return {
                'success': True,
                'data': response.json(),
                'status_code': response.status_code
            }
        else:
            error_msg = f"API returned status {response.status_code}"
            if response.status_code == 429:
                error_msg = "Rate limited - please wait 1 minute"
            elif response.status_code == 400:
                error_msg = "Bad request - invalid input"
            elif response.status_code == 500:
                error_msg = "Internal server error - service may be down"
            elif response.status_code == 503:
                error_msg = "Service unavailable - try again later"
            elif response.status_code == 502:
                error_msg = "Bad gateway - service error"
            elif response.status_code == 504:
                error_msg = "Gateway timeout - service may be overloaded"
                
            return {
                'success': False,
                'error': error_msg,
                'status_code': response.status_code
            }
            
    except requests.exceptions.Timeout:
        return {
            'success': False,
            'error': "Request timeout - service may be slow or down"
        }
    except requests.exceptions.ConnectionError:
        return {
            'success': False,
            'error': "Connection error - check your internet connection"
        }
    except requests.exceptions.RequestException as e:
        return {
            'success': False,
            'error': f"Network error: {e}"
        }
    except Exception as e:
        return {
            'success': False,
            'error': f"Unexpected error: {e}"
        }

# Keep the rest of the functions (save_batch_results, display_username_results) the same as before
# ... [rest of the file remains the same] ...

def save_batch_results(all_results, filepath, output_area):
    """Save batch username results to file"""
    try:
        # Calculate summary stats
        successful_searches = sum(1 for r in all_results if r['result'].get('success'))
        total_records = sum(len(r['result'].get('data', {}).get('results', [])) 
                          for r in all_results if r['result'].get('success'))
        usernames_with_breaches = sum(1 for r in all_results 
                                    if r['result'].get('success') and 
                                    r['result'].get('data', {}).get('results'))
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("BREACH.VIP USERNAME SEARCH RESULTS\n")
            f.write("=" * 60 + "\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Usernames Searched: {len(all_results)}\n")
            f.write("=" * 60 + "\n\n")
            
            for result in all_results:
                username = result['username']
                search_result = result['result']
                timestamp = result['timestamp']
                
                f.write(f"USERNAME: {username}\n")
                f.write(f"SEARCH TIME: {timestamp}\n")
                f.write(f"STATUS: {'SUCCESS' if search_result.get('success') else 'FAILED'}\n")
                
                if search_result.get('success') and search_result.get('data'):
                    data = search_result['data']
                    if data.get('results') and len(data['results']) > 0:
                        records = data['results']
                        f.write(f"RECORDS FOUND: {len(records)}\n")
                        
                        # Group by breach source
                        breaches_by_source = {}
                        for record in records:
                            source = record.get('source', 'Unknown Source')
                            if source not in breaches_by_source:
                                breaches_by_source[source] = []
                            breaches_by_source[source].append(record)
                            
                        f.write("BREACHES:\n")
                        for source, source_records in breaches_by_source.items():
                            f.write(f"  - {source}: {len(source_records)} record(s)\n")
                            
                        # Show sample data
                        f.write("SAMPLE DATA:\n")
                        for source, source_records in breaches_by_source.items():
                            f.write(f"  {source}:\n")
                            sample_record = source_records[0]
                            for key, value in sample_record.items():
                                if value and key not in ['source', 'categories']:
                                    f.write(f"    {key}: {value}\n")
                                    
                        # Show matching field info
                        f.write("MATCHING FIELDS:\n")
                        for record in records[:3]:  # Show first 3 records
                            if 'email' in record:
                                f.write(f"  Associated email: {record['email']}\n")
                            if 'name' in record:
                                f.write(f"  Associated name: {record['name']}\n")
                    else:
                        f.write("RECORDS FOUND: 0\n")
                        f.write("STATUS: No breach records found\n")
                else:
                    f.write(f"ERROR: {search_result.get('error', 'Unknown error')}\n")
                    
                f.write("-" * 40 + "\n\n")
                
            # Add summary
            f.write("SUMMARY\n")
            f.write("=" * 60 + "\n")
            f.write(f"Successful searches: {successful_searches}/{len(all_results)}\n")
            f.write(f"Usernames with breaches: {usernames_with_breaches}\n")
            f.write(f"Total breach records found: {total_records}\n")
            f.write("=" * 60 + "\n")
            
    except Exception as e:
        if output_area:
            output_area.append(f"❌ Error saving batch results: {e}")

def display_username_results(data, username, output_area, source="Breach.vip"):
    """Display username breach results in a formatted way and save to file"""
    if not output_area:
        return
        
    output_area.append(f"\n📊 {source.upper()} USERNAME RESULTS FOR: {username}")
    output_area.append("=" * 60)
    
    # Create results directory if it doesn't exist
    results_dir = "results"
    if not os.path.exists(results_dir):
        os.makedirs(results_dir)
        
    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_username = re.sub(r'[^\w\-_.]', '_', username)
    filename = f"{source.lower()}_username_{safe_username}_{timestamp}.txt"
    filepath = os.path.join(results_dir, filename)
    
    # Prepare content
    display_lines = []
    file_lines = []
    
    try:
        if source.lower() == 'fallback':
            # Handle fallback response format
            display_lines.append(f"⚠️  Using fallback method (Breach.vip API unavailable)")
            display_lines.append(f"👤 Username: {username}")
            if data.get('username_valid'):
                display_lines.append("✅ Username appears valid")
                display_lines.append(f"📏 Length: {data.get('length', 'N/A')} characters")
                if data.get('has_special_chars'):
                    display_lines.append("⚠️  Contains special characters (may be invalid on some platforms)")
                
                if data.get('suggestions'):
                    display_lines.append("💡 Suggestions:")
                    for suggestion in data['suggestions']:
                        display_lines.append(f"  • {suggestion}")
            else:
                display_lines.append("❌ Username appears invalid")
                if data.get('suggestions'):
                    for suggestion in data['suggestions']:
                        display_lines.append(f"  • {suggestion}")
            
            file_lines.append(f"{source.upper()} USERNAME CHECK FOR: {username}")
            file_lines.append(f"Search Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            file_lines.append(f"Status: Breach.vip API unavailable, using fallback check")
            file_lines.append(f"Username Validation: {'VALID' if data.get('username_valid') else 'INVALID'}")
            file_lines.append(f"Length: {data.get('length', 'N/A')} characters")
            file_lines.append(f"Special Characters: {'YES' if data.get('has_special_chars') else 'NO'}")
            file_lines.append(f"Note: Full breach check requires Breach.vip API access")
            
        elif 'results' in data and isinstance(data['results'], list):
            # Original Breach.vip response handling
            results = data['results']
            
            if len(results) > 0:
                display_lines.append(f"🚨 Found {len(results)} breach record(s)")
                file_lines.append(f"BREACH.VIP USERNAME RESULTS FOR: {username}")
                file_lines.append(f"Search Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                file_lines.append(f"Records Found: {len(results)}")
                file_lines.append("=" * 60)
                file_lines.append("")
                
                # Group by email if available
                email_groups = {}
                for result in results:
                    email = result.get('email')
                    if email:
                        if email not in email_groups:
                            email_groups[email] = []
                        email_groups[email].append(result)
                
                # Display by email groups
                if email_groups:
                    display_lines.append(f"📧 Found across {len(email_groups)} unique email(s):")
                    file_lines.append(f"ASSOCIATED EMAILS: {len(email_groups)}")
                    
                    for i, (email, email_results) in enumerate(email_groups.items(), 1):
                        display_lines.append(f"  {i}. {email}:")
                        file_lines.append(f"\nEMAIL {i}: {email}")
                        
                        for j, result in enumerate(email_results, 1):
                            source_name = result.get('source', 'Unknown Source')
                            display_lines.append(f"     📦 Breach: {source_name}")
                            file_lines.append(f"  Breach {j}: {source_name}")
                            
                            # Show other fields
                            for field, value in result.items():
                                if field not in ['source', 'categories', 'email'] and value:
                                    if len(str(value)) > 100:
                                        display_value = str(value)[:100] + "..."
                                    else:
                                        display_value = str(value)
                                    display_lines.append(f"     🔍 {field}: {display_value}")
                                    file_lines.append(f"    {field}: {value}")
                            
                            display_lines.append("")
                            file_lines.append("")
                
                # Show records without email
                no_email_records = [r for r in results if not r.get('email')]
                if no_email_records:
                    display_lines.append("📝 Other records (no email association):")
                    file_lines.append("\nOTHER RECORDS (no email association):")
                    
                    for i, result in enumerate(no_email_records, 1):
                        source_name = result.get('source', 'Unknown Source')
                        display_lines.append(f"  {i}. {source_name}")
                        file_lines.append(f"  Record {i}: {source_name}")
                
                # Summary
                unique_breaches = len(set(r.get('source', '') for r in results))
                unique_emails = len(email_groups)
                display_lines.append(f"\n📈 Summary: {len(results)} records, {unique_breaches} breaches, {unique_emails} emails")
                file_lines.append(f"\nSUMMARY: {len(results)} records, {unique_breaches} breaches, {unique_emails} associated emails")
                
            else:
                display_lines.append("✅ No breach records found for this username")
                display_lines.append("💡 This username appears clean in Breach.vip database")
                
                file_lines.append(f"BREACH.VIP USERNAME RESULTS FOR: {username}")
                file_lines.append(f"Search Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                file_lines.append("RESULTS: No breach records found")
                file_lines.append("STATUS: Username appears clean in Breach.vip database")
        else:
            display_lines.append("❌ Unexpected response format from API")
            file_lines.append(f"BREACH.VIP USERNAME RESULTS FOR: {username}")
            file_lines.append(f"Search Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            file_lines.append("ERROR: Unexpected response format from API")
            
    except Exception as e:
        error_msg = f"❌ Error processing results: {e}"
        display_lines.append(error_msg)
        file_lines.append(f"{source.upper()} USERNAME RESULTS FOR: {username}")
        file_lines.append(f"Search Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        file_lines.append(f"ERROR: {error_msg}")
        
    # Add footer
    display_lines.append("=" * 60)
    if source == "Breach.vip":
        display_lines.append("💡 Note: Username search may return associated emails from breaches")
        file_lines.append("=" * 60)
        file_lines.append(f"Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        display_lines.append("⚠️  Note: Using fallback method - limited information available")
        file_lines.append("=" * 60)
        file_lines.append(f"Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        file_lines.append("Note: Fallback method used - Breach.vip API was unavailable")
    
    # Display results
    for line in display_lines:
        output_area.append(line)
        
    # Save to file
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(file_lines))
        output_area.append(f"💾 Results saved to: {filepath}")
    except Exception as e:
        output_area.append(f"❌ Error saving results to file: {e}")