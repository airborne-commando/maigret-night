#!/usr/bin/env python3
"""
Frequency Analyzer for Blackbird Web Interface
Analyzes historical search results to determine how often usernames appear on websites
"""

import os
import json
import csv
import re
from datetime import datetime
from collections import defaultdict, Counter
import glob
from pathlib import Path
from typing import Dict, List, Tuple, Set, Optional
import hashlib

class FrequencyAnalyzer:
    """Analyze frequency of usernames across historical search results"""
    
    def __init__(self, reports_folder: str):
        """
        Initialize the analyzer with the reports folder
        
        Args:
            reports_folder: Path to the folder containing Blackbird results
        """
        self.reports_folder = Path(reports_folder)
        self.username_cache = {}  # Cache for username lookups
        self.frequency_cache = {}  # Cache for frequency data
        self.cache_file = self.reports_folder / ".frequency_cache.json"
        self.last_scan_time = None
        
        # Load cache if exists
        self._load_cache()
    
    def _load_cache(self):
        """Load frequency cache from file"""
        try:
            if self.cache_file.exists():
                with open(self.cache_file, 'r') as f:
                    cache_data = json.load(f)
                    self.frequency_cache = cache_data.get('frequency_data', {})
                    self.last_scan_time = cache_data.get('last_scan_time')
                    print(f"Loaded frequency cache with {len(self.frequency_cache)} entries")
        except Exception as e:
            print(f"Error loading cache: {e}")
            self.frequency_cache = {}
    
    def _save_cache(self):
        """Save frequency cache to file"""
        try:
            cache_data = {
                'frequency_data': self.frequency_cache,
                'last_scan_time': datetime.now().isoformat(),
                'version': '1.0'
            }
            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
            print(f"Saved frequency cache with {len(self.frequency_cache)} entries")
        except Exception as e:
            print(f"Error saving cache: {e}")
    
    def scan_reports(self, force_rescan: bool = False) -> Dict:
        """
        Scan all reports and build frequency statistics
        
        Args:
            force_rescan: If True, rescan all files even if cache exists
            
        Returns:
            Dictionary with frequency statistics
        """
        # Check if we need to rescan
        if not force_rescan and self.frequency_cache and self._is_cache_fresh():
            print("Using cached frequency data")
            return self.frequency_cache
        
        print("Scanning reports for frequency analysis...")
        
        # Initialize statistics
        frequency_data = {
            'total_reports': 0,
            'total_accounts': 0,
            'unique_usernames': set(),
            'unique_emails': set(),
            'unique_sites': set(),
            'site_frequency': defaultdict(int),  # site -> count
            'username_frequency': defaultdict(int),  # username -> total sites found
            'username_site_map': defaultdict(set),  # username -> set of sites
            'site_username_map': defaultdict(set),  # site -> set of usernames
            'category_frequency': defaultdict(int),  # category -> count
            'recent_searches': [],  # Most recent searches
            'search_timeline': defaultdict(list),  # date -> list of searches
            'last_scan': datetime.now().isoformat()
        }
        
        # Find all JSON and CSV files
        json_files = list(self.reports_folder.rglob("*.json"))
        csv_files = list(self.reports_folder.rglob("*.csv"))
        
        print(f"Found {len(json_files)} JSON files and {len(csv_files)} CSV files")
        
        # Process JSON files
        for json_file in json_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Extract username/email from filename
                filename = json_file.stem
                username_match = re.match(r'^([^_]+)_', filename)
                if username_match:
                    username = username_match.group(1)
                    
                    # Check if this is email or username
                    is_email = '@' in username
                    
                    if is_email:
                        frequency_data['unique_emails'].add(username)
                        identifier = f"email:{username}"
                    else:
                        frequency_data['unique_usernames'].add(username)
                        identifier = f"username:{username}"
                    
                    frequency_data['total_reports'] += 1
                    
                    # Process found accounts
                    if isinstance(data, list):
                        for account in data:
                            site_name = account.get('name', 'Unknown')
                            category = account.get('category', 'unknown')
                            status = account.get('status', 'UNKNOWN')
                            
                            if status == 'FOUND':
                                frequency_data['total_accounts'] += 1
                                frequency_data['unique_sites'].add(site_name)
                                frequency_data['site_frequency'][site_name] += 1
                                frequency_data['username_frequency'][identifier] += 1
                                frequency_data['username_site_map'][identifier].add(site_name)
                                frequency_data['site_username_map'][site_name].add(identifier)
                                frequency_data['category_frequency'][category] += 1
                    
                    # Add to timeline
                    try:
                        # Extract date from folder structure
                        date_match = re.search(r'(\d{2})_(\d{2})_(\d{4})', str(json_file.parent))
                        if date_match:
                            date_str = f"{date_match.group(3)}-{date_match.group(1)}-{date_match.group(2)}"
                            frequency_data['search_timeline'][date_str].append({
                                'username': username,
                                'file': str(json_file.relative_to(self.reports_folder)),
                                'timestamp': datetime.fromtimestamp(json_file.stat().st_mtime).isoformat(),
                                'accounts_found': len([a for a in data if isinstance(data, list) and a.get('status') == 'FOUND'])
                            })
                    except:
                        pass
                        
            except Exception as e:
                print(f"Error processing {json_file}: {e}")
                continue
        
        # Process CSV files
        for csv_file in csv_files:
            try:
                # Skip if we already processed the JSON version
                json_version = csv_file.with_suffix('.json')
                if json_version.exists():
                    continue
                
                # Extract username/email from filename
                filename = csv_file.stem
                username_match = re.match(r'^([^_]+)_', filename)
                if username_match:
                    username = username_match.group(1)
                    is_email = '@' in username
                    
                    if is_email:
                        identifier = f"email:{username}"
                    else:
                        identifier = f"username:{username}"
                    
                    frequency_data['total_reports'] += 1
                    
                    # Read CSV
                    with open(csv_file, 'r', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            site_name = row.get('Site', 'Unknown')
                            category = row.get('Category', 'unknown')
                            status = row.get('Status', 'UNKNOWN')
                            
                            if status == 'FOUND':
                                frequency_data['total_accounts'] += 1
                                frequency_data['unique_sites'].add(site_name)
                                frequency_data['site_frequency'][site_name] += 1
                                frequency_data['username_frequency'][identifier] += 1
                                frequency_data['username_site_map'][identifier].add(site_name)
                                frequency_data['site_username_map'][site_name].add(identifier)
                                frequency_data['category_frequency'][category] += 1
                                
            except Exception as e:
                print(f"Error processing {csv_file}: {e}")
                continue
        
        # Convert sets to lists for JSON serialization
        frequency_data['unique_usernames'] = list(frequency_data['unique_usernames'])
        frequency_data['unique_emails'] = list(frequency_data['unique_emails'])
        frequency_data['unique_sites'] = list(frequency_data['unique_sites'])
        
        # Convert defaultdict to regular dict
        frequency_data['site_frequency'] = dict(frequency_data['site_frequency'])
        frequency_data['username_frequency'] = dict(frequency_data['username_frequency'])
        frequency_data['username_site_map'] = {k: list(v) for k, v in frequency_data['username_site_map'].items()}
        frequency_data['site_username_map'] = {k: list(v) for k, v in frequency_data['site_username_map'].items()}
        frequency_data['category_frequency'] = dict(frequency_data['category_frequency'])
        frequency_data['search_timeline'] = dict(frequency_data['search_timeline'])
        
        # Get recent searches (last 10)
        all_searches = []
        for date_str, searches in frequency_data['search_timeline'].items():
            for search in searches:
                search['date'] = date_str
                all_searches.append(search)
        
        # Sort by timestamp (most recent first)
        all_searches.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        frequency_data['recent_searches'] = all_searches[:10]
        
        # Update cache
        self.frequency_cache = frequency_data
        self._save_cache()
        
        print(f"Frequency analysis complete:")
        print(f"  - Total reports: {frequency_data['total_reports']}")
        print(f"  - Unique usernames: {len(frequency_data['unique_usernames'])}")
        print(f"  - Unique emails: {len(frequency_data['unique_emails'])}")
        print(f"  - Unique sites: {len(frequency_data['unique_sites'])}")
        print(f"  - Total accounts found: {frequency_data['total_accounts']}")
        
        return frequency_data
    
    def _is_cache_fresh(self, max_age_hours: int = 1) -> bool:
        """Check if cache is fresh enough"""
        if not self.last_scan_time:
            return False
        
        try:
            last_scan = datetime.fromisoformat(self.last_scan_time)
            age = datetime.now() - last_scan
            return age.total_seconds() < (max_age_hours * 3600)
        except:
            return False
    
    def get_username_frequency(self, username: str) -> Dict:
        """
        Get frequency statistics for a specific username
        
        Args:
            username: Username to analyze
            
        Returns:
            Dictionary with frequency statistics for the username
        """
        # Ensure we have fresh data
        if not self.frequency_cache:
            self.scan_reports()
        
        # Check both username and email formats
        identifiers_to_check = [f"username:{username}"]
        if '@' in username:
            identifiers_to_check.append(f"email:{username}")
        
        result = {
            'username': username,
            'total_searches': 0,
            'sites_found': [],
            'site_count': 0,
            'categories': defaultdict(int),
            'first_seen': None,
            'last_seen': None,
            'search_history': []
        }
        
        for identifier in identifiers_to_check:
            if identifier in self.frequency_cache.get('username_site_map', {}):
                sites = self.frequency_cache['username_site_map'][identifier]
                result['sites_found'].extend(sites)
                result['site_count'] = len(sites)
                result['total_searches'] = self.frequency_cache['username_frequency'].get(identifier, 0)
        
        # Get category distribution
        for site in result['sites_found']:
            # Try to get category from site data
            # This would require additional data - for now we'll skip
            pass
        
        # Get search history from timeline
        for date_str, searches in self.frequency_cache.get('search_timeline', {}).items():
            for search in searches:
                if search['username'] == username:
                    result['search_history'].append({
                        'date': date_str,
                        'accounts_found': search['accounts_found'],
                        'file': search['file']
                    })
        
        # Sort search history by date
        result['search_history'].sort(key=lambda x: x['date'], reverse=True)
        
        # Get first and last seen
        if result['search_history']:
            result['first_seen'] = result['search_history'][-1]['date']
            result['last_seen'] = result['search_history'][0]['date']
        
        return result
    
    def get_site_frequency(self, site_name: str) -> Dict:
        """
        Get frequency statistics for a specific site
        
        Args:
            site_name: Site name to analyze
            
        Returns:
            Dictionary with frequency statistics for the site
        """
        if not self.frequency_cache:
            self.scan_reports()
        
        result = {
            'site_name': site_name,
            'total_found': self.frequency_cache.get('site_frequency', {}).get(site_name, 0),
            'usernames_found': self.frequency_cache.get('site_username_map', {}).get(site_name, []),
            'username_count': len(self.frequency_cache.get('site_username_map', {}).get(site_name, [])),
            'popularity_rank': 0,
            'percentage_of_searches': 0
        }
        
        # Calculate popularity rank
        if self.frequency_cache.get('site_frequency'):
            sorted_sites = sorted(
                self.frequency_cache['site_frequency'].items(),
                key=lambda x: x[1],
                reverse=True
            )
            for rank, (site, _) in enumerate(sorted_sites, 1):
                if site == site_name:
                    result['popularity_rank'] = rank
                    break
        
        # Calculate percentage
        total_accounts = self.frequency_cache.get('total_accounts', 1)
        result['percentage_of_searches'] = (result['total_found'] / total_accounts * 100) if total_accounts > 0 else 0
        
        return result
    
    def get_most_common_sites(self, limit: int = 10) -> List[Tuple[str, int]]:
        """Get most commonly found sites"""
        if not self.frequency_cache:
            self.scan_reports()
        
        site_freq = self.frequency_cache.get('site_frequency', {})
        return sorted(site_freq.items(), key=lambda x: x[1], reverse=True)[:limit]
    
    def get_most_active_usernames(self, limit: int = 10) -> List[Tuple[str, int]]:
        """Get usernames found on most sites"""
        if not self.frequency_cache:
            self.scan_reports()
        
        username_freq = {}
        for identifier, sites in self.frequency_cache.get('username_site_map', {}).items():
            username_freq[identifier] = len(sites)
        
        return sorted(username_freq.items(), key=lambda x: x[1], reverse=True)[:limit]
    
    def search_historical_data(self, search_term: str) -> Dict:
        """
        Search historical data for usernames or sites containing search term
        
        Args:
            search_term: Term to search for
            
        Returns:
            Search results
        """
        if not self.frequency_cache:
            self.scan_reports()
        
        results = {
            'usernames': [],
            'emails': [],
            'sites': [],
            'total_matches': 0
        }
        
        search_term_lower = search_term.lower()
        
        # Search usernames
        for username in self.frequency_cache.get('unique_usernames', []):
            if search_term_lower in username.lower():
                freq_data = self.get_username_frequency(username)
                results['usernames'].append({
                    'username': username,
                    'site_count': freq_data['site_count'],
                    'first_seen': freq_data['first_seen'],
                    'last_seen': freq_data['last_seen']
                })
        
        # Search emails
        for email in self.frequency_cache.get('unique_emails', []):
            if search_term_lower in email.lower():
                freq_data = self.get_username_frequency(email)
                results['emails'].append({
                    'email': email,
                    'site_count': freq_data['site_count'],
                    'first_seen': freq_data['first_seen'],
                    'last_seen': freq_data['last_seen']
                })
        
        # Search sites
        for site in self.frequency_cache.get('unique_sites', []):
            if search_term_lower in site.lower():
                freq_data = self.get_site_frequency(site)
                results['sites'].append({
                    'site': site,
                    'total_found': freq_data['total_found'],
                    'username_count': freq_data['username_count'],
                    'popularity_rank': freq_data['popularity_rank']
                })
        
        results['total_matches'] = (
            len(results['usernames']) + 
            len(results['emails']) + 
            len(results['sites'])
        )
        
        return results
    
    def get_overall_statistics(self) -> Dict:
        """Get overall statistics"""
        if not self.frequency_cache:
            self.scan_reports()
        
        return {
            'total_reports': self.frequency_cache.get('total_reports', 0),
            'total_accounts': self.frequency_cache.get('total_accounts', 0),
            'unique_usernames': len(self.frequency_cache.get('unique_usernames', [])),
            'unique_emails': len(self.frequency_cache.get('unique_emails', [])),
            'unique_sites': len(self.frequency_cache.get('unique_sites', [])),
            'most_common_sites': self.get_most_common_sites(5),
            'most_active_usernames': self.get_most_active_usernames(5),
            'last_scan': self.frequency_cache.get('last_scan', 'Never'),
            'cache_fresh': self._is_cache_fresh()
        }

    def get_username_sites(self, username: str) -> dict:
        """
        Get all sites where a username was found
        
        Args:
            username: Username to look up
            
        Returns:
            Dictionary with sites and their details
        """
        if not self.frequency_cache:
            self.scan_reports()
        
        # Check both username and email formats
        identifiers_to_check = [f"username:{username}"]
        if '@' in username:
            identifiers_to_check.append(f"email:{username}")
        
        sites = []
        
        for identifier in identifiers_to_check:
            if identifier in self.frequency_cache.get('username_site_map', {}):
                site_list = self.frequency_cache['username_site_map'][identifier]
                
                # Get additional details for each site
                for site_name in site_list:
                    site_details = {
                        'site_name': site_name,
                        'found_count': self.frequency_cache.get('site_frequency', {}).get(site_name, 0),
                        'popularity_rank': 0,
                        'found_date': None
                    }
                    
                    # Calculate popularity rank
                    if self.frequency_cache.get('site_frequency'):
                        sorted_sites = sorted(
                            self.frequency_cache['site_frequency'].items(),
                            key=lambda x: x[1],
                            reverse=True
                        )
                        for rank, (site, _) in enumerate(sorted_sites, 1):
                            if site == site_name:
                                site_details['popularity_rank'] = rank
                                break
                    
                    sites.append(site_details)
        
        return {
            'username': username,
            'sites_found': sites,
            'total_sites': len(sites),
            'identifier_type': 'email' if '@' in username else 'username'
        }

def main():
    """Command-line interface for frequency analyzer"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Analyze Blackbird search frequency')
    parser.add_argument('--reports-folder', default='../results',
                       help='Path to reports folder')
    parser.add_argument('--scan', action='store_true',
                       help='Scan reports and build frequency data')
    parser.add_argument('--stats', action='store_true',
                       help='Show overall statistics')
    parser.add_argument('--username', help='Get frequency for specific username')
    parser.add_argument('--site', help='Get frequency for specific site')
    parser.add_argument('--search', help='Search historical data')
    parser.add_argument('--top-sites', type=int, default=10,
                       help='Show top N sites (default: 10)')
    parser.add_argument('--top-users', type=int, default=10,
                       help='Show top N users (default: 10)')
    parser.add_argument('--force-rescan', action='store_true',
                       help='Force rescan of all reports')
    
    args = parser.parse_args()
    
    analyzer = FrequencyAnalyzer(args.reports_folder)
    
    if args.scan or args.force_rescan:
        print("Scanning reports...")
        analyzer.scan_reports(force_rescan=args.force_rescan)
    
    if args.stats:
        stats = analyzer.get_overall_statistics()
        print("\n=== Overall Statistics ===")
        print(f"Total reports: {stats['total_reports']}")
        print(f"Total accounts found: {stats['total_accounts']}")
        print(f"Unique usernames: {stats['unique_usernames']}")
        print(f"Unique emails: {stats['unique_emails']}")
        print(f"Unique sites: {stats['unique_sites']}")
        print(f"Last scan: {stats['last_scan']}")
        print(f"Cache fresh: {stats['cache_fresh']}")
        
        print("\n=== Top 5 Most Common Sites ===")
        for site, count in stats['most_common_sites']:
            print(f"  {site}: {count} accounts")
        
        print("\n=== Top 5 Most Active Usernames ===")
        for user, count in stats['most_active_usernames']:
            print(f"  {user}: {count} sites")
    
    if args.username:
        freq = analyzer.get_username_frequency(args.username)
        print(f"\n=== Frequency for '{args.username}' ===")
        print(f"Total searches: {freq['total_searches']}")
        print(f"Sites found: {freq['site_count']}")
        print(f"First seen: {freq['first_seen']}")
        print(f"Last seen: {freq['last_seen']}")
        print(f"Sites: {', '.join(freq['sites_found'])}")
        
        if freq['search_history']:
            print(f"\nSearch History:")
            for hist in freq['search_history'][:5]:  # Show last 5
                print(f"  {hist['date']}: {hist['accounts_found']} accounts")
    
    if args.site:
        freq = analyzer.get_site_frequency(args.site)
        print(f"\n=== Frequency for site '{args.site}' ===")
        print(f"Total accounts found: {freq['total_found']}")
        print(f"Unique usernames: {freq['username_count']}")
        print(f"Popularity rank: #{freq['popularity_rank']}")
        print(f"Percentage of all searches: {freq['percentage_of_searches']:.1f}%")
    
    if args.search:
        results = analyzer.search_historical_data(args.search)
        print(f"\n=== Search Results for '{args.search}' ===")
        print(f"Total matches: {results['total_matches']}")
        
        if results['usernames']:
            print(f"\nMatching Usernames ({len(results['usernames'])}):")
            for user in results['usernames'][:5]:  # Show first 5
                print(f"  {user['username']} - {user['site_count']} sites")
        
        if results['emails']:
            print(f"\nMatching Emails ({len(results['emails'])}):")
            for email in results['emails'][:5]:
                print(f"  {email['email']} - {email['site_count']} sites")
        
        if results['sites']:
            print(f"\nMatching Sites ({len(results['sites'])}):")
            for site in results['sites'][:5]:
                print(f"  {site['site']} - {site['total_found']} accounts")
    
    if args.top_sites > 0 and not (args.username or args.site or args.search):
        print(f"\n=== Top {args.top_sites} Most Common Sites ===")
        top_sites = analyzer.get_most_common_sites(args.top_sites)
        for i, (site, count) in enumerate(top_sites, 1):
            percentage = (count / analyzer.frequency_cache.get('total_accounts', 1) * 100) if analyzer.frequency_cache.get('total_accounts', 0) > 0 else 0
            print(f"{i:2}. {site:30} {count:4} accounts ({percentage:.1f}%)")
    
    if args.top_users > 0 and not (args.username or args.site or args.search):
        print(f"\n=== Top {args.top_users} Most Active Usernames ===")
        top_users = analyzer.get_most_active_usernames(args.top_users)
        for i, (user, count) in enumerate(top_users, 1):
            print(f"{i:2}. {user:40} {count:3} sites")


if __name__ == '__main__':
    main()