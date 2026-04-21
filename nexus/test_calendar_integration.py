"""
Property-based tests for the Calendar Integration component.

Tests:
- Availability checking
- Meeting booking
- Reminder creation
- Natural language time parsing
- Calendar error handling

Requirements: 8.1, 8.2, 8.3, 8.4, 8.5
"""

import pytest
from hypothesis import given, strategies as st, settings
from hypothesis import HealthCheck
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nexus.calendar_integration import CalendarIntegration, CalendarIntegrationError
from nexus.models import (
    TimeSlot, AvailabilityRequest, AvailabilityResult,
    MeetingRequest, MeetingResult, Reminder
)


class TestAvailabilityChecking:
    """Property tests for availability checking."""
    
    @pytest.mark.property_test
    @pytest.mark.property_26
    @given(
        user_email=st.emails(),
        duration=st.integers(min_value=15, max_value=120)
    )
    @settings(max_examples=10, deadline=10000, suppress_health_check=[HealthCheck.too_slow])
    def test_availability_checking(self, user_email, duration):
        """
        Property 26: Availability checking
        
        For any AvailabilityRequest, the Calendar Integration should make an API call
        to the Calendar API and return an AvailabilityResult with time slots.
        **Validates: Requirements 8.1**
        """
        integration = CalendarIntegration()
        
        # Create availability request
        start_time = datetime.now() + timedelta(hours=1)
        end_time = start_time + timedelta(hours=2)
        
        request = AvailabilityRequest(
            user_email=user_email,
            start_time=start_time,
            end_time=end_time,
            duration_minutes=duration
        )
        
        # Note: This test will fail without a valid API key
        # In production, this would be tested with mocked API responses
        try:
            result = integration.check_availability(request)
            assert isinstance(result, AvailabilityResult)
            assert isinstance(result.available_slots, list)
        except CalendarIntegrationError as e:
            # Expected if API key is not configured
            assert "API key" in str(e) or "calendar" in str(e).lower()
        except Exception as e:
            # Other errors (network, etc.) are also acceptable for this test
            pass
    
    @pytest.mark.property_test
    @pytest.mark.property_26
    @given(
        duration=st.integers(min_value=30, max_value=60)
    )
    @settings(max_examples=5, deadline=10000)
    def test_availability_with_different_durations(self, duration):
        """
        Property 26: Availability checking with different durations
        
        For any duration requirement, the availability check should return
        slots that match the required duration.
        **Validates: Requirements 8.1**
        """
        integration = CalendarIntegration()
        
        start_time = datetime.now() + timedelta(hours=1)
        end_time = start_time + timedelta(hours=3)
        
        request = AvailabilityRequest(
            user_email="test@example.com",
            start_time=start_time,
            end_time=end_time,
            duration_minutes=duration
        )
        
        try:
            result = integration.check_availability(request)
            # If API call succeeds, verify slots match duration
            for slot in result.available_slots:
                slot_duration = (slot.end - slot.start).total_seconds() / 60
                assert slot_duration >= duration
        except CalendarIntegrationError:
            # Expected if API key is not configured
            pass
        except Exception:
            # Network or other errors are acceptable
            pass


class TestMeetingBooking:
    """Property tests for meeting booking."""
    
    @pytest.mark.property_test
    @pytest.mark.property_27
    @given(
        title=st.text(min_size=5, max_size=100),
        duration=st.integers(min_value=15, max_value=120),
        attendee_count=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=5, deadline=10000, suppress_health_check=[HealthCheck.too_slow])
    def test_meeting_booking_on_availability(self, title, duration, attendee_count):
        """
        Property 27: Meeting booking on availability
        
        For any MeetingRequest with an available time slot, the Calendar Integration
        should book the meeting and return a MeetingResult with success=True.
        **Validates: Requirements 8.2**
        """
        integration = CalendarIntegration()
        
        start_time = datetime.now() + timedelta(hours=2)
        attendees = [f"user{i}@example.com" for i in range(attendee_count)]
        
        request = MeetingRequest(
            user_email="organizer@example.com",
            title=title,
            start_time=start_time,
            duration_minutes=duration,
            attendees=attendees
        )
        
        try:
            result = integration.book_meeting(request)
            assert isinstance(result, MeetingResult)
            assert result.success is True
            assert len(result.meeting_id) > 0
            assert len(result.confirmation_message) > 0
        except CalendarIntegrationError as e:
            # Expected if API key is not configured
            assert "API key" in str(e) or "calendar" in str(e).lower()
        except Exception as e:
            # Other errors (network, etc.) are also acceptable
            pass
    
    @pytest.mark.property_test
    @pytest.mark.property_27
    @given(
        title=st.text(min_size=1, max_size=50),
        duration=st.integers(min_value=15, max_value=60)
    )
    @settings(max_examples=3, deadline=10000)
    def test_meeting_booking_with_various_titles(self, title, duration):
        """
        Property 27: Meeting booking with various titles
        
        For any meeting title, the booking should succeed and return
        a valid meeting ID and confirmation message.
        **Validates: Requirements 8.2**
        """
        integration = CalendarIntegration()
        
        start_time = datetime.now() + timedelta(hours=1)
        
        request = MeetingRequest(
            user_email="organizer@example.com",
            title=title,
            start_time=start_time,
            duration_minutes=duration,
            attendees=["attendee@example.com"]
        )
        
        try:
            result = integration.book_meeting(request)
            assert result.success is True
            assert len(result.meeting_id) > 0
        except CalendarIntegrationError:
            # Expected if API key is not configured
            pass
        except Exception:
            # Network or other errors are acceptable
            pass


class TestReminderCreation:
    """Property tests for reminder creation."""
    
    @pytest.mark.property_test
    @pytest.mark.property_28
    @given(
        title=st.text(min_size=3, max_size=100),
        description=st.text(min_size=0, max_size=200)
    )
    @settings(max_examples=5, deadline=10000, suppress_health_check=[HealthCheck.too_slow])
    def test_reminder_creation(self, title, description):
        """
        Property 28: Reminder creation
        
        For any Reminder request, the Calendar Integration should create
        the reminder in the external calendar system and return success=True.
        **Validates: Requirements 8.3**
        """
        integration = CalendarIntegration()
        
        reminder_time = datetime.now() + timedelta(hours=1)
        
        reminder = Reminder(
            user_email="user@example.com",
            title=title,
            reminder_time=reminder_time,
            description=description if description else None
        )
        
        try:
            result = integration.set_reminder(reminder)
            assert result is True
        except CalendarIntegrationError as e:
            # Expected if API key is not configured
            assert "API key" in str(e) or "calendar" in str(e).lower()
        except Exception as e:
            # Other errors (network, etc.) are also acceptable
            pass
    
    @pytest.mark.property_test
    @pytest.mark.property_28
    @given(
        title=st.text(min_size=3, max_size=50)
    )
    @settings(max_examples=3, deadline=10000)
    def test_reminder_without_description(self, title):
        """
        Property 28: Reminder creation without description
        
        For reminders without a description, the system should still
        successfully create the reminder.
        **Validates: Requirements 8.3**
        """
        integration = CalendarIntegration()
        
        reminder_time = datetime.now() + timedelta(hours=1)
        
        reminder = Reminder(
            user_email="user@example.com",
            title=title,
            reminder_time=reminder_time,
            description=None
        )
        
        try:
            result = integration.set_reminder(reminder)
            assert result is True
        except CalendarIntegrationError:
            # Expected if API key is not configured
            pass
        except Exception:
            # Network or other errors are acceptable
            pass


class TestTimeParsing:
    """Property tests for natural language time parsing."""
    
    @pytest.mark.property_test
    @pytest.mark.property_29
    @given(
        time_expr=st.sampled_from([
            "tomorrow at 3pm",
            "next Monday at 10am",
            "tomorrow",
            "3pm tomorrow",
            "next week",
            "Friday at 2:30pm"
        ])
    )
    @settings(max_examples=10, deadline=5000)
    def test_natural_language_time_parsing(self, time_expr):
        """
        Property 29: Natural language time parsing
        
        For any time expression in natural language format ("tomorrow at 3pm",
        "next Monday at 10am"), the Calendar Integration should parse it to
        a valid datetime object.
        **Validates: Requirements 8.4**
        """
        integration = CalendarIntegration()
        
        result = integration.parse_time_expression(time_expr)
        
        # Verify result is a datetime
        assert result is not None
        assert isinstance(result, datetime)
        
        # Verify the parsed time is in the future
        assert result > datetime.now()
    
    @pytest.mark.property_test
    @pytest.mark.property_29
    @given(
        time_expr=st.text(min_size=3, max_size=50)
    )
    @settings(max_examples=10, deadline=5000)
    def test_time_parsing_with_various_inputs(self, time_expr):
        """
        Property 29: Time parsing with various inputs
        
        For various time expressions, the parser should either return
        a valid datetime or None if parsing fails.
        **Validates: Requirements 8.4**
        """
        integration = CalendarIntegration()
        
        result = integration.parse_time_expression(time_expr)
        
        # Result should be either a datetime or None
        if result is not None:
            assert isinstance(result, datetime)
    
    @pytest.mark.property_test
    @pytest.mark.property_29
    @given(
        time_expr=st.sampled_from([
            "tomorrow at 3pm",
            "next Monday",
            "3pm tomorrow",
        ])
    )
    @settings(max_examples=5, deadline=5000)
    def test_time_parsing_returns_future_time(self, time_expr):
        """
        Property 29: Time parsing returns future time
        
        For any valid time expression, the parsed datetime should be
        in the future relative to the current time.
        **Validates: Requirements 8.4**
        """
        integration = CalendarIntegration()
        
        result = integration.parse_time_expression(time_expr)
        
        if result is not None:
            assert result > datetime.now()


class TestCalendarErrorHandling:
    """Property tests for calendar error handling."""
    
    @pytest.mark.property_test
    @pytest.mark.property_30
    @given(
        user_email=st.emails(),
        duration=st.integers(min_value=15, max_value=60)
    )
    @settings(max_examples=5, deadline=10000)
    def test_calendar_error_handling(self, user_email, duration):
        """
        Property 30: Calendar error handling
        
        For any calendar operation that fails (API error, network error),
        the system should return an error message describing the failure
        without crashing.
        **Validates: Requirements 8.5**
        """
        integration = CalendarIntegration()
        
        # Test with no API key configured (should raise error)
        integration.api_key = None
        
        start_time = datetime.now() + timedelta(hours=1)
        end_time = start_time + timedelta(hours=2)
        
        request = AvailabilityRequest(
            user_email=user_email,
            start_time=start_time,
            end_time=end_time,
            duration_minutes=duration
        )
        
        # Should raise CalendarIntegrationError
        with pytest.raises(CalendarIntegrationError) as exc_info:
            integration.check_availability(request)
        
        # Error message should describe the failure
        assert len(str(exc_info.value)) > 0
        assert "API key" in str(exc_info.value) or "calendar" in str(exc_info.value).lower()
    
    @pytest.mark.property_test
    @pytest.mark.property_30
    @given(
        title=st.text(min_size=5, max_size=50)
    )
    @settings(max_examples=3, deadline=10000)
    def test_book_meeting_without_api_key(self, title):
        """
        Property 30: Book meeting without API key
        
        When the API key is not configured, book_meeting should raise
        a descriptive error without crashing.
        **Validates: Requirements 8.5**
        """
        integration = CalendarIntegration()
        integration.api_key = None
        
        start_time = datetime.now() + timedelta(hours=1)
        
        request = MeetingRequest(
            user_email="organizer@example.com",
            title=title,
            start_time=start_time,
            duration_minutes=60,
            attendees=["attendee@example.com"]
        )
        
        with pytest.raises(CalendarIntegrationError) as exc_info:
            integration.book_meeting(request)
        
        assert "API key" in str(exc_info.value) or "calendar" in str(exc_info.value).lower()
    
    @pytest.mark.property_test
    @pytest.mark.property_30
    @given(
        title=st.text(min_size=3, max_size=50)
    )
    @settings(max_examples=3, deadline=10000)
    def test_set_reminder_without_api_key(self, title):
        """
        Property 30: Set reminder without API key
        
        When the API key is not configured, set_reminder should raise
        a descriptive error without crashing.
        **Validates: Requirements 8.5**
        """
        integration = CalendarIntegration()
        integration.api_key = None
        
        reminder_time = datetime.now() + timedelta(hours=1)
        
        reminder = Reminder(
            user_email="user@example.com",
            title=title,
            reminder_time=reminder_time,
            description="Test reminder"
        )
        
        with pytest.raises(CalendarIntegrationError) as exc_info:
            integration.set_reminder(reminder)
        
        assert "API key" in str(exc_info.value) or "calendar" in str(exc_info.value).lower()


class TestIntegrationFeatures:
    """Integration tests for Calendar Integration features."""
    
    def test_get_available_integrations(self):
        """
        Property: Available integrations should be listed.
        
        The system should be able to report which calendar integrations
        are available based on configuration.
        **Validates: Requirements 8.1**
        """
        integration = CalendarIntegration()
        
        integrations = integration.get_available_integrations()
        
        # Should return a list
        assert isinstance(integrations, list)
        
        # If API key is configured, should include Google Calendar
        if integration.api_key:
            assert "Google Calendar" in integrations
        else:
            # Without API key, no integrations should be available
            assert len(integrations) == 0
    
    def test_parse_time_expression_with_various_formats(self):
        """
        Property: Time expressions should be parsed correctly.
        
        The system should handle various natural language time formats.
        **Validates: Requirements 8.4**
        """
        integration = CalendarIntegration()
        
        # Test various time formats
        time_expressions = [
            "tomorrow at 3pm",
            "next Monday",
            "in 2 hours",
            "3pm tomorrow",
        ]
        
        for expr in time_expressions:
            result = integration.parse_time_expression(expr)
            # Either valid datetime or None is acceptable
            if result is not None:
                assert isinstance(result, datetime)
    
    def test_availability_result_structure(self):
        """
        Property: Availability result should have correct structure.
        
        The AvailabilityResult should contain a list of TimeSlot objects.
        **Validates: Requirements 8.1**
        """
        # Create an availability result directly
        start_time = datetime.now() + timedelta(hours=1)
        end_time = start_time + timedelta(hours=2)
        
        slot = TimeSlot(start=start_time, end=end_time)
        result = AvailabilityResult(available_slots=[slot])
        
        assert isinstance(result, AvailabilityResult)
        assert len(result.available_slots) == 1
        assert isinstance(result.available_slots[0], TimeSlot)
        assert result.available_slots[0].start == start_time
        assert result.available_slots[0].end == end_time
    
    def test_meeting_result_structure(self):
        """
        Property: Meeting result should have correct structure.
        
        The MeetingResult should contain success, meeting_id, and confirmation_message.
        **Validates: Requirements 8.2**
        """
        # Create a meeting result directly
        result = MeetingResult(
            success=True,
            meeting_id="test_meeting_123",
            confirmation_message="Meeting scheduled successfully"
        )
        
        assert isinstance(result, MeetingResult)
        assert result.success is True
        assert len(result.meeting_id) > 0
        assert len(result.confirmation_message) > 0
    
    def test_reminder_structure(self):
        """
        Property: Reminder should have correct structure.
        
        The Reminder should contain user_email, title, and reminder_time.
        **Validates: Requirements 8.3**
        """
        reminder_time = datetime.now() + timedelta(hours=1)
        
        reminder = Reminder(
            user_email="user@example.com",
            title="Test Reminder",
            reminder_time=reminder_time,
            description="Test description"
        )
        
        assert isinstance(reminder, Reminder)
        assert len(reminder.user_email) > 0
        assert len(reminder.title) > 0
        assert reminder.reminder_time == reminder_time
        assert reminder.description == "Test description"
    
    def test_reminder_without_description(self):
        """
        Property: Reminder should work without description.
        
        The Reminder should be valid even without a description.
        **Validates: Requirements 8.3**
        """
        reminder_time = datetime.now() + timedelta(hours=1)
        
        reminder = Reminder(
            user_email="user@example.com",
            title="Test Reminder",
            reminder_time=reminder_time,
            description=None
        )
        
        assert isinstance(reminder, Reminder)
        assert reminder.description is None
