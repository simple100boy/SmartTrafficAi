"""
sumo_source.py
--------------
Connects YOUR SUMO simulation to SmartTrafficAI.
Uses your exact junction B, edges AB/CB/DB/EB.
"""

import os
import sys
import time
import traci
from typing import Dict, List
from dataclasses import dataclass

# ── Set SUMO_HOME ─────────────────────────────────────────────
SUMO_HOME = r"C:\Program Files (x86)\Eclipse\Sumo"
if os.path.exists(SUMO_HOME):
    os.environ["SUMO_HOME"] = SUMO_HOME
    sys.path.append(os.path.join(SUMO_HOME, "tools"))

# ── Your exact SUMO config path ───────────────────────────────
SUMO_CONFIG  = r"C:\sumo_traffic\config.sumocfg"

# ── Your junction ID (main intersection) ─────────────────────
JUNCTION_ID  = "B"

# ── Map YOUR edge IDs → lane names used in SmartTrafficAI ────
EDGE_TO_LANE = {
    "AB": "West",    # vehicles coming from A (west) toward B
    "CB": "East",    # vehicles coming from C (east) toward B
    "DB": "North",   # vehicles coming from D (north) toward B
    "EB": "South",   # vehicles coming from E (south) toward B
}

LANE_NAMES   = ["West", "East", "North", "South"]
SPEED_LIMIT  = 50   # km/h (matches your maxSpeed in rou.xml)


@dataclass
class SUMOVehicle:
    track_id:    int
    class_name:  str      # car, bus, truck
    lane:        str      # West, East, North, South
    speed_kmh:   float
    waiting_time: float


class SUMOSource:
    def __init__(self, use_gui: bool = True):
        self.use_gui      = use_gui
        self._running     = False
        self._step        = 0
        self._id_map: Dict[str, int] = {}
        self._next_id     = 1
        self._cumulative: Dict[str, int] = {l: 0 for l in LANE_NAMES}
        self._seen_ids:   set = set()

    # ── Start SUMO ───────────────────────────────────────────
    def start(self):
        # Find SUMO binary with full path
        sumo_home = os.environ.get(
            "SUMO_HOME",
            "C:/Program Files (x86)/Eclipse/Sumo"
        )
        
        if self.use_gui:
            binary = os.path.join(sumo_home, "bin", "sumo-gui.exe")
        else:
            binary = os.path.join(sumo_home, "bin", "sumo.exe")

        # Check if binary exists
        if not os.path.exists(binary):
            print(f"[SUMO] ❌ SUMO not found at: {binary}")
            print("[SUMO] Please check your SUMO installation path")
            raise FileNotFoundError(f"SUMO binary not found: {binary}")

        traci.start([
            binary,
            "-c", SUMO_CONFIG,
            "--no-warnings", "true",
        ])
        self._running = True
        print("[SUMO] ✅ Simulation started")
        print(f"[SUMO] Junction: {JUNCTION_ID}")
        print(f"[SUMO] Watching edges: {list(EDGE_TO_LANE.keys())}")

    def stop(self):
        if self._running:
            traci.close()
            self._running = False
            print("[SUMO] Stopped")

    @property
    def is_running(self):
        try:
            return self._running and traci.simulation.getMinExpectedNumber() > 0
        except:
            return False

    # ── Main data extraction — call every loop iteration ─────
    def get_frame_data(self) -> Dict:
        """
        Advance SUMO one step and return traffic data.
        This replaces reading a video frame + YOLOv8 detection.
        """
        if not self._running:
            return {}

        traci.simulationStep()
        self._step += 1

        vehicles     = self._extract_vehicles()
        occupancy    = self._compute_occupancy(vehicles)
        speed_map    = {v.track_id: v.speed_kmh for v in vehicles}
        signal_state = self._get_signal_states()
        stats        = self._compute_stats(vehicles)

        return {
            "vehicles":     vehicles,
            "occupancy":    occupancy,
            "speed_map":    speed_map,
            "signal_state": signal_state,
            "cumulative":   dict(self._cumulative),
            "stats":        stats,
            "step":         self._step,
        }

    # ── Extract vehicles on approach edges only ───────────────
    def _extract_vehicles(self) -> List[SUMOVehicle]:
        vehicles = []

        for sumo_id in traci.vehicle.getIDList():
            edge = traci.vehicle.getRoadID(sumo_id)

            # Only care about vehicles on approach edges
            lane = EDGE_TO_LANE.get(edge)
            if lane is None:
                continue

            # Stable integer ID
            if sumo_id not in self._id_map:
                self._id_map[sumo_id] = self._next_id
                self._next_id += 1

            track_id = self._id_map[sumo_id]

            # Count new arrivals for cumulative count
            unique_key = f"{sumo_id}_{lane}"
            if unique_key not in self._seen_ids:
                self._seen_ids.add(unique_key)
                self._cumulative[lane] += 1

            speed_ms  = traci.vehicle.getSpeed(sumo_id)
            speed_kmh = round(speed_ms * 3.6, 1)
            wait_time = traci.vehicle.getWaitingTime(sumo_id)
            veh_type  = traci.vehicle.getTypeID(sumo_id)

            vehicles.append(SUMOVehicle(
                track_id     = track_id,
                class_name   = veh_type,
                lane         = lane,
                speed_kmh    = speed_kmh,
                waiting_time = wait_time,
            ))

        return vehicles

    # ── Count vehicles per lane ───────────────────────────────
    def _compute_occupancy(self, vehicles: List[SUMOVehicle]) -> Dict[str, int]:
        occ = {l: 0 for l in LANE_NAMES}
        for v in vehicles:
            occ[v.lane] += 1
        return occ

    # ── Read signal states from your junction B ───────────────
    def _get_signal_states(self) -> Dict[str, str]:
        try:
            # Junction B has 22-char state string
            # Phase 0: "rrrrrGGGGggrrrrrGGGGgg" → AB/BC green
            # Phase 2: "GGGggrrrrrrGGGggrrrrrr" → DB/EB green
            state_str = traci.trafficlight.getRedYellowGreenState(JUNCTION_ID)

            # Check key positions for each approach
            # AB (West) = linkIndex 17,18,19 → chars 17,18,19
            # CB (East) = linkIndex 6,7,8   → chars 6,7,8
            # DB (North)= linkIndex 1,2     → chars 1,2
            # EB (South)= linkIndex 12,13   → chars 12,13

            def get_state(indices):
                chars = [state_str[i].upper() if i < len(state_str) else 'R'
                         for i in indices]
                if any(c == 'G' for c in chars):
                    return "GREEN"
                elif any(c == 'Y' for c in chars):
                    return "YELLOW"
                else:
                    return "RED"

            return {
                "West":  get_state([17, 18, 19]),
                "East":  get_state([6, 7, 8]),
                "North": get_state([1, 2]),
                "South": get_state([12, 13]),
            }
        except Exception as e:
            return {l: "RED" for l in LANE_NAMES}

    # ── Push optimized green times back to SUMO ──────────────
    def set_signal_timing(self, green_lane: str, duration: float):
        """
        Called by signal controller to update SUMO signals.
        Closes the loop: ML output → SUMO input.
        Phase 0 = West+East green
        Phase 2 = North+South green
        """
        lane_to_phase = {
            "West":  0,
            "East":  0,
            "North": 2,
            "South": 2,
        }
        phase = lane_to_phase.get(green_lane, 0)
        try:
            current = traci.trafficlight.getPhase(JUNCTION_ID)
            # Only change if not in yellow/clearance
            if current in [0, 2]:
                traci.trafficlight.setPhase(JUNCTION_ID, phase)
                traci.trafficlight.setPhaseDuration(
                    JUNCTION_ID,
                    max(10, min(60, duration))
                )
        except Exception as e:
            pass

    # ── Simulation statistics ─────────────────────────────────
    def _compute_stats(self, vehicles: List[SUMOVehicle]) -> Dict:
        if not vehicles:
            return {
                "total_vehicles": 0,
                "avg_speed_kmh":  0.0,
                "avg_wait_s":     0.0,
                "step":           self._step,
            }
        avg_speed = sum(v.speed_kmh    for v in vehicles) / len(vehicles)
        avg_wait  = sum(v.waiting_time for v in vehicles) / len(vehicles)
        return {
            "total_vehicles": len(vehicles),
            "avg_speed_kmh":  round(avg_speed, 1),
            "avg_wait_s":     round(avg_wait,  1),
            "step":           self._step,
        }