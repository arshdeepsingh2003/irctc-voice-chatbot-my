# services/railway_service.py

from models.schemas import Intent, RailwayAPIResult, ExtractedEntities
from services.data_service import (
    get_pnr_status,
    get_train_running_status,
    get_seat_availability,
)


# ══════════════════════════════════════════════════════════════════
#  PNR STATUS
# ══════════════════════════════════════════════════════════════════

async def fetch_pnr_status(pnr_number: str) -> RailwayAPIResult:
    # Validate PNR
    if not pnr_number or len(pnr_number) != 10 or not pnr_number.isdigit():
        return RailwayAPIResult(
            success=False,
            intent=Intent.pnr_status,
            error=f"Invalid PNR: '{pnr_number}'. Must be 10 digits."
        )

    # Fetch from dataset
    data = get_pnr_status(pnr_number)

    if not data:
        return RailwayAPIResult(
            success=False,
            intent=Intent.pnr_status,
            error="PNR not found in dataset."
        )

    # Map dataset → schema
    return RailwayAPIResult(
        success=True,
        intent=Intent.pnr_status,
        data={
            "pnr_number": data.get("pnrNumber"),
            "train_number": data.get("trainNo"),
            "train_name": data.get("trainName"),
            "doj": data.get("doj"),
            "from_station": data.get("fromStnCode"),
            "to_station": data.get("toStnCode"),
            "status": data.get("bookingStatus"),
            "chart_prepared": data.get("chartPrepared", False),
            "seat_number": data.get("seatNumber"),
            "fare": data.get("fareInr"),
            "note": data.get("note", ""),
        }
    )


# ══════════════════════════════════════════════════════════════════
#  TRAIN RUNNING STATUS
# ══════════════════════════════════════════════════════════════════

async def fetch_train_status(train_number: str) -> RailwayAPIResult:
    # Validate train number
    if not train_number or not str(train_number).strip().isdigit():
        return RailwayAPIResult(
            success=False,
            intent=Intent.train_status,
            error=f"Invalid train number: '{train_number}'"
        )

    # Fetch from dataset
    data = get_train_running_status(train_number)

    if not data:
        return RailwayAPIResult(
            success=False,
            intent=Intent.train_status,
            error=f"Train {train_number} not found in dataset."
        )

    return RailwayAPIResult(
        success=True,
        intent=Intent.train_status,
        data={
            "train_number": data.get("trainNo"),
            "train_name": data.get("trainName"),
            "current_station": data.get("currentStation"),
            "delay_minutes": data.get("delayMinutes"),
            "last_updated": data.get("lastUpdated"),
            "status": data.get("status"),
            "pantry_car": data.get("pantryCar"),
            "days_of_run": data.get("daysOfRun"),
            "note": data.get("note", ""),
        }
    )


# ══════════════════════════════════════════════════════════════════
#  SEAT AVAILABILITY
# ══════════════════════════════════════════════════════════════════

async def fetch_seat_availability(
    train_number: str,
    from_station: str,
    to_station: str,
    travel_date: str,
    travel_class: str
) -> RailwayAPIResult:

    # Validate required fields
    missing = [
        f for f, v in {
            "train number": train_number,
            "travel date": travel_date,
            "travel class": travel_class,
        }.items() if not v
    ]

    if missing:
        return RailwayAPIResult(
            success=False,
            intent=Intent.seat_availability,
            error=f"Missing: {', '.join(missing)}"
        )

    # Fetch from dataset
    # First check if train exists
    from services.data_service import find_train_by_number
    train = find_train_by_number(train_number)
    if not train:
        return RailwayAPIResult(
            success=False,
            intent=Intent.seat_availability,
            error=f"Train {train_number} not found in our database."
        )

    data = get_seat_availability(train_number, travel_class, travel_date)

    if not data:
        # Get available classes
        available_classes = [cls.get("trainClass") for cls in train.get("classes", [])]
        classes_str = ", ".join(available_classes) if available_classes else "none"
        return RailwayAPIResult(
            success=False,
            intent=Intent.seat_availability,
            error=f"Class {travel_class} is not available on train {train_number}. Available classes: {classes_str}."
        )

    return RailwayAPIResult(
        success=True,
        intent=Intent.seat_availability,
        data={
            "train_number": data.get("trainNo"),
            "train_name": data.get("trainName"),
            "from_station": data.get("fromStnCode", from_station),
            "to_station": data.get("toStnCode", to_station),
            "travel_date": data.get("date"),
            "travel_class": data.get("classCode"),
            "available": data.get("availableCount"),
            "status": data.get("availabilityStatus"),
            "fare": data.get("fareInr"),
            "tatkal_fare": data.get("tatkalFareInr"),
            "wl_number": data.get("wlNumber"),
            "wl_prediction": data.get("wlPredictionPct"),
            "note": data.get("note", ""),
        }
    )


# ══════════════════════════════════════════════════════════════════
#  MAIN DISPATCHER (UNCHANGED)
# ══════════════════════════════════════════════════════════════════

async def fetch_railway_data(
    intent: Intent,
    entities: ExtractedEntities
) -> RailwayAPIResult:
    """
    Single entry point for all railway data calls.
    """

    print(f"\n🚂 Railway call → intent: {intent}")

    if intent == Intent.pnr_status:
        return await fetch_pnr_status(
            entities.pnr_number or ""
        )

    elif intent == Intent.train_status:
        return await fetch_train_status(
            entities.train_number or ""
        )

    elif intent == Intent.seat_availability:
        return await fetch_seat_availability(
            train_number=entities.train_number or "",
            from_station=entities.station_from or "",
            to_station=entities.station_to or "",
            travel_date=entities.travel_date or "",
            travel_class=entities.travel_class or "SL"
        )

    # General queries (no dataset needed)
    return RailwayAPIResult(
        success=True,
        intent=intent,
        data=None
    )