import http.server
import socketserver
import threading
import json
import time

current_data = {"tps": 2500, "cpu": 10, "status": "Healthy"}

class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/data':
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(current_data).encode())
        elif self.path == '/':
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Live TPS Dashboard</title>
                <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
                <style>
                    body { background-color: #111; color: #fff; font-family: sans-serif; text-align: center; }
                    .container { width: 80%; margin: auto; padding-top: 50px; }
                    #status { font-size: 24px; font-weight: bold; margin-bottom: 20px; color: #4ade80; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Real-Time Application Throughput</h1>
                    <div id="status">System Status: Healthy</div>
                    <canvas id="tpsChart"></canvas>
                </div>
                <script>
                    const ctx = document.getElementById('tpsChart').getContext('2d');
                    const tpsChart = new Chart(ctx, {
                        type: 'line',
                        data: {
                            labels: [],
                            datasets: [{
                                label: 'Transactions Per Second (TPS)',
                                data: [],
                                borderColor: '#3b82f6',
                                backgroundColor: 'rgba(59, 130, 246, 0.2)',
                                fill: true,
                                tension: 0.4
                            }]
                        },
                        options: {
                            responsive: true,
                            scales: {
                                y: { beginAtZero: true, max: 3000 },
                                x: { display: false }
                            },
                            animation: { duration: 0 }
                        }
                    });

                    setInterval(async () => {
                        const res = await fetch('/api/data');
                        const data = await res.json();
                        
                        document.getElementById('status').innerText = `System Status: ${data.status}`;
                        document.getElementById('status').style.color = data.status === 'Healthy' ? '#4ade80' : '#ef4444';
                        
                        const now = new Date().toLocaleTimeString();
                        tpsChart.data.labels.push(now);
                        tpsChart.data.datasets[0].data.push(data.tps);
                        
                        if (tpsChart.data.labels.length > 30) {
                            tpsChart.data.labels.shift();
                            tpsChart.data.datasets[0].data.shift();
                        }
                        tpsChart.update();
                    }, 1000);
                </script>
            </body>
            </html>
            """
            self.wfile.write(html.encode())
        else:
            self.send_response(404)
            self.end_headers()

def start_server():
    with socketserver.TCPServer(("", 8080), DashboardHandler) as httpd:
        httpd.serve_forever()

threading.Thread(target=start_server, daemon=True).start()

print("Server started at http://localhost:8080")
print("Updating data...")
for i in range(10):
    time.sleep(1)
    if i == 3:
        current_data = {"tps": 500, "cpu": 100, "status": "Fault Active"}
    elif i == 7:
        current_data = {"tps": 2450, "cpu": 15, "status": "Healthy"}
print("Done")
