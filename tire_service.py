# tire_service.py — Tire telemetry service, prediction engine, and terminal visualisation
# Provides dummy sensor data, predicts degradation for the next bank/turn,
# and renders a colored progress bar in the terminal.

import math
import random
import sys
import io

# ---------------------------------------------------------------------------
# Constants — F1 tyre physics parameters
# ---------------------------------------------------------------------------
TIRE_CIRCUMFERENCE_M = 2.0          # Approximate F1 tyre circumference in metres
DEFAULT_CIRCUIT_LENGTH_M = 5300     # Average F1 circuit length in metres
DEFAULT_TURNS_PER_LAP = 15          # Average number of turns per lap

# Base total revolutions each compound can survive (on a straight-only track)
BASE_LIFECYCLE_REVOLUTIONS = {
    "soft":   50_000,
    "medium": 75_000,
    "hard":  100_000,
}

# Turn penalty: each turn per lap reduces total lifecycle by this fraction
TURN_PENALTY_PER_TURN = 0.002       # 0.2 % per turn

# Baseline tyre pressures (PSI) — compound-specific
BASELINE_PRESSURE_PSI = {
    "soft":   21.0,
    "medium": 22.0,
    "hard":   23.0,
}

# Temperature range parameters (°C)
TEMP_BASE = 80.0        # Surface temp on fresh tyres
TEMP_CEILING = 115.0    # Surface temp on severely degraded tyres

# Cliff points (same as tools.py for consistency)
CLIFF_POINTS = {
    "soft":   15,
    "medium": 25,
    "hard":   35,
}

# Known circuits — turns per lap lookup
CIRCUIT_TURNS = {
    "silverstone":   18,
    "monaco":        19,
    "spa":           20,
    "monza":         11,
    "singapore":     23,
    "suzuka":        18,
    "bahrain":       15,
    "jeddah":        27,
    "melbourne":     14,
    "imola":         19,
    "barcelona":     16,
    "montreal":      14,
    "spielberg":      10,
    "hungaroring":   14,
    "zandvoort":     14,
    "baku":          20,
    "cota":          20,
    "interlagos":    15,
    "las_vegas":     17,
    "abu_dhabi":     16,
    "shanghai":      16,
    "miami":         19,
}

# Circuit lengths (metres) for known tracks
CIRCUIT_LENGTHS = {
    "silverstone":  5891,
    "monaco":       3337,
    "spa":          7004,
    "monza":        5793,
    "singapore":    4940,
    "suzuka":       5807,
    "bahrain":      5412,
    "jeddah":       6174,
    "melbourne":    5278,
    "imola":        4909,
    "barcelona":    4657,
    "montreal":     4361,
    "spielberg":    4318,
    "hungaroring":  4381,
    "zandvoort":    4259,
    "baku":         6003,
    "cota":         5513,
    "interlagos":   4309,
    "las_vegas":    6201,
    "abu_dhabi":    5281,
    "shanghai":     5451,
    "miami":        5412,
}


# ═══════════════════════════════════════════════════════════════════════════
# 1. DUMMY TIRE TELEMETRY SERVICE
# ═══════════════════════════════════════════════════════════════════════════

def get_tire_telemetry_data(compound: str, lap_age: int, circuit: str = "") -> dict:
    """
    Simulates a tyre telemetry data pull from onboard sensors.

    Args:
        compound: 'soft', 'medium', or 'hard'
        lap_age:  how many laps the current set has been on the car
        circuit:  optional circuit name (e.g. 'silverstone') for turn count lookup

    Returns:
        dict with pressure_psi, temperature_c, life_pct_used,
        current_revolutions, total_lifecycle_revolutions, turns_per_lap
    """
    compound = compound.lower().strip()

    # ── Look up circuit-specific data or fall back to defaults ──
    circuit_key = circuit.lower().strip().replace(" ", "_") if circuit else ""
    turns_per_lap = CIRCUIT_TURNS.get(circuit_key, DEFAULT_TURNS_PER_LAP)
    circuit_length = CIRCUIT_LENGTHS.get(circuit_key, DEFAULT_CIRCUIT_LENGTH_M)

    # ── Calculate total lifecycle revolutions (factoring in turns) ──
    base_revs = BASE_LIFECYCLE_REVOLUTIONS.get(compound, 75_000)
    turn_factor = 1 + TURN_PENALTY_PER_TURN * turns_per_lap
    total_lifecycle_revolutions = int(base_revs / turn_factor)

    # ── Current revolutions from laps driven ──
    revs_per_lap = circuit_length / TIRE_CIRCUMFERENCE_M
    current_revolutions = int(lap_age * revs_per_lap)

    # ── Life percentage used ──
    life_pct_used = min((current_revolutions / total_lifecycle_revolutions) * 100, 130.0)

    # ── Pressure: drifts slightly from baseline as tyre wears ──
    baseline_psi = BASELINE_PRESSURE_PSI.get(compound, 22.0)
    # Pressure drops slightly as rubber degrades (up to -1.5 PSI at 100% life)
    pressure_drop = (life_pct_used / 100.0) * 1.5
    noise = random.uniform(-0.3, 0.3)   # Sensor noise
    pressure_psi = round(baseline_psi - pressure_drop + noise, 1)

    # ── Temperature: rises with degradation ──
    # Maps life_pct linearly from TEMP_BASE to TEMP_CEILING
    temp_ratio = min(life_pct_used / 100.0, 1.3)
    temperature_c = round(TEMP_BASE + (TEMP_CEILING - TEMP_BASE) * temp_ratio
                          + random.uniform(-2.0, 2.0), 1)

    return {
        "compound":                    compound.capitalize(),
        "lap_age":                     lap_age,
        "circuit":                     circuit_key or "generic",
        "pressure_psi":                pressure_psi,
        "temperature_c":               temperature_c,
        "life_pct_used":               round(life_pct_used, 1),
        "current_revolutions":         current_revolutions,
        "total_lifecycle_revolutions": total_lifecycle_revolutions,
        "turns_per_lap":               turns_per_lap,
    }


# ═══════════════════════════════════════════════════════════════════════════
# 2. TIRE LIFE PREDICTION ENGINE
# ═══════════════════════════════════════════════════════════════════════════

def predict_tire_degradation(telemetry: dict) -> dict:
    """
    Predicts additional tyre degradation if the car takes the next banking/turn,
    and estimates remaining tyre life in laps.

    Uses an exponential degradation curve: wear rate accelerates as life_pct
    approaches and exceeds the compound's cliff point.

    Args:
        telemetry: dict returned by get_tire_telemetry_data()

    Returns:
        dict with predicted_next_bank_pct, laps_remaining_in_tire, risk_level
    """
    compound = telemetry["compound"].lower()
    life_pct = telemetry["life_pct_used"]
    turns = telemetry["turns_per_lap"]
    total_revs = telemetry["total_lifecycle_revolutions"]

    cliff = CLIFF_POINTS.get(compound, 25)

    # ── Base wear per single turn (as % of total lifecycle) ──
    # One turn ≈ ~50 m of cornering load at ~2650 rev/turn-equivalent
    single_turn_revs = 25  # approximate extra-equivalent revolutions per hard turn
    base_wear_per_turn = (single_turn_revs / total_revs) * 100  # as %

    # ── Exponential acceleration factor ──
    # When life_pct is near/past the cliff, wear per turn multiplies
    # cliff_ratio: how far through the cliff zone we are (0 = fresh, 1 = at cliff, >1 = past)
    cliff_lap = cliff  # cliff in laps
    # Map life_pct to an equivalent "lap position" relative to cliff
    # life_pct at cliff ≈ (cliff_laps * revs_per_lap) / total_revs * 100
    # Simplify: use life_pct / 100 as wear fraction
    wear_fraction = life_pct / 100.0

    # Exponential factor: accelerates sharply past 70% life used
    exp_factor = math.exp(2.0 * max(0, wear_fraction - 0.5))

    # Predicted cost of the next bank/turn
    predicted_next_bank_pct = round(base_wear_per_turn * exp_factor, 2)

    # ── Estimate laps remaining ──
    # Average wear per lap = life_pct / lap_age (if lap_age > 0)
    lap_age = telemetry["lap_age"]
    if lap_age > 0:
        avg_wear_per_lap = life_pct / lap_age
        # Project forward with exponential increase: next laps will wear faster
        # Use current exponential rate for a more pessimistic (realistic) estimate
        projected_wear_per_lap = avg_wear_per_lap * (1 + 0.3 * max(0, wear_fraction - 0.5))
        if projected_wear_per_lap > 0:
            laps_remaining = max(0, (100.0 - life_pct) / projected_wear_per_lap)
        else:
            laps_remaining = 99  # fresh tyre, essentially unlimited
    else:
        laps_remaining = 99  # no data yet

    laps_remaining = round(laps_remaining, 1)

    # ── Risk level ──
    if life_pct >= 90:
        risk_level = "CRITICAL"
    elif life_pct >= 75:
        risk_level = "HIGH"
    elif life_pct >= 50:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    return {
        "predicted_next_bank_pct": predicted_next_bank_pct,
        "laps_remaining_in_tire":  laps_remaining,
        "risk_level":              risk_level,
        "life_pct_after_bank":     round(life_pct + predicted_next_bank_pct, 1),
    }


# ═══════════════════════════════════════════════════════════════════════════
# 3. TERMINAL PROGRESS BAR RENDERER
# ═══════════════════════════════════════════════════════════════════════════

# ANSI color codes for terminal output
_GREEN  = "\033[92m"    # Bright green  — consumed life
_BLUE   = "\033[94m"    # Bright blue   — remaining usable life
_ORANGE = "\033[38;5;208m"  # Orange    — predicted next-bank degradation
_RED    = "\033[91m"    # Bright red    — past 100%
_GRAY   = "\033[90m"    # Gray          — unused / background
_BOLD   = "\033[1m"
_RESET  = "\033[0m"
_DIM    = "\033[2m"


def render_tire_life_bar(telemetry: dict, prediction: dict) -> str:
    """
    Renders a colored ASCII progress bar showing tyre life status.

    Segments:
        Green  (█) — already consumed life (0% → life_pct_used)
        Blue   (░) — remaining usable life
        Orange (▓) — predicted additional degradation from next bank

    Also prints a scale with percentage markers and a prediction summary.

    Args:
        telemetry:  dict from get_tire_telemetry_data()
        prediction: dict from predict_tire_degradation()

    Returns:
        The full formatted string (also printed to terminal)
    """
    life_pct = telemetry["life_pct_used"]
    next_bank_pct = prediction["predicted_next_bank_pct"]
    life_after_bank = prediction["life_pct_after_bank"]
    laps_remaining = prediction["laps_remaining_in_tire"]
    risk_level = prediction["risk_level"]
    compound = telemetry["compound"]
    lap_age = telemetry["lap_age"]

    # ── Bar dimensions ──
    total_bar_width = 60       # characters wide
    max_pct = 125.0            # bar goes from 0% to 125% (to show overshoot)

    # Calculate segment widths in characters
    consumed_chars = int((life_pct / max_pct) * total_bar_width)
    bank_chars = max(1, int((next_bank_pct / max_pct) * total_bar_width))
    remaining_chars = total_bar_width - consumed_chars - bank_chars
    if remaining_chars < 0:
        remaining_chars = 0
        bank_chars = total_bar_width - consumed_chars
        if bank_chars < 0:
            bank_chars = 0
            consumed_chars = total_bar_width

    # ── Build the bar ──
    bar = (
        f"{_GREEN}{'█' * consumed_chars}{_RESET}"
        f"{_BLUE}{'░' * remaining_chars}{_RESET}"
        f"{_ORANGE}{'▓' * bank_chars}{_RESET}"
    )

    # ── Percentage scale line ──
    # Positions for 0%, 25%, 50%, 75%, 100%, 125%
    markers = [0, 25, 50, 75, 100, 125]
    scale_line = ""
    dash_line = ""
    for i, m in enumerate(markers):
        pos = int((m / max_pct) * total_bar_width)
        label = f"{m}%"
        if i == 0:
            scale_line += label
            dash_line += "|"
        else:
            # Pad to reach the correct position
            gap = pos - len(scale_line.replace(_GRAY, "").replace(_RESET, ""))
            scale_line += " " * max(1, gap - len(label)) + f"{label}"
            gap_d = pos - len(dash_line)
            dash_line += "-" * max(0, gap_d) + "|"

    # Pad dash_line to total_bar_width
    if len(dash_line) < total_bar_width + 1:
        dash_line += "-" * (total_bar_width + 1 - len(dash_line))

    # ── Risk color ──
    risk_colors = {
        "LOW":      "\033[92m",   # green
        "MEDIUM":   "\033[93m",   # yellow
        "HIGH":     "\033[38;5;208m",  # orange
        "CRITICAL": "\033[91m",   # red
    }
    rc = risk_colors.get(risk_level, _RESET)

    # ── Build full output ──
    sep = f"{_DIM}{'━' * 62}{_RESET}"
    output_lines = [
        "",
        sep,
        f"  {_BOLD}🏎️  TIRE STATUS{_RESET} — {compound} | Lap Age: {lap_age}",
        sep,
        f"  Pressure:      {_BOLD}{telemetry['pressure_psi']}{_RESET} PSI",
        f"  Temperature:   {_BOLD}{telemetry['temperature_c']}{_RESET}°C",
        f"  Life Used:     {_BOLD}{life_pct}{_RESET}%",
        f"  Revolutions:   {telemetry['current_revolutions']:,} / {telemetry['total_lifecycle_revolutions']:,}",
        "",
        f"  {_DIM}{scale_line}{_RESET}",
        f"  {_DIM}{dash_line}{_RESET}",
        f"  |{bar}|",
        f"  {_GREEN}█ consumed{_RESET}   {_BLUE}░ remaining{_RESET}   {_ORANGE}▓ next bank impact{_RESET}",
        "",
        f"  {_BOLD}🔮 PREDICTION — Next Bank Impact:{_RESET}",
        f"     Additional degradation: {_ORANGE}+{next_bank_pct}%{_RESET}",
        f"     Life after next bank:   {life_after_bank}%",
        f"     Est. tire laps left:    {_BOLD}{laps_remaining}{_RESET} laps",
        f"     Risk level:             {rc}{_BOLD}{risk_level}{_RESET}",
        sep,
        "",
    ]

    output = "\n".join(output_lines)
    # Print directly to terminal (side effect) so it is always visible
    # Use UTF-8 encoding to handle special characters on Windows terminals
    try:
        sys.stdout.buffer.write(output.encode("utf-8"))
        sys.stdout.buffer.write(b"\n")
        sys.stdout.buffer.flush()
    except (AttributeError, OSError):
        # Fallback: strip non-ASCII and print plain
        print(output.encode("ascii", errors="replace").decode("ascii"))
    return output
