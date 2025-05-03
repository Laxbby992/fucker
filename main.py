from flask import Flask, request, render_template_string, Response, stream_with_context
import os, re, json
from concurrent.futures import ThreadPoolExecutor
from queue import Queue, Empty

app = Flask(__name__)
EXTS = ('.txt', '.csv', '.json')
EXEC = ThreadPoolExecutor(max_workers=150)

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="windows-1252">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Oldantest ~ Leaks Finder</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@600&display=swap');
* { box-sizing:border-box; }
body { margin:0; font-family:'Orbitron',sans-serif; background:#000000; color:#eee; overflow-x:hidden; }
.container { max-width:880px; margin:60px auto; background:#111; padding:40px; border-radius:20px; box-shadow:0 0 80px #00ffff44; animation:fadeIn 1.2s ease; transition:0.3s; }
h1 { text-align:center; color:#00ffff; font-size:2.5em; margin-bottom:30px; text-shadow:0 0 12px #00ffff88; letter-spacing:1px; }
input, button { font-size:18px; }
form { display:flex; gap:10px; margin-bottom:30px; animation:slideDown 0.7s ease; }
input { flex:1; padding:16px; background:#000; color:#fff; border:2px solid #00ffff88; border-radius:10px; outline:none; transition:0.3s; }
input:focus { border-color:#00ffff; box-shadow:0 0 12px #00ffff44; }
button { padding:16px 28px; background:#00ffff; border:none; color:#000; border-radius:10px; cursor:pointer; font-weight:bold; box-shadow:0 0 15px #00ffff55; transition:0.3s ease; }
button:hover { background:#00cccc; transform:scale(1.03); }
.result-item { background:#1c1c1c; margin:15px 0; padding:22px; border-radius:12px; box-shadow:0 0 16px #00ffff33; animation:fadeIn 0.4s ease-in-out; }
.result-item strong { display:block; color:#00ffff; margin-bottom:10px; font-size:16px; }
.result-item pre { background:#000; padding:12px; border-radius:8px; overflow:auto; color:#fff; font-size:15px; }
.highlight { background:#ffff00; color:#000; padding:2px 4px; border-radius:5px; }
.no-results { text-align:center; margin-top:30px; font-size:19px; color:#666; animation:fadeIn 0.7s ease-in; }
@keyframes fadeIn { from{opacity:0;transform:translateY(10px);} to{opacity:1;transform:translateY(0);} }
@keyframes slideDown { from{opacity:0;transform:translateY(-20px);} to{opacity:1;transform:translateY(0);} }
</style>
</head>
<body>
<div class="container">
    <h1>Oldantest ~ Leaks Finder</h1>
    <form id="searchForm">
        <input type="text" id="query" placeholder="Type anything...">
        <button type="submit">Search</button>
    </form>
    <div id="results"></div>
</div>
<script>
const form = document.getElementById('searchForm'), input = document.getElementById('query'), resultsDiv = document.getElementById('results');
let es;
form.addEventListener('submit', e => {
    e.preventDefault();
    const q = input.value.trim();
    if (es) es.close();
    resultsDiv.innerHTML = '';
    if (!q) return;
    es = new EventSource('/search?query=' + encodeURIComponent(q));
    es.onmessage = e => {
        const item = JSON.parse(e.data);
        const div = document.createElement('div');
        div.className = 'result-item';
        const title = document.createElement('strong');
        title.textContent = item.file;
        const pre = document.createElement('pre');
        const rx = new RegExp(item.regex, 'gi');
        pre.innerHTML = item.snippet.replace(rx, m => `<span class="highlight">${m}</span>`);
        div.append(title, pre);
        resultsDiv.append(div);
    };
    es.onerror = () => {
        es.close();
        if (!resultsDiv.hasChildNodes()) {
            resultsDiv.innerHTML = '<div class="no-results">No results found</div>';
        }
    };
});
</script>
</body>
</html>"""

def build_pattern(q):
    parts = map(re.escape, q.split())
    return re.compile(r'\W*'.join(parts), re.IGNORECASE)

def file_scanner(path, pat, out_q):
    try:
        with open(path, 'r', errors='ignore') as f:
            for line in f:
                if pat.search(line):
                    out_q.put({
                        'file': os.path.relpath(path),
                        'snippet': line.strip(),
                        'regex': pat.pattern
                    })
    except:
        pass

@app.route('/')
def index():
    return render_template_string(HTML)

@app.route('/search')
def search():
    q = request.args.get('query', '').strip()
    if not q:
        return '', 204
    pat = build_pattern(q)
    q_out = Queue()
    futures = []
    for root, _, files in os.walk('.'):
        for fn in files:
            if fn.lower().endswith(EXTS):
                path = os.path.join(root, fn)
                futures.append(EXEC.submit(file_scanner, path, pat, q_out))
    def gen():
        alive = True
        while alive:
            try:
                item = q_out.get(timeout=0.1)
                yield f"data: {json.dumps(item)}\n\n"
            except Empty:
                if all(f.done() for f in futures):
                    alive = False
        yield "event: done\ndata: {}\n\n"
    return Response(stream_with_context(gen()), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)