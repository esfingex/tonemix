"""
Documentation Generator for ToneMix
Generates a modern, responsive HTML documentation site from Markdown files.
"""
import os
import markdown
import shutil
from pathlib import Path
from datetime import datetime

# Configuration
DOCS_DIR = Path("docs")
OUTPUT_DIR = Path("public_docs")
TEMPLATE_DIR = Path("tools/templates")

# Define navigation order
NAV_ORDER = [
    "index.md",
    "technical_architecture.md",
    "ui_design.md",
    "github_setup.md"
]

TITLES = {
    "index.md": "Overview",
    "technical_architecture.md": "Technical Architecture",
    "ui_design.md": "UI Design Spec",
    "github_setup.md": "GitHub Setup"
}

# Modern Dark Theme CSS
CSS = """
:root {
    --bg-color: #121212;
    --sidebar-bg: #1a1a1a;
    --text-color: #e0e0e0;
    --heading-color: #ffffff;
    --accent-color: #00d9ff;
    --link-color: #4dc4ff;
    --code-bg: #2a2a2a;
    --border-color: #333;
}

* { box-sizing: border-box; }

body {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background-color: var(--bg-color);
    color: var(--text-color);
    margin: 0;
    display: flex;
    min-height: 100vh;
}

/* Sidebar */
.sidebar {
    width: 280px;
    background-color: var(--sidebar-bg);
    border-right: 1px solid var(--border-color);
    padding: 2rem 1.5rem;
    position: fixed;
    height: 100vh;
    overflow-y: auto;
}

.logo {
    font-size: 1.5rem;
    font-weight: bold;
    color: var(--accent-color);
    margin-bottom: 2rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.nav-links {
    list-style: none;
    padding: 0;
    margin: 0;
}

.nav-item {
    margin-bottom: 0.5rem;
}

.nav-link {
    display: block;
    padding: 0.75rem 1rem;
    color: var(--text-color);
    text-decoration: none;
    border-radius: 6px;
    transition: all 0.2s;
    opacity: 0.8;
}

.nav-link:hover {
    background-color: rgba(255, 255, 255, 0.05);
    opacity: 1;
    color: var(--accent-color);
}

.nav-link.active {
    background-color: rgba(0, 217, 255, 0.1);
    color: var(--accent-color);
    font-weight: 500;
}

/* Main Content */
.main-content {
    margin-left: 280px;
    padding: 3rem 4rem;
    max-width: 900px;
    width: 100%;
}

/* Typography */
h1, h2, h3, h4, h5, h6 {
    color: var(--heading-color);
    margin-top: 2rem;
    margin-bottom: 1rem;
    line-height: 1.3;
}

h1 { font-size: 2.5rem; border-bottom: 1px solid var(--border-color); padding-bottom: 1rem; }
h2 { font-size: 1.8rem; margin-top: 2.5rem; }
h3 { font-size: 1.4rem; }

p { line-height: 1.7; margin-bottom: 1.2rem; }

a { color: var(--link-color); text-decoration: none; }
a:hover { text-decoration: underline; }

ul, ol { margin-bottom: 1.5rem; padding-left: 1.5rem; }
li { margin-bottom: 0.5rem; line-height: 1.6; }

/* Code Blocks */
pre {
    background-color: var(--code-bg);
    padding: 1rem;
    border-radius: 8px;
    overflow-x: auto;
    margin: 1.5rem 0;
    border: 1px solid var(--border-color);
}

code {
    font-family: 'Fira Code', 'source-code-pro', monospace;
    font-size: 0.9em;
}

p code {
    background-color: rgba(255, 255, 255, 0.1);
    padding: 0.2rem 0.4rem;
    border-radius: 4px;
    color: #ff79c6;
}

img {
    max-width: 100%;
    border-radius: 8px;
    margin: 1.5rem 0;
    border: 1px solid var(--border-color);
}

/* Tables */
table {
    width: 100%;
    border-collapse: collapse;
    margin: 1.5rem 0;
    background-color: var(--sidebar-bg);
    border-radius: 8px;
    overflow: hidden;
}

th, td {
    padding: 1rem;
    border-bottom: 1px solid var(--border-color);
    text-align: left;
}

th {
    background-color: rgba(255, 255, 255, 0.05);
    font-weight: 600;
}

/* Footer */
footer {
    margin-top: 4rem;
    padding-top: 2rem;
    border-top: 1px solid var(--border-color);
    color: #666;
    font-size: 0.9rem;
}
"""

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - ToneMix Docs</title>
    <style>
        {css}
    </style>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.7.0/styles/atom-one-dark.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.7.0/highlight.min.js"></script>
    <script>hljs.highlightAll();</script>
</head>
<body>
    <nav class="sidebar">
        <div class="logo">🎵 ToneMix Docs</div>
        <ul class="nav-links">
            {nav_links}
        </ul>
        <div style="margin-top: 2rem; font-size: 0.8rem; color: #666;">
            Version: 0.1.0<br>
            Updated: {date}
        </div>
    </nav>
    <main class="main-content">
        {content}
        <footer>
            Built with ❤️ by ToneMix Team
        </footer>
    </main>
</body>
</html>
"""

def generate_docs():
    # Create output directory
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir()
    
    # Configure Markdown parser with extensions
    md = markdown.Markdown(extensions=[
        'fenced_code',
        'tables',
        'toc',
        'sane_lists'
    ])
    
    # Generate navigation links
    nav_links = ""
    for filename in NAV_ORDER:
        title = TITLES.get(filename, filename.replace('.md', '').title())
        output_filename = filename.replace('.md', '.html')
        nav_links += f'<li class="nav-item"><a href="{output_filename}" class="nav-link" id="nav-{output_filename}">{title}</a></li>'
    
    # Process each file
    today = datetime.now().strftime("%Y-%m-%d")
    
    for filename in NAV_ORDER:
        input_path = DOCS_DIR / filename
        if not input_path.exists():
            print(f"Warning: {input_path} not found")
            continue
            
        print(f"Processing {filename}...")
        
        # Read Markdown
        with open(input_path, 'r', encoding='utf-8') as f:
            text = f.read()
            
        # Convert to HTML
        html_content = md.convert(text)
        
        # Prepare template variables
        output_filename = filename.replace('.md', '.html')
        page_title = TITLES.get(filename, "Documentation")
        
        # Mark active link
        current_nav = nav_links.replace(f'id="nav-{output_filename}"', f'class="nav-link active"')
        
        # Fill template
        full_html = HTML_TEMPLATE.format(
            title=page_title,
            css=CSS,
            nav_links=current_nav,
            content=html_content,
            date=today
        )
        
        # Write Output
        with open(OUTPUT_DIR / output_filename, 'w', encoding='utf-8') as f:
            f.write(full_html)
            
    print(f"\n✅ Documentation generated in {OUTPUT_DIR.absolute()}")

if __name__ == "__main__":
    generate_docs()
