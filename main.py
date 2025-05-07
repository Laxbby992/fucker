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
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600&display=swap" rel="stylesheet">
<style>
body {
  font-family: 'Poppins', sans-serif;
  margin: 0;
  background: #111;
  color: #fff;
  overflow-x: hidden;
}
.container {
  padding: 1rem;
  max-width: 900px;
  margin: auto;
}
.controls {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 1rem;
}
.controls input, .controls select, .controls button {
  padding: 0.6rem;
  font-size: 1rem;
  border: none;
  border-radius: 8px;
}
.controls input, .controls select {
  flex: 1 1 150px;
}
.controls button {
  background-color: #222;
  color: #fff;
  cursor: pointer;
}
.controls button:hover {
  background-color: #444;
}
#results {
  margin-top: 1rem;
}
.result-item {
  background: #222;
  padding: 1rem;
  border-radius: 12px;
  margin-bottom: 1rem;
  animation: fadeIn 0.3s ease-out forwards;
}
.result-item pre {
  white-space: pre-wrap;
  word-wrap: break-word;
}
.highlight {
  background: yellow;
  color: black;
}
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
canvas {
  position: fixed;
  top: 0;
  left: 0;
  z-index: -1;
}
.no-results {
  text-align: center;
  padding: 2rem;
  color: #888;
}
footer {
  text-align: center;
  margin-top: 3rem;
  color: #555;
  font-size: 0.9rem;
}
@media (max-width: 768px) {
  .controls {
    flex-direction: column;
  }
}
</style>
</head>
<body data-theme="dark">
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
    <button id="exportBtn" onclick="exportResults()" style="display:none;">Export</button>
  </div>
  <div id="counter">Results: 0</div>
  <div id="results"></div>
</div>
<audio id="beep" src="/static/beep-6-96243.mp3"></audio>
<footer>&copy; Oldantest 2025. All rights reserved.</footer>
<script>
let es, results = []
function exportResults() {
  if (results.length === 0) return alert("No results.")
  const text = results.map(r => r.file + "\\n" + r.snippet).join("\\n\\n")
  const blob = new Blob([text], {type: "text/plain"})
  const a = document.createElement("a")
  a.href = URL.createObjectURL(blob)
  a.download = "results.txt"
  a.click()
}
function startSearch() {
  const input = document.getElementById('query')
  const ext = document.getElementById('exts').value
  const resultsDiv = document.getElementById('results')
  const counter = document.getElementById('counter')
  const q = input.value.trim()
  if (!q) return
  if (es) es.close()
  resultsDiv.innerHTML = ''
  results = []
  counter.textContent = "Results: 0"
  document.getElementById("exportBtn").style.display = "none"
  es = new EventSource(`/search?query=${encodeURIComponent(q)}&ext=${ext}`)
  es.onmessage = e => {
    const item = JSON.parse(e.data)
    results.push(item)
    const div = document.createElement('div')
    div.className = 'result-item'
    const title = document.createElement('strong')
    title.textContent = item.file
    const pre = document.createElement('pre')
    const rx = new RegExp(item.regex, 'gi')
    pre.innerHTML = item.snippet.replace(rx, m => `<span class="highlight">${m}</span>`)
    div.append(title, pre)
    resultsDiv.append(div)
    document.getElementById("beep").play()
    counter.textContent = "Results: " + results.length
    document.getElementById("exportBtn").style.display = "inline-block"
    window.scrollTo(0, document.body.scrollHeight)
  }
  es.onerror = () => {
    es.close()
    if (!resultsDiv.hasChildNodes()) {
      resultsDiv.innerHTML = '<div class="no-results">No results found</div>'
      document.getElementById("exportBtn").style.display = "none"
    }
  }
}
document.getElementById('query').addEventListener('keydown', e => {
  if (e.key === 'Enter') startSearch()
})
const canvas = document.getElementById('bg')
const ctx = canvas.getContext('2d')
let w, h, dots = []
function resize() {
  w = canvas.width = window.innerWidth
  h = canvas.height = window.innerHeight
  dots = Array.from({length: 50}, () => ({
    x: Math.random()*w,
    y: Math.random()*h,
    r: Math.random()*1.5+1,
    dx: Math.random()*0.5-0.25,
    dy: Math.random()*0.5-0.25
  }))
}
function animate() {
  ctx.clearRect(0, 0, w, h)
  for (let dot of dots) {
    dot.x += dot.dx
    dot.y += dot.dy
    if (dot.x < 0 || dot.x > w) dot.dx *= -1
    if (dot.y < 0 || dot.y > h) dot.dy *= -1
    ctx.beginPath()
    ctx.arc(dot.x, dot.y, dot.r, 0, Math.PI*2)
    ctx.fillStyle = "rgba(255,255,255,0.2)"
    ctx.fill()
  }
  requestAnimationFrame(animate)
}
window.addEventListener('resize', resize)
resize()
animate()
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
