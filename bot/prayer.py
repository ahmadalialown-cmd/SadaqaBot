"""Offline Doha prayer times (Qatar method: Fajr 18°, Isha = Maghrib + 90 min,
Asr shadow factor 1). Standard astronomical formulas (praytimes.org style)."""
import math
from datetime import date, datetime, time, timedelta, timezone

DOHA = (25.2854, 51.5310)
TZ = timezone(timedelta(hours=3))
FAJR_ANGLE = 18.0
# Small safety margins (minutes) similar to official tables
# Tuned against the "Qatar" (Awqaf) method on timesprayer.com for 2026-11-06
ADJUST = {"fajr": 0, "dhuhr": 0, "asr": 0, "maghrib": 1}

d2r, r2d = math.radians, math.degrees


def _sun(jd):
    D = jd - 2451545.0
    g = (357.529 + 0.98560028 * D) % 360
    q = (280.459 + 0.98564736 * D) % 360
    L = (q + 1.915 * math.sin(d2r(g)) + 0.020 * math.sin(d2r(2 * g))) % 360
    e = 23.439 - 0.00000036 * D
    RA = r2d(math.atan2(math.cos(d2r(e)) * math.sin(d2r(L)), math.cos(d2r(L)))) / 15
    decl = r2d(math.asin(math.sin(d2r(e)) * math.sin(d2r(L))))
    eqt = q / 15 - (RA % 24)
    eqt = (eqt + 12) % 24 - 12
    return decl, eqt


def _jd(d: date):
    y, m = d.year, d.month
    if m <= 2:
        y, m = y - 1, m + 12
    A = y // 100
    B = 2 - A + A // 4
    return int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + d.day + B - 1524.5


def times(d: date, lat=DOHA[0], lon=DOHA[1], tz=3):
    jd = _jd(d) - lon / 360
    decl, eqt = _sun(jd + 0.5)
    noon = 12 - eqt - lon / 15 + tz

    def hour_angle(angle):
        v = (-math.sin(d2r(angle)) - math.sin(d2r(decl)) * math.sin(d2r(lat))) / (
            math.cos(d2r(decl)) * math.cos(d2r(lat)))
        return r2d(math.acos(v)) / 15

    def asr_angle():
        return -r2d(math.atan(1 / (1 + math.tan(d2r(abs(lat - decl))))))

    t = {
        "fajr": noon - hour_angle(FAJR_ANGLE),
        "sunrise": noon - hour_angle(0.833),
        "dhuhr": noon,
        "asr": noon + hour_angle(asr_angle()),
        "maghrib": noon + hour_angle(0.833),
    }
    out = {}
    for k, h in t.items():
        dt = datetime.combine(d, time(0), TZ) + timedelta(hours=h, minutes=ADJUST.get(k, 0))
        out[k] = (dt + timedelta(seconds=30)).replace(second=0, microsecond=0)
    out["isha"] = out["maghrib"] + timedelta(minutes=90)
    return out


if __name__ == "__main__":
    import sys
    d = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else datetime.now(TZ).date()
    for k, v in times(d).items():
        print(f"{k:8s} {v:%H:%M}")
