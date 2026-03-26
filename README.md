# 🚦 Real Time Traffic Management


> **Intelligent Traffic Management System** combining YOLOv8 vehicle detection with SUMO traffic simulation for adaptive signal control, real-time analytics, and a live web dashboard.

---

## 📌 Overview

Real Time Traffic Management
 is a Python-based intelligent traffic management system that:

- Uses **SUMO simulation** as a virtual camera (no real camera needed)
- Detects and classifies vehicles — `car`, `bus`, `truck`
- **Adaptively controls traffic signals** based on live vehicle density per lane
- Enforces a **10-second minimum green time** safety lock to prevent rapid signal changes
- Measures **speed, occupancy, flow rate, and Level of Service (LOS)**
- Displays a **real-time web dashboard** at `http://localhost:5000`
- Exports **CSV reports** for traffic planning studies
- Supports **emergency vehicle preemption**

---

## 🗂️ Project Structure

```
Real Time Traffic Management
/
│
├── main.py                          # Entry point (real camera / video file)
├── main_sumo.py                     # Entry point (SUMO simulation as input)
├── sumo_source.py                   # SUMO → Real Time Traffic Management
 data bridge
├── config.py                        # All configuration (paths, timing, zones)
├── requirements.txt
│
├── core/
│   ├── detector.py                  # YOLOv8 + ByteTrack vehicle detection
│   ├── speed_estimator.py           # Calibration-line speed estimation
│   └── zone_manager.py              # ROI zone management per lane
│
├── signal_control/
│   ├── signal_controller.py         # Adaptive signal timing + safety lock
│   └── emergency_handler.py         # Emergency vehicle preemption
│
├── analytics/
│   ├── kpi_calculator.py            # LOS, delay, flow rate, occupancy
│   ├── csv_exporter.py              # Export summaries + violations to CSV
│   └── heatmap.py                   # Vehicle density heatmap overlay
│
├── dashboard/
│   ├── app.py                       # Flask + SocketIO real-time dashboard
│   └── templates/
│       └── index.html               # Live dashboard UI
│
├── utils/
│   ├── logger.py                    # Timestamped console logger
│   └── visualizer.py                # OpenCV drawing utilities
│
├── sumo_traffic/
│   ├── config.sumocfg               # SUMO simulation config
│   ├── map.net.xml                  # Road network (4-arm intersection)
│   ├── nodes.nod.xml                # Junction nodes
│   ├── edges.edg.xml                # Road edges
│   ├── vehicles.rou.xml             # Vehicle flows (car/bus/truck)
│   ├── detector.add.xml             # SUMO lane detectors
│   ├── gui-settings.xml             # SUMO GUI appearance
│   └── summary.xml                  # SUMO output summary
│
└── data/
    └── logs/                        # Auto-generated CSV reports
```

---

## 🧠 How It Works

```
SUMO Simulation
      ↓
  sumo_source.py  ←── Extracts vehicle counts, speeds, types per lane
      ↓
  signal_controller.py  ←── Adaptive green time based on density
      ↓                       (minimum 10s safety lock enforced)
  kpi_calculator.py     ←── LOS, delay, flow rate computed
      ↓
  csv_exporter.py       ←── Saves reports every 60 seconds
      ↓
  dashboard/app.py      ←── Pushes live data via SocketIO
      ↓
  Browser @ localhost:5000
      ↓
  Optimized signal timings pushed back to SUMO  ← Closed loop
```

---

## 🗺️ SUMO Network

Your simulation uses a **4-arm signalized intersection** (Junction B):

| Lane Name | SUMO Edge | Direction |
|-----------|-----------|-----------|
| West      | `AB`      | A → B     |
| East      | `CB`      | C → B     |
| North     | `DB`      | D → B     |
| South     | `EB`      | E → B     |

**Signal phases at Junction B:**
- Phase 0 (42s): West + East green
- Phase 2 (42s): North + South green

**Vehicle flows defined:**
- Cars: 500–1200 veh/hr per approach
- Rush hour spike at t=120s → 2000 veh/hr
- Buses: 40–60 veh/hr
- Trucks: 50–80 veh/hr

---

## ⚙️ Configuration (`config.py`)

Key settings you can change:

```python
# Signal timing
MIN_GREEN_SECONDS  = 10    # minimum green (safety lock)
MAX_GREEN_SECONDS  = 60    # maximum green
DEFAULT_GREEN      = 20    # default green
YELLOW_SECONDS     = 3     # yellow phase
ALL_RED_SECONDS    = 2     # all-red clearance

# Analytics
ANALYTICS_INTERVAL_SEC = 60   # KPI snapshot every N seconds
SPEED_LIMIT_KMPH       = 50   # speed violation threshold

# Video source (for main.py only)
VIDEO_SOURCE = 0              # 0 = webcam, or "path/to/video.mp4"
```

---

## 🚀 Setup & Installation

### 1. Clone the repository
```bash
git clone https://github.com/simple100boy/Real Time Traffic Management
.git
cd Real Time Traffic Management

```

### 2. Create virtual environment
```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # Mac/Linux
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Install SUMO
Download from [sumo.dlr.de](https://sumo.dlr.de/docs/Downloads.php) and install.

Set environment variable:
```
SUMO_HOME = C:\Program Files (x86)\Eclipse\Sumo
```

### 5. Update SUMO path in `sumo_source.py`
```python
SUMO_HOME   = r"C:\Program Files (x86)\Eclipse\Sumo"
SUMO_CONFIG = r"path\to\sumo_traffic\config.sumocfg"
```

---

## ▶️ Running the System

### Option A — With SUMO simulation (recommended)
```bash
python main_sumo.py
```

### Option B — Without SUMO GUI (faster, headless)
```bash
python main_sumo.py --no-gui
```

### Option C — With real camera or video file
```bash
python main.py
```

### Option D — Disable web dashboard
```bash
python main_sumo.py --no-dashboard
```

---

## 📊 Outputs

| Output | Location | Description |
|--------|----------|-------------|
| SUMO GUI | Desktop window | Live simulation with vehicles |
| Web dashboard | `http://localhost:5000` | Real-time charts, signals, KPIs |
| Traffic summary CSV | `data/logs/traffic_summary_*.csv` | Flow, LOS, delay per lane |
| Speed violations CSV | `data/logs/speed_violations_*.csv` | Vehicles exceeding speed limit |
| Terminal logs | Console | Per-step stats every 10 seconds |

---

## 📈 KPIs Computed

| Metric | Description |
|--------|-------------|
| Flow rate (vph) | Vehicles per hour per lane |
| Occupancy | Vehicles currently in zone |
| Average speed (km/h) | Mean speed of vehicles in lane |
| Estimated delay (s) | Average delay per vehicle |
| LOS (A–F) | Level of Service per HCM standard |
| Green time (s) | Allocated green time per lane |
| Cumulative count | Total vehicles counted since start |

---

## 🛡️ Safety Features

- **Minimum 10-second green lock** — no signal switches faster than 10 seconds
- **All-red clearance** — 2-second all-red interval between every phase change
- **Yellow phase** — 3-second yellow before every red
- **Emergency preemption** — detects large fast-moving vehicles and overrides cycle
- **Speed violation logging** — flags and logs vehicles exceeding 50 km/h

---

## 🛠️ Tech Stack

| Tool | Purpose |
|------|---------|
| Python 3.10+ | Core language |
| SUMO 1.26.0 | Traffic simulation (virtual camera) |
| TraCI | Python ↔ SUMO real-time control API |
| YOLOv8 (Ultralytics) | Vehicle detection (for real camera mode) |
| OpenCV | Video processing and visualization |
| Flask + SocketIO | Live web dashboard |
| Pandas | CSV analytics export |
| NumPy | Numerical computation |

---

## 📁 CSV Report Format

**traffic_summary_*.csv**
```
timestamp, lane, flow_rate_vph, occupancy, avg_speed_kmph, delay_est_s, los, green_time_s, cumulative_count
```

**speed_violations_*.csv**
```
timestamp, track_id, lane, class, speed_kmph, limit_kmph, over_by
```

---

## 📌 Credits


---

## 👤 Author

**Prasad** — Artificial Intelligence and Data Science (AI&DS), JSPM Narhe Technical Campus, Pune  
GitHub: [@simple100boy](https://github.com/simple100boy)
**Harshavardhan** -Artificial Intelligence and Data Science (AI&DS), JSPM Narhe Technical Campus, Pune
**Manav** -Artificial Intelligence and Data Science (AI&DS), JSPM Narhe Technical Campus, Pune
**Pragati** -Artificial Intelligence and Data Science (AI&DS), JSPM Narhe Technical Campus, Pune
**Sakshi** -Artificial Intelligence and Data Science (AI&DS), JSPM Narhe Technical Campus, Pune
**Piyush** -Artificial Intelligence and Data Science (AI&DS), JSPM Narhe Technical Campus, Pune