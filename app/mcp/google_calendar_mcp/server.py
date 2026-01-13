"""
Google Calendar API service wrapper.
Pure Python class used by the MCP app entrypoint (see app.py).
"""

import os
from pathlib import Path
from typing import Any, Optional, cast
import json
from datetime import datetime, timedelta

from app.core.logger import logging
from google.auth.transport.requests import Request
from google.auth.credentials import Credentials as BaseCredentials
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)
SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/calendar.events'
]

TOKEN_PATH = Path(__file__).parent / 'tokens' / 'token.json'
CREDENTIALS_PATH = Path(__file__).parent / 'tokens' / 'credentials.json'


class GoogleCalendarService:
    """Google Calendar API wrapper"""
    
    def __init__(self):
        # Use the base Credentials type to allow for different credential implementations
        self.creds: Optional[BaseCredentials] = None
        self.service: Any = None
        self.CREDENTIALS_PATH = CREDENTIALS_PATH
        self.TOKEN_PATH = TOKEN_PATH
        logger.info(f"Raw GOOGLE_CREDENTIALS_PATH from env: {self.CREDENTIALS_PATH}")
        logger.info(f"Raw GOOGLE_TOKEN_PATH from env: {self.TOKEN_PATH}")
        logger.info(f"Using TOKEN_PATH: {TOKEN_PATH}, CREDENTIALS_PATH: {CREDENTIALS_PATH}")

    
    def _get_credentials_path(self) -> Path:
        """Resolve OAuth client secrets path.

        Priority:
        1) GOOGLE_CREDENTIALS_PATH env var (file path)
        2) credentials.json alongside this server.py
        """
        return CREDENTIALS_PATH
        
    def authenticate(self) -> bool:
        """Authenticate using OAuth 2.0"""
        # Load existing credentials
        if TOKEN_PATH.exists():
            self.creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
        
        # Refresh or get new credentials
        if not self.creds or not self.creds.valid:
            if self.creds and getattr(self.creds, "expired", False) and getattr(self.creds, "refresh_token", None):
                self.creds.refresh(Request())
            else:
                cred_path = self._get_credentials_path()
                if not cred_path.exists():
                    env_hint = os.environ.get("GOOGLE_CREDENTIALS_PATH")
                    msg = [
                        "Credentials file not found.",
                        f"Looked for: {cred_path}",
                    ]
                    if env_hint:
                        msg.append("GOOGLE_CREDENTIALS_PATH is set but the file was not found at that path.")
                    msg.append(
                        "Set GOOGLE_CREDENTIALS_PATH to your OAuth client secrets JSON path, "
                        f"or place a 'credentials.json' next to this server at: {CREDENTIALS_PATH}"
                    )
                    raise FileNotFoundError("\n".join(msg))

                flow = InstalledAppFlow.from_client_secrets_file(
                    str(cred_path), SCOPES
                )
                # run_local_server may return different credential implementations; both conform to BaseCredentials
                self.creds = flow.run_local_server(port=0)
            
            # Save credentials
            TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
            # self.creds is guaranteed non-None here, but cast for pylance to access to_json safely
            assert self.creds is not None
            with open(TOKEN_PATH, 'w') as token:
                token.write(cast(Any, self.creds).to_json())
        
        # Build service
        self.service = build('calendar', 'v3', credentials=self.creds)
        return True
    
    
    def list_calendars(self) -> dict:
        """List all calendars"""
        try:
            assert self.service is not None
            calendars_result = self.service.calendarList().list().execute()
            calendars = calendars_result.get('items', [])
            
            return {
                'count': len(calendars),
                'calendars': [
                    {
                        'id': cal['id'],
                        'summary': cal.get('summary', ''),
                        'description': cal.get('description', ''),
                        'timeZone': cal.get('timeZone', ''),
                        'primary': cal.get('primary', False),
                        'accessRole': cal.get('accessRole', '')
                    }
                    for cal in calendars
                ]
            }
        except HttpError as e:
            raise Exception(f"Failed to list calendars: {e}")
    
    def list_events(
        self, 
        calendar_id: str = 'primary',
        max_results: int = 10,
        time_min: Optional[str] = None,
        time_max: Optional[str] = None
    ) -> dict:
        """List events from a calendar"""
        try:
            assert self.service is not None
            # Default to next 7 days if no time range specified
            if not time_min:
                time_min = datetime.utcnow().isoformat() + 'Z'
            if not time_max:
                future = datetime.utcnow() + timedelta(days=7)
                time_max = future.isoformat() + 'Z'
            
            events_result = self.service.events().list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            return {
                'calendar_id': calendar_id,
                'count': len(events),
                'events': [
                    {
                        'id': event['id'],
                        'summary': event.get('summary', 'No Title'),
                        'description': event.get('description', ''),
                        'start': event['start'].get('dateTime', event['start'].get('date')),
                        'end': event['end'].get('dateTime', event['end'].get('date')),
                        'location': event.get('location', ''),
                        'attendees': [
                            att.get('email') for att in event.get('attendees', [])
                        ],
                        'htmlLink': event.get('htmlLink', '')
                    }
                    for event in events
                ]
            }
        except HttpError as e:
            raise Exception(f"Failed to list events: {e}")
    
    def create_event(
        self,
        calendar_id: str = 'primary',
        summary: str = '',
        description: str = '',
        start_time: str = '',
        end_time: str = '',
        location: str = '',
        attendees: Optional[list[str]] = None,
        timezone: str = 'UTC'
    ) -> dict:
        """Create a new calendar event"""
        try:
            assert self.service is not None
            event_body = {
                'summary': summary,
                'description': description,
                'start': {
                    'dateTime': start_time,
                    'timeZone': timezone,
                },
                'end': {
                    'dateTime': end_time,
                    'timeZone': timezone,
                },
            }
            
            if location:
                event_body['location'] = location
            
            if attendees:
                event_body['attendees'] = [{'email': email} for email in attendees]
            
            event = self.service.events().insert(
                calendarId=calendar_id,
                body=event_body
            ).execute()
            
            return {
                'id': event['id'],
                'summary': event.get('summary'),
                'htmlLink': event.get('htmlLink'),
                'message': 'Event created successfully'
            }
        except HttpError as e:
            raise Exception(f"Failed to create event: {e}")
    
    def update_event(
        self,
        calendar_id: str,
        event_id: str,
        summary: Optional[str] = None,
        description: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        location: Optional[str] = None,
        timezone: str = 'UTC'
    ) -> dict:
        """Update an existing event"""
        try:
            assert self.service is not None
            # Get existing event
            event = self.service.events().get(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()
            
            # Update fields
            if summary is not None:
                event['summary'] = summary
            if description is not None:
                event['description'] = description
            if location is not None:
                event['location'] = location
            if start_time is not None:
                event['start'] = {'dateTime': start_time, 'timeZone': timezone}
            if end_time is not None:
                event['end'] = {'dateTime': end_time, 'timeZone': timezone}
            
            updated_event = self.service.events().update(
                calendarId=calendar_id,
                eventId=event_id,
                body=event
            ).execute()
            
            return {
                'id': updated_event['id'],
                'summary': updated_event.get('summary'),
                'htmlLink': updated_event.get('htmlLink'),
                'message': 'Event updated successfully'
            }
        except HttpError as e:
            raise Exception(f"Failed to update event: {e}")
    
    def delete_event(self, calendar_id: str, event_id: str) -> dict:
        """Delete an event"""
        try:
            assert self.service is not None
            self.service.events().delete(
                calendarId=calendar_id,
                eventId=event_id
            ).execute()
            
            return {
                'event_id': event_id,
                'message': 'Event deleted successfully'
            }
        except HttpError as e:
            raise Exception(f"Failed to delete event: {e}")
    
    def search_events(
        self,
        query: str,
        calendar_id: str = 'primary',
        max_results: int = 10
    ) -> dict:
        """Search for events"""
        try:
            assert self.service is not None
            events_result = self.service.events().list(
                calendarId=calendar_id,
                q=query,
                maxResults=max_results,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            return {
                'query': query,
                'count': len(events),
                'events': [
                    {
                        'id': event['id'],
                        'summary': event.get('summary', 'No Title'),
                        'description': event.get('description', ''),
                        'start': event['start'].get('dateTime', event['start'].get('date')),
                        'end': event['end'].get('dateTime', event['end'].get('date')),
                        'htmlLink': event.get('htmlLink', '')
                    }
                    for event in events
                ]
            }
        except HttpError as e:
            raise Exception(f"Failed to search events: {e}")
    
    def get_free_busy(
        self,
        time_min: str,
        time_max: str,
        calendar_ids: Optional[list[str]] = None
    ) -> dict:
        """Check free/busy status"""
        try:
            assert self.service is not None
            if calendar_ids is None:
                calendar_ids = ['primary']
            
            body = {
                'timeMin': time_min,
                'timeMax': time_max,
                'items': [{'id': cal_id} for cal_id in calendar_ids]
            }
            
            result = self.service.freebusy().query(body=body).execute()
            
            return {
                'timeMin': time_min,
                'timeMax': time_max,
                'calendars': result.get('calendars', {})
            }
        except HttpError as e:
            raise Exception(f"Failed to get free/busy info: {e}")


# This module intentionally contains only the service class. The MCP server entrypoint lives in app.py.