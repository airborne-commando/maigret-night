import json, csv, os, html as html_module
from pathlib import Path

def load_css():
    base = '''body{font-family:sans-serif;background:linear-gradient(135deg,#667eea 0%,#764ba2)}
    .container{max-width:1400px;margin:0 auto;padding:2rem}
    h1{color:white;text-align:center;margin-bottom:2rem}
    h2{background:linear-gradient(45deg,#4facfe 0%,#00f2fe);color:white;padding:1rem;margin-top:2rem}
    h3{color:#333;margin:0 0 0.5rem 0;font-size:1.2rem;display:flex;justify-content:space-between;align-items:center}
    h4{color:#555;margin:1.5rem 0 0.5rem 0;padding-bottom:0.5rem;border-bottom:2px solid #667eea}
    table{width:100%;background:#fff;border-collapse:collapse;margin:1rem 0;box-shadow:0 4px 6px rgba(0,0,0,0.1)}
    th{background:#667eea;color:#fff;padding:1rem;cursor:pointer;text-align:left}
    td{padding:0.75rem;border-bottom:1px solid #eee;vertical-align:top}
    .file-item{border:1px solid #ddd;border-radius:8px;padding:1rem;margin-bottom:1rem;background:#fff;position:relative}
    .dir-item{border:2px solid #667eea;border-radius:8px;padding:1.5rem;margin-bottom:2rem;background:#f8f9ff}
    pre{background:#f5f7fa;padding:1rem;border-radius:8px;white-space:pre-wrap;margin:0;font-family:monospace}
    .is-hidden{display:none}.json-toggle{cursor:pointer}.json-toggle:hover{background:#4a5fc1}
    .csv-toggle{cursor:pointer}.csv-toggle:hover{background:#4a5fc1}
    .empty{text-align:center;color:#888;padding:2rem;font-style:italic}
    .error{background:#ffe6e6;border-left:4px solid #ff4444;padding:1rem;margin:0.5rem 0}
    tr:hover td{background:#f9f9f9}
    .edit-btn{background:#4CAF50;color:white;border:none;padding:0.5rem 1rem;border-radius:4px;cursor:pointer;font-size:0.9rem;transition:background 0.3s}
    .edit-btn:hover{background:#45a049}
    .delete-btn{background:#f44336;color:white;border:none;padding:0.5rem 1rem;border-radius:4px;cursor:pointer;font-size:0.9rem;margin-left:0.5rem;transition:background 0.3s}
    .delete-btn:hover{background:#d32f2f}
    .btn-group{display:flex;justify-content:flex-end;margin-top:1rem}
    /* Modal styles */
    .modal{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.7);z-index:1000}
    .modal-content{background:#fff;margin:5% auto;padding:2rem;border-radius:8px;width:80%;max-width:800px;max-height:80vh;overflow-y:auto}
    .modal-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:1rem;padding-bottom:1rem;border-bottom:1px solid #eee}
    .modal-title{font-size:1.5rem;color:#333;margin:0}
    .close-btn{background:none;border:none;font-size:1.5rem;cursor:pointer;color:#777}
    .close-btn:hover{color:#333}
    .modal-body textarea{width:100%;min-height:300px;padding:1rem;border:1px solid #ddd;border-radius:4px;font-family:monospace;font-size:0.9rem;resize:vertical}
    .modal-body .json-editor,.modal-body .csv-editor{display:none}
    .save-btn{background:#2196F3;color:white;border:none;padding:0.75rem 1.5rem;border-radius:4px;cursor:pointer;font-size:1rem;margin-top:1rem}
    .save-btn:hover{background:#1976D2}
    .cancel-btn{background:#9e9e9e;color:white;border:none;padding:0.75rem 1.5rem;border-radius:4px;cursor:pointer;font-size:1rem;margin-top:1rem;margin-right:0.5rem}
    .cancel-btn:hover{background:#757575}
    .modal-footer{display:flex;justify-content:flex-end;margin-top:1.5rem;padding-top:1rem;border-top:1px solid #eee}
    .notification{position:fixed;top:20px;right:20px;padding:1rem 1.5rem;border-radius:4px;color:white;font-weight:bold;z-index:1001;animation:fadeOut 3s forwards}
    .success{background:#4CAF50}
    .error-notif{background:#f44336}
    @keyframes fadeOut{0%{opacity:1}70%{opacity:1}100%{opacity:0;display:none}}
    .json-editor textarea{min-height:400px}
    .csv-table-editor{width:100%;border-collapse:collapse;margin-bottom:1rem}
    .csv-table-editor th,.csv-table-editor td{border:1px solid #ddd;padding:0.5rem}
    .csv-table-editor input{border:none;outline:none;width:100%;padding:0.25rem;font-family:inherit}
    .add-row-btn,.add-col-btn{background:#4CAF50;color:white;border:none;padding:0.5rem 1rem;border-radius:4px;cursor:pointer;margin:0.5rem 0.25rem;font-size:0.9rem}
    .remove-row-btn,.remove-col-btn{background:#f44336;color:white;border:none;padding:0.5rem 1rem;border-radius:4px;cursor:pointer;margin:0.5rem 0.25rem;font-size:0.9rem}
    .table-controls{display:flex;flex-wrap:wrap;margin-bottom:1rem}
    .editor-tabs{display:flex;border-bottom:1px solid #ddd;margin-bottom:1rem}
    .tab-btn{padding:0.75rem 1.5rem;background:none;border:none;cursor:pointer;border-bottom:3px solid transparent}
    .tab-btn.active{border-bottom-color:#2196F3;color:#2196F3;font-weight:bold}
    .tab-btn:hover{background:#f5f5f5}
    .raw-editor{display:block}
    .json-structure{background:#f5f7fa;padding:1rem;border-radius:4px;margin-bottom:1rem}
    .json-key{color:#d32f2f}
    .json-value{color:#1976D2}
    .json-string{color:#388E3C}
    .json-number{color:#F57C00}
    .json-boolean{color:#7B1FA2}
    .json-null{color:#455A64}'''
    
    if Path('css').exists():
        for f in sorted(Path('css').glob('*.css')):
            try: base += f.read_text()
            except: pass
    return base

def load_js():
    js = '''<script>
// Toggle foldable rows
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

// Modal functions
let currentFile = '';
let currentFilePath = '';
let originalData = '';

function showNotification(message, type = 'success') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.remove();
    }, 3000);
}

function openEditor(filePath, fileName, fileType, content) {
    currentFile = fileName;
    currentFilePath = filePath;
    originalData = content;
    
    document.getElementById('modalTitle').textContent = `Edit ${fileName}`;
    document.getElementById('saveBtn').setAttribute('data-type', fileType);
    
    // Reset all editors
    document.getElementById('rawEditor').style.display = 'none';
    document.getElementById('jsonEditor').style.display = 'none';
    document.getElementById('csvEditor').style.display = 'none';
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    
    // Set content based on file type
    if (fileType === 'json') {
        document.getElementById('jsonTab').click();
        try {
            const formatted = JSON.stringify(JSON.parse(content), null, 2);
            document.getElementById('jsonContent').value = formatted;
            updateJsonStructure(formatted);
        } catch (e) {
            document.getElementById('jsonContent').value = content;
            updateJsonStructure(content);
        }
    } else if (fileType === 'csv') {
        document.getElementById('csvTab').click();
        parseCSVToTable(content);
    } else {
        document.getElementById('rawTab').click();
        document.getElementById('rawContent').value = content;
    }
    
    document.getElementById('editorModal').style.display = 'block';
}

function closeEditor() {
    document.getElementById('editorModal').style.display = 'none';
    currentFile = '';
    currentFilePath = '';
    originalData = '';
}

function saveFile() {
    const fileType = document.getElementById('saveBtn').getAttribute('data-type');
    let content = '';
    
    if (fileType === 'json') {
        content = document.getElementById('jsonContent').value;
    } else if (fileType === 'csv') {
        content = convertTableToCSV();
    } else {
        content = document.getElementById('rawContent').value;
    }
    
    if (content === originalData) {
        showNotification('No changes to save', 'error-notif');
        return;
    }
    
    // Send save request
    fetch('/save_file', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            file_path: currentFilePath,
            content: content,
            file_type: fileType
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('File saved successfully');
            setTimeout(() => {
                window.location.reload();
            }, 1500);
        } else {
            showNotification('Error saving file: ' + data.error, 'error-notif');
        }
    })
    .catch(error => {
        showNotification('Error saving file: ' + error, 'error-notif');
    });
}

function deleteFile(filePath, fileName) {
    if (!confirm(`Are you sure you want to delete "${fileName}"? This action cannot be undone.`)) {
        return;
    }
    
    fetch('/delete_file', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ file_path: filePath })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('File deleted successfully');
            setTimeout(() => {
                window.location.reload();
            }, 1500);
        } else {
            showNotification('Error deleting file: ' + data.error, 'error-notif');
        }
    })
    .catch(error => {
        showNotification('Error deleting file: ' + error, 'error-notif');
    });
}

function createNewFile(dirPath, fileType) {
    const fileName = prompt(`Enter new ${fileType.toUpperCase()} filename:`);
    if (!fileName) return;
    
    const fullPath = dirPath + '/' + (fileName.endsWith('.' + fileType) ? fileName : fileName + '.' + fileType);
    let defaultContent = '';
    
    if (fileType === 'json') {
        defaultContent = '{\n    "key": "value"\n}';
    } else if (fileType === 'csv') {
        defaultContent = 'Column1,Column2,Column3\\nValue1,Value2,Value3';
    } else if (fileType === 'txt') {
        defaultContent = 'New text file content';
    }
    
    openEditor(fullPath, fileName, fileType, defaultContent);
}

// JSON Editor Functions
function updateJsonStructure(jsonText) {
    const structureDiv = document.getElementById('jsonStructure');
    try {
        const obj = JSON.parse(jsonText);
        structureDiv.innerHTML = formatJsonStructure(obj);
    } catch (e) {
        structureDiv.innerHTML = '<div class="error">Invalid JSON</div>';
    }
}

function formatJsonStructure(obj, indent = 0) {
    let html = '';
    const indentStr = '&nbsp;'.repeat(indent * 4);
    
    if (Array.isArray(obj)) {
        html += `${indentStr}<span class="json-key">[</span><br>`;
        obj.forEach((item, i) => {
            html += `${indentStr}&nbsp;&nbsp;${formatJsonStructure(item, indent + 1)}`;
            if (i < obj.length - 1) html += '<span class="json-key">,</span>';
            html += '<br>';
        });
        html += `${indentStr}<span class="json-key">]</span>`;
    } else if (obj && typeof obj === 'object') {
        html += `${indentStr}<span class="json-key">{</span><br>`;
        const keys = Object.keys(obj);
        keys.forEach((key, i) => {
            html += `${indentStr}&nbsp;&nbsp;<span class="json-string">"${key}"</span>: `;
            html += formatJsonStructure(obj[key], indent + 1);
            if (i < keys.length - 1) html += '<span class="json-key">,</span>';
            html += '<br>';
        });
        html += `${indentStr}<span class="json-key">}</span>`;
    } else if (typeof obj === 'string') {
        html += `<span class="json-string">"${obj}"</span>`;
    } else if (typeof obj === 'number') {
        html += `<span class="json-number">${obj}</span>`;
    } else if (typeof obj === 'boolean') {
        html += `<span class="json-boolean">${obj}</span>`;
    } else if (obj === null) {
        html += `<span class="json-null">null</span>`;
    }
    
    return html;
}

// CSV Editor Functions
function parseCSVToTable(csvText) {
    const rows = csvText.split('\\n').filter(row => row.trim());
    const table = document.getElementById('csvTable');
    table.innerHTML = '';
    
    rows.forEach((row, rowIndex) => {
        const cells = row.split(',');
        const tr = document.createElement('tr');
        
        cells.forEach((cell, cellIndex) => {
            const td = rowIndex === 0 ? document.createElement('th') : document.createElement('td');
            const input = document.createElement('input');
            input.value = cell;
            input.dataset.row = rowIndex;
            input.dataset.col = cellIndex;
            td.appendChild(input);
            tr.appendChild(td);
        });
        
        if (rowIndex > 0) {
            const deleteTd = document.createElement('td');
            const deleteBtn = document.createElement('button');
            deleteBtn.className = 'remove-row-btn';
            deleteBtn.textContent = '×';
            deleteBtn.onclick = () => removeRow(rowIndex);
            deleteTd.appendChild(deleteBtn);
            tr.appendChild(deleteTd);
        } else {
            const headerTd = document.createElement('th');
            headerTd.textContent = 'Actions';
            tr.appendChild(headerTd);
        }
        
        table.appendChild(tr);
    });
}

function convertTableToCSV() {
    const rows = [];
    const table = document.getElementById('csvTable');
    
    Array.from(table.rows).forEach((row, rowIndex) => {
        const cells = [];
        Array.from(row.cells).forEach((cell, cellIndex) => {
            if (cellIndex < row.cells.length - 1) { // Exclude action column
                const input = cell.querySelector('input');
                cells.push(input ? input.value : cell.textContent);
            }
        });
        rows.push(cells.join(','));
    });
    
    return rows.join('\\n');
}

function addRow() {
    const table = document.getElementById('csvTable');
    const headerRow = table.rows[0];
    const colCount = headerRow.cells.length - 1; // Exclude action column
    const newRow = table.insertRow(-1);
    
    for (let i = 0; i < colCount; i++) {
        const cell = newRow.insertCell(i);
        const input = document.createElement('input');
        input.value = '';
        input.dataset.row = table.rows.length - 1;
        input.dataset.col = i;
        cell.appendChild(input);
    }
    
    const deleteCell = newRow.insertCell(colCount);
    const deleteBtn = document.createElement('button');
    deleteBtn.className = 'remove-row-btn';
    deleteBtn.textContent = '×';
    deleteBtn.onclick = () => removeRow(table.rows.length - 1);
    deleteCell.appendChild(deleteBtn);
}

function removeRow(rowIndex) {
    const table = document.getElementById('csvTable');
    if (table.rows.length > 2) { // Keep at least header and one data row
        table.deleteRow(rowIndex);
    }
}

function addColumn() {
    const table = document.getElementById('csvTable');
    Array.from(table.rows).forEach((row, rowIndex) => {
        const cell = rowIndex === 0 ? document.createElement('th') : document.createElement('td');
        const input = document.createElement('input');
        input.value = rowIndex === 0 ? `Column${row.cells.length}` : '';
        input.dataset.row = rowIndex;
        input.dataset.col = row.cells.length - 1; // Before action column
        cell.appendChild(input);
        row.insertBefore(cell, row.cells[row.cells.length - 1]);
    });
}

function removeColumn() {
    const table = document.getElementById('csvTable');
    if (table.rows[0].cells.length > 2) { // Keep at least one column + action column
        Array.from(table.rows).forEach(row => {
            row.deleteCell(row.cells.length - 2); // Remove second last cell (before action column)
        });
    }
}

function switchTab(tabName) {
    // Hide all editors
    document.getElementById('rawEditor').style.display = 'none';
    document.getElementById('jsonEditor').style.display = 'none';
    document.getElementById('csvEditor').style.display = 'none';
    
    // Remove active class from all tabs
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    
    // Show selected editor and activate tab
    document.getElementById(tabName + 'Tab').classList.add('active');
    document.getElementById(tabName + 'Editor').style.display = 'block';
}

// Close modal when clicking outside
window.onclick = function(event) {
    const modal = document.getElementById('editorModal');
    if (event.target === modal) {
        closeEditor();
    }
}
</script>'''
    
    if Path('js').exists():
        for f in sorted(Path('js').glob('*.js')):
            try: js += f'<script>{f.read_text()}</script>'
            except: pass
    return js

def process_file(file_path, file_name, relative_path=''):
    """Process a single file and return HTML content."""
    try:
        # Get the file type
        if file_name.endswith('.json'):
            file_type = 'json'
        elif file_name.endswith('.csv'):
            file_type = 'csv'
        elif file_name.endswith('.txt'):
            file_type = 'txt'
        else:
            return ''
        
        # Read file content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Create edit and delete buttons
        display_name = html_module.escape(file_name)
        if relative_path:
            display_name = f"{relative_path}/{display_name}"
        
        buttons = f'''
        <div class="btn-group">
            <button class="edit-btn" onclick="openEditor('{file_path}', '{display_name}', '{file_type}', `{html_module.escape(content).replace('`', '\\`')}`)">Edit</button>
            <button class="delete-btn" onclick="deleteFile('{file_path}', '{display_name}')">Delete</button>
        </div>
        '''
        
        # Format content based on file type
        if file_type == 'json':
            try:
                data = json.loads(content)
                rows = '<tbody><tr class="json-toggle" onclick="toggleFoldable(this)"><th colspan="2">JSON Data (▼)</th></tr>'
                if isinstance(data, dict):
                    for key, value in data.items():
                        rows += f'<tr class="is-hidden"><td><strong>{html_module.escape(str(key))}</strong></td><td><pre>{html_module.escape(json.dumps(value, indent=2))}</pre></td></tr>'
                elif isinstance(data, list):
                    for item in data:
                        rows += f'<tr class="is-hidden"><td colspan="2"><pre>{html_module.escape(json.dumps(item, indent=2))}</pre></td></tr>'
                content_html = f'<table>{rows}</tbody></table>'
            except json.JSONDecodeError:
                content_html = f'<div class="error"><pre>Invalid JSON: {html_module.escape(content[:200])}...</pre></div>'
        
        elif file_type == 'csv':
            rows = list(csv.reader(content.splitlines()))
            if not rows:
                content_html = '<p class="empty">Empty CSV file</p>'
            else:
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
                content_html = f'<table>{table_html}</tbody></table>'
        
        elif file_type == 'txt':
            if len(content) > 1000:
                short = content[:1000] + '... (truncated)'
                content_html = f'''
                <pre onclick="this.innerHTML=this.innerHTML.includes('... (truncated)')?'{html_module.escape(content).replace("'", "\\'")}':'{html_module.escape(short).replace("'", "\\'")}'" style="cursor:pointer">
                {html_module.escape(short)}
                </pre>'''
            else:
                content_html = f'<pre>{html_module.escape(content)}</pre>'
        
        icon = '📊' if file_type == 'json' else '📈' if file_type == 'csv' else '📄'
        
        return f'''
        <div class="file-item">
            <h3>
                {icon} {display_name}
                <span style="font-size:0.8rem;color:#777;">{os.path.getsize(file_path)} bytes</span>
            </h3>
            {content_html}
            {buttons}
        </div>'''
    
    except Exception as e:
        return f'<div class="file-item error"><h3>⚠ {html_module.escape(file_name)}</h3><p>Error: {html_module.escape(str(e))}</p></div>'

def load_dir(dir_path):
    """Load all files from directory and its subdirectories."""
    path = Path(dir_path)
    if not path.exists():
        return '<div class="error">Directory not found</div>'
    
    output = []
    
    # Add create new file buttons
    output.append(f'''
    <div style="display:flex;gap:1rem;margin-bottom:1rem;">
        <button class="edit-btn" onclick="createNewFile('{dir_path}', 'json')">New JSON File</button>
        <button class="edit-btn" onclick="createNewFile('{dir_path}', 'csv')">New CSV File</button>
        <button class="edit-btn" onclick="createNewFile('{dir_path}', 'txt')">New Text File</button>
    </div>
    ''')
    
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
                rel_path = file_path.relative_to(subdir)
                output.append(process_file(file_path, file_path.name, f"{subdir.name}/{rel_path.parent}" if rel_path.parent != Path('.') else subdir.name))
            output.append('</div>')
    
    if not files and not dirs:
        output.append('<div class="empty">No JSON, CSV, or TXT files found. Create a new file using the buttons above.</div>')
    
    return ''.join(output)

def generate_dashboard():
    """Generate the dashboard HTML file"""
    
    # Create modal HTML
    modal_html = '''
    <div id="editorModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h3 class="modal-title" id="modalTitle">Edit File</h3>
                <button class="close-btn" onclick="closeEditor()">×</button>
            </div>
            <div class="modal-body">
                <div class="editor-tabs">
                    <button class="tab-btn active" id="rawTab" onclick="switchTab('raw')">Raw Text</button>
                    <button class="tab-btn" id="jsonTab" onclick="switchTab('json')">JSON Editor</button>
                    <button class="tab-btn" id="csvTab" onclick="switchTab('csv')">CSV Editor</button>
                </div>
                
                <div id="rawEditor" class="raw-editor">
                    <textarea id="rawContent" placeholder="Edit file content here..."></textarea>
                </div>
                
                <div id="jsonEditor" class="json-editor">
                    <div class="json-structure">
                        <strong>JSON Structure Preview:</strong>
                        <div id="jsonStructure"></div>
                    </div>
                    <textarea id="jsonContent" placeholder="Edit JSON content here..." oninput="updateJsonStructure(this.value)"></textarea>
                </div>
                
                <div id="csvEditor" class="csv-editor">
                    <div class="table-controls">
                        <button class="add-row-btn" onclick="addRow()">Add Row</button>
                        <button class="remove-row-btn" onclick="removeRow(document.getElementById('csvTable').rows.length - 1)">Remove Last Row</button>
                        <button class="add-col-btn" onclick="addColumn()">Add Column</button>
                        <button class="remove-col-btn" onclick="removeColumn()">Remove Last Column</button>
                    </div>
                    <table id="csvTable" class="csv-table-editor"></table>
                </div>
            </div>
            <div class="modal-footer">
                <button class="cancel-btn" onclick="closeEditor()">Cancel</button>
                <button class="save-btn" id="saveBtn" onclick="saveFile()">Save Changes</button>
            </div>
        </div>
    </div>
    '''
    
    html_output = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Data Dashboard - File Editor</title>
    <style>{load_css()}</style>
    {load_js()}
</head>
<body>
    {modal_html}
    <div class="container">
        <h1>📊 Data Dashboard - File Editor</h1>
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
    
    print("Dashboard generated successfully at dashboard.html")
    print("NOTE: To enable file editing, you need to run a backend server.")
    print("\nQuick start with Python Flask server:")
    print("1. Install Flask: pip install flask")
    print("2. Create a file named 'server.py' with the following content:")
    
    server_code = '''
from flask import Flask, request, jsonify, send_file
import os
from pathlib import Path
import json
import csv

app = Flask(__name__)

@app.route('/')
def serve_dashboard():
    return send_file('dashboard.html')

@app.route('/save_file', methods=['POST'])
def save_file():
    try:
        data = request.json
        file_path = data['file_path']
        content = data['content']
        file_type = data.get('file_type', 'txt')
        
        # Ensure directory exists
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Write file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # Validate JSON if applicable
        if file_type == 'json':
            with open(file_path, 'r', encoding='utf-8') as f:
                json.load(f)
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/delete_file', methods=['POST'])
def delete_file():
    try:
        data = request.json
        file_path = data['file_path']
        
        if os.path.exists(file_path):
            os.remove(file_path)
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'File not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True, port=5000)
    '''
    
    print(server_code)
    print("\n3. Run the server: python server.py")
    print("4. Open browser and go to: http://localhost:5000")
    
    return 'dashboard.html'

if __name__ == '__main__':
    generate_dashboard()