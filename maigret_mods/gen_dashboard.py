import json, csv, os, html as html_module
from pathlib import Path

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
    tr:hover td{background:#f9f9f9}'''
    if Path('css').exists():
        for f in sorted(Path('css').glob('*.css')):
            try: base += f.read_text()
            except: pass
    return base

def load_js():
    js = '''<script>
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
}</script>'''
    if Path('js').exists():
        for f in sorted(Path('js').glob('*.js')):
            try: js += f'<script>{f.read_text()}</script>'
            except: pass
    return js

def process_file(file_path, file_name):
    """Process a single file and return HTML content."""
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
            return f'<div class="file-item"><h3>📊 {html_module.escape(file_name)}</h3><table>{rows}</tbody></table></div>'
        
        elif file_name.endswith('.csv'):
            with open(file_path, 'r', encoding='utf-8') as f:
                rows = list(csv.reader(f))
            if not rows:
                return f'<div class="file-item"><h3>📈 {html_module.escape(file_name)}</h3><p class="empty">Empty CSV file</p></div>'
            
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
            
            return f'<div class="file-item"><h3>📈 {html_module.escape(file_name)}</h3><table>{table_html}</tbody></table></div>'
        
        elif file_name.endswith('.txt'):
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            if len(content) > 1000:
                short = content[:1000] + '... (truncated)'
                return f'''<div class="file-item"><h3>📄 {html_module.escape(file_name)}</h3>
                    <pre onclick="this.innerHTML=this.innerHTML.includes('... (truncated)')?'{html_module.escape(content).replace("'", "\\'")}':'{html_module.escape(short).replace("'", "\\'")}'" style="cursor:pointer">
                    {html_module.escape(short)}
                    </pre></div>'''
            return f'<div class="file-item"><h3>📄 {html_module.escape(file_name)}</h3><pre>{html_module.escape(content)}</pre></div>'
    
    except Exception as e:
        return f'<div class="file-item error"><h3>⚠ {html_module.escape(file_name)}</h3><p>Error: {html_module.escape(str(e))}</p></div>'
    
    return ''

def load_dir(dir_path):
    """Load all files from directory and its subdirectories."""
    path = Path(dir_path)
    if not path.exists():
        return '<div class="error">Directory not found</div>'
    
    output = []
    
    # Process files in current directory
    files = sorted([f for f in path.iterdir() if f.is_file() and f.suffix in ['.json', '.csv', '.txt']])
    if files:
        output.append(f'<h4>📂 {dir_path}/</h4>')
        for file_path in files:
            output.append(process_file(file_path, file_path.name))
    
    # Process subdirectories
    dirs = sorted([d for d in path.iterdir() if d.is_dir()])
    for subdir in dirs:
        subdir_files = sorted([f for f in subdir.rglob('*') if f.is_file() and f.suffix in ['.json', '.csv', '.txt']])
        if subdir_files:
            output.append(f'<div class="dir-item"><h4>📁 {subdir.name}/</h4>')
            for file_path in subdir_files:
                output.append(process_file(file_path, f"{subdir.name}/{file_path.relative_to(subdir)}"))
            output.append('</div>')
    
    if not output:
        return '<div class="empty">No JSON, CSV, or TXT files found</div>'
    
    return ''.join(output)

def generate_dashboard():
    """Generate the dashboard HTML file"""
    html_output = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Data Dashboard</title>
    <style>{load_css()}</style>
    {load_js()}
</head>
<body>
    <div class="container">
        <h1>📊 Data Dashboard</h1>
        <section>
            <h2>📁 Reports Directory</h2>
            {load_dir('reports')}
        </section>
        <section>
            <h2>📈 Results/Misc Directory</h2>
            {load_dir('results')}
        </section>
    </div>
</body>
</html>'''

    with open('dashboard.html', 'w', encoding='utf-8') as f:
        f.write(html_output)
    
    return 'dashboard.html'