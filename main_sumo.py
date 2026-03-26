"""
main_sumo.py
-------------
Run SmartTrafficAI using your SUMO simulation as input.
No camera or video needed.

Usage:
    python main_sumo.py              # with SUMO GUI
    python main_sumo.py --no-gui     # headless faster
    python main_sumo.py --no-dashboard
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import argparse
import time
import threading

import config
from sumo_source                      import SUMOSource, LANE_NAMES, SPEED_LIMIT
from signal_control.signal_controller import SignalController
from analytics.kpi_calculator         import KPICalculator
from analytics.csv_exporter           import CSVExporter
from utils.logger                     import log


def parse_args():
    p = argparse.ArgumentParser(description="SmartTrafficAI + SUMO")
    p.add_argument("--no-gui",       action="store_true",
                   help="Run SUMO without GUI (faster)")
    p.add_argument("--no-dashboard", action="store_true",
                   help="Disable web dashboard")
    return p.parse_args()


def run(args):
    log("Main", "Starting SmartTrafficAI + SUMO integration", "OK")

    # ── Init all modules ─────────────────────────────────────
    sumo        = SUMOSource(use_gui=not args.no_gui)
    signal_ctrl = SignalController(LANE_NAMES)
    kpi_calc    = KPICalculator(LANE_NAMES)
    csv_exp     = CSVExporter()

    # ── Dashboard ────────────────────────────────────────────
    push_update = lambda d: None
    if not args.no_dashboard:
        try:
            from dashboard.app import run_dashboard, push_update as _push
            push_update = _push
            t = threading.Thread(target=run_dashboard, daemon=True)
            t.start()
            log("Main", f"Dashboard → http://localhost:{config.DASHBOARD_PORT}", "OK")
        except Exception as e:
            log("Main", f"Dashboard failed to start: {e}", "WARN")

    # ── Start SUMO + signals ──────────────────────────────────
    sumo.start()
    signal_ctrl.start()

    log("Main", "SUMO running. Press Ctrl+C to stop.", "OK")
    log("Main", f"CSV reports → {csv_exp.summary_path}", "INFO")

    last_kpi_time    = time.time()
    last_print_time  = time.time()
    latest_kpis      = {}
    violations_count = 0
    step             = 0

    try:
        while sumo.is_running:
            step += 1

            # ── Get data from SUMO ────────────────────────────
            data = sumo.get_frame_data()
            if not data:
                break

            occupancy    = data["occupancy"]
            speed_map    = data["speed_map"]
            signal_state = data["signal_state"]
            vehicles     = data["vehicles"]
            cumulative   = data["cumulative"]
            stats        = data["stats"]

            # ── Update signal controller ──────────────────────
            signal_ctrl.update_density(occupancy)
            green_times = signal_ctrl.get_green_times()

            # Find busiest lane → give it green in SUMO
            if occupancy:
                busiest = max(occupancy, key=occupancy.get)
                if occupancy[busiest] > 0:
                    sumo.set_signal_timing(
                        green_lane = busiest,
                        duration   = green_times.get(busiest, 20)
                    )

            # ── Speed violation detection ─────────────────────
            for v in vehicles:
                if v.speed_kmh > SPEED_LIMIT:
                    violations_count += 1
                    csv_exp.export_violation(
                        v.track_id,
                        v.lane,
                        v.speed_kmh,
                        v.class_name,
                    )

            # ── KPI snapshot every interval ───────────────────
            now = time.time()
            if now - last_kpi_time >= config.ANALYTICS_INTERVAL_SEC:
                last_kpi_time = now
                latest_kpis = kpi_calc.compute_snapshot(
                    zone_occupancy     = occupancy,
                    cumulative_counts  = cumulative,
                    signal_green_times = green_times,
                )
                csv_exp.export_snapshot(latest_kpis)

            # ── Print stats to terminal every 10 seconds ──────
            if now - last_print_time >= 10:
                last_print_time = now
                log("SUMO",
                    f"Step {step:4d} | "
                    f"Vehicles: {stats['total_vehicles']:3d} | "
                    f"Avg Speed: {stats['avg_speed_kmh']:5.1f} km/h | "
                    f"Avg Wait: {stats['avg_wait_s']:5.1f}s | "
                    f"Violations: {violations_count}",
                    "INFO")

                # Print per-lane occupancy
                occ_str = " | ".join(
                    f"{lane}: {occupancy.get(lane, 0)} veh"
                    for lane in LANE_NAMES
                )
                log("Lanes", occ_str, "INFO")

                # Print signal states
                sig_str = " | ".join(
                    f"{lane}: {signal_state.get(lane, 'RED')}"
                    for lane in LANE_NAMES
                )
                log("Signal", sig_str, "INFO")

            # ── Push to web dashboard ─────────────────────────
            if step % 10 == 0:
                push_update({
                    "signal_states":    signal_state,
                    "green_times":      green_times,
                    "zone_occupancy":   occupancy,
                    "speed_map":        {str(k): v for k, v in speed_map.items()},
                    "latest_kpis":      latest_kpis,
                    "cumulative":       cumulative,
                    "frame_count":      step,
                    "fps":              round(1.0 / 0.1, 1),
                    "violations_today": violations_count,
                })

    except KeyboardInterrupt:
        log("Main", "Stopped by user (Ctrl+C)", "WARN")

    finally:
        signal_ctrl.stop()
        sumo.stop()
        log("Main", "─" * 50, "INFO")
        log("Main", f"Total steps run:      {step}", "OK")
        log("Main", f"Speed violations:     {violations_count}", "OK")
        log("Main", f"Reports saved to:     {csv_exp.summary_path}", "OK")
        log("Main", f"Violations saved to:  {csv_exp.violations_path}", "OK")


if __name__ == "__main__":
    args = parse_args()
    run(args)