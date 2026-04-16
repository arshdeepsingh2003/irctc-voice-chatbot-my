import json
import os
import difflib
from pathlib import Path
from typing import Optional

# ─── Load dataset once at startup ─────────────────────────────────
DATA_PATH = Path(__file__).parent.parent / "data" / "trains.json"

def _load_data() -> list[dict]:
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            print(f"✅ Loaded {len(data)} trains from dataset")
            return data
    except FileNotFoundError:
        print(f"❌ trains.json not found at {DATA_PATH}")
        return []
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in trains.json: {e}")
        return []

TRAINS_DB: list[dict] = _load_data()


# ══════════════════════════════════════════════════════════════════
#   QUERY FUNCTIONS
# ══════════════════════════════════════════════════════════════════

def find_train_by_number(train_number: str) -> Optional[dict]:
    """Find a train by its number."""
    for train in TRAINS_DB:
        if str(train.get("trainNo", "")) == str(train_number).strip():
            return train
    return None


def find_trains_by_route(
    from_station: str,
    to_station: str
) -> list[dict]:
    """Find all trains between two stations."""
    from_upper = from_station.upper().strip()
    to_upper   = to_station.upper().strip()

    results = []
    for train in TRAINS_DB:
        src = train.get("fromStnCode", "").upper()
        dst = train.get("toStnCode",   "").upper()
        src_name = train.get("fromStnName", "").upper()
        dst_name = train.get("toStnName",   "").upper()

        # Match by code OR name
        src_match = (from_upper in src or from_upper in src_name)
        dst_match = (to_upper   in dst or to_upper   in dst_name)

        if src_match and dst_match:
            results.append(train)

    return results


def _normalize_class_code(cls: dict) -> str:
    return str(cls.get("trainClass") or cls.get("classCode") or "").upper().strip()


def _normalize_class_name(cls: dict) -> str:
    if cls.get("className"):
        return cls.get("className")
    code = _normalize_class_code(cls)
    return {
        "SL": "Sleeper",
        "3A": "Third AC",
        "2A": "Second AC",
        "1A": "First AC",
        "CC": "Chair Car",
        "EC": "Executive Chair Car",
        "2S": "Second Sitting",
        "3E": "Third AC Economy",
        "FC": "First Class",
    }.get(code, code)


def get_seat_availability(
    train_number: str,
    travel_class: str,
    travel_date:  str
) -> Optional[dict]:
    """
    Get seat availability for a specific train, class, and date.
    Returns a dict with availability info or None if not found.
    """
    train = find_train_by_number(train_number)
    if not train:
        return None

    classes = train.get("classes", [])
    class_upper = travel_class.upper().strip()

    for cls in classes:
        if _normalize_class_code(cls) == class_upper:
            # Find availability for the requested date
            matrix = cls.get("availabilityMatrix", [])

            # Try exact date match first, or allow placeholder date entries
            for entry in matrix:
                entry_date = entry.get("date")
                if entry_date == travel_date or str(entry_date).startswith("{{"):
                    return {
                        "trainNo":     train.get("trainNo"),
                        "trainName":   train.get("trainName"),
                        "fromStnCode": train.get("fromStnCode"),
                        "toStnCode":   train.get("toStnCode"),
                        "classCode":   _normalize_class_code(cls),
                        "className":   _normalize_class_name(cls),
                        "fareInr":     cls.get("fareInr"),
                        "tatkalFareInr": cls.get("tatkalFareInr"),
                        "date":        travel_date,
                        "availabilityStatus": entry.get("availabilityStatus"),
                        "availableCount":     entry.get("availableCount"),
                        "wlNumber":    entry.get("wlNumber"),
                        "wlPredictionPct": entry.get("wlPredictionPct"),
                    }

            # If date not found, return first available entry with note
            if matrix:
                entry = matrix[0]
                return {
                    "trainNo":     train.get("trainNo"),
                    "trainName":   train.get("trainName"),
                    "fromStnCode": train.get("fromStnCode"),
                    "toStnCode":   train.get("toStnCode"),
                    "classCode":   _normalize_class_code(cls),
                    "className":   _normalize_class_name(cls),
                    "fareInr":     cls.get("fareInr"),
                    "tatkalFareInr": cls.get("tatkalFareInr"),
                    "date":        travel_date,
                    "availabilityStatus": entry.get("availabilityStatus"),
                    "availableCount":     entry.get("availableCount"),
                    "wlNumber":    entry.get("wlNumber"),
                    "wlPredictionPct": entry.get("wlPredictionPct"),
                    "note": "Exact date not in dataset — showing closest available data"
                }

    return None


def get_train_running_status(train_number: str) -> Optional[dict]:
    """
    Simulate live running status from dataset.
    Since dataset is static, we simulate delay based on train type.
    """
    train = find_train_by_number(train_number)
    if not train:
        return None

    import random
    train_type = train.get("trainType", "").lower()

    # Simulate realistic delays by train type
    delay_ranges = {
        "rajdhani":   (0, 15),
        "shatabdi":   (0, 10),
        "duronto":    (0, 20),
        "superfast":  (0, 45),
        "express":    (5, 90),
        "passenger":  (10, 120),
    }
    low, high = delay_ranges.get(train_type, (0, 60))
    delay = random.randint(low, high)

    # Pick a realistic current station
    stations = ["Departure Station", "En Route", "Approaching Destination"]
    current = random.choice(stations)

    return {
        "trainNo":        train.get("trainNo"),
        "trainName":      train.get("trainName"),
        "fromStnCode":    train.get("fromStnCode"),
        "toStnCode":      train.get("toStnCode"),
        "departureTime":  train.get("departureTime"),
        "arrivalTime":    train.get("arrivalTime"),
        "duration":       train.get("duration"),
        "trainType":      train.get("trainType"),
        "currentStation": current,
        "delayMinutes":   delay,
        "status":         "On Time" if delay == 0 else f"Late by {delay} mins",
        "lastUpdated":    "Just now (simulated)",
        "pantryCar":      train.get("pantryCar", False),
        "daysOfRun":      train.get("daysOfRun", []),
        "note":           "Status simulated from local dataset"
    }


def get_pnr_status(pnr_number: str) -> Optional[dict]:
    """
    Simulate PNR status using dataset trains.
    Maps PNR digits to a train + class for realistic simulation.
    """
    if not pnr_number or len(pnr_number) != 10:
        return None

    # Use PNR digits to deterministically pick a train + class
    idx        = int(pnr_number[-3:]) % len(TRAINS_DB) if TRAINS_DB else 0
    train      = TRAINS_DB[idx] if TRAINS_DB else None
    if not train:
        return None

    classes    = train.get("classes", [])
    class_idx  = int(pnr_number[-1]) % len(classes) if classes else 0
    cls        = classes[class_idx] if classes else {}

    matrix     = cls.get("availabilityMatrix", [{}])
    avail      = matrix[0] if matrix else {}

    status_map = {
        "0": "CNF", "1": "CNF", "2": "CNF",
        "3": "RAC", "4": "RAC",
        "5": "WL",  "6": "WL",  "7": "WL",
        "8": "CNF", "9": "CNF",
    }
    booking_status = status_map.get(pnr_number[-2], "CNF")

    seat_no = f"S{int(pnr_number[-4]) + 1}/{int(pnr_number[-3]) % 72 + 1}"

    from datetime import datetime, timedelta
    journey_date = (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")

    return {
        "pnrNumber":    pnr_number,
        "trainNo":      train.get("trainNo"),
        "trainName":    train.get("trainName"),
        "fromStnCode":  train.get("fromStnCode"),
        "fromStnName":  train.get("fromStnName"),
        "toStnCode":    train.get("toStnCode"),
        "toStnName":    train.get("toStnName"),
        "doj":          journey_date,
        "classCode":    _normalize_class_code(cls) or "SL",
        "className":    _normalize_class_name(cls),
        "bookingStatus": booking_status,
        "currentStatus": booking_status,
        "seatNumber":   seat_no if booking_status == "CNF" else None,
        "fareInr":      cls.get("fareInr"),
        "chartPrepared": False,
        "passengerCount": 1,
        "note":         "Simulated from local dataset"
    }


def search_trains(query: str) -> list[dict]:
    """Full-text search across train names and types."""
    q = query.lower().strip()
    results = []
    for train in TRAINS_DB:
        searchable = (
            train.get("trainName",    "").lower() +
            train.get("trainType",    "").lower() +
            train.get("fromStnName",  "").lower() +
            train.get("toStnName",    "").lower() +
            str(train.get("trainNo", ""))
        )
        if q in searchable:
            results.append(train)
    return results[:5]   # return top 5


def get_all_routes() -> list[str]:
    """Return all unique routes in the dataset."""
    routes = set()
    for train in TRAINS_DB:
        src = train.get("fromStnName", "")
        dst = train.get("toStnName",   "")
        if src and dst:
            routes.add(f"{src} → {dst}")
    return sorted(list(routes))


def get_train_number_by_name(train_name: str) -> str | None:
    """Find train number by name (case-insensitive partial match or fuzzy match for typos)."""
    name_lower = train_name.lower().strip()
    
    # First try exact partial match
    for train in TRAINS_DB:
        train_name_db = train.get("trainName", "").lower()
        if name_lower in train_name_db:
            return str(train.get("trainNo", ""))
    
    # If no exact match, try fuzzy match
    all_names = [train.get("trainName", "").lower() for train in TRAINS_DB if train.get("trainName")]
    matches = difflib.get_close_matches(name_lower, all_names, n=1, cutoff=0.6)
    if matches:
        closest = matches[0]
        for train in TRAINS_DB:
            if train.get("trainName", "").lower() == closest:
                return str(train.get("trainNo", ""))
    
    return None


def get_all_train_names() -> list[str]:
    """Return all train names from the dataset."""
    return [train.get("trainName", "").lower() for train in TRAINS_DB if train.get("trainName")]


def get_all_train_numbers() -> list[str]:
    """Return all train numbers from the dataset."""
    return [str(train.get("trainNo", "")) for train in TRAINS_DB if train.get("trainNo")]


def get_dataset_stats() -> dict:
    """Return summary stats about the loaded dataset."""
    if not TRAINS_DB:
        return {"loaded": False, "total_trains": 0}

    train_types = {}
    for t in TRAINS_DB:
        tt = t.get("trainType", "Unknown")
        train_types[tt] = train_types.get(tt, 0) + 1

    return {
        "loaded":        True,
        "total_trains":  len(TRAINS_DB),
        "train_types":   train_types,
        "routes":        get_all_routes(),
        "data_path":     str(DATA_PATH),
    }