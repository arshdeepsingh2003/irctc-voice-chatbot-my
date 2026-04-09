import httpx
import os
from dotenv import load_dotenv
from models.schemas import (
    Intent, RailwayAPIResult,
    PNRData, TrainStatusData, SeatAvailabilityData,
    ExtractedEntities
)

load_dotenv()

# ─── Config ───────────────────────────────────────────────────────
RAPIDAPI_KEY  = os.getenv("RAPIDAPI_KEY", "")
RAPIDAPI_HOST = os.getenv("RAPIDAPI_HOST", "irctc1.p.rapidapi.com")
API_TIMEOUT   = int(os.getenv("API_TIMEOUT", 10))

BASE_URL = f"https://{RAPIDAPI_HOST}"

HEADERS = {
    "X-RapidAPI-Key":  RAPIDAPI_KEY,
    "X-RapidAPI-Host": RAPIDAPI_HOST,
}


# ══════════════════════════════════════════════════════════════════
#  SAFETY CHECK — never call API without a key
# ══════════════════════════════════════════════════════════════════

def _api_key_missing() -> bool:
    return not RAPIDAPI_KEY or RAPIDAPI_KEY == "your_rapidapi_key_here"


def _no_key_response(intent: Intent) -> RailwayAPIResult:
    return RailwayAPIResult(
        success=False,
        intent=intent,
        error="Railway API key not configured. Please add RAPIDAPI_KEY to .env"
    )


# ══════════════════════════════════════════════════════════════════
#  PNR STATUS
# ══════════════════════════════════════════════════════════════════

async def fetch_pnr_status(pnr_number: str) -> RailwayAPIResult:
    """
    Fetch real PNR status from IRCTC API.
    Endpoint: GET /api/v3/getPNRStatus
    """
    if _api_key_missing():
        return _no_key_response(Intent.pnr_status)

    # Validate PNR format
    if not pnr_number or len(pnr_number) != 10 or not pnr_number.isdigit():
        return RailwayAPIResult(
            success=False,
            intent=Intent.pnr_status,
            error=f"Invalid PNR format: '{pnr_number}'. PNR must be 10 digits."
        )

    try:
        async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
            response = await client.get(
                f"{BASE_URL}/api/v3/getPNRStatus",
                headers=HEADERS,
                params={"pnrNumber": pnr_number}
            )

            print(f"📡 PNR API status code: {response.status_code}")

            if response.status_code == 401:
                return RailwayAPIResult(
                    success=False,
                    intent=Intent.pnr_status,
                    error="Invalid API key. Check your RAPIDAPI_KEY in .env"
                )

            if response.status_code == 429:
                return RailwayAPIResult(
                    success=False,
                    intent=Intent.pnr_status,
                    error="API rate limit reached. Please try again later."
                )

            if response.status_code != 200:
                return RailwayAPIResult(
                    success=False,
                    intent=Intent.pnr_status,
                    error=f"API returned status {response.status_code}"
                )

            raw = response.json()
            print(f"📥 PNR raw response: {str(raw)[:300]}")

            # Parse the response
            return _parse_pnr_response(raw, pnr_number)

    except httpx.TimeoutException:
        return RailwayAPIResult(
            success=False,
            intent=Intent.pnr_status,
            error="Request timed out. Railway API is slow. Try again."
        )
    except httpx.RequestError as e:
        return RailwayAPIResult(
            success=False,
            intent=Intent.pnr_status,
            error=f"Network error: {str(e)}"
        )
    except Exception as e:
        return RailwayAPIResult(
            success=False,
            intent=Intent.pnr_status,
            error=f"Unexpected error: {str(e)}"
        )


def _parse_pnr_response(raw: dict, pnr_number: str) -> RailwayAPIResult:
    """Parse raw PNR API response into clean structured data."""
    try:
        # RapidAPI IRCTC response structure
        if not raw.get("status") and raw.get("message"):
            return RailwayAPIResult(
                success=False,
                intent=Intent.pnr_status,
                error=raw.get("message", "PNR not found")
            )

        data = raw.get("data", raw)

        pnr_data = PNRData(
            pnr_number=pnr_number,
            train_number=str(data.get("trainNumber", data.get("train_number", ""))),
            train_name=data.get("trainName", data.get("train_name", "Unknown")),
            doj=data.get("doj", data.get("dateOfJourney", "")),
            from_station=data.get("boardingPoint",
                         data.get("boardingStation",
                         data.get("from", ""))),
            to_station=data.get("destinationStation",
                       data.get("to", "")),
            status=_extract_pnr_status(data),
            chart_prepared=data.get("chartPrepared", False)
        )

        return RailwayAPIResult(
            success=True,
            intent=Intent.pnr_status,
            data=pnr_data.model_dump()
        )

    except Exception as e:
        return RailwayAPIResult(
            success=False,
            intent=Intent.pnr_status,
            error=f"Failed to parse PNR response: {str(e)}"
        )


def _extract_pnr_status(data: dict) -> str:
    """Extract booking status from various API response formats."""
    # Try different field names used by different APIs
    for field in ["bookingStatus", "booking_status", "passengerStatus",
                  "currentStatus", "status"]:
        if field in data:
            return str(data[field])

    # Check passenger list
    passengers = data.get("passengerList",
                 data.get("passengers", []))
    if passengers and isinstance(passengers, list):
        statuses = [p.get("currentStatusCode",
                    p.get("bookingStatusCode", "")) for p in passengers]
        statuses = [s for s in statuses if s]
        if statuses:
            return ", ".join(statuses)

    return "Unknown"


# ══════════════════════════════════════════════════════════════════
#  TRAIN RUNNING STATUS
# ══════════════════════════════════════════════════════════════════

async def fetch_train_status(train_number: str) -> RailwayAPIResult:
    """
    Fetch live train running status.
    Endpoint: GET /api/v1/liveTrainStatus
    """
    if _api_key_missing():
        return _no_key_response(Intent.train_status)

    if not train_number or not train_number.strip().isdigit():
        return RailwayAPIResult(
            success=False,
            intent=Intent.train_status,
            error=f"Invalid train number: '{train_number}'"
        )

    try:
        from datetime import datetime
        today = datetime.now().strftime("%d-%m-%Y")

        async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
            response = await client.get(
                f"{BASE_URL}/api/v1/liveTrainStatus",
                headers=HEADERS,
                params={
                    "trainNo":   train_number,
                    "startDay":  "1"
                }
            )

            print(f"📡 Train status API code: {response.status_code}")

            if response.status_code == 401:
                return RailwayAPIResult(
                    success=False,
                    intent=Intent.train_status,
                    error="Invalid API key."
                )

            if response.status_code == 429:
                return RailwayAPIResult(
                    success=False,
                    intent=Intent.train_status,
                    error="API rate limit reached."
                )

            if response.status_code != 200:
                return RailwayAPIResult(
                    success=False,
                    intent=Intent.train_status,
                    error=f"API returned {response.status_code}"
                )

            raw = response.json()
            print(f"📥 Train status raw: {str(raw)[:300]}")
            return _parse_train_status_response(raw, train_number)

    except httpx.TimeoutException:
        return RailwayAPIResult(
            success=False,
            intent=Intent.train_status,
            error="Request timed out."
        )
    except Exception as e:
        return RailwayAPIResult(
            success=False,
            intent=Intent.train_status,
            error=f"Error: {str(e)}"
        )


def _parse_train_status_response(raw: dict, train_number: str) -> RailwayAPIResult:
    """Parse train running status response."""
    try:
        if not raw.get("status", True) is False and "message" in raw:
            msg = raw.get("message", "")
            if "not found" in msg.lower() or "invalid" in msg.lower():
                return RailwayAPIResult(
                    success=False,
                    intent=Intent.train_status,
                    error=f"Train {train_number} not found."
                )

        data = raw.get("data", raw)

        # Extract delay info
        delay = 0
        for field in ["delayInMinutes", "delay", "lateByMinutes"]:
            if field in data:
                try:
                    delay = int(data[field])
                    break
                except (ValueError, TypeError):
                    pass

        status_data = TrainStatusData(
            train_number=train_number,
            train_name=data.get("trainName",
                       data.get("train_name", f"Train {train_number}")),
            current_station=data.get("currentStation",
                            data.get("stationName",
                            data.get("at", "En route"))),
            delay_minutes=delay,
            last_updated=data.get("lastUpdated",
                         data.get("updatedAt", "Recently")),
            status=data.get("runningStatus",
                   data.get("status", "Running"))
        )

        return RailwayAPIResult(
            success=True,
            intent=Intent.train_status,
            data=status_data.model_dump()
        )

    except Exception as e:
        return RailwayAPIResult(
            success=False,
            intent=Intent.train_status,
            error=f"Parse error: {str(e)}"
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
    """
    Fetch seat availability for a train.
    Endpoint: GET /api/v1/checkSeatAvailability
    """
    if _api_key_missing():
        return _no_key_response(Intent.seat_availability)

    # Validate required fields
    missing = []
    if not train_number:  missing.append("train number")
    if not from_station:  missing.append("source station")
    if not to_station:    missing.append("destination station")
    if not travel_date:   missing.append("travel date")
    if not travel_class:  missing.append("travel class")

    if missing:
        return RailwayAPIResult(
            success=False,
            intent=Intent.seat_availability,
            error=f"Missing required fields: {', '.join(missing)}"
        )

    try:
        async with httpx.AsyncClient(timeout=API_TIMEOUT) as client:
            response = await client.get(
                f"{BASE_URL}/api/v1/checkSeatAvailability",
                headers=HEADERS,
                params={
                    "classType":   travel_class,
                    "fromStationCode": from_station,
                    "quota":       "GN",
                    "toStationCode": to_station,
                    "trainNo":     train_number,
                    "date":        travel_date
                }
            )

            print(f"📡 Seat avail API code: {response.status_code}")

            if response.status_code == 401:
                return RailwayAPIResult(
                    success=False,
                    intent=Intent.seat_availability,
                    error="Invalid API key."
                )

            if response.status_code == 429:
                return RailwayAPIResult(
                    success=False,
                    intent=Intent.seat_availability,
                    error="API rate limit reached."
                )

            if response.status_code != 200:
                return RailwayAPIResult(
                    success=False,
                    intent=Intent.seat_availability,
                    error=f"API returned {response.status_code}"
                )

            raw = response.json()
            print(f"📥 Seat avail raw: {str(raw)[:300]}")
            return _parse_seat_availability_response(
                raw, train_number, from_station,
                to_station, travel_date, travel_class
            )

    except httpx.TimeoutException:
        return RailwayAPIResult(
            success=False,
            intent=Intent.seat_availability,
            error="Request timed out."
        )
    except Exception as e:
        return RailwayAPIResult(
            success=False,
            intent=Intent.seat_availability,
            error=f"Error: {str(e)}"
        )


def _parse_seat_availability_response(
    raw: dict,
    train_number: str,
    from_station: str,
    to_station: str,
    travel_date: str,
    travel_class: str
) -> RailwayAPIResult:
    """Parse seat availability response."""
    try:
        data = raw.get("data", raw)

        # Handle list response
        if isinstance(data, list) and data:
            entry = data[0]
        else:
            entry = data if isinstance(data, dict) else {}

        available_count = None
        for field in ["availableCount", "available", "seats", "seatsAvailable"]:
            if field in entry:
                try:
                    available_count = int(entry[field])
                    break
                except (ValueError, TypeError):
                    pass

        status = entry.get("availabilityStatus",
                 entry.get("status", "UNKNOWN"))

        seat_data = SeatAvailabilityData(
            train_number=train_number,
            train_name=entry.get("trainName", f"Train {train_number}"),
            from_station=from_station,
            to_station=to_station,
            travel_date=travel_date,
            travel_class=travel_class,
            available=available_count,
            status=status
        )

        return RailwayAPIResult(
            success=True,
            intent=Intent.seat_availability,
            data=seat_data.model_dump()
        )

    except Exception as e:
        return RailwayAPIResult(
            success=False,
            intent=Intent.seat_availability,
            error=f"Parse error: {str(e)}"
        )


# ══════════════════════════════════════════════════════════════════
#  MAIN DISPATCHER
# ══════════════════════════════════════════════════════════════════

async def fetch_railway_data(
    intent: Intent,
    entities: ExtractedEntities
) -> RailwayAPIResult:
    """
    Single entry point for all railway API calls.
    Routes to the correct fetcher based on intent.
    """
    print(f"\n🚂 Railway API call → intent: {intent}")

    if intent == Intent.pnr_status:
        return await fetch_pnr_status(
            pnr_number=entities.pnr_number or ""
        )

    elif intent == Intent.train_status:
        return await fetch_train_status(
            train_number=entities.train_number or ""
        )

    elif intent == Intent.seat_availability:
        return await fetch_seat_availability(
            train_number=entities.train_number or "",
            from_station=entities.station_from or "",
            to_station=entities.station_to or "",
            travel_date=entities.travel_date or "",
            travel_class=entities.travel_class or "SL"
        )

    else:
        # general_query — no API call needed
        return RailwayAPIResult(
            success=True,
            intent=intent,
            data=None
        )