import datetime
import os.path
import re
import datefinder

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.adk.agents import Agent
from google.genai import types

MODEL = "gemini-2.0-flash-001" # Using a more recent model
# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar"]

# Please install datefinder by running: pip install datefinder


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
    location: str ,
    description: str 
):
    service = get_calendar_service()
    event = {
        "summary": summary,
        "start": {"dateTime": start_datetime, "timeZone": "UTC"},
        "end": {"dateTime": end_datetime, "timeZone": "UTC"},
    }
    if location: event["location"] = location
    if description: event["description"] = description
    created = service.events().insert(calendarId="primary", body=event).execute()
    return f"Event created: {created.get('htmlLink')}"


def list_events():
    service = get_calendar_service()
    now = datetime.datetime.now(tz=datetime.timezone.utc).isoformat()
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
        print("No upcoming events found.")
    else:
      return [
          f"{event['start'].get('dateTime', event['start'].get('date'))} - {event['summary']}"
          for event in events
      ]



# --- Agent Definition ---
calendar_agent_instruction_text = """You are a helpful and precise calendar assistant.
  
Event Creation Instructions:

When the user wants to create an event:

Collect these required details:

Event title

Start date and time

End date and time (or duration)

Collect these optional details if provided:

Location

Description or agenda

Convert the provided date and time to ISO 8601 format (YYYY-MM-DDTHH:MM:SSZ) in UTC before calling the event creation function.

If any required information is missing (like time, date, or title), ask the user to provide it.

After the event is created, respond with:

A short confirmation message

The event title and time

A link to the event (if available)

Event Listing Instructions:

When the user asks to see their schedule or upcoming events:

Call the list_events tool to fetch the next 10 events.

Display them in a clean and easy-to-read format, showing:

Date and time

Event name or summary

If there are no upcoming events, say so politely.

General Instructions:

Always be accurate with time and date information.

Keep responses short and user-friendly (avoid technical jargon unless asked).

Never expose raw JSON or API response data directly to the user.

Prioritize clarity, brevity, and correctness in every response.

"""


root_agent = Agent(
    model=MODEL,
    name="google_calendar_agent",
    description=" An AI assistant that manages your Google Calendar using natural language."+calendar_agent_instruction_text,
    generate_content_config=types.GenerateContentConfig(temperature=0.2),
    tools=[create_event, list_events],
)
