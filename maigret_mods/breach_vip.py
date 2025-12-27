# breach_vip.py
import os
import json
import re
import time
import requests
import socket
from datetime import datetime
from PyQt6.QtWidgets import QMessageBox

def is_enabled(parent):
    """Check if email search is enabled"""
    return hasattr(parent, 'enable_breach_email_checkbox') and parent.enable_breach_email_checkbox.isChecked()

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

def get_alternative_api_endpoints():
    """Return alternative endpoints for breach data (if Breach.vip is down)"""
    return [
        "https://breachdirectory.p.rapidapi.com/",
        "https://haveibeenpwned.com/api/v3/",
        # Note: These may require API keys or have different interfaces
    ]

def process_single_email(email, output_area):
    """Process a single email for Breach.vip search with wildcard support"""
    if not output_area:
        return
        
    # Check if email contains wildcards
    contains_wildcard = '*' in email or '?' in email
    
    # Validate email format with wildcard support
    if contains_wildcard:
        # For wildcard emails, we need more flexible validation
        # Split by @ to check basic structure
        parts = email.split('@')
        if len(parts) != 2:
            output_area.append(f"❌ Invalid email format (must contain exactly one @): {email}")
            return
            
        local_part, domain_part = parts
        
        # Check if wildcard starts with * or ? (not allowed by API)
        if local_part.startswith('*') or local_part.startswith('?'):
            output_area.append("❌ Wildcard queries cannot begin with * or ? in local part")
            return
            
        # Domain part can have wildcards anywhere (like *.com, gmail.*, etc.)
        # No validation needed for domain wildcards
    else:
        # Regular email validation for non-wildcard emails
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            output_area.append(f"❌ Invalid email format: {email}")
            return
    
    output_area.append(f"🔍 Searching Breach.vip for: {email}")
    if contains_wildcard:
        output_area.append("💡 Using wildcard search")
    
    # Check if Breach.vip is accessible
    if not check_breach_vip_status():
        output_area.append("⚠️  Breach.vip appears to be down or unreachable")
        if not contains_wildcard:
            output_area.append("💡 Trying alternative methods...")
            result = search_single_email_fallback(email)
            if result.get('success', False):
                data = result['data']
                display_email_results(data, email, output_area, source="Alternative")
            else:
                output_area.append("❌ All search methods failed")
                output_area.append("Please try again later or check your internet connection")
        return
    
    try:
        # Use field-specific search for better results
        result = search_single_email_api(email, contains_wildcard)
        
        if result.get('success', False):
            data = result['data']
            display_email_results(data, email, output_area, contains_wildcard)
        else:
            error_msg = result.get('error', 'Unknown error')
            output_area.append(f"❌ Search failed: {error_msg}")
            
            # If API returns 503/500, try fallback for non-wildcard emails
            if not contains_wildcard and ('503' in error_msg or '500' in error_msg or '429' in error_msg):
                output_area.append("🔄 Trying fallback method...")
                result = search_single_email_fallback(email)
                if result.get('success', False):
                    data = result['data']
                    display_email_results(data, email, output_area, source="Fallback")
            
    except Exception as e:
        output_area.append(f"❌ Error searching {email}: {e}")
        if not contains_wildcard:
            output_area.append("🔄 Trying fallback method...")
            result = search_single_email_fallback(email)
            if result.get('success', False):
                data = result['data']
                display_email_results(data, email, output_area, source="Fallback")

def search_single_email_fallback(email):
    """Fallback method for email search when API is down"""
    try:
        # For wildcard emails, we can't do DNS validation
        if '*' in email or '?' in email:
            return {
                'success': True,
                'data': {
                    'results': [],
                    'status': 'fallback',
                    'message': f'API unavailable. Wildcard email: {email}',
                    'valid_wildcard_email': True
                },
                'source': 'fallback'
            }
        
        # Try DNS-based check for regular emails
        domain = email.split('@')[-1]
        
        # Check if domain has MX records (basic validation)
        try:
            import dns.resolver
            mx_records = dns.resolver.resolve(domain, 'MX')
            has_mx = len(mx_records) > 0
        except:
            has_mx = True  # Assume valid if DNS check fails
        
        # Create a mock response with basic info
        return {
            'success': True,
            'data': {
                'results': [],
                'status': 'fallback',
                'message': f'API unavailable. Email format valid, domain: {domain}',
                'valid_email': True,
                'has_mx_records': has_mx
            },
            'source': 'fallback'
        }
    except Exception as e:
        return {
            'success': False,
            'error': f'Fallback failed: {str(e)[:100]}',
            'source': 'fallback'
        }

def process_email_file(file_path, output_area):
    """Process a file containing multiple emails for Breach.vip search"""
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
            emails = [line.strip() for line in f if line.strip()]
            
        if not emails:
            QMessageBox.warning(None, "File Error", "The file is empty or contains no valid entries.")
            return
            
        valid_entries = []
        invalid_entries = []
        wildcard_entries = []
        
        # Validate entries with wildcard support
        for entry in emails:
            contains_wildcard = '*' in entry or '?' in entry
            
            if contains_wildcard:
                # Validate wildcard email format
                parts = entry.split('@')
                if len(parts) != 2:
                    invalid_entries.append((entry, "Invalid format (must contain @)"))
                    continue
                    
                local_part, domain_part = parts
                
                # Check if wildcard starts with * or ? (not allowed by API)
                if local_part.startswith('*') or local_part.startswith('?'):
                    invalid_entries.append((entry, "Wildcard cannot start with * or ? in local part"))
                    continue
                    
                wildcard_entries.append(entry)
                valid_entries.append(entry)
            else:
                # Regular email validation
                if re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', entry):
                    valid_entries.append(entry)
                else:
                    invalid_entries.append((entry, "Invalid email format"))
                
        if not valid_entries:
            QMessageBox.warning(None, "File Error", "No valid email addresses or search terms found in the file.")
            return
            
        # Show confirmation dialog
        if len(valid_entries) > 1:
            warning_text = f"Found {len(valid_entries)} valid entry(s) and {len(invalid_entries)} invalid entry(s)."
            if wildcard_entries:
                warning_text += f"\nIncluding {len(wildcard_entries)} wildcard search(es)."
            
            reply = QMessageBox.question(
                None,
                "Multiple Entries Found",
                f"{warning_text}\n\nDo you want to search all {len(valid_entries)} entries?\n"
                f"This may take a while due to rate limits (15 requests per minute).",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
                
        # Process all valid entries
        output_area.append(f"📁 Processing {len(valid_entries)} entry(s) from file: {os.path.basename(file_path)}")
        if wildcard_entries:
            output_area.append(f"⚠️  Contains {len(wildcard_entries)} wildcard search(es)")
        if invalid_entries:
            output_area.append(f"⚠️  Skipped {len(invalid_entries)} invalid entries")
            
        output_area.append("=" * 60)
    
        # Create results directory if it doesn't exist
        results_dir = "results"
        if not os.path.exists(results_dir):
            os.makedirs(results_dir)
            
        # Generate batch filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        batch_filename = f"breach_vip_search_{timestamp}.txt"
        batch_filepath = os.path.join(results_dir, batch_filename)
        
        all_results = []
        service_down = False
        rate_limited = False
        
        for i, entry in enumerate(valid_entries, 1):
            if service_down:
                output_area.append(f"⚠️  Skipping remaining entries - service unavailable")
                break
                
            contains_wildcard = '*' in entry or '?' in entry
            entry_type = "wildcard_email" if '@' in entry and contains_wildcard else "email" if '@' in entry else "wildcard"
            output_area.append(f"\n🔍 [{i}/{len(valid_entries)}] Searching {entry_type}: {entry}")
            
            try:
                # Re-check service status periodically
                if i % 5 == 0 and not check_breach_vip_status():
                    output_area.append("❌ Breach.vip service became unavailable")
                    service_down = True
                    break
                
                result = search_single_email_api(entry, contains_wildcard)
                all_results.append({
                    'entry': entry,
                    'type': entry_type,
                    'result': result,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
                
                # Display brief result
                if result.get('success', False) and result.get('data'):
                    data = result['data']
                    if data.get('results') and len(data['results']) > 0:
                        record_count = len(data['results'])
                        unique_breaches = len(set(r.get('source', '') for r in data['results']))
                        max_shown = " (max 10,000 shown)" if record_count >= 10000 else ""
                        output_area.append(f"   🚨 Found {record_count} records across {unique_breaches} breaches{max_shown}")
                    else:
                        output_area.append(f"   ✅ No breach records found")
                else:
                    error_msg = result.get('error', 'Unknown error')
                    output_area.append(f"   ❌ Search failed: {error_msg}")
                    
                    # Check if it's a rate limit error
                    if '429' in error_msg or 'Rate limit' in error_msg:
                        output_area.append("   ⚠️  Rate limited by API")
                        rate_limited = True
                    elif '503' in error_msg or '500' in error_msg:
                        output_area.append("   ⚠️  Service error detected")
                
                # Respect rate limit - wait between requests
                if i < len(valid_entries):  # Don't wait after the last one
                    time.sleep(4)  # 4 seconds between requests to stay under 15/minute
                    
                # Handle rate limiting
                if rate_limited:
                    output_area.append("   💤 Rate limited, waiting 60 seconds...")
                    time.sleep(60)
                    rate_limited = False
                    
            except Exception as e:
                output_area.append(f"   ❌ Error searching {entry}: {e}")
                all_results.append({
                    'entry': entry,
                    'type': entry_type,
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
                output_area.append(f"⚠️  Search interrupted - {len(all_results)}/{len(valid_entries)} entries processed")
            else:
                output_area.append("🎉 Batch search completed!")
        else:
            output_area.append("❌ No results to save")
        
    except Exception as e:
        output_area.append(f"❌ Error processing file: {e}")

def search_single_email_api(search_term, is_wildcard=False):
    """Make API call to Breach.vip with support for wildcards and field searching"""
    try:
        url = "https://breach.vip/api/search"
        
        # Check if search term contains @ (email format)
        is_email_format = '@' in search_term
        
        # Prepare search fields
        if is_email_format:
            # For email formats, search specifically in email field
            fields = ["email"]
        elif is_wildcard:
            # For wildcard non-email terms, search in multiple fields
            fields = ["email", "username", "name", "ip_address", "domain", "password", "hash"]
        else:
            # For non-email terms without wildcards, search in username and name fields
            fields = ["username", "name"]
        
        payload = {
            "term": search_term,
            "fields": fields,
            "categories": None,
            "wildcard": is_wildcard,
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
            data = response.json()
            
            # Check if we hit the 10,000 result limit
            if data.get('results') and len(data['results']) >= 10000:
                data['warning'] = "Results limited to 10,000 records. Try a more specific search."
            
            return {
                'success': True,
                'data': data,
                'status_code': response.status_code,
                'is_wildcard': is_wildcard
            }
        else:
            error_msg = f"API returned status {response.status_code}"
            if response.status_code == 429:
                error_msg = "Rate limit exceeded (15 requests per minute)"
            elif response.status_code == 400:
                # Check if error is about wildcard starting with * or ?
                error_data = response.json() if response.content else {}
                if 'wildcard' in str(error_data).lower() or 'cannot start' in str(error_data).lower():
                    error_msg = "Wildcard queries cannot begin with * or ?"
                else:
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
                'status_code': response.status_code,
                'is_wildcard': is_wildcard
            }
            
    except requests.exceptions.Timeout:
        return {
            'success': False,
            'error': "Request timeout - service may be slow or down",
            'is_wildcard': is_wildcard
        }
    except requests.exceptions.ConnectionError:
        return {
            'success': False,
            'error': "Connection error - check your internet connection",
            'is_wildcard': is_wildcard
        }
    except requests.exceptions.RequestException as e:
        return {
            'success': False,
            'error': f"Network error: {e}",
            'is_wildcard': is_wildcard
        }
    except Exception as e:
        return {
            'success': False,
            'error': f"Unexpected error: {e}",
            'is_wildcard': is_wildcard
        }

def save_batch_results(all_results, filepath, output_area):
    """Save batch email results to file"""
    try:
        # Calculate summary stats
        successful_searches = sum(1 for r in all_results if r['result'].get('success'))
        total_records = sum(len(r['result'].get('data', {}).get('results', [])) 
                          for r in all_results if r['result'].get('success'))
        entries_with_breaches = sum(1 for r in all_results 
                                 if r['result'].get('success') and 
                                 r['result'].get('data', {}).get('results'))
        wildcard_searches = sum(1 for r in all_results if 'wildcard' in r.get('type', ''))
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("BREACH.VIP SEARCH RESULTS\n")
            f.write("=" * 60 + "\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Entries Searched: {len(all_results)}\n")
            if wildcard_searches > 0:
                f.write(f"Wildcard Searches: {wildcard_searches}\n")
            f.write("=" * 60 + "\n\n")
            
            for result in all_results:
                entry = result['entry']
                entry_type = result.get('type', 'email')
                search_result = result['result']
                timestamp = result['timestamp']
                
                f.write(f"ENTRY: {entry}\n")
                f.write(f"TYPE: {entry_type.upper()}\n")
                f.write(f"SEARCH TIME: {timestamp}\n")
                f.write(f"STATUS: {'SUCCESS' if search_result.get('success') else 'FAILED'}\n")
                
                if search_result.get('success') and search_result.get('data'):
                    data = search_result['data']
                    
                    # Check for warning about result limit
                    if data.get('warning'):
                        f.write(f"WARNING: {data['warning']}\n")
                    
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
                            
                        # Show sample data (limit to 5 records per entry)
                        f.write("SAMPLE DATA (First 5 records):\n")
                        sample_records = records[:5]
                        for i, record in enumerate(sample_records, 1):
                            f.write(f"  Record {i}:\n")
                            for key, value in record.items():
                                if value and key not in ['source', 'categories']:
                                    f.write(f"    {key}: {value}\n")
                            if i < len(sample_records):
                                f.write("    ---\n")
                                
                        # If there are more records, indicate this
                        if len(records) > 5:
                            f.write(f"  ... and {len(records) - 5} more records\n")
                            
                        # Show unique count of matching fields
                        if 'wildcard' in entry_type:
                            f.write("MATCHING FIELDS:\n")
                            field_matches = {}
                            for record in records:
                                for field in ['email', 'username', 'name', 'ip_address', 'domain', 'password']:
                                    if field in record and record[field]:
                                        if field not in field_matches:
                                            field_matches[field] = 0
                                        field_matches[field] += 1
                            
                            for field, count in field_matches.items():
                                f.write(f"  {field}: {count} matches\n")
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
            f.write(f"Entries with breaches: {entries_with_breaches}\n")
            f.write(f"Total breach records found: {total_records}\n")
            if wildcard_searches > 0:
                f.write(f"Wildcard searches performed: {wildcard_searches}\n")
            f.write("=" * 60 + "\n")
            
    except Exception as e:
        if output_area:
            output_area.append(f"❌ Error saving batch results: {e}")

def display_email_results(data, search_term, output_area, is_wildcard=False, source="Breach.vip"):
    """Display email breach results in a formatted way and save to file"""
    if not output_area:
        return
        
    # Determine search type
    if '@' in search_term:
        search_type = "WILDCARD_EMAIL" if is_wildcard else "EMAIL"
    else:
        search_type = "WILDCARD" if is_wildcard else "TERM"
        
    output_area.append(f"\n📊 {source.upper()} {search_type} RESULTS FOR: {search_term}")
    output_area.append("=" * 60)
    
    # Create results directory if it doesn't exist
    results_dir = "results"
    if not os.path.exists(results_dir):
        os.makedirs(results_dir)
        
    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_term = re.sub(r'[^\w\-_.*?@]', '_', search_term)
    filename = f"{source.lower()}_{search_type.lower()}_{safe_term}_{timestamp}.txt"
    filepath = os.path.join(results_dir, filename)
    
    # Prepare content
    display_lines = []
    file_lines = []
    
    try:
        if source.lower() == 'fallback':
            # Handle fallback response format
            display_lines.append(f"⚠️  Using fallback method (Breach.vip API unavailable)")
            display_lines.append(f"🔍 Search term: {search_term}")
            if is_wildcard and '@' in search_term:
                display_lines.append("✅ Valid wildcard email format")
            elif data.get('valid_email'):
                display_lines.append("✅ Email format is valid")
            if data.get('valid_wildcard_email'):
                display_lines.append("✅ Valid wildcard email format")
            if data.get('has_mx_records'):
                display_lines.append("✅ Domain has MX records")
            if data.get('message'):
                display_lines.append(f"💡 {data['message']}")
            
            file_lines.append(f"{source.upper()} SEARCH RESULTS FOR: {search_term}")
            file_lines.append(f"Search Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            file_lines.append(f"Status: Breach.vip API unavailable, using fallback check")
            if is_wildcard and '@' in search_term:
                file_lines.append(f"Type: WILDCARD EMAIL")
            elif data.get('valid_email'):
                file_lines.append(f"Email Validation: VALID")
            if data.get('valid_wildcard_email'):
                file_lines.append(f"Wildcard Email: VALID")
            if data.get('has_mx_records'):
                file_lines.append(f"MX Records: PRESENT")
            file_lines.append(f"Note: Full breach check requires Breach.vip API access")
            
        elif 'results' in data and isinstance(data['results'], list):
            # Original Breach.vip response handling
            results = data['results']
            
            if len(results) > 0:
                max_results_note = ""
                if len(results) >= 10000:
                    max_results_note = " (max limit reached)"
                    display_lines.append(f"⚠️  Maximum of 10,000 results shown. Try a more specific search.")
                
                display_lines.append(f"🚨 Found {len(results)} breach record(s){max_results_note}")
                file_lines.append(f"BREACH.VIP {search_type} RESULTS FOR: {search_term}")
                file_lines.append(f"Search Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                file_lines.append(f"Records Found: {len(results)}{max_results_note}")
                if data.get('warning'):
                    file_lines.append(f"Warning: {data['warning']}")
                file_lines.append("=" * 60)
                file_lines.append("")
                
                # Show unique breach sources
                unique_breaches = set(r.get('source', 'Unknown Source') for r in results)
                display_lines.append(f"📊 Breach Sources ({len(unique_breaches)} unique):")
                for breach in sorted(unique_breaches)[:10]:  # Show first 10
                    count = sum(1 for r in results if r.get('source') == breach)
                    display_lines.append(f"   • {breach}: {count} record(s)")
                
                if len(unique_breaches) > 10:
                    display_lines.append(f"   ... and {len(unique_breaches) - 10} more breaches")
                
                # For wildcard searches, show which fields matched
                if is_wildcard:
                    display_lines.append("")
                    display_lines.append("🔍 Matching Fields:")
                    field_counts = {}
                    for result in results:
                        for field in ['email', 'username', 'name', 'ip_address', 'domain', 'password', 'hash']:
                            if field in result and result[field]:
                                field_counts[field] = field_counts.get(field, 0) + 1
                    
                    for field, count in sorted(field_counts.items()):
                        display_lines.append(f"   • {field}: {count} match(es)")
                
                # Show sample records (limit to 3 for display)
                display_lines.append("")
                display_lines.append("📋 Sample Records:")
                for i, result in enumerate(results[:3], 1):
                    display_lines.append(f"   📦 Record #{i}:")
                    
                    # Source (breach name)
                    source_name = result.get('source', 'Unknown Source')
                    display_lines.append(f"      📛 Breach: {source_name}")
                    
                    # Show key fields
                    key_fields = ['email', 'username', 'name', 'password', 'ip_address', 'domain', 'hash']
                    for field in key_fields:
                        if field in result and result[field]:
                            value = str(result[field])
                            if len(value) > 50:
                                value = value[:47] + "..."
                            display_lines.append(f"      🔍 {field}: {value}")
                    
                    display_lines.append("")
                
                # File content - more detailed
                for i, result in enumerate(results[:10], 1):  # Show first 10 in file
                    file_lines.append(f"RECORD #{i}:")
                    
                    # Source (breach name)
                    source_name = result.get('source', 'Unknown Source')
                    file_lines.append(f"Breach: {source_name}")
                    
                    # Categories
                    categories = result.get('categories')
                    if categories:
                        if isinstance(categories, list):
                            file_lines.append(f"Categories: {', '.join(categories)}")
                        else:
                            file_lines.append(f"Category: {categories}")
                            
                    # Show all other fields
                    for field_name, field_value in result.items():
                        if field_name not in ['source', 'categories'] and field_value:
                            file_lines.append(f"{field_name}: {field_value}")
                    
                    file_lines.append("")
                
                # Summary
                display_lines.append(f"📈 Summary: {len(results)} records across {len(unique_breaches)} unique breaches")
                file_lines.append(f"SUMMARY: {len(results)} records across {len(unique_breaches)} unique breaches")
                
                # Add note about viewing full results
                if len(results) > 10:
                    file_lines.append(f"Note: Showing first 10 of {len(results)} total records")
                    file_lines.append(f"See saved file for complete results.")
                
            else:
                display_lines.append("✅ No breach records found")
                display_lines.append("💡 This search term appears clean in Breach.vip database")
                
                file_lines.append(f"BREACH.VIP {search_type} RESULTS FOR: {search_term}")
                file_lines.append(f"Search Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                file_lines.append("RESULTS: No breach records found")
                file_lines.append("STATUS: Search term appears clean in Breach.vip database")
        else:
            display_lines.append("❌ Unexpected response format from API")
            file_lines.append(f"BREACH.VIP {search_type} RESULTS FOR: {search_term}")
            file_lines.append(f"Search Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            file_lines.append("ERROR: Unexpected response format from API")
            
    except Exception as e:
        error_msg = f"❌ Error processing results: {e}"
        display_lines.append(error_msg)
        file_lines.append(f"{source.upper()} {search_type} RESULTS FOR: {search_term}")
        file_lines.append(f"Search Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        file_lines.append(f"ERROR: {error_msg}")
        
    # Add footer
    display_lines.append("=" * 60)
    if source == "Breach.vip":
        if is_wildcard:
            display_lines.append("💡 Note: Wildcard searches may return up to 10,000 results")
        if '@' in search_term:
            display_lines.append("💡 Note: Searching in email field only")
        display_lines.append("💡 Note: Rate limit is 15 requests per minute")
        file_lines.append("=" * 60)
        file_lines.append(f"Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        if is_wildcard:
            file_lines.append("Note: Wildcard searches are limited to 10,000 results")
        file_lines.append("Note: Breach.vip rate limit is 15 requests per minute")
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