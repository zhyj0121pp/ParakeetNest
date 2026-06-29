"""Calendar service boundary."""


class CalendarService:
    """Collect earnings, dividends, macro releases, and conference dates."""

    def fetch_events(self) -> tuple[dict[str, object], ...]:
        """Return placeholder calendar events."""
        return ()
