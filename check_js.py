import re
import os

html_path = r'c:\Users\Higor\Documents\minhaloja\templates\index.html'
js_path = r'c:\Users\Higor\Documents\minhaloja\test.js'

with open(html_path, 'r', encoding='utf-8') as f:
    content = f.read()

match = re.search(r'<script>(.*?)</script>', content, re.DOTALL)
if match:
    with open(js_path, 'w', encoding='utf-8') as f:
        f.write(match.group(1))
    print("JS extracted. Running node -c test.js")
    os.system(f'node -c "{js_path}"')
else:
    print("No script tag found")
