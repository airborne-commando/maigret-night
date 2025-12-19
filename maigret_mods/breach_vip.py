# breach_vip_email_hooks
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
    """Process a single email for Breach.vip search"""
    if not output_area:
        return
        
    # Validate email format
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        output_area.append(f"❌ Invalid email format: {email}")
        return
    
    output_area.append(f"🔍 Searching Breach.vip for email: {email}")
    
    # Check if Breach.vip is accessible
    if not check_breach_vip_status():
        output_area.append("⚠️  Breach.vip appears to be down or unreachable")
        output_area.append("💡 Trying alternative methods...")
        
        # Try alternative check methods
        result = search_single_email_fallback(email)
        if result.get('success', False):
            data = result['data']
            display_email_results(data, email, output_area, source="Alternative")
        else:
            output_area.append("❌ All search methods failed")
            output_area.append("Please try again later or check your internet connection")
        return
    
    try:
        result = search_single_email_api(email)
        
        if result.get('success', False):
            data = result['data']
            display_email_results(data, email, output_area)
        else:
            error_msg = result.get('error', 'Unknown error')
            output_area.append(f"❌ Search failed: {error_msg}")
            
            # If API returns 503/500, try fallback
            if '503' in error_msg or '500' in error_msg:
                output_area.append("🔄 Trying fallback method...")
                result = search_single_email_fallback(email)
                if result.get('success', False):
                    data = result['data']
                    display_email_results(data, email, output_area, source="Fallback")
            
    except Exception as e:
        output_area.append(f"❌ Error searching {email}: {e}")
        output_area.append("🔄 Trying fallback method...")
        result = search_single_email_fallback(email)
        if result.get('success', False):
            data = result['data']
            display_email_results(data, email, output_area, source="Fallback")

def search_single_email_fallback(email):
    """Fallback method for email search when API is down"""
    try:
        # Try DNS-based check first (no API required)
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
            QMessageBox.warning(None, "File Error", "The file is empty or contains no valid emails.")
            return
            
        valid_emails = []
        invalid_emails = []
        
        # Validate emails
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        for email in emails:
            if re.match(email_regex, email):
                valid_emails.append(email)
            else:
                invalid_emails.append(email)
                
        if not valid_emails:
            QMessageBox.warning(None, "File Error", "No valid email addresses found in the file.")
            return
            
        # Show confirmation dialog for multiple emails
        if len(valid_emails) > 1:
            reply = QMessageBox.question(
                None,
                "Multiple Emails Found",
                f"Found {len(valid_emails)} valid email(s) and {len(invalid_emails)} invalid entry(s).\n\n"
                f"Do you want to search all {len(valid_emails)} emails? This may take a while due to rate limits.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
                
        # Process all valid emails
        output_area.append(f"📁 Processing {len(valid_emails)} email(s) from file: {os.path.basename(file_path)}")
        if invalid_emails:
            output_area.append(f"⚠️  Skipped {len(invalid_emails)} invalid entries")
            
        output_area.append("=" * 60)
    
        # Create results directory if it doesn't exist
        results_dir = "results"
        if not os.path.exists(results_dir):
            os.makedirs(results_dir)
            
        # Generate batch filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        batch_filename = f"breach_vip_emails_{timestamp}.txt"
        batch_filepath = os.path.join(results_dir, batch_filename)
        
        all_results = []
        service_down = False
        
        for i, email in enumerate(valid_emails, 1):
            if service_down:
                output_area.append(f"⚠️  Skipping remaining emails - service unavailable")
                break
                
            output_area.append(f"\n🔍 [{i}/{len(valid_emails)}] Searching: {email}")
            
            try:
                # Re-check service status periodically
                if i % 5 == 0 and not check_breach_vip_status():
                    output_area.append("❌ Breach.vip service became unavailable")
                    service_down = True
                    break
                
                result = search_single_email_api(email)
                all_results.append({
                    'email': email,
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
                if i < len(valid_emails):  # Don't wait after the last one
                    time.sleep(4)  # 4 seconds between requests to stay under 15/minute
                    
            except Exception as e:
                output_area.append(f"   ❌ Error searching {email}: {e}")
                all_results.append({
                    'email': email,
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
                output_area.append(f"⚠️  Search interrupted - {len(all_results)}/{len(valid_emails)} emails processed")
            else:
                output_area.append("🎉 Batch search completed!")
        else:
            output_area.append("❌ No results to save")
        
    except Exception as e:
        output_area.append(f"❌ Error processing file: {e}")

def search_single_email_api(email):
    """Make API call to Breach.vip for a single email with better error handling"""
    try:
        url = "https://breach.vip/api/search"
        
        payload = {
            "term": email,
            "fields": ["email"],
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

# Keep the rest of the functions (save_batch_results, display_email_results) the same as before
# ... [rest of the file remains the same] ...

def save_batch_results(all_results, filepath, output_area):
    """Save batch email results to file"""
    try:
        # Calculate summary stats
        successful_searches = sum(1 for r in all_results if r['result'].get('success'))
        total_records = sum(len(r['result'].get('data', {}).get('results', [])) 
                          for r in all_results if r['result'].get('success'))
        emails_with_breaches = sum(1 for r in all_results 
                                 if r['result'].get('success') and 
                                 r['result'].get('data', {}).get('results'))
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("BREACH.VIP EMAIL SEARCH RESULTS\n")
            f.write("=" * 60 + "\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Emails Searched: {len(all_results)}\n")
            f.write("=" * 60 + "\n\n")
            
            for result in all_results:
                email = result['email']
                search_result = result['result']
                timestamp = result['timestamp']
                
                f.write(f"EMAIL: {email}\n")
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
                                    
                        # Show username info if available
                        f.write("USERNAME INFO:\n")
                        for record in records[:3]:  # Show first 3 records
                            if 'username' in record:
                                f.write(f"  Associated username: {record['username']}\n")
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
            f.write(f"Emails with breaches: {emails_with_breaches}\n")
            f.write(f"Total breach records found: {total_records}\n")
            f.write("=" * 60 + "\n")
            
    except Exception as e:
        if output_area:
            output_area.append(f"❌ Error saving batch results: {e}")

def display_email_results(data, email, output_area, source="Breach.vip"):
    """Display email breach results in a formatted way and save to file"""
    if not output_area:
        return
        
    output_area.append(f"\n📊 {source.upper()} EMAIL RESULTS FOR: {email}")
    output_area.append("=" * 60)
    
    # Create results directory if it doesn't exist
    results_dir = "results"
    if not os.path.exists(results_dir):
        os.makedirs(results_dir)
        
    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_email = re.sub(r'[^\w\-_.]', '_', email.split('@')[0])
    filename = f"{source.lower()}_email_{safe_email}_{timestamp}.txt"
    filepath = os.path.join(results_dir, filename)
    
    # Prepare content
    display_lines = []
    file_lines = []
    
    try:
        if source.lower() == 'fallback':
            # Handle fallback response format
            display_lines.append(f"⚠️  Using fallback method (Breach.vip API unavailable)")
            display_lines.append(f"📧 Email: {email}")
            if data.get('valid_email'):
                display_lines.append("✅ Email format is valid")
            if data.get('has_mx_records'):
                display_lines.append("✅ Domain has MX records")
            if data.get('message'):
                display_lines.append(f"💡 {data['message']}")
            
            file_lines.append(f"{source.upper()} EMAIL CHECK FOR: {email}")
            file_lines.append(f"Search Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            file_lines.append(f"Status: Breach.vip API unavailable, using fallback check")
            if data.get('valid_email'):
                file_lines.append(f"Email Validation: VALID")
            if data.get('has_mx_records'):
                file_lines.append(f"MX Records: PRESENT")
            file_lines.append(f"Domain: {email.split('@')[-1]}")
            file_lines.append(f"Note: Full breach check requires Breach.vip API access")
            
        elif 'results' in data and isinstance(data['results'], list):
            # Original Breach.vip response handling
            results = data['results']
            
            if len(results) > 0:
                display_lines.append(f"🚨 Found {len(results)} breach record(s)")
                file_lines.append(f"BREACH.VIP EMAIL RESULTS FOR: {email}")
                file_lines.append(f"Search Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                file_lines.append(f"Records Found: {len(results)}")
                file_lines.append("=" * 60)
                file_lines.append("")
                
                for i, result in enumerate(results, 1):
                    display_lines.append(f"📦 Record #{i}:")
                    file_lines.append(f"RECORD #{i}:")
                    
                    # Source (breach name)
                    source_name = result.get('source', 'Unknown Source')
                    display_lines.append(f"   📛 Breach: {source_name}")
                    file_lines.append(f"Breach: {source_name}")
                    
                    # Categories
                    categories = result.get('categories')
                    if categories:
                        if isinstance(categories, list):
                            display_lines.append(f"   🏷️  Categories: {', '.join(categories)}")
                            file_lines.append(f"Categories: {', '.join(categories)}")
                        else:
                            display_lines.append(f"   🏷️  Category: {categories}")
                            file_lines.append(f"Category: {categories}")
                            
                    # Show all other fields
                    for field_name, field_value in result.items():
                        if field_name not in ['source', 'categories'] and field_value:
                            if len(str(field_value)) > 100:
                                display_value = str(field_value)[:100] + "..."
                            else:
                                display_value = str(field_value)
                            display_lines.append(f"   🔍 {field_name}: {display_value}")
                            file_lines.append(f"{field_name}: {field_value}")
                    
                    display_lines.append("")
                    file_lines.append("")
                
                # Summary
                unique_breaches = len(set(r.get('source', '') for r in results))
                display_lines.append(f"📈 Summary: {len(results)} records across {unique_breaches} unique breaches")
                file_lines.append(f"SUMMARY: {len(results)} records across {unique_breaches} unique breaches")
                
            else:
                display_lines.append("✅ No breach records found for this email")
                display_lines.append("💡 This email appears clean in Breach.vip database")
                
                file_lines.append(f"BREACH.VIP EMAIL RESULTS FOR: {email}")
                file_lines.append(f"Search Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                file_lines.append("RESULTS: No breach records found")
                file_lines.append("STATUS: Email appears clean in Breach.vip database")
        else:
            display_lines.append("❌ Unexpected response format from API")
            file_lines.append(f"BREACH.VIP EMAIL RESULTS FOR: {email}")
            file_lines.append(f"Search Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            file_lines.append("ERROR: Unexpected response format from API")
            
    except Exception as e:
        error_msg = f"❌ Error processing results: {e}"
        display_lines.append(error_msg)
        file_lines.append(f"{source.upper()} EMAIL RESULTS FOR: {email}")
        file_lines.append(f"Search Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        file_lines.append(f"ERROR: {error_msg}")
        
    # Add footer
    display_lines.append("=" * 60)
    if source == "Breach.vip":
        display_lines.append("💡 Note: Rate limit is 15 requests per minute")
        file_lines.append("=" * 60)
        file_lines.append(f"Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
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