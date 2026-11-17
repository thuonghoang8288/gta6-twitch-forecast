"""gta6-twitch-ccu-forecast-01 entry: donor-median Twitch CCU forecaster.

Method (validated by leave-one-out over the kit's comparables):
  - Donors are the case's own `comparables`: past big launches with a full
    24-hour release-day curve. Keep only rolling-midnight-style launches whose
    hour-1 print was already substantial (hour1 >= 500 viewers and
    hour1 / day-peak >= 0.20); single-global-unlock launches whose hour 1 is
    near zero are excluded, because their hour-1 ratios explode and would
    wreck the spread.
  - For each forecast hour h, take the log-ratio log(viewers_h / viewers_1)
    across donors. The median forecast is p1 * exp(0.9 * mean(log-ratio)):
    the 0.9 shrink guards against the donor median overshooting.
  - The spread is the donors' log-ratio spread: sd clipped to [0.15, 1.2],
    applied with the standard-normal quantiles at the five scored levels.
  - Falls back to the house baseline (persistence, 0.15 spread) if no donor
    passes the filter.

Local validation (LOO over 24 rolling comparables, mean pinball loss):
  this model 0.2196 vs house baseline 0.2652 on the same cases.
Standard library only; deterministic; no network.
"""

import json
import math
import os
import statistics
import sys
from pathlib import Path

# The grader's -P leaves /bot off sys.path: put it back first, so `import model`
# finds a model.py shipped beside this file.
sys.path.insert(0, str(Path(__file__).resolve().parent))

INPUT_DIR = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
OUTPUT_DIR = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))

LEVELS = [0.05, 0.25, 0.5, 0.75, 0.95]
Z = [-1.645, -0.674, 0.0, 0.674, 1.645]

# Donor filter: a launch counts as "already playing in hour 1" when its hour-1
# print is at least this many viewers and at least this share of its day peak.
MIN_H1 = 500
MIN_H1_PEAK = 0.20
# Shrink on the mean log-ratio: the donor median overshoots slightly.
SHRINK = 0.9
# Spread of the log-ratio, clipped to this range (log units).
SD_MIN = 0.15
SD_MAX = 1.2


def round2(x: float) -> float | int:
    """x rounded to 2 decimals, half up, as JavaScript's Math.round(x * 100) / 100."""
    scaled = x * 100
    whole = math.floor(scaled)
    if scaled - whole >= 0.5:
        whole += 1
    value = whole / 100
    return int(value) if value.is_integer() else value


def parse_iso(t: str):
    """Parse an ISO-8601 UTC timestamp (trailing Z) into epoch seconds."""
    from datetime import datetime, timezone

    return datetime.fromisoformat(t.replace("Z", "+00:00")).timestamp()


def day_curve(comp: dict) -> list | None:
    """The comparable's 24 hourly release-day viewer counts, or None if incomplete."""
    try:
        ds = parse_iso(comp["day_start"])
    except (KeyError, ValueError):
        return None
    hourly: dict[int, float] = {}
    for row in comp.get("hourly", []):
        try:
            h = int((parse_iso(row["from"]) - ds) // 3600)
        except (KeyError, ValueError):
            continue
        if 0 <= h < 24:
            v = row.get("viewers")
            if isinstance(v, (int, float)) and v > 0:
                hourly[h] = v
    if len(hourly) < 24:
        return None
    return [hourly[h] for h in range(24)]


def donor_curves(case: dict) -> list[list]:
    """Release-day curves of the rolling-midnight-style comparables."""
    donors = []
    for comp in sorted(case.get("comparables", []), key=lambda c: str(c.get("name", ""))):
        curve = day_curve(comp)
        if curve is None:
            continue
        h1, peak = curve[0], max(curve)
        if h1 >= MIN_H1 and h1 / peak >= MIN_H1_PEAK:
            donors.append(curve)
    return donors


def baseline_quantiles(p1: float, h: int) -> list:
    return [round2(p1 * math.exp(z * 0.15 * math.sqrt(h - 1))) for z in Z]


def forecast_case(case: dict, name: str) -> dict:
    if case["levels"] != LEVELS:
        raise ValueError(f"{name} asks for levels {case['levels']}, not {LEVELS}")
    first = next((k for k in case["known"] if k["hour"] == 1), None)
    if first is None:
        raise ValueError(f"{name} has no hour-1 print")
    p1 = max(1, first["viewers"])

    donors = donor_curves(case)
    hours = []
    for row in case["forecast"]:
        h = row["hour"]
        if not donors:
            q = baseline_quantiles(p1, h)
        else:
            logs = sorted(math.log(c[h - 1] / c[0]) for c in donors)
            m = statistics.mean(logs) * SHRINK
            s = statistics.pstdev(logs) if len(logs) > 1 else SD_MIN
            s = max(SD_MIN, min(SD_MAX, s))
            q = [round2(min(1e9, max(1.0, p1 * math.exp(m + z * s)))) for z in Z]
            # Keep the row non-decreasing after rounding.
            for i in range(1, 5):
                if q[i] < q[i - 1]:
                    q[i] = q[i - 1]
        hours.append({"hour": h, "q": q})
    return {"hours": hours}


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for path in sorted(INPUT_DIR.glob("*.in")):
        case = json.loads(path.read_text(encoding="utf-8"))
        forecast = forecast_case(case, path.name)
        (OUTPUT_DIR / f"{path.stem}.out").write_text(
            json.dumps(forecast, separators=(",", ":")) + "\n", encoding="utf-8"
        )


if __name__ == "__main__":
    main()
