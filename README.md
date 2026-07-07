# Internet Stability Monitor v2.2

A lightweight, terminal-based Internet monitoring service for Ubuntu/Linux that continuously monitors Internet connectivity in the background, tracks outages, records public IP changes, and provides a live dashboard on demand.

Unlike traditional ping tools, Internet Stability Monitor is designed to run 24×7 with minimal resource usage while maintaining a detailed history of Internet outages and network changes.

---

## Features

### Background Monitoring

* Runs as a background service
* Very low CPU and memory usage
* Dashboard can be opened anytime without interrupting monitoring
* Graceful start and stop commands

### Connectivity Monitoring

* Continuous Internet monitoring using ICMP Ping
* Configurable target host (Google DNS by default)
* Tracks:

  * Packets Sent
  * Packets Received
  * Packets Dropped
  * Packet Loss %
  * Internet Uptime %
* Live latency statistics:

  * Current
  * Minimum
  * Average
  * Maximum

### Network Information

Displays live network information including:

* Public IP Address
* Private IP Address
* Default Gateway (Router IP)
* ISP Name
* Approximate Location (City / Region / Country)

Public IP information refreshes automatically every 5 minutes.

---

## Outage Tracking

Automatically detects Internet outages and records:

* Start time
* End time
* Duration
* Packets lost during outage

### Last 10 Outages

Shows the most recent connectivity interruptions.

### Major Outages

Maintains a separate history of outages longer than 5 minutes.

### Downtime Statistics

Tracks:

* Current outage duration
* Today's cumulative downtime
* Longest outage
* Last restored time
* Total outage count

---

## Public IP Change Detection

The monitor automatically detects whenever your ISP assigns a new public IP address.

Example:

| Time     | Previous IP       | Current IP    |
| -------- | ----------------- | ------------- |
| 14:25:18 | ~~49.xxx.xxx.12~~ | 49.xxx.xxx.48 |

Useful for:

* Dynamic IP connections
* ISP troubleshooting
* Router reboot verification
* PPPoE reconnect detection

---

## Dashboard

The dashboard is divided into four compact panels:

```
+----------------------+----------------------+
| Metrics              | Last 10 Outages      |
+----------------------+----------------------+
| Major Outages        | Public IP Changes    |
+----------------------+----------------------+
```

The dashboard can be opened anytime while monitoring continues in the background.

---

## Logging

All outages are automatically logged into daily CSV files.

Example:

```
~/.internet-monitor/
├── internet_monitor_2026-07-07.csv
├── state.json
└── monitor.pid
```

CSV format:

```
event,start_time,end_time,duration_seconds,packets_lost
OUTAGE,2026-07-07 10:15:11,2026-07-07 10:15:16,5,5
```

---

## Installation

Clone the repository:

```bash
git clone https://github.com/<your-username>/internet-stability-monitor.git
cd internet-stability-monitor
```

Install dependencies:

```bash
sudo apt update
sudo apt install python3 python3-pip -y
pip3 install rich
```

Make executable:

```bash
chmod +x internet_monitor.py
```

---

## Usage

### Start background monitoring

```bash
./internet_monitor.py start
```

---

### Open live dashboard

```bash
./internet_monitor.py monitor
```

---

### Display current statistics

```bash
./internet_monitor.py status
```

---

### Stop monitoring

```bash
./internet_monitor.py stop
```

---

### Reset statistics

```bash
./internet_monitor.py reset
```

---

## Configuration

Default settings:

```python
HOST = "8.8.8.8"
INTERVAL = 1
MAJOR_OUTAGE_SECONDS = 300
IP_REFRESH_SECONDS = 300
```

You can easily customize:

* Ping target
* Ping interval
* Major outage threshold
* Public IP refresh interval

---

## Project Structure

```
internet-monitor/
│
├── internet_monitor.py
├── README.md
└── LICENSE
```

Runtime files:

```
~/.internet-monitor/
│
├── monitor.pid
├── state.json
├── internet_monitor_YYYY-MM-DD.csv
```

---

## Typical Use Cases

* Monitor ISP reliability
* Detect intermittent Internet issues
* Verify broadband stability
* Monitor router reconnects
* Detect public IP changes
* Collect evidence for ISP support tickets
* Long-term home lab monitoring
* Remote workstation monitoring

---

## License

MIT License

---

## Contributing

Contributions, bug reports, and feature requests are welcome. Feel free to open an issue or submit a pull request.

If you find this project useful, consider giving it a ⭐ on GitHub.
