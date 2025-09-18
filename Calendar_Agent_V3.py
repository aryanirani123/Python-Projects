
import datetime
import os.path
import re
from dateutil import parser as dateutil_parser
import dateparser
import pytz
from tzlocal import get_localzone
from typing import Optional, List, Dict
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.adk.agents import Agent
from google.genai import types

MODEL = "gemini-2.0-flash-001"
SCOPES = ["https://www.googleapis.com/auth/calendar"]

def get_user_timezone() -> str:
    """
    Detect the user's local time zone. Falls back to 'Asia/Kolkata' if detection fails.
    """
    try:
        return str(get_localzone())
    except Exception as e:
        print(f"Warning: Could not detect local time zone ({str(e)}). Falling back to 'Asia/Kolkata'.")
        return "Asia/Kolkata"

def parse_natural_language_datetime(datetime_string: str, duration: Optional[str] = None) -> tuple[str, str]:
    """
    Parses a natural language date/time string in the user's local time zone
    and returns start and end times in ISO 8601 UTC format.
    
    Args:
        datetime_string: Natural language input (e.g., "next Friday at 11 AM").
        duration: Optional duration (e.g., "for 1 hour") to calculate end time.
    
    Returns:
        Tuple of (start_datetime, end_datetime) in ISO 8601 UTC format.
    """
    user_timezone = get_user_timezone()
    settings = {
        'TIMEZONE': user_timezone,
        'TO_TIMEZONE': 'UTC',
        'RETURN_AS_TIMEZONE_AWARE': True,
        'PREFER_DATES_FROM': 'future',
        'DATE_ORDER': 'DMY',
        'STRICT_PARSING': False
    }

    parsed_datetime = dateparser.parse(
        datetime_string,
        languages=['en'],
        settings=settings
    )

    if not parsed_datetime:
        match = re.match(r'next\s+(\w+)\s*(at\s+)?(.+)', datetime_string, re.IGNORECASE)
        if match:
            day_name, _, time_part = match.groups()
            print(f"Manual parsing: day_name={day_name}, time_part={time_part}")

            day_map = {
                'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
                'friday': 4, 'saturday': 5, 'sunday': 6
            }
            if day_name.lower() not in day_map:
                raise ValueError(f"Invalid day name: {day_name}")

            target_weekday = day_map[day_name.lower()]
            current_date = datetime.datetime.now(pytz.timezone(user_timezone))
            current_weekday = current_date.weekday()
            days_ahead = (target_weekday - current_weekday + 7) % 7 or 7
            target_date = current_date + datetime.timedelta(days=days_ahead)

            try:
                time_parsed = dateutil_parser.parse(time_part, fuzzy=True)
                parsed_datetime = target_date.replace(
                    hour=time_parsed.hour,
                    minute=time_parsed.minute,
                    second=0,
                    microsecond=0
                )
            except ValueError:
                raise ValueError(f"Could not parse time part: {time_part}")

    if not parsed_datetime:
        raise ValueError(f"Could not parse date/time: {datetime_string}")

    parsed_datetime = parsed_datetime.astimezone(pytz.UTC)
    start_datetime = parsed_datetime.isoformat().replace('+00:00', 'Z')

    if duration:
        duration_match = re.match(r'for\s+(\d+)\s*(hour|hours|minute|minutes)', duration, re.IGNORECASE)
        if duration_match:
            value, unit = duration_match.groups()
            value = int(value)
            delta = datetime.timedelta(hours=value) if unit.lower().startswith('hour') else datetime.timedelta(minutes=value)
            end_datetime = (parsed_datetime + delta).isoformat().replace('+00:00', 'Z')
        else:
            raise ValueError(f"Could not parse duration: {duration}")
    else:
        end_datetime = (parsed_datetime + datetime.timedelta(hours=1)).isoformat().replace('+00:00', 'Z')

    return start_datetime, end_datetime

def get_calendar_service():
    creds = None
    if os.path.exists("token.json"):
        try:
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)
        except (UnicodeDecodeError, ValueError):
            print("Warning: 'token.json' is invalid or has an encoding issue. Attempting to re-authorize.")
            os.remove("token.json")

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w", encoding="utf-8") as token:
            token.write(creds.to_json())
    return build("calendar", "v3", credentials=creds)

def create_event(
    summary: str,
    start_datetime: str,
    end_datetime: str,
    location: str = "",
    description: str = ""
):
    user_timezone = get_user_timezone()
    service = get_calendar_service()
    event = {
        "summary": summary,
        "start": {"dateTime": start_datetime, "timeZone": user_timezone},
        "end": {"dateTime": end_datetime, "timeZone": user_timezone},
    }

    if location and location.strip() != "":
        event["location"] = location
    if description and description.strip() != "":
        event["description"] = description

    try:
        created = service.events().insert(calendarId="primary", body=event).execute()
        return f"Event created: {created.get('htmlLink')}"
    except HttpError as error:
        raise ValueError(f"Failed to create event: {str(error)}")

def get_event(event_id: str, calendar_id: str = "primary") -> Dict:
    """
    Fetch details of a specific event.
    """
    service = get_calendar_service()
    try:
        event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()
        return event
    except HttpError as error:
        raise ValueError(f"Failed to get event: {str(error)}")

def update_event(
    event_id: str,
    summary: Optional[str] = None,
    start_datetime: Optional[str] = None,
    end_datetime: Optional[str] = None,
    location: Optional[str] = None,
    description: Optional[str] = None,
    calendar_id: str = "primary",
    send_updates: str = "none"
) -> str:
    """
    Update an existing event with partial changes.
    
    Args:
        event_id: The ID of the event to update.
        summary: New summary (title), if provided.
        start_datetime: New start date/time in ISO 8601 UTC, if provided.
        end_datetime: New end date/time in ISO 8601 UTC, if provided.
        location: New location, if provided.
        description: New description, if provided.
        calendar_id: Calendar ID (default: "primary").
        send_updates: Whether to send updates ("all", "externalOnly", "none").
    """
    service = get_calendar_service()
    update_body = {}
    
    if summary is not None:
        update_body["summary"] = summary
    if start_datetime is not None:
        update_body["start"] = {"dateTime": start_datetime, "timeZone": get_user_timezone()}
    if end_datetime is not None:
        update_body["end"] = {"dateTime": end_datetime, "timeZone": get_user_timezone()}
    if location is not None:
        update_body["location"] = location
    if description is not None:
        update_body["description"] = description
    
    if not update_body:
        raise ValueError("No fields provided to update.")
    
    try:
        updated = service.events().patch(
            calendarId=calendar_id,
            eventId=event_id,
            body=update_body,
            sendUpdates=send_updates
        ).execute()
        return f"Event updated: {updated.get('htmlLink')}"
    except HttpError as error:
        raise ValueError(f"Failed to update event: {str(error)}")

def delete_event(event_id: str, calendar_id: str = "primary", send_updates: str = "none") -> str:
    """
    Delete an event.
    
    Args:
        event_id: The ID of the event to delete.
        calendar_id: Calendar ID (default: "primary").
        send_updates: Whether to send updates ("all", "externalOnly", "none").
    """
    service = get_calendar_service()
    try:
        service.events().delete(
            calendarId=calendar_id,
            eventId=event_id,
            sendUpdates=send_updates
        ).execute()
        return "Event deleted successfully."
    except HttpError as error:
        raise ValueError(f"Failed to delete event: {str(error)}")

def search_events(
    query: Optional[str] = None,
    time_min: Optional[str] = None,
    time_max: Optional[str] = None,
    max_results: int = 10,
    calendar_id: str = "primary"
) -> List[str]:
    """
    Search for events matching criteria.
    
    Args:
        query: Free-text search query.
        time_min: Lower bound for event end time (ISO 8601 UTC).
        time_max: Upper bound for event start time (ISO 8601 UTC).
        max_results: Maximum number of results.
        calendar_id: Calendar ID (default: "primary").
    
    Returns:
        List of formatted event strings (time - summary - id).
    """
    service = get_calendar_service()
    params = {
        "calendarId": calendar_id,
        "maxResults": max_results,
        "singleEvents": True,
        "orderBy": "startTime"
    }
    if query:
        params["q"] = query
    if time_min:
        params["timeMin"] = time_min
    if time_max:
        params["timeMax"] = time_max
    
    try:
        events_result = service.events().list(**params).execute()
        events = events_result.get("items", [])
        
        if not events:
            return ["No events found."]
        
        user_tz = pytz.timezone(get_user_timezone())
        formatted_events = []
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            if 'dateTime' in event['start']:
                utc_time = datetime.datetime.fromisoformat(start.replace('Z', '+00:00'))
                local_time = utc_time.astimezone(user_tz)
                formatted_time = local_time.strftime("%Y-%m-%d %I:%M %p %Z")
            else:
                formatted_time = start
            formatted_events.append(f"{formatted_time} - {event['summary']} - ID: {event['id']}")
        
        return formatted_events
    except HttpError as error:
        raise ValueError(f"Failed to search events: {str(error)}")

def list_events(max_results: int = 10):
    now = datetime.datetime.now(tz=pytz.UTC).isoformat()
    return search_events(time_min=now, max_results=max_results)

# --- Agent Definition ---
calendar_agent_instruction_text = """You are a helpful and precise calendar assistant that operates in the user's local time zone (e.g., IST for Asia/Kolkata).

Event Creation Instructions:
When the user wants to create an event:
- Collect essential details: title, start time, end time/duration.
- Use `parse_natural_language_datetime` to parse dates/times/durations into ISO 8601 UTC.
- Location and description are optional; only include if provided.
- Call `create_event` with parsed values.
- Respond with confirmation, title/time in local TZ, and link.

Event Updating/Editing Instructions:
When the user wants to update or edit an event:
- First, identify the event: Use `search_events` or `get_event` if ID is known, to find/confirm the event ID.
- Ask for clarification if multiple matches or ambiguous.
- Use `parse_natural_language_datetime` if updating times/durations.
- Call `update_event` with the event ID and only the fields to change (pass None for unchanged).
- Set `send_updates` to "all" if attendees might be affected, else "none".
- Respond with confirmation and updated details in local TZ.

Event Deletion Instructions:
When the user wants to delete an event:
- Identify the event: Use `search_events` to find the event ID.
- Confirm with the user if needed (e.g., show details via `get_event`).
- Call `delete_event` with the event ID.
- Set `send_updates` to "all" if notifying others, else "none".
- Respond with confirmation.

Event Search and Querying Instructions:
When the user asks to search or query events:
- Use `search_events` with query (keywords), time_min/max (parsed via `parse_natural_language_datetime` if needed).
- Display results in local TZ, including event ID for reference.
- If no results, say so politely.
- For upcoming events, use `list_events`.

General Instructions:
- Always use local time zone (e.g., IST) for inputs/outputs; convert to UTC for API.
- For "next [day]" (e.g., "next Friday"), interpret as next occurrence.
- If event ID unknown for update/delete, search first.
- Handle ambiguities by asking questions.
- Keep responses short, user-friendly; no raw JSON.
- Prioritize clarity and correctness.
"""

root_agent = Agent(
    model=MODEL,
    name="google_calendar_agent",
    description="An AI assistant that manages your Google Calendar using natural language, including creating, updating, deleting, listing, and searching events in your local time zone." + calendar_agent_instruction_text,
    generate_content_config=types.GenerateContentConfig(temperature=0.2),
    tools=[create_event, get_event, update_event, delete_event, search_events, list_events, parse_natural_language_datetime],
)
