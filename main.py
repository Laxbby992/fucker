from flask import Flask, request, render_template_string, Response, stream_with_context
import os, re, json
from concurrent.futures import ThreadPoolExecutor
from queue import Queue, Empty

app = Flask(__name__)
EXTS = ('.txt', '.csv', '.json')
EXEC = ThreadPoolExecutor(max_workers=500)

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="windows-1252">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Oldantest ~ Leaks Finder</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@600&display=swap');
* { box-sizing:border-box; }
body { margin:0; font-family:'Orbitron',sans-serif; background:#0a0a0a; color:#eee; overflow-x:hidden; }
.container { max-width:880px; margin:40px auto; background:#141414; padding:30px; border-radius:20px; box-shadow:0 0 40px #00ffff66; animation:fadeIn 1s ease-in-out; }
h1 { text-align:center; color:#00ffff; font-size:2.5em; margin-bottom:30px; text-shadow:0 0 12px #00ffff; }
input, button { font-size:18px; border-radius:8px; transition:.3s; }
input { width:calc(100% - 120px); padding:15px; background:#111; color:#fff; border:none; outline:none; float:left; margin-bottom:20px; }
button { width:100px; padding:15px; margin-left:10px; background:#00ffff; border:none; color:#000; cursor:pointer; }
button:hover { background:#00cccc; }
#bar { display:flex; flex-wrap:wrap; justify-content:center; margin-bottom:20px; }
.result-item { background:#1e1e1e; margin:12px 0; padding:18px; border-radius:12px; box-shadow:0 0 12px #00ffff33; animation:fadeSlide 0.5s ease-out; }
.result-item strong { display:block; color:#00ffff; margin-bottom:8px; }
.result-item pre { background:#111; padding:12px; border-radius:8px; overflow:auto; color:#fff; font-size:0.95em; }
.highlight { background:#ff0; color:#000; padding:2px 4px; border-radius:4px; }
.no-results { text-align:center; margin-top:30px; font-size:20px; color:#888; }
@keyframes fadeIn { from{opacity:0; transform:scale(0.97);} to{opacity:1; transform:scale(1);} }
@keyframes fadeSlide { from{opacity:0; transform:translateY(10px);} to{opacity:1; transform:translateY(0);} }
</style>
</head>
<body>
<div class="container">
    <h1>Oldantest ~ Leaks Finder</h1>
    <div id="bar">
        <input type="text" id="query" placeholder="Name, Last Name, Email, Phone Number..." autocomplete="off">
        <button onclick="startSearch()">Search</button>
    </div>
    <div id="results"></div>
</div>
<script>
let es;
function debounce(fn, ms){ let t; return (...args)=>{ clearTimeout(t); t = setTimeout(()=>fn(...args), ms); }; }
function startSearch(){
    const input = document.getElementById('query');
    const resultsDiv = document.getElementById('results');
    const q = input.value.trim();
    if(es) es.close();
    resultsDiv.innerHTML = '';
    if(!q) return;
    es = new EventSource('/search?query='+encodeURIComponent(q));
    es.onmessage = e => {
        const item = JSON.parse(e.data);
        const div = document.createElement('div');
        div.className = 'result-item';
        const title = document.createElement('strong');
        title.textContent = item.file;
        const pre = document.createElement('pre');
        const rx = new RegExp(item.regex,'gi');
        pre.innerHTML = item.snippet.replace(rx,m=>`<span class="highlight">${m}</span>`);
        div.append(title, pre);
        resultsDiv.append(div);
    };
    es.onerror = ()=>{ es.close(); if(!resultsDiv.hasChildNodes()){ resultsDiv.innerHTML = '<div class="no-results">No results found</div>'; } };
}
document.getElementById('query').addEventListener('keydown',e=>{ if(e.key==='Enter') startSearch(); });
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
    q = request.args.get('query','').strip()
    if not q:
        return '', 204
    pat = build_pattern(q)
    q_out = Queue()
    futures = []
    for root,_,files in os.walk('.'):
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
    app.run(host='0.0.0.0', port=5001, threaded=True)
