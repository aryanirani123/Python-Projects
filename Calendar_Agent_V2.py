import datetime
import os.path
import re
from dateutil import parser as dateutil_parser
import dateparser
import pytz
from tzlocal import get_localzone
from typing import Optional
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
        Tuple of (start_datetime, end_datetime) in ISO 8601 UTC format (e.g., '2025-09-26T05:30:00Z').
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

    # Try parsing with dateparser
    parsed_datetime = dateparser.parse(
        datetime_string,
        languages=['en'],
        settings=settings
    )

    if not parsed_datetime:
        # Fallback: Manual handling for "next [day]" patterns
        match = re.match(r'next\s+(\w+)\s*(at\s+)?(.+)', datetime_string, re.IGNORECASE)
        if match:
            day_name, _, time_part = match.groups()
            print(f"Manual parsing: day_name={day_name}, time_part={time_part}")

            # Map day names to weekday numbers (0=Monday, ..., 6=Sunday)
            day_map = {
                'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
                'friday': 4, 'saturday': 5, 'sunday': 6
            }
            if day_name.lower() not in day_map:
                raise ValueError(f"Invalid day name: {day_name}")

            target_weekday = day_map[day_name.lower()]
            current_date = datetime.datetime.now(pytz.timezone(user_timezone))
            current_weekday = current_date.weekday()
            days_ahead = (target_weekday - current_weekday + 7) % 7 or 7  # Next occurrence
            target_date = current_date + datetime.timedelta(days=days_ahead)

            # Parse time part
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

    # Convert to UTC
    parsed_datetime = parsed_datetime.astimezone(pytz.UTC)
    start_datetime = parsed_datetime.isoformat().replace('+00:00', 'Z')

    # Calculate end time based on duration
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
        # Default to 1-hour duration if not specified
        end_datetime = (parsed_datetime + datetime.timedelta(hours=1)).isoformat().replace('+00:00', 'Z')

    return start_datetime, end_datetime

def get_calendar_service():
    """Retrieve authenticated Google Calendar service."""
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
    """Create a Google Calendar event in the user's local time zone."""
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

def list_events():
    """List the next 10 upcoming events, displaying times in the user's local time zone."""
    user_timezone = get_user_timezone()
    service = get_calendar_service()
    now = datetime.datetime.now(tz=pytz.UTC).isoformat()
    print("Getting the upcoming 10 events")
    events_result = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=now,
            maxResults=10,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    events = events_result.get("items", [])

    if not events:
        return "No upcoming events found."
    
    user_tz = pytz.timezone(user_timezone)
    formatted_events = []
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        try:
            if 'dateTime' in event['start']:
                utc_time = datetime.datetime.fromisoformat(start.replace('Z', '+00:00'))
                local_time = utc_time.astimezone(user_tz)
                formatted_time = local_time.strftime("%Y-%m-%d %I:%M %p %Z")
            else:
                formatted_time = start
            formatted_events.append(f"{formatted_time} - {event['summary']}")
        except Exception as e:
            print(f"Error converting time for event '{event['summary']}': {str(e)}")
            formatted_events.append(f"{start} - {event['summary']} (UTC)")
    
    return formatted_events

# --- Agent Definition ---
calendar_agent_instruction_text = """You are a helpful and precise calendar assistant that operates in the user's local time zone (e.g., IST for Asia/Kolkata).

Event Creation Instructions:
When the user wants to create an event:
**First, focus on collecting the essential details to create an event:**
* Event title
* Start date and time (you can understand natural language like "tomorrow at 3 PM", "in 2 hours", "next Friday at 11 AM")
* End date and time or duration (e.g., "for 1 hour", "until 5 PM")
**Use the `parse_natural_language_datetime` tool to convert natural language date/time expressions into ISO 8601 UTC format. The tool assumes inputs are in the user's local time zone (e.g., IST) and converts them to UTC for the Google Calendar API.**
**If a duration is provided (e.g., "for 1 hour"), pass it to the `parse_natural_language_datetime` tool to calculate the end time. If no duration or end time is specified, assume a 1-hour duration.**
**Location and description are strictly optional. Only include them if the user explicitly provides them. Do not prompt for location or description if not mentioned. When calling the `create_event` tool, always include `location` and `description` parameters, passing an empty string (`""`) if not provided.**
**Events are created with the user's local time zone for display in Google Calendar.**
**If any essential information (title, start time, end time/duration) is missing, ask the user to provide it.**
**For phrases like "next [day]" (e.g., "next Friday"), interpret them as the next occurrence of that day in the following week.**
After the event is created, respond with:
- A short confirmation message
- The event title and time (in the user's local time zone, e.g., IST)
- A link to the event (if available)

Event Listing Instructions:
When the user asks to see their schedule or upcoming events:
- Call the `list_events` tool to fetch the next 10 events.
- Display them in a clean and easy-to-read format, showing:
  - Date and time in the user's local time zone (e.g., IST)
  - Event name or summary
- If there are no upcoming events, say so politely.

General Instructions:
- Always interpret and display times in the user's local time zone (e.g., IST) for a seamless experience.
- Use the `parse_natural_language_datetime` tool for all date/time inputs to ensure consistency.
- For "next [day]" patterns (e.g., "next Friday"), ensure the date is set to the next occurrence of that day (e.g., one week from the current day if today is not Friday).
- Keep responses short and user-friendly (avoid technical jargon unless asked).
- Never expose raw JSON or API response data directly to the user.
- Prioritize clarity, brevity, and correctness in every response.
"""

root_agent = Agent(
    model=MODEL,
    name="google_calendar_agent",
    description="An AI assistant that manages your Google Calendar using natural language, operating in your local time zone (e.g., IST for Asia/Kolkata)." + calendar_agent_instruction_text,
    generate_content_config=types.GenerateContentConfig(temperature=0.2),
    tools=[create_event, list_events, parse_natural_language_datetime],
)
