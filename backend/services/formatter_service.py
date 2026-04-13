from models.schemas import (
    Intent, Emotion, RailwayAPIResult,
    FormattedContext
)

# ══════════════════════════════════════════════════════════════════
#   PNR STATUS FORMATTER
# ══════════════════════════════════════════════════════════════════

PNR_STATUS_MAP = {
    "CNF":  ("Confirmed ✅",       Emotion.excited,  False),
    "WL":   ("Waitlisted ⏳",      Emotion.neutral,  True),
    "RAC":  ("RAC (Seat Sharing) 🔄", Emotion.neutral, True),
    "PQWL": ("Pooled Quota WL ⏳", Emotion.neutral,  True),
    "RLWL": ("Remote Location WL ⏳", Emotion.neutral, True),
    "GNWL": ("General WL ⏳",      Emotion.neutral,  True),
    "CAN":  ("Cancelled ❌",        Emotion.sorry,    True),
    "REGRET": ("No Availability ❌", Emotion.sorry,   True),
}

def _parse_pnr_status_code(status: str):
    if not status:
        return ("Status Unknown ❓", Emotion.neutral, False)

    upper = status.upper()

    if upper in PNR_STATUS_MAP:
        return PNR_STATUS_MAP[upper]

    for code, value in PNR_STATUS_MAP.items():
        if upper.startswith(code):
            return value

    return (status, Emotion.friendly, False)


def _pnr_alert(status: str, chart_prepared: bool):
    upper = (status or "").upper()

    if "WL" in upper:
        wl_num = ""
        parts = upper.split("/")
        for p in parts:
            if p.isdigit():
                wl_num = p
                break
        msg = "Your ticket is on the waitlist."
        if wl_num:
            msg += f" Current position: WL{wl_num}."
        msg += " Confirmation depends on cancellations closer to the travel date."
        return msg

    if "RAC" in upper:
        return ("RAC means you'll get a side-lower berth to share. "
                "A full berth may be allotted at chart preparation.")

    if upper == "CAN":
        return ("This ticket has been CANCELLED. Refund should be processed in 5-7 days.")

    if not chart_prepared:
        return ("Chart not prepared yet. Final seat numbers will be assigned later.")

    return None


def format_pnr_response(data: dict) -> FormattedContext:
    pnr     = data.get("pnr_number", "N/A")
    status  = data.get("status", "")
    train   = data.get("train_name", data.get("train_number", "your train"))
    doj     = data.get("doj", "your travel date")
    src     = data.get("from_station", "")
    dst     = data.get("to_station", "")
    chart   = data.get("chart_prepared", False)

    status_label, emotion, needs_alert = _parse_pnr_status_code(status)
    alert = _pnr_alert(status, chart) if needs_alert else None

    journey = f" ({src} → {dst})" if src and dst else ""

    summary = (
        f"PNR {pnr} for {train}{journey} on {doj}: "
        f"Status is {status_label}."
    )

    summary += " Chart prepared." if chart else " Chart not yet prepared."

    return FormattedContext(
        summary=summary,
        emotion=emotion,
        key_facts={
            "pnr": pnr,
            "status": status_label,
            "train": train,
            "date": doj,
        },
        alert=alert
    )


# ══════════════════════════════════════════════════════════════════
#   TRAIN STATUS FORMATTER
# ══════════════════════════════════════════════════════════════════

def _delay_label(minutes):
    if minutes is None:
        return ("Running status unknown", Emotion.neutral, None)
    if minutes == 0:
        return ("Running on time ✅", Emotion.excited, None)
    if minutes <= 15:
        return (f"Slightly delayed by {minutes} mins ⚠️", Emotion.neutral, None)
    if minutes <= 60:
        return (f"Delayed by {minutes} minutes ⚠️", Emotion.neutral, None)
    if minutes <= 180:
        return (f"Significantly delayed by {minutes} minutes ❗", Emotion.sorry, None)
    return (f"Very heavily delayed by {minutes} minutes 🚨", Emotion.sorry, None)


def format_train_status_response(data: dict) -> FormattedContext:
    train_no  = data.get("train_number", "")
    train_nm  = data.get("train_name", f"Train {train_no}")
    station   = data.get("current_station", "en route")
    delay_min = data.get("delay_minutes")
    updated   = data.get("last_updated", "recently")
    status    = data.get("status", "")

    delay_label, emotion, alert = _delay_label(delay_min)

    summary = (
        f"{train_nm} (#{train_no}) is at {station}. "
        f"{delay_label}. Last updated: {updated}."
    )

    if status and status.lower() not in ["running", ""]:
        summary += f" Status: {status}."

    return FormattedContext(
        summary=summary,
        emotion=emotion,
        key_facts={
            "train": train_nm,
            "station": station,
            "delay": delay_label,
            "last_updated": updated,
        },
        alert=alert
    )


# ══════════════════════════════════════════════════════════════════
#   SEAT AVAILABILITY FORMATTER
# ══════════════════════════════════════════════════════════════════

CLASS_FULL_NAMES = {
    "SL": "Sleeper Class",
    "3A": "Third AC",
    "2A": "Second AC",
    "1A": "First AC",
    "CC": "Chair Car",
    "EC": "Executive Chair Car",
    "2S": "Second Sitting",
    "FC": "First Class",
}

def _availability_label(status, count):
    if not status:
        return ("Availability unknown ❓", Emotion.neutral, None)

    upper = status.upper()

    if "AVAILABLE" in upper and "NOT" not in upper:
        seats = f"{count} seats" if count else "Seats"
        return (f"{seats} available ✅", Emotion.excited, None)

    if "WL" in upper:
        return ("Waitlisted ⏳", Emotion.neutral, None)

    if "RAC" in upper:
        return ("RAC available 🔄", Emotion.neutral, None)

    if "NOT AVAILABLE" in upper or "REGRET" in upper:
        return ("Not available ❌", Emotion.sorry, None)

    return (status, Emotion.neutral, None)


def format_seat_availability_response(data: dict) -> FormattedContext:
    train_no = data.get("train_number", "")
    train_nm = data.get("train_name", f"Train {train_no}")
    src      = data.get("from_station", "")
    dst      = data.get("to_station", "")
    date     = data.get("travel_date", "")
    cls      = data.get("travel_class", "SL")
    count    = data.get("available")
    status   = data.get("status", "")

    cls_name = CLASS_FULL_NAMES.get(cls, cls)
    avail_label, emotion, alert = _availability_label(status, count)

    journey = f"{src} → {dst}" if src and dst else ""

    summary = (
        f"{cls_name} seats on {train_nm} (#{train_no})"
        f"{' for ' + journey if journey else ''}"
        f"{' on ' + date if date else ''}: "
        f"{avail_label}."
    )

    return FormattedContext(
        summary=summary,
        emotion=emotion,
        key_facts={
            "train": train_nm,
            "class": cls_name,
            "route": journey,
            "date": date,
            "status": avail_label,
        },
        alert=alert
    )


# ══════════════════════════════════════════════════════════════════
#   ERROR FORMATTER
# ══════════════════════════════════════════════════════════════════

ERROR_MESSAGES = {
    "timeout":    "The railway server took too long to respond.",
    "rate limit": "Too many requests.",
    "invalid":    "Invalid input provided.",
    "not found":  "Couldn't find the requested information.",
    "api key":    "Railway API misconfigured.",
    "network":    "Network issue.",
}

def format_error_response(error: str) -> FormattedContext:
    error_lower = error.lower()

    friendly_msg = "I couldn't fetch railway data."
    for key, msg in ERROR_MESSAGES.items():
        if key in error_lower:
            friendly_msg = msg
            break

    return FormattedContext(
        summary=f"Error: {friendly_msg}",
        emotion=Emotion.sorry,
        key_facts={"error": error},
        alert=friendly_msg
    )


# ══════════════════════════════════════════════════════════════════
#   MAIN DISPATCHER
# ══════════════════════════════════════════════════════════════════

def format_api_result(api_result: RailwayAPIResult) -> FormattedContext:
    if not api_result.success or not api_result.data:
        return format_error_response(api_result.error or "Unknown error")

    if api_result.intent == Intent.pnr_status:
        return format_pnr_response(api_result.data)

    elif api_result.intent == Intent.train_status:
        return format_train_status_response(api_result.data)

    elif api_result.intent == Intent.seat_availability:
        return format_seat_availability_response(api_result.data)

    return FormattedContext(
        summary="Here is the information you requested.",
        emotion=Emotion.friendly,
        key_facts=api_result.data or {}
    )