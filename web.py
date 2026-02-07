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
    <title>Pi Dashboard SSE</title>
</head>
<body>
    <h1>Raspberry Pi Live Dashboard</h1>
    <div id="stats"></div>

    <script>
        const evtSource = new EventSource("/stream");
        evtSource.onmessage = function(e) {
            const data = JSON.parse(e.data);
            document.getElementById("stats").innerHTML = `
                <p>CPU Usage: ${data.cpu}%</p>
                <p>Memory Usage: ${data.mem}%</p>
                <p>CPU Temp: ${data.temp}°C</p>
                <p>Uptime: ${data.uptime}</p>
            `;
        };
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
