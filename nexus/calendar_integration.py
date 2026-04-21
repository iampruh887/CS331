"""
Calendar Integration for the Nexus Intelligent Chatbot System.

Interfaces with external calendar APIs for scheduling meetings and setting reminders.
"""

import re
from datetime import datetime, timedelta
from typing import Optional, List

import dateparser
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials

from nexus.config import config
from nexus.models import (
    TimeSlot, AvailabilityRequest, AvailabilityResult,
    MeetingRequest, MeetingResult, Reminder
)


class CalendarIntegrationError(Exception):
    """Raised when calendar integration operations fail."""
    pass


class CalendarIntegration:
    """
    Calendar API integration for Nexus.
    
    Provides methods for checking availability, booking meetings,
    setting reminders, and parsing natural language time expressions.
    """
    
    def __init__(self, api_key: Optional[str] = None, default_timezone: str = "UTC"):
        """
        Initialize Calendar Integration.
        
        Args:
            api_key: Calendar API key. If None, uses config.
            default_timezone: Default timezone for calendar operations.
        """
        self.api_key = api_key or config.CALENDAR_API_KEY
        self.default_timezone = default_timezone
        self._service = None
        
        # Timeout configuration
        self._timeout = config.CALENDAR_API_TIMEOUT
    
    def _get_service(self):
        """
        Get or create calendar API service.
        
        Returns:
            Google Calendar API service object
        """
        if self._service is None:
            if not self.api_key:
                raise CalendarIntegrationError(
                    "CALENDAR_API_KEY is not configured. Please set the environment variable."
                )
            
            # Build the calendar service
            self._service = build(
                "calendar",
                "v3",
                developerKey=self.api_key,
                cache_discovery=False
            )
        
        return self._service
    
    def check_availability(self, request: AvailabilityRequest) -> AvailabilityResult:
        """
        Check calendar availability for a time slot.
        
        Args:
            request: AvailabilityRequest with time range and duration
            
        Returns:
            AvailabilityResult with available time slots
            
        Raises:
            CalendarIntegrationError: If API call fails
        """
        try:
            service = self._get_service()
            
            # Get user's calendar events
            events_result = service.events().list(
                calendarId='primary',
                timeMin=request.start_time.isoformat() + 'Z',
                timeMax=request.end_time.isoformat() + 'Z',
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            # Find available time slots
            available_slots = self._find_available_slots(
                events,
                request.start_time,
                request.end_time,
                request.duration_minutes
            )
            
            return AvailabilityResult(available_slots=available_slots)
            
        except HttpError as e:
            raise CalendarIntegrationError(
                f"Google Calendar API error: {e.resp.status} - {e.reason}"
            ) from e
        except Exception as e:
            raise CalendarIntegrationError(f"Failed to check availability: {str(e)}") from e
    
    def _find_available_slots(
        self,
        events: List[dict],
        start_time: datetime,
        end_time: datetime,
        duration_minutes: int
    ) -> List[TimeSlot]:
        """
        Find available time slots between events.
        
        Args:
            events: List of calendar events
            start_time: Requested start time
            end_time: Requested end time
            duration_minutes: Required duration in minutes
            
        Returns:
            List of available time slots
        """
        available_slots = []
        
        # Sort events by start time
        sorted_events = sorted(
            events,
            key=lambda e: datetime.fromisoformat(e['start'].get('dateTime', e['start'].get('date')))
        )
        
        # Current time pointer
        current_time = start_time
        
        for event in sorted_events:
            event_start = datetime.fromisoformat(
                event['start'].get('dateTime', event['start'].get('date'))
            )
            event_end = datetime.fromisoformat(
                event['end'].get('dateTime', event['end'].get('date'))
            )
            
            # Check if there's enough time before this event
            if current_time + timedelta(minutes=duration_minutes) <= event_start:
                available_slots.append(TimeSlot(
                    start=current_time,
                    end=current_time + timedelta(minutes=duration_minutes)
                ))
            
            # Move current time past this event
            current_time = max(current_time, event_end)
        
        # Check if there's time after the last event
        if current_time + timedelta(minutes=duration_minutes) <= end_time:
            available_slots.append(TimeSlot(
                start=current_time,
                end=current_time + timedelta(minutes=duration_minutes)
            ))
        
        return available_slots
    
    def book_meeting(self, request: MeetingRequest) -> MeetingResult:
        """
        Book a meeting in the calendar.
        
        Args:
            request: MeetingRequest with meeting details
            
        Returns:
            MeetingResult with confirmation
            
        Raises:
            CalendarIntegrationError: If API call fails
        """
        try:
            service = self._get_service()
            
            # Create event body
            event = {
                'summary': request.title,
                'start': {
                    'dateTime': request.start_time.isoformat() + 'Z',
                    'timeZone': self.default_timezone,
                },
                'end': {
                    'dateTime': (request.start_time + timedelta(minutes=request.duration_minutes)).isoformat() + 'Z',
                    'timeZone': self.default_timezone,
                },
                'attendees': [{'email': email} for email in request.attendees],
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': 10},
                        {'method': 'popup', 'minutes': 5},
                    ],
                },
            }
            
            # Insert the event
            created_event = service.events().insert(
                calendarId='primary',
                body=event
            ).execute()
            
            return MeetingResult(
                success=True,
                meeting_id=created_event.get('id', ''),
                confirmation_message=f"Meeting '{request.title}' scheduled successfully."
            )
            
        except HttpError as e:
            raise CalendarIntegrationError(
                f"Google Calendar API error: {e.resp.status} - {e.reason}"
            ) from e
        except Exception as e:
            raise CalendarIntegrationError(f"Failed to book meeting: {str(e)}") from e
    
    def set_reminder(self, reminder: Reminder) -> bool:
        """
        Set a reminder in the calendar.
        
        Args:
            reminder: Reminder to create
            
        Returns:
            True if successful
            
        Raises:
            CalendarIntegrationError: If API call fails
        """
        try:
            service = self._get_service()
            
            # Create reminder event (use a special summary to identify it as a reminder)
            event = {
                'summary': f"Reminder: {reminder.title}",
                'start': {
                    'dateTime': reminder.reminder_time.isoformat() + 'Z',
                    'timeZone': self.default_timezone,
                },
                'end': {
                    'dateTime': (reminder.reminder_time + timedelta(minutes=15)).isoformat() + 'Z',
                    'timeZone': self.default_timezone,
                },
                'attendees': [{'email': reminder.user_email}],
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'email', 'minutes': 0},  # Email at reminder time
                        {'method': 'popup', 'minutes': 0},  # Popup at reminder time
                    ],
                },
            }
            
            if reminder.description:
                event['description'] = reminder.description
            
            # Insert the event
            service.events().insert(
                calendarId='primary',
                body=event
            ).execute()
            
            return True
            
        except HttpError as e:
            raise CalendarIntegrationError(
                f"Google Calendar API error: {e.resp.status} - {e.reason}"
            ) from e
        except Exception as e:
            raise CalendarIntegrationError(f"Failed to set reminder: {str(e)}") from e
    
    def _parse_natural_language_time(self, time_expr: str) -> Optional[datetime]:
        """
        Parse natural language time expressions.
        
        Args:
            time_expr: Time expression (e.g., "tomorrow at 3pm", "next Monday")
            
        Returns:
            Parsed datetime or None if parsing fails
        """
        try:
            # Use dateparser for natural language parsing
            parsed = dateparser.parse(
                time_expr,
                settings={
                    'PREFER_DATES_FROM': 'future',
                    'TIMEZONE': self.default_timezone,
                    'RETURN_AS_TIMEZONE_AWARE': True,
                    'DATE_ORDER': 'MDY'
                }
            )
            
            if parsed:
                # Convert to naive datetime for consistency
                return parsed.replace(tzinfo=None)
            
            return None
            
        except Exception:
            return None
    
    def parse_time_expression(self, time_expr: str) -> Optional[datetime]:
        """
        Parse natural language time expressions with fallbacks.
        
        Args:
            time_expr: Time expression to parse
            
        Returns:
            Parsed datetime or None if parsing fails
        """
        # Try dateparser first
        parsed = self._parse_natural_language_time(time_expr)
        if parsed:
            return parsed
        
        # Try common patterns
        patterns = [
            # "tomorrow at 3pm"
            r'tomorrow\s+at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?',
            # "next Monday at 10am"
            r'next\s+(\w+)\s+at\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?',
            # "in 2 hours"
            r'in\s+(\d+)\s*(hours?|minutes?|days?)',
            # "3pm tomorrow"
            r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\s+tomorrow',
        ]
        
        time_expr_lower = time_expr.lower()
        
        for pattern in patterns:
            match = re.search(pattern, time_expr_lower, re.IGNORECASE)
            if match:
                groups = match.groups()
                
                if 'tomorrow' in time_expr_lower or 'next' in time_expr_lower:
                    # Parse day of week
                    if len(groups) >= 1 and groups[0] in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']:
                        days_until = self._days_until_day(groups[0])
                        target_date = datetime.now() + timedelta(days=days_until)
                        
                        hour = int(groups[1]) if len(groups) > 1 and groups[1] else 12
                        minute = int(groups[2]) if len(groups) > 2 and groups[2] else 0
                        ampm = groups[3] if len(groups) > 3 and groups[3] else 'am'
                        
                        if ampm.lower() == 'pm' and hour != 12:
                            hour += 12
                        elif ampm.lower() == 'am' and hour == 12:
                            hour = 0
                        
                        return target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
                
                elif 'in' in time_expr_lower:
                    # Parse relative time
                    value = int(groups[0])
                    unit = groups[1] if len(groups) > 1 else 'hours'
                    
                    if 'minute' in unit:
                        return datetime.now() + timedelta(minutes=value)
                    elif 'day' in unit:
                        return datetime.now() + timedelta(days=value)
                    else:  # hours
                        return datetime.now() + timedelta(hours=value)
        
        return None
    
    def _days_until_day(self, day_name: str) -> int:
        """
        Calculate days until a specific day of the week.
        
        Args:
            day_name: Day of week name (e.g., "monday")
            
        Returns:
            Number of days until that day
        """
        days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        today = datetime.now().weekday()
        target_day = days.index(day_name.lower())
        
        days_until = (target_day - today) % 7
        if days_until == 0:
            days_until = 7  # Next week
        
        return days_until
    
    def get_available_integrations(self) -> List[str]:
        """
        Get list of available calendar integrations.
        
        Returns:
            List of integration names
        """
        integrations = []
        
        if self.api_key:
            integrations.append("Google Calendar")
        
        return integrations
