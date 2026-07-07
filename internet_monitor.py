#!/usr/bin/env python3

import subprocess, time, csv, os, socket, re, json, signal, sys
from datetime import datetime
from urllib.request import urlopen
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.console import Console

HOST = "8.8.8.8"
INTERVAL = 1
MAJOR_OUTAGE_SECONDS = 300
IP_REFRESH_SECONDS = 300

BASE_DIR = os.path.expanduser("~/.internet-monitor")
PID_FILE = f"{BASE_DIR}/monitor.pid"
STATE_FILE = f"{BASE_DIR}/state.json"

console = Console()


def ensure_dir():
    os.makedirs(BASE_DIR, exist_ok=True)


def today_log_file():
    return f"{BASE_DIR}/internet_monitor_{datetime.now().strftime('%Y-%m-%d')}.csv"


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
        result = subprocess.run(["ip", "route"], capture_output=True, text=True)
        match = re.search(r"default via ([0-9.]+)", result.stdout)
        return match.group(1) if match else "-"
    except Exception:
        return "-"


def get_public_ip_details():
    sources = ["https://ipinfo.io/json", "https://ipapi.co/json/"]

    for source in sources:
        try:
            data = json.loads(urlopen(source, timeout=5).read().decode())
            ip = data.get("ip", "-")
            isp = data.get("org") or data.get("asn", "-")
            location = ", ".join(x for x in [
                data.get("city", ""),
                data.get("region", ""),
                data.get("country", "")
            ] if x)
            return ip, isp, location or "-"
        except Exception:
            pass

    for source in [
        "https://api.ipify.org",
        "https://ifconfig.me/ip",
        "https://icanhazip.com",
        "https://checkip.amazonaws.com"
    ]:
        try:
            ip = urlopen(source, timeout=5).read().decode().strip()
            if ip:
                return ip, "-", "-"
        except Exception:
            pass

    return "Unavailable", "-", "-"


def default_state():
    return {
        "total": 0,
        "success": 0,
        "failed": 0,
        "outages": 0,
        "today_downtime": 0,
        "longest_outage": 0,
        "last_restored_time": "-",
        "last_status": None,
        "current_down_start": None,
        "current_down_packets": 0,
        "latencies": [],
        "last_10_outages": [],
        "major_outages": [],
        "public_ip": "Loading...",
        "public_ip_history": [],
        "isp": "-",
        "location": "-",
        "private_ip": get_private_ip(),
        "router_ip": get_router_ip(),
        "last_ip_update": 0,
        "started_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


def load_state():
    ensure_dir()
    if not os.path.exists(STATE_FILE):
        return default_state()
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return default_state()


def save_state(state):
    ensure_dir()
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f)
    os.replace(tmp, STATE_FILE)


def init_log():
    log_file = today_log_file()
    if not os.path.exists(log_file):
        with open(log_file, "w", newline="") as f:
            csv.writer(f).writerow([
                "event",
                "start_time",
                "end_time",
                "duration_seconds",
                "packets_lost"
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
    init_log()
    with open(today_log_file(), "a", newline="") as f:
        csv.writer(f).writerow([
            "OUTAGE",
            start,
            end,
            duration,
            packets
        ])


def update_public_ip_history(state, new_ip):
    old_ip = state.get("public_ip")

    if not new_ip or new_ip in ["-", "Unavailable", "Loading..."]:
        return

    if old_ip and old_ip not in ["-", "Unavailable", "Loading..."] and old_ip != new_ip:
        state.setdefault("public_ip_history", []).append({
            "old_ip": old_ip,
            "new_ip": new_ip,
            "changed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        state["public_ip_history"] = state["public_ip_history"][-10:]

    state["public_ip"] = new_ip


def format_duration(seconds):
    seconds = int(seconds or 0)
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m {seconds % 60}s"
    return f"{seconds // 3600}h {(seconds % 3600) // 60}m"


def is_running():
    if not os.path.exists(PID_FILE):
        return False
    try:
        with open(PID_FILE) as f:
            pid = int(f.read().strip())
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def daemon_loop():
    ensure_dir()
    init_log()

    state = load_state()
    running = True

    def shutdown(signum, frame):
        nonlocal running
        running = False

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    while running:
        now_ts = time.time()

        if now_ts - state.get("last_ip_update", 0) > IP_REFRESH_SECONDS:
            new_ip, new_isp, new_location = get_public_ip_details()
            update_public_ip_history(state, new_ip)

            state["isp"] = new_isp
            state["location"] = new_location
            state["private_ip"] = get_private_ip()
            state["router_ip"] = get_router_ip()
            state["last_ip_update"] = now_ts

        state["total"] += 1
        now = datetime.now()
        ok, latency = ping()

        if ok:
            state["success"] += 1

            if latency is not None:
                state["latencies"].append(latency)
                state["latencies"] = state["latencies"][-10000:]

            if state["last_status"] is False and state["current_down_start"]:
                restored = now
                start_dt = datetime.strptime(
                    state["current_down_start"],
                    "%Y-%m-%d %H:%M:%S"
                )
                duration = int((restored - start_dt).total_seconds())

                state["today_downtime"] += duration
                state["longest_outage"] = max(state["longest_outage"], duration)
                state["last_restored_time"] = restored.strftime("%H:%M:%S")

                outage = {
                    "start": state["current_down_start"],
                    "end": restored.strftime("%Y-%m-%d %H:%M:%S"),
                    "duration": duration,
                    "packets": state["current_down_packets"]
                }

                state["last_10_outages"].append(outage)
                state["last_10_outages"] = state["last_10_outages"][-10:]

                if duration > MAJOR_OUTAGE_SECONDS:
                    state["major_outages"].append(outage)
                    state["major_outages"] = state["major_outages"][-50:]

                log_outage(
                    outage["start"],
                    outage["end"],
                    duration,
                    state["current_down_packets"]
                )

                state["current_down_start"] = None
                state["current_down_packets"] = 0

            state["last_status"] = True

        else:
            state["failed"] += 1

            if state["last_status"] is not False:
                state["outages"] += 1
                state["current_down_start"] = now.strftime("%Y-%m-%d %H:%M:%S")
                state["current_down_packets"] = 1
            else:
                state["current_down_packets"] += 1

            state["last_status"] = False

        save_state(state)
        time.sleep(INTERVAL)

    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)


def start():
    ensure_dir()

    if is_running():
        console.print("Monitor is already running.")
        return

    process = subprocess.Popen(
        [sys.executable, os.path.abspath(__file__), "daemon"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        start_new_session=True
    )

    with open(PID_FILE, "w") as f:
        f.write(str(process.pid))

    console.print(f"Started background monitor. PID: {process.pid}")


def stop():
    if not os.path.exists(PID_FILE):
        console.print("Monitor is not running.")
        return

    try:
        with open(PID_FILE) as f:
            pid = int(f.read().strip())

        os.kill(pid, signal.SIGTERM)
        time.sleep(1)

        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)

        console.print("Stopped background monitor.")
    except Exception:
        console.print("Unable to stop monitor. Removing stale PID file.")
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)


def build_dashboard(state):
    total = state["total"]
    success = state["success"]
    failed = state["failed"]
    latencies = state.get("latencies", [])

    uptime = (success / total * 100) if total else 0
    loss = (failed / total * 100) if total else 0

    avg = sum(latencies) / len(latencies) if latencies else 0
    mn = min(latencies) if latencies else 0
    mx = max(latencies) if latencies else 0
    cur = f"{latencies[-1]:.1f}" if latencies else "-"

    status = "ONLINE" if state["last_status"] else "OFFLINE"

    if state["current_down_start"]:
        start_dt = datetime.strptime(
            state["current_down_start"],
            "%Y-%m-%d %H:%M:%S"
        )
        current_down = int((datetime.now() - start_dt).total_seconds())
        current_down_text = f"{format_duration(current_down)} / {state['current_down_packets']} lost"
    else:
        current_down_text = "0s"

    metrics = Table(
        title="Internet Monitor v2.2",
        expand=True,
        show_lines=False,
        pad_edge=False
    )
    metrics.add_column("Metric", no_wrap=True, width=15)
    metrics.add_column("Value", no_wrap=True)

    metrics.add_row("Service", "RUNNING" if is_running() else "STOPPED")
    metrics.add_row("Status", status)
    metrics.add_row("Target", HOST)
    metrics.add_row("Public IP", state.get("public_ip", "-"))
    metrics.add_row("Private IP", state.get("private_ip", "-"))
    metrics.add_row("Router IP", state.get("router_ip", "-"))
    metrics.add_row("ISP", state.get("isp", "-")[:35])
    metrics.add_row("Location", state.get("location", "-")[:35])
    metrics.add_row("Pkt S/R/L", f"{total}/{success}/{failed}")
    metrics.add_row("Loss/Uptime", f"{loss:.2f}% / {uptime:.2f}%")
    metrics.add_row("Ping C/M/A/X", f"{cur}/{mn:.1f}/{avg:.1f}/{mx:.1f} ms")
    metrics.add_row("Outages", str(state["outages"]))
    metrics.add_row("Curr Down", current_down_text)
    metrics.add_row("Today Down", format_duration(state["today_downtime"]))
    metrics.add_row("Longest", format_duration(state["longest_outage"]))
    metrics.add_row("Last Up", state["last_restored_time"])

    recent = Table(
        title="Last 10 Outages",
        expand=True,
        show_lines=False,
        pad_edge=False
    )
    recent.add_column("Start", no_wrap=True)
    recent.add_column("Dur", no_wrap=True)
    recent.add_column("Lost", no_wrap=True)

    if state.get("last_10_outages"):
        for outage in reversed(state.get("last_10_outages", [])):
            recent.add_row(
                outage["start"][11:19],
                format_duration(outage["duration"]),
                str(outage["packets"])
            )
    else:
        recent.add_row("-", "-", "-")

    major = Table(
        title="Major Outages > 5m",
        expand=True,
        show_lines=False,
        pad_edge=False
    )
    major.add_column("Start", no_wrap=True)
    major.add_column("End", no_wrap=True)
    major.add_column("Dur", no_wrap=True)
    major.add_column("Lost", no_wrap=True)

    if state.get("major_outages"):
        for outage in reversed(state.get("major_outages", [])):
            major.add_row(
                outage["start"][11:19],
                outage["end"][11:19],
                format_duration(outage["duration"]),
                str(outage["packets"])
            )
    else:
        major.add_row("-", "-", "-", "-")

    ip_history = Table(
        title="Public IP Changes",
        expand=True,
        show_lines=False,
        pad_edge=False
    )
    ip_history.add_column("Time", no_wrap=True)
    ip_history.add_column("Old IP", no_wrap=True)
    ip_history.add_column("New IP", no_wrap=True)

    history = state.get("public_ip_history", [])

    if history:
        for item in reversed(history[-10:]):
            ip_history.add_row(
                item["changed_at"][11:19],
                f"[strike]{item['old_ip']}[/strike]",
                item["new_ip"]
            )
    else:
        ip_history.add_row("-", "-", "-")

    top = Layout()
    top.split_row(
        Layout(Panel(metrics), ratio=1),
        Layout(Panel(recent), ratio=1)
    )

    bottom = Layout()
    bottom.split_row(
        Layout(Panel(major), ratio=1),
        Layout(Panel(ip_history), ratio=1)
    )

    layout = Layout()
    layout.split_column(
        Layout(top, ratio=2),
        Layout(bottom, ratio=1)
    )

    return layout


def monitor():
    try:
        with Live(build_dashboard(load_state()), refresh_per_second=2, screen=True) as live:
            while True:
                live.update(build_dashboard(load_state()))
                time.sleep(1)
    except KeyboardInterrupt:
        console.print("\nExited dashboard. Background monitor is still running.")


def status():
    console.print(build_dashboard(load_state()))


def reset():
    if is_running():
        console.print("Stop monitor before reset: ./internet_monitor.py stop")
        return

    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)

    console.print("Stats reset completed.")


def usage():
    console.print("""
Usage:
  ./internet_monitor.py start      Start monitor in background
  ./internet_monitor.py monitor    Show live dashboard
  ./internet_monitor.py status     Show current stats once
  ./internet_monitor.py stop       Stop background monitor
  ./internet_monitor.py reset      Reset stats after stopping monitor
  ./internet_monitor.py daemon     Internal background mode
""")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        usage()
        sys.exit(0)

    command = sys.argv[1].lower()

    if command == "start":
        start()
    elif command == "daemon":
        daemon_loop()
    elif command == "monitor":
        monitor()
    elif command == "status":
        status()
    elif command == "stop":
        stop()
    elif command == "reset":
        reset()
    else:
        usage()
