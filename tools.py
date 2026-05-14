# tools.py — All LangChain @tool decorated functions for the F1 Race Strategy Agent
# Each tool is a callable that the LangChain agent can invoke autonomously

from langchain_core.tools import tool          # Decorator to register a function as a LangChain tool
from langchain_community.tools import DuckDuckGoSearchRun  # Web search via DuckDuckGo (no API key needed)

# Tire telemetry service, prediction engine, and terminal bar renderer
from tire_service import (
    get_tire_telemetry_data,
    predict_tire_degradation,
    render_tire_life_bar,
)

# ---------------------------------------------------------------------------
# Tool 1: get_race_situation
# Returns hardcoded snapshot of the current race state.
# In a real system this would pull live telemetry; here it is faked for demo.
# ---------------------------------------------------------------------------
@tool
def get_race_situation() -> str:
    """Returns the current F1 race situation including lap number, position,
    tyre compound, tyre age, gaps to competitors, and weather conditions."""
    return (
        "Current Race Situation:\n"
        "  Lap: 28 / 53\n"
        "  Position: P3\n"
        "  Tyre compound: Medium\n"
        "  Tyre age: 22 laps\n"
        "  Gap ahead: +4.2 s (to Verstappen in P2)\n"
        "  Gap behind: -1.8 s (Sainz in P4 closing)\n"
        "  Weather: Dry, track temperature 38 degrees C"
    )


# ---------------------------------------------------------------------------
# Tool 2: get_tyre_degradation
# Evaluates how degraded a tyre is based on compound and laps run.
# Each compound has a different cliff point (age at which grip falls sharply).
# ---------------------------------------------------------------------------
@tool
def get_tyre_degradation(compound: str, lap_age: int) -> str:
    """Assesses tyre degradation level given the tyre compound and how many laps
    it has been on the car. Compound must be 'soft', 'medium', or 'hard'."""
    # Normalise compound to lowercase so 'Soft' and 'soft' both work
    compound = compound.lower().strip()

    # Define cliff points: the lap age at which each compound falls off a cliff
    cliff_points = {
        "soft":   15,   # Softs degrade very quickly
        "medium": 25,   # Mediums give moderate life
        "hard":   35,   # Hards are the most durable
    }

    # Return an error message if the compound is not recognised
    if compound not in cliff_points:
        return f"Unknown compound '{compound}'. Please specify 'soft', 'medium', or 'hard'."

    cliff = cliff_points[compound]  # Fetch the cliff lap for this compound

    # Determine degradation category based on how close we are to the cliff
    if lap_age >= cliff:
        level = "CRITICAL — tyre is past cliff, grip severely degraded"
        recommendation = "Box this lap or next lap. High risk of blowout or 2+ s lap time loss."
    elif lap_age >= cliff - 5:  # Within 5 laps of the cliff
        level = "HIGH — approaching degradation cliff"
        recommendation = "Pit window is open. Recommend boxing within 3 laps."
    elif lap_age >= cliff - 10:  # Within 10 laps of the cliff
        level = "MEDIUM — degradation building"
        recommendation = "Monitor closely. Pit stop viable but not yet urgent."
    else:
        level = "LOW — tyre performing well"
        recommendation = "No immediate pit stop required. Continue on current strategy."

    return (
        f"Compound: {compound.capitalize()}\n"
        f"Age: {lap_age} laps (cliff at {cliff} laps)\n"
        f"Degradation: {level}\n"
        f"Recommendation: {recommendation}"
    )


# ---------------------------------------------------------------------------
# Tool 3: calculate_pit_window
# Decides whether pitting now is strategically safe given the traffic situation.
# The key constraint: after a pit stop (~22 s stationary + out-lap), do we
# rejoin ahead of the car behind us?
# ---------------------------------------------------------------------------
@tool
def calculate_pit_window(current_lap: int, total_laps: int, gap_behind: float) -> str:
    """Calculates whether it is strategically safe to pit given the current lap,
    total race laps, and the gap (in seconds) to the car immediately behind.
    gap_behind should be a positive float representing seconds behind."""
    laps_remaining = total_laps - current_lap  # How many laps are left after this one

    # A pit stop typically costs ~22 s in stationary time + ~5 s out-lap delta
    # So we need at least 27 s gap behind to ensure we rejoin ahead
    pit_cost_seconds = 27.0

    # Make gap_behind positive for arithmetic (it may be passed as negative)
    gap_behind = abs(gap_behind)

    if laps_remaining < 5:
        # Too few laps left — a pit stop will almost certainly cost positions
        return (
            f"Laps remaining: {laps_remaining}\n"
            "Pit window: CLOSED — too few laps to recover pit stop time loss.\n"
            "Recommendation: Stay out and defend on current tyres."
        )

    if gap_behind >= pit_cost_seconds:
        # Gap is large enough to absorb the pit stop and rejoin ahead
        return (
            f"Gap behind: {gap_behind:.1f} s | Pit cost estimate: {pit_cost_seconds} s\n"
            f"Laps remaining: {laps_remaining}\n"
            "Pit window: OPEN — safe to pit. Should rejoin ahead of car behind.\n"
            "Recommendation: Box now for fresh tyres."
        )
    else:
        # Gap is too small — we would come out behind the car behind us (undercut risk)
        undercut_risk = pit_cost_seconds - gap_behind  # How many seconds short we are
        return (
            f"Gap behind: {gap_behind:.1f} s | Pit cost estimate: {pit_cost_seconds} s\n"
            f"Laps remaining: {laps_remaining}\n"
            f"Pit window: TIGHT — {undercut_risk:.1f} s short of safe margin.\n"
            "Recommendation: Risk of undercut. Consider waiting for a safety car or pitting after car behind pits."
        )


# ---------------------------------------------------------------------------
# Tool 4: search_f1_data
# Uses DuckDuckGo to look up real-world F1 data such as circuit characteristics,
# historical race strategies, weather forecasts, and tyre compounds.
# ---------------------------------------------------------------------------
@tool
def search_f1_data(query: str) -> str:
    """Searches the web for real F1 data including circuit history, historical
    strategies, tyre behaviour, and weather. Use this for any factual lookup."""
    # Initialise the DuckDuckGo search runner (no API key required)
    search = DuckDuckGoSearchRun()
    # Run the search and return the top results as a string
    results = search.run(query)
    return results


# ---------------------------------------------------------------------------
# Tool 5: check_tire_status
# Pulls live telemetry from the dummy tyre service, runs the prediction engine,
# and renders a colored progress bar in the terminal.
# ---------------------------------------------------------------------------
@tool
def check_tire_status(compound: str, lap_age: int, circuit: str = "") -> str:
    """Checks the current tyre status including pressure, temperature, and
    percentage of tyre life consumed. Also predicts additional degradation if
    the car takes the next bank/turn and shows a visual progress bar.
    compound must be 'soft', 'medium', or 'hard'. circuit is optional
    (e.g. 'silverstone', 'monaco', 'spa')."""

    compound = compound.lower().strip()
    if compound not in ("soft", "medium", "hard"):
        return f"Unknown compound '{compound}'. Please specify 'soft', 'medium', or 'hard'."

    # Step 1 — Pull dummy telemetry data from onboard sensors
    telemetry = get_tire_telemetry_data(compound, lap_age, circuit)

    # Step 2 — Run prediction engine for next-bank degradation estimate
    prediction = predict_tire_degradation(telemetry)

    # Step 3 — Render the colored progress bar to the terminal (side effect)
    render_tire_life_bar(telemetry, prediction)

    # Step 4 — Build a text summary to return to the agent
    summary = (
        f"Tire Status Report:\n"
        f"  Compound: {telemetry['compound']}\n"
        f"  Lap Age: {telemetry['lap_age']} laps\n"
        f"  Circuit: {telemetry['circuit']}\n"
        f"  Turns/Lap: {telemetry['turns_per_lap']}\n"
        f"  Pressure: {telemetry['pressure_psi']} PSI\n"
        f"  Temperature: {telemetry['temperature_c']}°C\n"
        f"  Life Used: {telemetry['life_pct_used']}%\n"
        f"  Revolutions: {telemetry['current_revolutions']:,} / "
        f"{telemetry['total_lifecycle_revolutions']:,}\n"
        f"\n"
        f"Prediction — Next Bank Impact:\n"
        f"  Additional degradation: +{prediction['predicted_next_bank_pct']}%\n"
        f"  Life after next bank: {prediction['life_pct_after_bank']}%\n"
        f"  Estimated tire laps remaining: {prediction['laps_remaining_in_tire']} laps\n"
        f"  Risk level: {prediction['risk_level']}"
    )
    return summary
