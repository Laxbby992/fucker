from flask import Flask, request, render_template_string, Response, stream_with_context
import os, re, json
from concurrent.futures import ThreadPoolExecutor
from queue import Queue, Empty

app = Flask(__name__)
EXTS = ['.txt', '.csv', '.json']
EXEC = ThreadPoolExecutor(max_workers=500)

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Oldantest ~ Data Leak Finder</title>
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;500;700&display=swap" rel="stylesheet">
<style>
body {
  margin: 0;
  font-family: 'Poppins', sans-serif;
  background: #0d1117;
  color: white;
  overflow-x: hidden;
}
.container {
  max-width: 800px;
  margin: auto;
  padding: 2rem;
}
h1 {
  text-align: center;
  font-size: 2rem;
  margin-bottom: 1rem;
}
.controls {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: center;
  margin-bottom: 1rem;
}
.controls input, .controls select, .controls button {
  font-family: 'Poppins', sans-serif;
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 12px;
  font-size: 1rem;
}
.controls button {
  background: linear-gradient(135deg, #00ffff, #0066ff);
  color: black;
  transition: all 0.3s ease;
  cursor: pointer;
}
.controls button:hover {
  opacity: 0.8;
}
#results {
  margin-top: 1rem;
}
.result-item {
  background: #161b22;
  padding: 1rem;
  margin-bottom: 1rem;
  border-radius: 12px;
  animation: fadeIn 0.5s ease-out forwards;
}
.result-item pre {
  white-space: pre-wrap;
  word-break: break-word;
}
.highlight {
  background: yellow;
  color: black;
  padding: 0 4px;
  border-radius: 3px;
}
.no-results {
  text-align: center;
  margin-top: 2rem;
  font-size: 1.2rem;
}
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
canvas {
  position: fixed;
  top: 0; left: 0;
  z-index: -1;
}
footer {
  text-align: center;
  margin-top: 4rem;
  padding-bottom: 1rem;
  color: #888;
  font-size: 0.9rem;
}
</style>
</head>
<body>
<canvas id="bg"></canvas>
<div class="container">
  <h1>Oldantest ~ Leaks Finder</h1>
  <div class="controls">
    <input type="text" id="query" placeholder="Search..." autocomplete="off">
    <select id="exts">
      <option value="all">All</option>
      <option value=".txt">.txt</option>
      <option value=".csv">.csv</option>
      <option value=".json">.json</option>
    </select>
    <button onclick="startSearch()">Search</button>
    <button onclick="exportResults()">Export</button>
    <button onclick="toggleTheme()">Theme</button>
  </div>
  <div id="counter">Results: 0</div>
  <div id="results"></div>
</div>
<audio id="beep" src="https://freesound.org/data/previews/341/341695_5260877-lq.mp3"></audio>
<footer>&copy; Oldantest 2025. All rights reserved.</footer>
<script>
let es, results = [], theme = localStorage.getItem("theme") || "dark";
document.body.setAttribute("data-theme", theme);
document.getElementById('query').value = localStorage.getItem("lastQuery") || "";

function toggleTheme() {
  theme = theme === "dark" ? "light" : "dark";
  document.body.setAttribute("data-theme", theme);
  localStorage.setItem("theme", theme);
}

function exportResults() {
  if (results.length === 0) return alert("No results.");
  const text = results.map(r => r.file + "\\n" + r.snippet).join("\\n\\n");
  const blob = new Blob([text], {type: "text/plain"});
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "results.txt";
  a.click();
}

function startSearch() {
  const input = document.getElementById('query');
  const ext = document.getElementById('exts').value;
  const q = input.value.trim();
  const resultsDiv = document.getElementById('results');
  const counter = document.getElementById('counter');
  if (!q) return;
  localStorage.setItem("lastQuery", q);
  if (es) es.close();
  resultsDiv.innerHTML = '';
  results = [];
  counter.textContent = "Results: 0";

  es = new EventSource(`/search?query=${encodeURIComponent(q)}&ext=${ext}`);
  es.onmessage = e => {
    const item = JSON.parse(e.data);
    results.push(item);
    const div = document.createElement('div');
    div.className = 'result-item';
    const title = document.createElement('strong');
    title.textContent = item.file;
    const pre = document.createElement('pre');
    const rx = new RegExp(item.regex, 'gi');
    pre.innerHTML = item.snippet.replace(rx, m => `<span class="highlight">${m}</span>`);
    div.append(title, pre);
    resultsDiv.append(div);
    document.getElementById("beep").play();
    counter.textContent = "Results: " + results.length;
    window.scrollTo(0, document.body.scrollHeight);
  };
  es.onerror = () => {
    es.close();
    if (!resultsDiv.hasChildNodes()) {
      resultsDiv.innerHTML = '<div class="no-results">No results found</div>';
    }
  };
}

document.getElementById('query').addEventListener('keydown', e => {
  if (e.key === 'Enter') startSearch();
});

const canvas = document.getElementById('bg');
const ctx = canvas.getContext('2d');
let w = canvas.width = window.innerWidth;
let h = canvas.height = window.innerHeight;
let particles = Array.from({length: 60}, () => ({
  x: Math.random() * w,
  y: Math.random() * h,
  r: Math.random() * 2 + 1,
  dx: (Math.random() - 0.5) * 0.5,
  dy: (Math.random() - 0.5) * 0.5
}));

function animate() {
  ctx.clearRect(0, 0, w, h);
  for (let p of particles) {
    ctx.beginPath();
    const gradient = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.r * 4);
    gradient.addColorStop(0, 'cyan');
    gradient.addColorStop(1, 'blue');
    ctx.fillStyle = gradient;
    ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
    ctx.fill();
    p.x += p.dx;
    p.y += p.dy;
    if (p.x < 0 || p.x > w) p.dx *= -1;
    if (p.y < 0 || p.y > h) p.dy *= -1;
  }
  requestAnimationFrame(animate);
}
animate();
window.onresize = () => {
  w = canvas.width = window.innerWidth;
  h = canvas.height = window.innerHeight;
};
</script>
</body>
</html>
"""

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
    ext = request.args.get('ext', 'all')
    if not q:
        return '', 204
    pat = build_pattern(q)
    q_out = Queue()
    futures = []
    for root, _, files in os.walk('.'):
        for fn in files:
            if not fn.lower().endswith(tuple(EXTS)):
                continue
            if ext != 'all' and not fn.lower().endswith(ext):
                continue
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
