"""
signal_control/signal_controller.py
-------------------------------------
Adaptive traffic signal controller with minimum green time safety lock.
No signal will change faster than MIN_GREEN_SECONDS (10s minimum).
"""

import time
import threading
from typing import Dict, Optional
import config


class SignalState:
    GREEN   = "GREEN"
    YELLOW  = "YELLOW"
    RED     = "RED"
    ALL_RED = "ALL_RED"


class SignalController:
    def __init__(self, lane_names: list):
        self.lanes = lane_names
        self._states: Dict[str, str]  = {lane: SignalState.RED for lane in lane_names}
        self._green_times: Dict[str, float] = {lane: config.DEFAULT_GREEN for lane in lane_names}
        self._current_green: Optional[str]  = None
        self._phase_idx   = 0
        self._running     = False
        self._thread: Optional[threading.Thread] = None
        self._lock        = threading.Lock()
        self._emergency_lane: Optional[str] = None

        # ── Safety lock ──────────────────────────────────────
        # Tracks when current green phase started
        self._green_start_time: float = 0.0
        # Minimum seconds a green must stay before switching
        self._min_green_lock: float = 10.0   # seconds

    # ── Start ─────────────────────────────────────────────────
    def start(self):
        self._running = True
        self._thread  = threading.Thread(target=self._cycle_loop, daemon=True)
        self._thread.start()
        print("[Signal] Controller started.")
        print(f"[Signal] Minimum green time lock: {self._min_green_lock}s")

    def stop(self):
        self._running = False

    # ── Called every frame with current zone vehicle counts ───
    def update_density(self, density: Dict[str, int]):
        total = sum(density.values()) or 1
        for lane in self.lanes:
            count = density.get(lane, 0)
            ratio = count / total
            green = config.MIN_GREEN_SECONDS + ratio * (
                config.MAX_GREEN_SECONDS - config.MIN_GREEN_SECONDS
            )
            green = max(config.MIN_GREEN_SECONDS, min(config.MAX_GREEN_SECONDS, green))
            with self._lock:
                self._green_times[lane] = green

    def trigger_emergency(self, lane: str):
        print(f"[Signal] Emergency preemption → {lane}")
        with self._lock:
            self._emergency_lane = lane

    # ── Getters ───────────────────────────────────────────────
    def get_states(self) -> Dict[str, str]:
        with self._lock:
            return dict(self._states)

    def get_green_times(self) -> Dict[str, float]:
        with self._lock:
            return dict(self._green_times)

    def time_in_current_green(self) -> float:
        """How many seconds the current green has been active."""
        if self._green_start_time == 0:
            return 0.0
        return time.time() - self._green_start_time

    # ── Main cycle loop ───────────────────────────────────────
    def _cycle_loop(self):
        while self._running:
            with self._lock:
                emergency = self._emergency_lane
                if emergency:
                    self._emergency_lane = None

            if emergency and emergency in self.lanes:
                # Emergency overrides safety lock
                self._serve_lane(emergency, override_time=config.MAX_GREEN_SECONDS)
            else:
                lane = self.lanes[self._phase_idx % len(self.lanes)]
                with self._lock:
                    green_t = self._green_times.get(lane, config.DEFAULT_GREEN)

                # ── SAFETY LOCK ───────────────────────────────
                # Enforce minimum green time before switching
                green_t = max(green_t, self._min_green_lock)

                self._serve_lane(lane, override_time=green_t)
                self._phase_idx += 1

    def _serve_lane(self, lane: str, override_time: float):
        """Set one lane GREEN, all others RED, then transition."""

        # ── All-red clearance interval ────────────────────────
        with self._lock:
            for l in self.lanes:
                self._states[l] = SignalState.ALL_RED
        time.sleep(config.ALL_RED_SECONDS)

        # ── Green phase ───────────────────────────────────────
        with self._lock:
            for l in self.lanes:
                self._states[l] = SignalState.RED
            self._states[lane]  = SignalState.GREEN
            self._current_green = lane
            self._green_start_time = time.time()

        print(f"[Signal] 🟢 {lane} → GREEN for {override_time:.1f}s")
        time.sleep(override_time)

        # ── Yellow transition ─────────────────────────────────
        with self._lock:
            self._states[lane] = SignalState.YELLOW
        print(f"[Signal] 🟡 {lane} → YELLOW for {config.YELLOW_SECONDS}s")
        time.sleep(config.YELLOW_SECONDS)

        # ── Red ───────────────────────────────────────────────
        with self._lock:
            self._states[lane] = SignalState.RED
        print(f"[Signal] 🔴 {lane} → RED")