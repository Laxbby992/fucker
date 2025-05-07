from flask import Flask, request
import os
import re
import html

app = Flask(__name__)

def normalize(text):
    return re.sub(r'[^a-z0-9]+', '', text.lower())

def search(query):
    results = []
    allowed = {'txt', 'csv', 'json'}
    norm_query = normalize(query)
    if not norm_query:
        return []
    for file in os.listdir('.'):
        path = os.path.join('.', file)
        ext = file.rsplit('.', 1)[-1].lower()
        if os.path.isfile(path) and ext in allowed:
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.read().splitlines()
                    for i, line in enumerate(lines):
                        if norm_query in normalize(line):
                            results.append({
                                'filename': html.escape(file),
                                'line_num': i + 1,
                                'line': html.escape(line)
                            })
            except:
                continue
    return results

@app.route('/', methods=['GET', 'POST'])
def index():
    query = ''
    results = []
    if request.method == 'POST':
        query = request.form.get('query', '')
        results = search(query)

    return f'''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Oldantest Breach Finder</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body {{ font-family: 'Inter', sans-serif; }}
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        .result-item {{ animation: fadeIn 0.3s ease-out forwards; }}
    </style>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700&display=swap" rel="stylesheet">
</head>
<body class="bg-gradient-to-br from-gray-900 to-gray-800 text-gray-100 min-h-screen flex flex-col">
    <div class="container mx-auto p-4 md:p-8 flex-grow">
        <header class="text-center mb-8">
            <h1 class="text-4xl md:text-5xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-pink-600 mb-2">
                Oldantest Breach Finder
            </h1>
            <p class="text-gray-400">Search for text in .txt, .csv, .json files in current directory</p>
        </header>
        <form method="post" class="mb-8 max-w-xl mx-auto">
            <div class="flex items-center bg-gray-700 rounded-full shadow-lg overflow-hidden">
                <input type="text" name="query" placeholder="Enter text to search..."
                       class="w-full px-6 py-3 text-gray-100 bg-gray-700 focus:outline-none placeholder-gray-400"
                       value="{html.escape(query)}">
                <button type="submit"
                        class="bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 text-white px-6 py-3 font-semibold transition duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-opacity-50">
                    Search
                </button>
            </div>
        </form>
        {"<div class='bg-gray-800 rounded-lg shadow-xl p-6 max-w-4xl mx-auto'><h2 class='text-2xl font-semibold mb-4 border-b border-gray-700 pb-2'>Search results for: \"" + html.escape(query) + "\"</h2>" if query else ""}
        {f"<p class='text-gray-400 mb-4'>Found {len(results)} matching lines:</p><ul class='space-y-3 max-h-[60vh] overflow-y-auto pr-2'>" + "".join([f"<li class='result-item bg-gray-700 p-4 rounded-md shadow hover:bg-gray-600 transition duration-150 ease-in-out'><div class='flex justify-between items-center mb-1'><span class='font-mono text-sm text-purple-400 break-all'>{r['filename']}</span><span class='text-xs text-gray-500'>Line: {r['line_num']}</span></div><code class='block text-sm text-gray-200 whitespace-pre-wrap break-words'>{r['line']}</code></li>" for r in results]) + "</ul>" if results else (f"<p class='text-gray-400'>No results found for \"{html.escape(query)}\".</p>" if query else "")}
        {"</div>" if query else ""}
    </div>
    <footer class="text-center p-4 text-gray-500 text-sm mt-8">
        © Oldantest by Laxbby99 2025. All rights reserved.
    </footer>
</body>
</html>
'''

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
