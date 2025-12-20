import json, csv, os, html as html_module
import re
from pathlib import Path
from collections import defaultdict, Counter
import math

def load_css():
    base = '''body{font-family:sans-serif;background:linear-gradient(135deg,#667eea 0%,#764ba2)}
    .container{max-width:1400px;margin:0 auto;padding:2rem}
    h1{color:white;text-align:center;margin-bottom:2rem}
    h2{background:linear-gradient(45deg,#4facfe 0%,#00f2fe);color:white;padding:1rem;margin-top:2rem}
    h3{color:#333;margin:0 0 0.5rem 0;font-size:1.2rem}
    h4{color:#555;margin:1.5rem 0 0.5rem 0;padding-bottom:0.5rem;border-bottom:2px solid #667eea}
    table{width:100%;background:#fff;border-collapse:collapse;margin:1rem 0;box-shadow:0 4px 6px rgba(0,0,0,0.1)}
    th{background:#667eea;color:#fff;padding:1rem;cursor:pointer;text-align:left}
    td{padding:0.75rem;border-bottom:1px solid #eee;vertical-align:top}
    .file-item{border:1px solid #ddd;border-radius:8px;padding:1rem;margin-bottom:1rem;background:#fff}
    .dir-item{border:2px solid #667eea;border-radius:8px;padding:1.5rem;margin-bottom:2rem;background:#f8f9ff}
    pre{background:#f5f7fa;padding:1rem;border-radius:8px;white-space:pre-wrap;margin:0;font-family:monospace}
    .is-hidden{display:none}.json-toggle{cursor:pointer}.json-toggle:hover{background:#4a5fc1}
    .csv-toggle{cursor:pointer}.csv-toggle:hover{background:#4a5fc1}
    .empty{text-align:center;color:#888;padding:2rem;font-style:italic}
    .error{background:#ffe6e6;border-left:4px solid #ff4444;padding:1rem;margin:0.5rem 0}
    tr:hover td{background:#f9f9f9}
    .chart-container{position:relative;height:400px;width:100%;margin:2rem 0;background:#fff;padding:1rem;border-radius:8px;box-shadow:0 4px 6px rgba(0,0,0,0.1)}
    .comparison-section{margin-top:3rem;border-top:2px solid #4facfe;padding-top:2rem}
    .comparison-stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:1rem;margin:1rem 0}
    .stat-card{background:#fff;padding:1rem;border-radius:8px;box-shadow:0 2px 4px rgba(0,0,0,0.1);text-align:center}
    .stat-value{font-size:1.5rem;font-weight:bold;color:#667eea}
    .stat-label{color:#666;font-size:0.9rem}
    .chart-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(500px,1fr));gap:2rem}
    @media(max-width:768px){.chart-grid{grid-template-columns:1fr}}
    .username-badge{display:inline-block;background:#667eea;color:white;padding:0.25rem 0.75rem;border-radius:20px;margin:0.25rem;font-size:0.85rem}
    .platform-link{color:#667eea;text-decoration:none;margin:0.25rem;display:inline-block;padding:0.25rem 0.5rem;background:#f0f4ff;border-radius:4px}
    .platform-link:hover{background:#667eea;color:white}
    .platform-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:0.5rem;margin:1rem 0}
    .success{color:#28a745;font-weight:bold}
    .warning{color:#ffc107;font-weight:bold}
    .danger{color:#dc3545;font-weight:bold}
    .summary-table{width:auto;margin:1rem 0}
    .summary-table th{background:#4facfe}
    .heatmap{display:inline-block;width:20px;height:20px;border-radius:3px;margin-right:5px}
    .heatmap-0{background:#e0e0e0}
    .heatmap-1{background:#ffeb3b}
    .heatmap-2{background:#ff9800}
    .heatmap-3{background:#ff5722}
    .heatmap-4{background:#d32f2f}
    .heatmap-5{background:#b71c1c}
    .blackbird-section{border:2px solid #764ba2;background:#f9f6ff;margin:2rem 0;padding:1.5rem;border-radius:12px}
    .source-badge{display:inline-block;padding:0.2rem 0.6rem;border-radius:12px;font-size:0.75rem;margin-left:0.5rem}
    .source-maigret{background:#667eea;color:white}
    .source-blackbird{background:#764ba2;color:white}
    '''
    if Path('css').exists():
        for f in sorted(Path('css').glob('*.css')):
            try: base += f.read_text()
            except: pass
    return base

def load_js():
    js = '''<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
function toggleFoldable(trigger){
  const table=trigger.closest('table');
  if(!table)return;
  const rows=table.querySelectorAll('tbody tr:not([class*="toggle"])');
  const isHidden=rows[0]&&rows[0].classList.contains('is-hidden');
  rows.forEach(r=>{
    r.classList.toggle('is-hidden',!isHidden);
    r.style.display=isHidden?'table-row':'none';
  });
  const header=trigger.querySelector('th');
  if(header){
    if(header.textContent.includes('(▲)')||header.textContent.includes('(▼)')){
      header.innerHTML=isHidden?header.innerHTML.replace('▼','▲'):header.innerHTML.replace('▲','▼');
    }else{
      header.innerHTML=isHidden?header.innerHTML+' (▲)':header.innerHTML+' (▼)';
    }
  }
}

function createPieChart(canvasId, chartData){
  const ctx=document.getElementById(canvasId).getContext('2d');
  const colors=generateColors(chartData.labels.length);
  
  return new Chart(ctx,{
    type:'pie',
    data:{
      labels:chartData.labels,
      datasets:[{
        data:chartData.values,
        backgroundColor:colors,
        borderColor:'#fff',
        borderWidth:2,
        hoverOffset:15
      }]
    },
    options:{
      responsive:true,
      maintainAspectRatio:false,
      plugins:{
        legend:{position:'right',labels:{font:{size:12},padding:20}},
        tooltip:{
          callbacks:{
            label:function(context){
              const label=context.label||'';
              const value=context.raw||0;
              const total=context.dataset.data.reduce((a,b)=>a+b,0);
              const percentage=Math.round((value/total)*100);
              return `${label}: ${value} (${percentage}%)`;
            }
          }
        }
      }
    }
  });
}

function createBarChart(canvasId, chartData){
  const ctx=document.getElementById(canvasId).getContext('2d');
  
  return new Chart(ctx,{
    type:'bar',
    data:{
      labels:chartData.labels,
      datasets:[{
        label:chartData.label||'Count',
        data:chartData.values,
        backgroundColor:'rgba(102, 126, 234, 0.7)',
        borderColor:'rgba(102, 126, 234, 1)',
        borderWidth:1
      }]
    },
    options:{
      responsive:true,
      maintainAspectRatio:false,
      scales:{
        y:{beginAtZero:true,ticks:{precision:0}}
      },
      plugins:{
        legend:{display:false}
      }
    }
  });
}

function generateColors(count){
  const colors=[];
  const baseColors=[
    '#667eea','#764ba2','#4facfe','#00f2fe',
    '#f093fb','#f5576c','#4facfe','#00f2fe',
    '#43e97b','#38f9d7','#fa709a','#fee140'
  ];
  for(let i=0;i<count;i++){
    colors.push(baseColors[i%baseColors.length]);
  }
  return colors;
}

function hide404Cells() {
    // Select all table data cells on the page
    const cells = document.querySelectorAll('td');

    // Loop through each cell
    cells.forEach(cell => {
        // Check if the cell's text content is exactly "404"
        if (cell.textContent.trim() === '404') {
            // Add the 'hide-404' class to the cell
            cell.classList.add('hide-404');
        }
    });
}

// Call the function when the page loads
document.addEventListener('DOMContentLoaded', (event) => {
    hide404Cells();
});


// Initialize all charts when page loads
document.addEventListener('DOMContentLoaded',function(){
  document.querySelectorAll('[data-chart-type="pie"]').forEach(canvas=>{
    const chartData=JSON.parse(canvas.dataset.chartData);
    createPieChart(canvas.id,chartData);
  });
  document.querySelectorAll('[data-chart-type="bar"]').forEach(canvas=>{
    const chartData=JSON.parse(canvas.dataset.chartData);
    createBarChart(canvas.id,chartData);
  });
});
</script>'''
    if Path('js').exists():
        for f in sorted(Path('js').glob('*.js')):
            try: js += f'<script>{f.read_text()}</script>'
            except: pass
    return js

def find_blackbird_csv_files(directory_path):
    """Recursively find all Blackbird CSV files in directory and subdirectories."""
    blackbird_files = []
    path = Path(directory_path)
    
    if not path.exists():
        return blackbird_files
    
    # Look for Blackbird CSV files in all subdirectories
    for csv_file in path.rglob('*.csv'):
        if 'blackbird' in csv_file.name.lower():
            blackbird_files.append(csv_file)
    
    # Also look for directories that contain Blackbird CSVs
    for item in path.iterdir():
        if item.is_dir() and 'blackbird' in item.name.lower():
            # Look inside this Blackbird directory
            for csv_file in item.rglob('*.csv'):
                blackbird_files.append(csv_file)
    
    return blackbird_files

def parse_blackbird_csv(file_path):
    """Parse Blackbird CSV files to extract URLs and platforms."""
    urls = []
    platforms = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                # Check common Blackbird CSV column names for URLs
                url_keys = ['url', 'link', 'website', 'profile_url', 'profile', 'uri']
                
                for key in url_keys:
                    if key in row and row[key]:
                        url = row[key].strip()
                        if url and url.startswith('http'):
                            urls.append(url)
                            
                            # Extract platform from URL
                            platform = extract_platform_from_url(url)
                            if platform:
                                platforms.append(platform)
                            else:
                                # Add generic platform if none found
                                platforms.append('Website')
    
    except Exception as e:
        print(f"Error parsing Blackbird CSV {file_path}: {e}")
    
    return urls, platforms

def extract_platform_from_url(url):
    """Extract platform name from URL."""
    # Common social media platforms mapping
    platform_patterns = {
        'Twitter/X': ['twitter.com', 'x.com'],
        'Facebook': ['facebook.com', 'fb.com'],
        'Instagram': ['instagram.com'],
        'GitHub': ['github.com'],
        'LinkedIn': ['linkedin.com'],
        'Reddit': ['reddit.com'],
        'YouTube': ['youtube.com', 'youtu.be'],
        'TikTok': ['tiktok.com'],
        'Pinterest': ['pinterest.com'],
        'Twitch': ['twitch.tv'],
        'SoundCloud': ['soundcloud.com'],
        'Flickr': ['flickr.com'],
        'Behance': ['behance.net'],
        'DeviantArt': ['deviantart.com'],
        'Imgur': ['imgur.com'],
        'Telegram': ['t.me', 'telegram.org'],
        'Discord': ['discord.com', 'discord.gg'],
        'Spotify': ['spotify.com'],
        'Snapchat': ['snapchat.com'],
        'Tumblr': ['tumblr.com'],
        'VK': ['vk.com'],
        'Weibo': ['weibo.com'],
        'QQ': ['qq.com'],
        'WhatsApp': ['whatsapp.com'],
        'Signal': ['signal.org'],
        'Keybase': ['keybase.io'],
        'HackerNews': ['news.ycombinator.com'],
        'ProductHunt': ['producthunt.com'],
        'Medium': ['medium.com'],
        'WordPress': ['wordpress.com'],
        'Blogger': ['blogger.com'],
        'StackOverflow': ['stackoverflow.com'],
        'GitLab': ['gitlab.com'],
        'Bitbucket': ['bitbucket.org'],
        'Steam': ['steamcommunity.com', 'steampowered.com'],
        'Xbox': ['xbox.com'],
        'PlayStation': ['playstation.com'],
        'Etsy': ['etsy.com'],
        'eBay': ['ebay.com'],
        'Amazon': ['amazon.com'],
        'PayPal': ['paypal.com'],
        'Venmo': ['venmo.com'],
        'CashApp': ['cash.app'],
        'OnlyFans': ['onlyfans.com'],
        'Patreon': ['patreon.com'],
        'Substack': ['substack.com'],
        'Clubhouse': ['clubhouse.com'],
        'Goodreads': ['goodreads.com'],
        'Letterboxd': ['letterboxd.com'],
        'IMDb': ['imdb.com'],
        'RottenTomatoes': ['rottentomatoes.com'],
        'Wikipedia': ['wikipedia.org'],
        'Breach.vip': ['breach.vip'],
    }
    
    if not url or not isinstance(url, str):
        return None
    
    url_lower = url.lower()
    
    for platform, patterns in platform_patterns.items():
        for pattern in patterns:
            if pattern in url_lower:
                return platform
    
    # Try to extract domain name as fallback
    try:
        domain = url.split('//')[-1].split('/')[0]
        if '.' in domain:
            parts = domain.split('.')
            if len(parts) >= 2:
                # Remove common TLDs and 'www'
                name = parts[-2]
                if name not in ['www', 'com', 'org', 'net', 'io', 'co', 'edu', 'gov']:
                    return name.capitalize()
    except:
        pass
    
    return None

def parse_report_file(content, filename):
    """Parse a report file to extract usernames and platforms, ignoring 404 errors."""
    lines = content.strip().split('\n')
    data = {
        'filename': filename,
        'username': None,
        'platforms': [],
        'total_detected': 0,
        'urls': [],
        'source': 'maigret'
    }
    
    # Try to extract username from filename (remove 'report_' and '.txt')
    base_name = filename.replace('report_', '').replace('.txt', '').replace('.csv', '')
    data['username'] = base_name
    
    current_line = 0
    while current_line < len(lines):
        line = lines[current_line].strip()
        
        # Check for URLs - ignore if line contains 404 error
        if line.startswith('http'):
            # Check if this is a 404 error URL
            if '404' not in line and 'not found' not in line.lower():
                data['urls'].append(line)
                # Extract platform from URL
                platform = extract_platform_from_url(line)
                if platform:
                    data['platforms'].append(platform)
            else:
                # Skip 404 URLs
                pass
        
        # Check for "Total Websites Username Detected On" line
        elif 'Total Websites Username Detected On' in line:
            try:
                # Extract number from line like "Total Websites Username Detected On : 5"
                match = re.search(r':\s*(\d+)', line)
                if match:
                    data['total_detected'] = int(match.group(1))
            except:
                pass
        
        current_line += 1
    
    # If we found URLs but no platforms were identified, use generic count
    if data['urls'] and not data['platforms']:
        data['platforms'] = ['Website'] * len(data['urls'])
    
    return data

def analyze_username_reports(report_data_list, blackbird_data_list):
    """Analyze all username reports (including Blackbird data) to generate statistics."""
    if not report_data_list and not blackbird_data_list:
        return None
    
    analysis = {
        'total_reports': len(report_data_list) + len(blackbird_data_list),
        'reports_with_detections': 0,
        'reports_without_detections': 0,
        'total_detections': 0,
        'total_detections_filtered': 0,  # Add this
        'total_unique_platforms': 0,
        'platform_distribution': defaultdict(int),
        'username_detection_counts': [],
        'top_platforms': [],
        'usernames_by_detection_count': defaultdict(list),
        'sources': defaultdict(int),
        'usernames': set(),
        'filtered_404s': 0  # Add this to track filtered URLs
    }
    
    all_platforms = set()
    
    # Process Maigret reports
    for report in report_data_list:
        actual_detections = len(report['urls'])  # This excludes 404s
        original_detections = report['total_detected']
        
        analysis['total_detections'] += original_detections
        analysis['total_detections_filtered'] += actual_detections  # Track filtered count
        analysis['filtered_404s'] += (original_detections - actual_detections)  # Track 404s
        analysis['sources']['Maigret'] += 1
        analysis['usernames'].add(report['username'])
        
        if actual_detections > 0:
            analysis['reports_with_detections'] += 1
        else:
            analysis['reports_without_detections'] += 1
        
        # Count platforms (only from non-404 URLs)
        for platform in report['platforms']:
            analysis['platform_distribution'][platform] += 1
            all_platforms.add(platform)
        
        # Group usernames by detection count (using filtered count)
        count = actual_detections
        analysis['username_detection_counts'].append(count)
        analysis['usernames_by_detection_count'][count].append(report['username'])

    # Process Blackbird data
    for blackbird_data in blackbird_data_list:
        username = blackbird_data['username']
        platforms = blackbird_data['platforms']
        urls = blackbird_data['urls']
        
        detections = len(platforms)
        analysis['total_detections'] += detections
        analysis['sources']['Blackbird'] += 1
        analysis['usernames'].add(username)
        
        if detections > 0:
            analysis['reports_with_detections'] += 1
        else:
            analysis['reports_without_detections'] += 1
        
        # Count platforms
        for platform in platforms:
            analysis['platform_distribution'][platform] += 1
            all_platforms.add(platform)
        
        # Group usernames by detection count
        analysis['username_detection_counts'].append(detections)
        analysis['usernames_by_detection_count'][detections].append(username)
    
    analysis['total_unique_platforms'] = len(all_platforms)
    analysis['total_unique_usernames'] = len(analysis['usernames'])
    
    # Sort platforms by frequency
    analysis['top_platforms'] = sorted(
        analysis['platform_distribution'].items(),
        key=lambda x: x[1],
        reverse=True
    )[:10]  # Top 10 platforms
    
    # Calculate percentages
    if analysis['total_reports'] > 0:
        analysis['detection_rate'] = (analysis['reports_with_detections'] / analysis['total_reports'] * 100)
        analysis['average_detections'] = analysis['total_detections'] / analysis['total_reports']
    else:
        analysis['detection_rate'] = 0
        analysis['average_detections'] = 0
    
    if analysis['reports_with_detections'] > 0:
        analysis['detections_per_report'] = analysis['total_detections'] / analysis['reports_with_detections']
    else:
        analysis['detections_per_report'] = 0
    
    return analysis

def generate_username_charts(analysis_data):
    """Generate chart data for username analysis."""
    if not analysis_data:
        return {}
    
    charts = {}
    
    # 1. Detection Status Pie Chart
    charts['detection_status'] = {
        'type': 'pie',
        'data': {
            'labels': ['With Detections', 'Without Detections'],
            'values': [
                analysis_data['reports_with_detections'],
                analysis_data['reports_without_detections']
            ],
            'title': 'Username Detection Status'
        }
    }
    
    # 2. Top Platforms Bar Chart
    if analysis_data['top_platforms']:
        platforms, counts = zip(*analysis_data['top_platforms'])
        charts['top_platforms'] = {
            'type': 'bar',
            'data': {
                'labels': platforms[:8],  # Top 8 for readability
                'values': counts[:8],
                'title': 'Most Common Platforms',
                'label': 'Detections'
            }
        }
    
    # 3. Detection Count Distribution
    if analysis_data['username_detection_counts']:
        count_distribution = Counter(analysis_data['username_detection_counts'])
        sorted_counts = sorted(count_distribution.items())
        if sorted_counts:
            counts, frequencies = zip(*sorted_counts)
            charts['detection_distribution'] = {
                'type': 'bar',
                'data': {
                    'labels': [str(c) for c in counts],
                    'values': frequencies,
                    'title': 'Distribution of Detection Counts',
                    'label': 'Number of Usernames'
                }
            }
    
    # 4. Data Sources Pie Chart
    if analysis_data['sources']:
        charts['data_sources'] = {
            'type': 'pie',
            'data': {
                'labels': list(analysis_data['sources'].keys()),
                'values': list(analysis_data['sources'].values()),
                'title': 'Data Sources'
            }
        }
    
    # 5. Platform Distribution Pie Chart (if not too many)
    if len(analysis_data['platform_distribution']) <= 15:
        platforms = list(analysis_data['platform_distribution'].keys())
        counts = list(analysis_data['platform_distribution'].values())
        charts['platform_pie'] = {
            'type': 'pie',
            'data': {
                'labels': platforms,
                'values': counts,
                'title': 'Platform Distribution'
            }
        }
    
    return charts

def generate_username_summary(analysis_data, report_data_list, blackbird_data_list):
    """Generate HTML summary for username analysis including Blackbird data."""
    if not analysis_data:
        return ""
    
    # Statistics cards
    stats_html = f'''
    <div class="comparison-stats">
        <div class="stat-card">
            <div class="stat-value">{analysis_data['total_reports']}</div>
            <div class="stat-label">Total Reports</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{analysis_data['total_unique_usernames']}</div>
            <div class="stat-label">Unique Usernames</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{analysis_data['total_detections']}</div>
            <div class="stat-label">Total Platform Detections</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{analysis_data['total_unique_platforms']}</div>
            <div class="stat-label">Unique Platforms</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{analysis_data['detection_rate']:.1f}%</div>
            <div class="stat-label">Detection Rate</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{analysis_data['average_detections']:.1f}</div>
            <div class="stat-label">Avg Detections per Report</div>
        </div>
    </div>
    '''
    
    # Data sources info
    sources_html = ""
    if analysis_data['sources']:
        sources_items = []
        for source, count in analysis_data['sources'].items():
            source_class = 'source-maigret' if 'maigret' in source.lower() else 'source-blackbird'
            sources_items.append(f'''
            <div style="display:flex;align-items:center;justify-content:space-between;margin:0.5rem 0;padding:0.5rem;background:#f8f9ff;border-radius:6px">
                <span><strong>{source}</strong></span>
                <span class="{source_class}">{count}</span>
            </div>
            ''')
        
        sources_html = f'''
        <div style="margin:1rem 0;padding:1rem;background:#f8f9ff;border-radius:8px">
            <h4 style="margin-top:0">📊 Data Sources</h4>
            {''.join(sources_items)}
            <p style="color:#666;font-size:0.85rem;margin-top:0.5rem">
                <span class="source-badge source-maigret">Maigret</span> = Maigret OSINT tool reports
                <br>
                <span class="source-badge source-blackbird">Blackbird</span> = Blackbird username search results
            </p>
        </div>
        '''
    
    # Top platforms list
    top_platforms_html = ""
    if analysis_data['top_platforms']:
        platform_items = []
        for platform, count in analysis_data['top_platforms'][:10]:
            platform_items.append(f'''
            <div style="display:flex;align-items:center;margin:0.25rem 0">
                <span class="heatmap heatmap-{min(count, 5)}"></span>
                <span style="flex:1">{platform}</span>
                <span style="font-weight:bold">{count}</span>
            </div>
            ''')
        
        top_platforms_html = f'''
        <div style="margin:1rem 0;padding:1rem;background:#f8f9ff;border-radius:8px">
            <h4 style="margin-top:0">🏆 Top Platforms Found</h4>
            <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:0.5rem">
                {''.join(platform_items)}
            </div>
        </div>
        '''
    
    # Combine all data for sorting
    all_reports = []
    
    # Add Maigret reports
    for report in report_data_list:
        all_reports.append({
            'username': report['username'],
            'detections': report['total_detected'],
            'platforms': list(set(report['platforms'])),
            'urls': report['urls'],
            'source': 'Maigret'
        })
    
    # Add Blackbird data
    for blackbird_data in blackbird_data_list:
        all_reports.append({
            'username': blackbird_data['username'],
            'detections': len(blackbird_data['platforms']),
            'platforms': list(set(blackbird_data['platforms'])),
            'urls': blackbird_data['urls'],
            'source': 'Blackbird'
        })
    
    # Sort by detection count
    sorted_reports = sorted(all_reports, key=lambda x: x['detections'], reverse=True)
    
    # Username summary table
    table_rows = []
    for i, report in enumerate(sorted_reports[:20], 1):  # Top 20
        status_class = "success" if report['detections'] > 0 else "danger"
        status_text = f'<span class="{status_class}">{report["detections"]}</span>'
        
        # Platform badges
        platform_badges = ""
        unique_platforms = sorted(set(report['platforms']))
        for platform in unique_platforms[:5]:  # Show up to 5 platforms
            platform_badges += f'<span class="username-badge">{platform}</span>'
        
        if len(unique_platforms) > 5:
            platform_badges += f'<span class="username-badge">+{len(unique_platforms)-5}</span>'
        
        # Source badge
        source_class = 'source-maigret' if report['source'] == 'Maigret' else 'source-blackbird'
        source_badge = f'<span class="source-badge {source_class}">{report["source"]}</span>'
        
        table_rows.append(f'''
        <tr>
            <td>{i}</td>
            <td><strong>{report["username"]}</strong> {source_badge}</td>
            <td>{status_text}</td>
            <td>{platform_badges}</td>
            <td>{len(report["urls"])}</td>
        </tr>
        ''')
    
    summary_table = f'''
    <div style="margin:1rem 0">
        <h4>👤 Top Usernames by Platform Count</h4>
        <table class="summary-table">
            <thead>
                <tr>
                    <th>#</th>
                    <th>Username (Source)</th>
                    <th>Platforms</th>
                    <th>Platform Types</th>
                    <th>URLs</th>
                </tr>
            </thead>
            <tbody>
                {''.join(table_rows)}
            </tbody>
        </table>
    </div>
    '''
    
    # Generate charts HTML
    charts = generate_username_charts(analysis_data)
    charts_html = ""
    chart_count = 0
    
    for chart_name, chart_info in charts.items():
        canvas_id = f"username-chart-{chart_count}"
        chart_type = chart_info['type']
        chart_count += 1
        
        charts_html += f'''
        <div class="chart-container">
            <h4>{chart_info['data']['title']}</h4>
            <div style="height:350px">
                <canvas id="{canvas_id}" 
                        data-chart-type="{chart_type}"
                        data-chart-data='{json.dumps(chart_info["data"])}'></canvas>
            </div>
        </div>
        '''
    
    return f'''
    <section class="comparison-section">
        <h2>👤 Username Intelligence Dashboard</h2>
        {stats_html}
        {sources_html}
        {top_platforms_html}
        <div class="chart-grid">
            {charts_html}
        </div>
        {summary_table}
        <p style="color:#666;font-size:0.9rem;margin-top:1rem;text-align:center">
            <em>Analyzed {analysis_data['total_reports']} reports ({analysis_data['total_unique_usernames']} unique usernames) with {analysis_data['total_detections']} total platform detections</em>
        </p>
    </section>
    '''

def process_blackbird_csv_file(file_path, file_name):
    """Process a Blackbird CSV file and extract username, URLs, and platforms."""
    try:
        # Extract username from Blackbird filename pattern
        username_match = re.search(r'(.+?)_\d{2}_\d{2}_\d{4}_blackbird', file_name)
        if username_match:
            username = username_match.group(1)
        else:
            # Try pattern like crystal-shaw-gallagher_12_19_2025_blackbird
            username_match = re.search(r'(.+?)_\d{1,2}_\d{1,2}_\d{4}_blackbird', file_name)
            if username_match:
                username = username_match.group(1)
            else:
                # Fallback: remove extension and _blackbird suffix
                username = file_name.replace('.csv', '').replace('_blackbird', '')
        
        urls, platforms = parse_blackbird_csv(file_path)
        
        return {
            'filename': file_name,
            'username': username,
            'platforms': platforms,
            'total_detected': len(platforms),
            'urls': urls,
            'source': 'Blackbird'
        }
    
    except Exception as e:
        print(f"Error processing Blackbird CSV {file_path}: {e}")
        return None

def process_file(file_path, file_name):
    """Process a single file and return HTML content and data."""
    try:
        if file_name.endswith('.json'):
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            rows = '<tbody><tr class="json-toggle" onclick="toggleFoldable(this)"><th colspan="2">JSON Data (▼)</th></tr>'
            if isinstance(data, dict):
                for key, value in data.items():
                    rows += f'<tr class="is-hidden"><td><strong>{html_module.escape(str(key))}</strong></td><td><pre>{html_module.escape(json.dumps(value, indent=2))}</pre></td></tr>'
            elif isinstance(data, list):
                for item in data:
                    rows += f'<tr class="is-hidden"><td colspan="2"><pre>{html_module.escape(json.dumps(item, indent=2))}</pre></td></tr>'
            html = f'<div class="file-item"><h3>📊 {html_module.escape(file_name)}</h3><table>{rows}</tbody></table></div>'
            return html, ('json', data)
        
        elif file_name.endswith('.csv'):
            # Check if this is a Blackbird CSV
            is_blackbird = 'blackbird' in file_name.lower()
            
            if is_blackbird:
                # Enhanced display for Blackbird CSV
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        rows = list(csv.reader(f))
                    
                    if not rows:
                        html = f'<div class="file-item"><h3>🦅 {html_module.escape(file_name)} (Blackbird)</h3><p class="empty">Empty Blackbird CSV file</p></div>'
                        return html, ('csv', [])
                    
                    # Extract URLs for preview
                    urls, platforms = parse_blackbird_csv(file_path)
                    
                    # Create enhanced display
                    status_class = "success" if urls else "danger"
                    status_text = f'<span class="{status_class}">{len(urls)} URLs found</span>'
                    
                    # Platform badges
                    platform_badges = ""
                    unique_platforms = set(platforms)
                    for platform in unique_platforms:
                        platform_badges += f'<span class="username-badge">{platform}</span>'
                    
                    # URL preview
                    url_preview = ""
                    for i, url in enumerate(urls[:5]):  # Show first 5 URLs
                        safe_url = html_module.escape(url)
                        url_preview += f'<a href="{safe_url}" target="_blank" class="platform-link">{safe_url}</a>'
                    
                    if len(urls) > 5:
                        url_preview += f'<span class="username-badge">+{len(urls)-5} more</span>'
                    
                    # Extract username from filename
                    username_match = re.search(r'(.+?)_\d{1,2}_\d{1,2}_\d{4}_blackbird', file_name)
                    username = username_match.group(1) if username_match else "Unknown"
                    
                    html = f'''
                    <div class="file-item blackbird-section">
                        <h3>🦅 {html_module.escape(file_name)}</h3>
                        <div style="margin:0.5rem 0">
                            <strong>Username:</strong> <span style="font-weight:bold;color:#764ba2">{username}</span>
                            <span class="source-badge source-blackbird">Blackbird</span>
                        </div>
                        <div style="margin:0.5rem 0">
                            <strong>Status:</strong> {status_text}
                        </div>
                        {f'<div style="margin:0.5rem 0"><strong>Platforms:</strong> {platform_badges}</div>' if platform_badges else ''}
                        {f'<div style="margin:0.5rem 0"><strong>URLs:</strong><br>{url_preview}</div>' if url_preview else ''}
                    </div>
                    '''
                except Exception as e:
                    html = f'<div class="file-item error"><h3>🦅 {html_module.escape(file_name)}</h3><p>Error processing Blackbird CSV: {html_module.escape(str(e))}</p></div>'
            else:
                # Regular CSV display
                with open(file_path, 'r', encoding='utf-8') as f:
                    rows = list(csv.reader(f))
                if not rows:
                    html = f'<div class="file-item"><h3>📈 {html_module.escape(file_name)}</h3><p class="empty">Empty CSV file</p></div>'
                    return html, ('csv', [])
                
                table_html = '<tbody>'
                if len(rows) > 10:
                    table_html += f'<tr class="csv-toggle" onclick="toggleFoldable(this)"><th colspan="{len(rows[0])}">CSV Data ({len(rows)-1} rows) (▼)</th></tr>'
                    for i, row in enumerate(rows):
                        display = 'none' if i > 10 else 'table-row'
                        cls = 'is-hidden' if i > 10 else ''
                        tag = 'th' if i == 0 else 'td'
                        table_html += f'<tr class="{cls}" style="display:{display}">' + ''.join(f'<{tag}>{html_module.escape(cell)}</{tag}>' for cell in row) + '</tr>'
                else:
                    for i, row in enumerate(rows):
                        tag = 'th' if i == 0 else 'td'
                        table_html += '<tr>' + ''.join(f'<{tag}>{html_module.escape(cell)}</{tag}>' for cell in row) + '</tr>'
                
                html = f'<div class="file-item"><h3>📈 {html_module.escape(file_name)}</h3><table>{table_html}</tbody></table></div>'
            
            return html, ('csv', rows)
        
        elif file_name.endswith('.txt'):
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Enhanced display for username reports
            if file_name.startswith('report_'):
                try:
                    parsed_data = parse_report_file(content, file_name)
                    
                    # Calculate actual detections (excluding 404s)
                    actual_detections = len(parsed_data['urls'])
                    
                    # Create enhanced display
                    status_class = "success" if actual_detections > 0 else "warning" if parsed_data['total_detected'] > 0 else "danger"
                    status_text = f'<span class="{status_class}">{actual_detections} valid platforms (original: {parsed_data["total_detected"]})</span>'
                    
                    # Add note about 404 filtering if applicable
                    if parsed_data['total_detected'] > actual_detections:
                        status_text += f'<br><small style="color:#666;">Filtered out {parsed_data["total_detected"] - actual_detections} 404 results</small>'

                    # Platform badges
                    platform_badges = ""
                    unique_platforms = set(parsed_data['platforms'])
                    for platform in unique_platforms:
                        platform_badges += f'<span class="username-badge">{platform}</span>'
                    
                    # URL links
                    url_links = ""
                    for url in parsed_data['urls']:
                        safe_url = html_module.escape(url)
                        url_links += f'<a href="{safe_url}" target="_blank" class="platform-link">{safe_url}</a>'
                    
                    html = f'''
                    <div class="file-item">
                        <h3>👤 {html_module.escape(file_name)}</h3>
                        <div style="margin:0.5rem 0">
                            <strong>Username:</strong> <span style="font-weight:bold;color:#667eea">{parsed_data['username']}</span>
                            <span class="source-badge source-maigret">Maigret</span>
                        </div>
                        <div style="margin:0.5rem 0">
                            <strong>Status:</strong> {status_text}
                        </div>
                        {f'<div style="margin:0.5rem 0"><strong>Platforms:</strong> {platform_badges}</div>' if platform_badges else ''}
                        {f'<div style="margin:0.5rem 0"><strong>URLs:</strong><br>{url_links}</div>' if url_links else ''}
                        <pre style="margin-top:1rem;background:#f8f9ff">{html_module.escape(content[:500])}{'...' if len(content) > 500 else ''}</pre>
                    </div>
                    '''
                except Exception as e:
                    html = f'<div class="file-item error"><h3>👤 {html_module.escape(file_name)}</h3><p>Error parsing report: {html_module.escape(str(e))}</p></div>'
            else:
                # Regular text file display - always show full content
                html = f'<div class="file-item"><h3>📄 {html_module.escape(file_name)}</h3><pre>{html_module.escape(content)}</pre></div>'
            
            return html, ('txt', content)
    
    except Exception as e:
        html = f'<div class="file-item error"><h3>⚠ {html_module.escape(file_name)}</h3><p>Error: {html_module.escape(str(e))}</p></div>'
        return html, (None, None)
    
    return '', (None, None)

def load_dir(dir_path, collect_data=False):
    """Load all files from directory and its subdirectories."""
    path = Path(dir_path)
    if not path.exists():
        return '<div class="error">Directory not found</div>', [], [], []
    
    output = []
    file_contents = []
    username_reports = []  # Maigret username reports
    blackbird_data = []    # Blackbird data
    
    # First, find all Blackbird CSV files in this directory and subdirectories
    if collect_data:
        blackbird_files = find_blackbird_csv_files(dir_path)
        for blackbird_file in blackbird_files:
            blackbird_result = process_blackbird_csv_file(blackbird_file, blackbird_file.name)
            if blackbird_result:
                blackbird_data.append(blackbird_result)
    
    # Process files in current directory
    files = sorted([f for f in path.iterdir() if f.is_file() and f.suffix in ['.json', '.csv', '.txt']])
    if files:
        output.append(f'<h4>📂 {dir_path}/</h4>')
        for file_path in files:
            html, data_info = process_file(file_path, file_path.name)
            output.append(html)
            
            # Collect data for analysis
            if collect_data:
                if data_info[0] in ['json', 'csv']:
                    file_contents.append((file_path.name, data_info[0], data_info[1]))
                
                # Check for Maigret username reports
                elif data_info[0] == 'txt' and file_path.name.startswith('report_'):
                    parsed_data = parse_report_file(data_info[1], file_path.name)
                    username_reports.append(parsed_data)
    
    # Process subdirectories (excluding Blackbird directories already processed)
    dirs = sorted([d for d in path.iterdir() if d.is_dir()])
    for subdir in dirs:
        # Skip if it's a Blackbird directory (we already processed CSV files)
        if 'blackbird' in subdir.name.lower():
            continue
            
        subdir_files = sorted([f for f in subdir.rglob('*') if f.is_file() and f.suffix in ['.json', '.csv', '.txt']])
        if subdir_files:
            output.append(f'<div class="dir-item"><h4>📁 {subdir.name}/</h4>')
            for file_path in subdir_files:
                html, data_info = process_file(file_path, f"{subdir.name}/{file_path.relative_to(subdir)}")
                output.append(html)
                
                if collect_data:
                    if data_info[0] in ['json', 'csv']:
                        file_contents.append((file_path.name, data_info[0], data_info[1]))
                    
                    # Check for Maigret username reports
                    elif data_info[0] == 'txt' and file_path.name.startswith('report_'):
                        parsed_data = parse_report_file(data_info[1], file_path.name)
                        username_reports.append(parsed_data)
            output.append('</div>')
    
    if not output:
        return '<div class="empty">No JSON, CSV, or TXT files found</div>', [], [], []
    
    return ''.join(output), file_contents, username_reports, blackbird_data

def generate_dashboard():
    """Generate the dashboard HTML file with username analysis including Blackbird data."""
    print("🔍 Searching for Maigret and Blackbird data...")
    
    # Load data from both directories
    reports_html, reports_data, reports_usernames, reports_blackbird = load_dir('reports', collect_data=True)
    results_html, results_data, results_usernames, results_blackbird = load_dir('results', collect_data=True)
    
    # Debug output
    print(f"📊 Found {len(reports_usernames)} Maigret reports in 'reports/' directory")
    print(f"🦅 Found {len(reports_blackbird)} Blackbird datasets in 'reports/' directory")
    print(f"📊 Found {len(results_usernames)} Maigret reports in 'results/' directory")
    print(f"🦅 Found {len(results_blackbird)} Blackbird datasets in 'results/' directory")
    
    # Combine all data
    all_username_reports = reports_usernames + results_usernames
    all_blackbird_data = reports_blackbird + results_blackbird
    
    print(f"📈 Total: {len(all_username_reports)} Maigret reports, {len(all_blackbird_data)} Blackbird datasets")
    
    # Generate username analysis section
    username_summary_html = ""
    if all_username_reports or all_blackbird_data:
        analysis_data = analyze_username_reports(all_username_reports, all_blackbird_data)
        if analysis_data:
            print(f"📊 Analysis complete: {analysis_data['total_reports']} total reports")
            print(f"📊 Sources: {dict(analysis_data['sources'])}")
            username_summary_html = generate_username_summary(analysis_data, all_username_reports, all_blackbird_data)
        else:
            print("⚠️ No analysis data generated")
    else:
        print("⚠️ No username data found for analysis")
    
    html_output = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Username Intelligence Dashboard</title>
    <style>{load_css()}</style>
    {load_js()}
</head>
<body>
    <div class="container">
        <h1>🔍 Username Intelligence Dashboard</h1>
        
        {username_summary_html}
        
        <section>
            <h2>📁 Reports Directory</h2>
            {reports_html if reports_html else '<div class="empty">No files found</div>'}
        </section>
        <section>
            <h2>📈 Results/Misc Directory</h2>
            {results_html if results_html else '<div class="empty">No files found</div>'}
        </section>
    </div>
</body>
</html>'''

    with open('dashboard.html', 'w', encoding='utf-8') as f:
        f.write(html_output)
    
    print(f"✅ Dashboard generated: dashboard.html")
    return 'dashboard.html'

# Run the dashboard generation
if __name__ == "__main__":
    result = generate_dashboard()
    print(f"✅ Username Intelligence Dashboard generated: {result}")
    print("\nEnhanced Features:")
    print("✓ Combined Maigret and Blackbird data analysis")
    print("✓ Recursive search for Blackbird CSV files")
    print("✓ URL extraction from Blackbird CSV files")
    print("✓ Platform detection from URLs")
    print("✓ Data source tracking with colored badges")
    print("✓ Enhanced visualization with source badges")
    print("✓ Interactive charts for combined data analysis")