from flask import Flask, Response, render_template_string
import psutil
import datetime
import time
import json

app = Flask(__name__)

HTML_PAGE = """
<!DOCTYPE html>
<html>
<head>
  <title>📊 Raspberry Pi Live Dashboard</title>

  <!-- Bootstrap CSS -->
  <link
    href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css"
    rel="stylesheet"
  >

  <style>
    body {
      background: linear-gradient(to bottom right, #232526, #414345);
      color: white;
    }
    .card {
      border: 2px solid #555;
      background: #2a2c2e;
    }
    .stat-big {
      font-size: 2.5rem;
      font-weight: bold;
    }
    .btn-theme {
      background: #007bff;
      color: white;
      font-weight: bold;
    }
    body.light-mode {
      background: #f8f9fa;
      color: #212529;
    }

    body.light-mode .card {
      background: white;
      border-color: #ccc;
    }

    body.light-mode .btn-theme,
      body.light-mode #themeToggle {
      color: #212529;
    }

  </style>
</head>
<body>

<nav class="navbar navbar-expand-lg navbar-dark bg-dark mb-4">
  <div class="container-fluid">
    <span class="navbar-brand">📈 Raspberry Pi Live Dashboard</span>
    <button id="themeToggle" class="btn btn-outline-light">Light Mode</button>
  </div>
</nav>

<div class="container text-center mb-4">
  <button class="btn btn-theme" onclick="toggleAutoUpdate()">
    Auto Refresh: <span id="autoState">ON</span>
  </button>
  <button class="btn btn-secondary ms-2" onclick="manualRefresh()">
    Manual Refresh
  </button>
  <span class="ms-4" id="lastUpdated">Last Updated: --:--:--</span>
</div>

<div class="container">
  <div class="row justify-content-center mb-4">

    <!-- CPU Card -->
    <div class="col-md-3 mb-3">
      <div class="card shadow-sm">
        <div class="card-body">
          <h5 class="card-title">⚙️ CPU Usage</h5>
          <p id="cpuValue" class="stat-big">--%</p>
          <small class="text-muted">Average across cores</small>
        </div>
      </div>
    </div>

    <!-- Memory Card -->
    <div class="col-md-3 mb-3">
      <div class="card shadow-sm">
        <div class="card-body">
          <h5 class="card-title">💾 Memory Usage</h5>
          <p id="memValue" class="stat-big">--%</p>
          <small class="text-muted">RAM Usage</small>
        </div>
      </div>
    </div>

    <!-- Temp Card -->
    <div class="col-md-3 mb-3">
      <div class="card shadow-sm">
        <div class="card-body">
          <h5 class="card-title">🔥 CPU Temp</h5>
          <p id="tempValue" class="stat-big">--°C</p>
          <small class="text-muted">Thermal Sensor</small>
        </div>
      </div>
    </div>

  </div>

  <div class="row">
    <canvas id="cpuChart" class="col-md-4"></canvas>
    <canvas id="memChart" class="col-md-4"></canvas>
    <canvas id="tempChart" class="col-md-4"></canvas>
  </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

<script>
let autoUpdate = true;

function toggleAutoUpdate() {
  autoUpdate = !autoUpdate;
  document.getElementById("autoState").innerText = autoUpdate ? "ON" : "OFF";
}

function manualRefresh() {
  fetch("/refresh")
    .then(res => res.json())
    .then(data => updateUI(data));
}

const cpuChart = new Chart(
  document.getElementById('cpuChart'),
  {
    type: 'line',
    data: { labels: [], datasets: [{ label: 'CPU %', data: [], borderColor: 'red', fill: false }]},
    options: { plugins: { tooltip: { enabled: true }}, scales: { y: { beginAtZero: true, max: 100 } } }
  }
);

const memChart = new Chart(
  document.getElementById('memChart'),
  {
    type: 'line',
    data: { labels: [], datasets: [{ label: 'Memory %', data: [], borderColor: 'blue', fill: false }]},
    options: { plugins: { tooltip: { enabled: true }}, scales: { y: { beginAtZero: true, max: 100 } } }
  }
);

const tempChart = new Chart(
  document.getElementById('tempChart'),
  {
    type: 'line',
    data: { labels: [], datasets: [{ label: 'Temp °C', data: [], borderColor: 'green', fill: false }]},
    options: { plugins: { tooltip: { enabled: true }}, scales: { y: { beginAtZero: true } } }
  }
);

const evtSource = new EventSource("/stream");

evtSource.onmessage = function(e) {
  const data = JSON.parse(e.data);
  if (autoUpdate) updateUI(data);
};

function updateUI(data) {
  const t = new Date().toLocaleTimeString();
  document.getElementById("lastUpdated").innerText = "Last Updated: " + t;

  document.getElementById("cpuValue").innerText = data.cpu + "%";
  document.getElementById("memValue").innerText = data.mem + "%";
  document.getElementById("tempValue").innerText = data.temp + "°C";

  cpuChart.data.labels.push(t);
  cpuChart.data.datasets[0].data.push(data.cpu);
  if (cpuChart.data.labels.length > 20) cpuChart.data.labels.shift(), cpuChart.data.datasets[0].data.shift();
  cpuChart.update();

  memChart.data.labels.push(t);
  memChart.data.datasets[0].data.push(data.mem);
  if (memChart.data.labels.length > 20) memChart.data.labels.shift(), memChart.data.datasets[0].data.shift();
  memChart.update();

  tempChart.data.labels.push(t);
  tempChart.data.datasets[0].data.push(data.temp);
  if (tempChart.data.labels.length > 20) tempChart.data.labels.shift(), tempChart.data.datasets[0].data.shift();
  tempChart.update();
}
// Theme toggle logic
const themeToggle = document.getElementById("themeToggle");

function setTheme(theme) {
  document.body.className = theme;
  localStorage.setItem("theme", theme);

  themeToggle.innerText = (theme === "light-mode") ? "Dark Mode" : "Light Mode";
}

// Load saved theme
const savedTheme = localStorage.getItem("theme");
if (savedTheme) {
  setTheme(savedTheme);
} else {
  setTheme(""); // default dark
}

themeToggle.addEventListener("click", () => {
  const current = document.body.className;
  if (current === "light-mode") setTheme("");
  else setTheme("light-mode");
});

</script>
</body>
</html>
"""

def get_stats():
    cpu = psutil.cpu_percent()
    mem = psutil.virtual_memory().percent
    temps = psutil.sensors_temperatures()
    temp = "N/A"
    if "cpu_thermal" in temps and temps["cpu_thermal"]:
        temp = temps["cpu_thermal"][0].current

    uptime = datetime.datetime.now() - datetime.datetime.fromtimestamp(psutil.boot_time())
    return {
        "cpu": cpu,
        "mem": mem,
        "temp": temp,
        "uptime": str(uptime).split(".")[0]
    }

@app.route("/")
def index():
    return render_template_string(HTML_PAGE)

@app.route("/stream")
def stream():
    def event_stream():
        while True:
            stats = get_stats()
            yield f"data: {json.dumps(stats)}\n\n"
            time.sleep(1)

    return Response(event_stream(), mimetype="text/event-stream")
@app.route("/refresh")
def refresh():
	return get_stats()
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
