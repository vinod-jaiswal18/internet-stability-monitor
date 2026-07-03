#!/usr/bin/env python3

import subprocess
import time
import csv
import os
import socket
import re
from datetime import datetime
from collections import deque
from urllib.request import urlopen

from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.console import Console

HOST = "8.8.8.8"
INTERVAL = 1
LOG_FILE = "internet_monitor_log.csv"
MAJOR_OUTAGE_SECONDS = 300

total = success = failed = outages = 0
latencies = []
last_status = None

current_down_start = None
current_down_packets = 0

last_10_outages = deque(maxlen=10)
major_outages = deque(maxlen=50)

console = Console()


def get_private_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "-"


def get_router_ip():
    try:
        result = subprocess.run(
            ["ip", "route"],
            capture_output=True,
            text=True
        )
        match = re.search(r"default via ([0-9.]+)", result.stdout)
        return match.group(1) if match else "-"
    except Exception:
        return "-"


def get_public_ip():
    try:
        return urlopen("https://api.ipify.org", timeout=3).read().decode()
    except Exception:
        return "-"


PRIVATE_IP = get_private_ip()
ROUTER_IP = get_router_ip()
PUBLIC_IP = get_public_ip()


def init_log():
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w", newline="") as f:
            csv.writer(f).writerow([
                "event", "start_time", "end_time",
                "duration_seconds", "packets_lost"
            ])


def ping():
    try:
        result = subprocess.run(
            ["ping", "-c", "1", "-W", "1", HOST],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if "time=" in line:
                    return True, float(line.split("time=")[1].split()[0])
            return True, None

        return False, None
    except Exception:
        return False, None


def log_outage(start, end, duration, packets):
    with open(LOG_FILE, "a", newline="") as f:
        csv.writer(f).writerow([
            "OUTAGE",
            start.strftime("%Y-%m-%d %H:%M:%S"),
            end.strftime("%Y-%m-%d %H:%M:%S"),
            duration,
            packets
        ])


def format_duration(seconds):
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    return f"{seconds // 60}m {seconds % 60}s"


def build_dashboard():
    loss_percent = (failed / total * 100) if total else 0
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    min_latency = min(latencies) if latencies else 0
    max_latency = max(latencies) if latencies else 0

    status = "ONLINE" if last_status else "OFFLINE"

    dashboard = Table(title="Internet Stability Monitor", expand=True, show_lines=False)
    dashboard.add_column("Metric", style="bold", no_wrap=True)
    dashboard.add_column("Value", no_wrap=True)

    dashboard.add_row("Target", HOST)
    dashboard.add_row("Status", status)
    dashboard.add_row("Public IP", PUBLIC_IP)
    dashboard.add_row("Private IP", PRIVATE_IP)
    dashboard.add_row("Router IP", ROUTER_IP)
    dashboard.add_row("Sent / Received / Dropped", f"{total} / {success} / {failed}")
    dashboard.add_row("Packet Loss", f"{loss_percent:.2f}%")
    dashboard.add_row("Outages", str(outages))
    dashboard.add_row("Ping Min / Avg / Max", f"{min_latency:.1f} / {avg_latency:.1f} / {max_latency:.1f} ms")
    dashboard.add_row("Current Ping", f"{latencies[-1]:.1f} ms" if latencies else "-")

    if current_down_start:
        down_time = int(time.time() - current_down_start.timestamp())
        dashboard.add_row("Current Downtime", f"{format_duration(down_time)} | Lost: {current_down_packets}")
    else:
        dashboard.add_row("Current Downtime", "0s")

    recent_table = Table(title="Last 10 Outages", expand=True, show_lines=False)
    recent_table.add_column("Start", no_wrap=True)
    recent_table.add_column("Restored", no_wrap=True)
    recent_table.add_column("Dur", no_wrap=True)
    recent_table.add_column("Lost", no_wrap=True)

    if last_10_outages:
        for outage in reversed(last_10_outages):
            recent_table.add_row(
                outage["start"],
                outage["end"],
                format_duration(outage["duration"]),
                str(outage["packets"])
            )
    else:
        recent_table.add_row("-", "-", "-", "-")

    major_table = Table(title="Outages > 5 Minutes", expand=True, show_lines=False)
    major_table.add_column("Start", no_wrap=True)
    major_table.add_column("Restored", no_wrap=True)
    major_table.add_column("Dur", no_wrap=True)
    major_table.add_column("Lost", no_wrap=True)

    if major_outages:
        for outage in reversed(major_outages):
            major_table.add_row(
                outage["start"],
                outage["end"],
                format_duration(outage["duration"]),
                str(outage["packets"])
            )
    else:
        major_table.add_row("-", "-", "-", "-")

    layout = Layout()
    layout.split_column(
        Layout(Panel(dashboard), size=15),
        Layout(Panel(recent_table), size=10),
        Layout(Panel(major_table), size=8)
    )

    return layout


def main():
    global total, success, failed, outages
    global last_status, current_down_start, current_down_packets

    init_log()

    try:
        with Live(build_dashboard(), refresh_per_second=2, screen=True) as live:
            while True:
                total += 1
                now = datetime.now()
                ok, latency = ping()

                if ok:
                    success += 1

                    if latency is not None:
                        latencies.append(latency)

                    if last_status is False and current_down_start:
                        restored_time = now
                        duration = int((restored_time - current_down_start).total_seconds())

                        outage_record = {
                            "start": current_down_start.strftime("%Y-%m-%d %H:%M:%S"),
                            "end": restored_time.strftime("%Y-%m-%d %H:%M:%S"),
                            "duration": duration,
                            "packets": current_down_packets
                        }

                        last_10_outages.append(outage_record)

                        if duration > MAJOR_OUTAGE_SECONDS:
                            major_outages.append(outage_record)

                        log_outage(
                            current_down_start,
                            restored_time,
                            duration,
                            current_down_packets
                        )

                        current_down_start = None
                        current_down_packets = 0

                    last_status = True

                else:
                    failed += 1

                    if last_status is not False:
                        outages += 1
                        current_down_start = now
                        current_down_packets = 1
                    else:
                        current_down_packets += 1

                    last_status = False

                live.update(build_dashboard())
                time.sleep(INTERVAL)

    except KeyboardInterrupt:
        console.print("\nMonitoring stopped.")
        console.print(f"Log saved at: {LOG_FILE}")


if __name__ == "__main__":
    main()
