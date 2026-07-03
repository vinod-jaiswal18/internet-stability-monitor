# Internet Stability Monitor

A lightweight terminal-based Internet monitoring tool for Ubuntu/Linux that continuously checks your Internet connection, detects outages, measures latency, and maintains a history of connectivity issues.

## Features

* ✅ Real-time Internet connectivity monitoring
* 📡 Live ping latency (Current / Min / Avg / Max)
* 📉 Packet loss statistics
* 📦 Total packets sent, received and dropped
* 🌐 Displays:

  * Public IP Address
  * Private IP Address
  * Default Gateway (Router IP)
* 🔴 Live outage detection
* ⏱ Tracks current outage duration
* 📋 Maintains the **last 10 outages**
* 🚨 Separate history for **major outages (>5 minutes)**
* 💾 Automatic CSV logging of all outages
* 🖥️ Compact terminal dashboard using Rich
* ⚡ Lightweight and suitable for 24×7 monitoring

---

## Screenshot

*Add a screenshot of the terminal dashboard here.*

---

## Requirements

* Ubuntu / Debian Linux
* Python 3.8+
* Rich library

Install dependencies:

```bash
sudo apt update
sudo apt install python3 python3-pip -y
pip3 install rich
```

---

## Installation

Clone the repository:

```bash
git clone https://github.com/<your-username>/internet-stability-monitor.git
cd internet-stability-monitor
```

Make the script executable:

```bash
chmod +x internet_monitor.py
```

Run the monitor:

```bash
./internet_monitor.py
```

Or:

```bash
python3 internet_monitor.py
```

---

## Dashboard Metrics

The dashboard displays:

* Connection Status
* Target Host
* Current Public IP
* Current Private IP
* Router (Gateway) IP
* Packets Sent
* Packets Received
* Packets Dropped
* Packet Loss %
* Total Outages
* Current Ping
* Minimum Ping
* Average Ping
* Maximum Ping
* Current Downtime
* Current Lost Packets

---

## Outage Tracking

### Last 10 Outages

Shows:

* Outage start time
* Connection restored time
* Total outage duration
* Number of packets lost

### Major Outages

Maintains a separate list of outages longer than five minutes for easy ISP reliability analysis.

---

## Log File

Every outage is automatically recorded in:

```text
internet_monitor_log.csv
```

Example:

```csv
event,start_time,end_time,duration_seconds,packets_lost
OUTAGE,2026-07-03 10:15:31,2026-07-03 10:15:38,7,7
```

---

## Customization

Change the target host:

```python
HOST = "8.8.8.8"
```

Examples:

| Host           | Purpose                  |
| -------------- | ------------------------ |
| 8.8.8.8        | Google DNS               |
| 1.1.1.1        | Cloudflare DNS           |
| Your Router IP | Local network monitoring |

Adjust ping interval:

```python
INTERVAL = 1
```

Adjust major outage threshold:

```python
MAJOR_OUTAGE_SECONDS = 300
```

---

## Typical Use Cases

* Monitor ISP stability
* Detect intermittent Internet drops
* Identify long outages
* Troubleshoot Wi-Fi connectivity
* Verify router stability
* Collect outage evidence for ISP support

---

## Roadmap

Planned enhancements:

* Email notifications
* Telegram alerts
* Desktop notifications
* Live latency graph
* Daily statistics
* Weekly and monthly reports
* Multiple host monitoring
* Automatic IP refresh
* Speed test integration
* Systemd service support
* Docker support
* Prometheus/Grafana integration

---

## License

MIT License
