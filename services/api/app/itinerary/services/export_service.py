# Purpose: Export service for Group Planner. Generates PDF itinerary and iCal calendar files.
"""
Export service for Group Planner.
Generates PDF itinerary and iCal calendar files.
"""

import io
import logging
from datetime import datetime, timedelta, timezone

from icalendar import Calendar, Event as CalEvent
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.trips.models import (
    ChecklistItem,
    ItineraryDocument,
    Place,
    TravelGroup,
    TripMember,
)
from app.core.db.connection import get_db_session

logger = logging.getLogger(__name__)


class ExportService:

    @staticmethod
    def generate_pdf(group_id: str, user_id: str) -> tuple:
        """Generate a PDF itinerary for the group. Returns (success, bytes_or_error)."""
        try:
            with get_db_session() as session:
                group = session.get(TravelGroup, group_id)
                if not group or not group.is_active:
                    return False, {'error': 'Group not found'}
                if not ExportService._is_active_member(session, group_id, user_id):
                    return False, {'error': 'Not a member of this group'}

                places = (
                    session.query(Place)
                    .filter(Place.group_id == group_id, Place.is_deleted == False)
                    .order_by(Place.visit_date.asc().nullslast(), Place.name)
                    .all()
                )
                checklist = (
                    session.query(ChecklistItem)
                    .filter(ChecklistItem.group_id == group_id, ChecklistItem.is_deleted == False)
                    .order_by(ChecklistItem.created_at)
                    .all()
                )
                itinerary = (
                    session.query(ItineraryDocument)
                    .filter(ItineraryDocument.group_id == group_id)
                    .first()
                )

                buf = io.BytesIO()
                doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=20 * mm, bottomMargin=20 * mm)
                styles = getSampleStyleSheet()
                title_style = ParagraphStyle('TripTitle', parent=styles['Title'], fontSize=20, spaceAfter=6)
                h2 = ParagraphStyle('H2', parent=styles['Heading2'], fontSize=14, spaceBefore=12, spaceAfter=6)

                elements = []

                # Title
                elements.append(Paragraph(group.name or 'Trip Itinerary', title_style))
                if group.destination:
                    elements.append(Paragraph(f'Destination: {group.destination}', styles['Normal']))
                if group.start_date or group.end_date:
                    date_str = f'{group.start_date or "?"} to {group.end_date or "?"}'
                    elements.append(Paragraph(f'Dates: {date_str}', styles['Normal']))
                if group.group_code:
                    elements.append(Paragraph(f'Group Code: {group.group_code}', styles['Normal']))
                elements.append(Spacer(1, 8 * mm))

                # Places
                if places:
                    elements.append(Paragraph('Places to Visit', h2))
                    data = [['#', 'Name', 'Category', 'Visit Date', 'Rating']]
                    for i, p in enumerate(places, 1):
                        data.append([
                            str(i),
                            p.name or '',
                            p.category or '-',
                            str(p.visit_date) if p.visit_date else '-',
                            str(p.rating) if p.rating else '-',
                        ])
                    t = Table(data, colWidths=[20, 180, 80, 80, 50])
                    t.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563eb')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                        ('FONTSIZE', (0, 0), (-1, -1), 9),
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f4ff')]),
                    ]))
                    elements.append(t)
                    elements.append(Spacer(1, 6 * mm))

                # Checklist
                if checklist:
                    elements.append(Paragraph('Checklist', h2))
                    for item in checklist:
                        mark = '[x]' if item.completed else '[ ]'
                        elements.append(Paragraph(f'{mark} {item.item}', styles['Normal']))
                    elements.append(Spacer(1, 6 * mm))

                # Itinerary notes
                if itinerary and itinerary.content:
                    elements.append(Paragraph('Notes', h2))
                    # Treat content as plain text (may be JSON or markdown)
                    content = itinerary.content if isinstance(itinerary.content, str) else str(itinerary.content)
                    for line in content.split('\n')[:100]:  # cap at 100 lines
                        elements.append(Paragraph(line, styles['Normal']))

                doc.build(elements)
                buf.seek(0)
                return True, buf.getvalue()

        except Exception as e:
            logger.error(f'PDF generation error: {e}')
            return False, {'error': 'Failed to generate PDF'}

    @staticmethod
    def generate_ical(group_id: str, user_id: str) -> tuple:
        """Generate an iCal file for the group. Returns (success, bytes_or_error)."""
        try:
            with get_db_session() as session:
                group = session.get(TravelGroup, group_id)
                if not group or not group.is_active:
                    return False, {'error': 'Group not found'}
                if not ExportService._is_active_member(session, group_id, user_id):
                    return False, {'error': 'Not a member of this group'}

                cal = Calendar()
                cal.add('prodid', '-//TripRaft//Group Planner//EN')
                cal.add('version', '2.0')
                cal.add('x-wr-calname', group.name or 'Trip')

                # Trip date range as an all-day event
                if group.start_date and group.end_date:
                    trip_ev = CalEvent()
                    trip_ev.add('summary', f'Trip: {group.name}')
                    trip_ev.add('dtstart', group.start_date)
                    # RFC 5545 all-day DTEND is exclusive, so include the
                    # final planned day by ending on the following date.
                    trip_ev.add('dtend', group.end_date + timedelta(days=1))
                    trip_ev.add('description', group.description or '')
                    if group.destination:
                        trip_ev.add('location', group.destination)
                    trip_ev['uid'] = f'tripraft-group-{group_id}@tripraft.com'
                    cal.add_component(trip_ev)

                # Places with visit dates
                places = (
                    session.query(Place)
                    .filter(Place.group_id == group_id, Place.is_deleted == False, Place.visit_date.isnot(None))
                    .order_by(Place.visit_date)
                    .all()
                )
                for p in places:
                    ev = CalEvent()
                    ev.add('summary', f'Visit: {p.name}')
                    ev.add('dtstart', p.visit_date)
                    # A dated place visit is also an all-day event. An equal
                    # DTSTART/DTEND is zero-duration and many clients hide it.
                    ev.add('dtend', p.visit_date + timedelta(days=1))
                    if p.address:
                        ev.add('location', p.address)
                    if p.description:
                        ev.add('description', p.description)
                    ev['uid'] = f'tripraft-place-{p.id}@tripraft.com'
                    cal.add_component(ev)

                return True, cal.to_ical()

        except Exception as e:
            logger.error(f'iCal generation error: {e}')
            return False, {'error': 'Failed to generate calendar'}

    @staticmethod
    def _is_active_member(session, group_id: str, user_id: str) -> bool:
        """Exports contain private group data and require active membership."""
        return session.query(TripMember.id).filter(
            TripMember.group_id == group_id,
            TripMember.user_id == user_id,
            TripMember.is_active == True,
        ).first() is not None


export_service = ExportService()
