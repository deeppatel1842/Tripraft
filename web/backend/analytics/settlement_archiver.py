"""
Settlement Archiver
===================
Archives old settlements and generates PDF reports.

FEATURES:
- Archive settlements older than 1 month
- Generate PDF summary with transaction details
- Send PDF via email to all group members
- Clean up archived settlements from active database
- Schedule automatic monthly archiving

Author: Production Team
Date: November 18, 2025
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import json
from io import BytesIO

try:
    from firebase_admin import firestore, storage
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
except ImportError:
    firestore = None
    storage = None
    SimpleDocTemplate = None


@dataclass
class SettlementSummary:
    """Settlement summary for PDF generation"""
    settlement_id: str
    group_id: str
    group_name: str
    payer_name: str
    payee_name: str
    amount: float
    currency: str
    settled_at: datetime
    description: Optional[str] = None
    
    # Related expenses
    related_expenses: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.related_expenses is None:
            self.related_expenses = []


class SettlementArchiver:
    """Manages settlement archiving and PDF generation"""
    
    def __init__(self, db=None, bucket=None):
        """
        Initialize settlement archiver
        
        Args:
            db: Firestore database instance
            bucket: Firebase Storage bucket
        """
        self.db = db
        self.bucket = bucket
        self.settlements_collection = "settlements"
        self.archived_settlements_collection = "archived_settlements"
        self.groups_collection = "groups"
        self.expenses_collection = "expenses"
        self.archive_age_days = 30  # Archive settlements older than 30 days
    
    # ==================== ARCHIVING ====================
    
    def find_settlements_to_archive(self) -> List[Dict[str, Any]]:
        """
        Find settlements that should be archived
        
        Returns:
            List of settlement documents
        """
        if not self.db:
            return []
        
        cutoff_date = datetime.utcnow() - timedelta(days=self.archive_age_days)
        
        try:
            settlements_ref = self.db.collection(self.settlements_collection)
            old_settlements = settlements_ref.where(
                "settled_at", "<", cutoff_date
            ).where(
                "status", "==", "completed"
            ).stream()
            
            return [
                {"id": doc.id, **doc.to_dict()}
                for doc in old_settlements
            ]
        
        except Exception as e:
            print(f"Error finding settlements to archive: {e}")
            return []
    
    def archive_settlement(
        self,
        settlement_id: str,
        settlement_data: Dict[str, Any]
    ) -> bool:
        """
        Archive a single settlement
        
        Args:
            settlement_id: Settlement ID
            settlement_data: Settlement data
            
        Returns:
            bool: Success status
        """
        if not self.db:
            return False
        
        try:
            # Add to archived collection
            archived_data = {
                **settlement_data,
                "archived_at": datetime.utcnow(),
                "original_id": settlement_id
            }
            
            self.db.collection(self.archived_settlements_collection).add(archived_data)
            
            # Delete from active collection
            self.db.collection(self.settlements_collection).document(settlement_id).delete()
            
            print(f"Archived settlement {settlement_id}")
            return True
        
        except Exception as e:
            print(f"Error archiving settlement {settlement_id}: {e}")
            return False
    
    def archive_all_old_settlements(self) -> int:
        """
        Archive all settlements older than cutoff date
        
        Returns:
            int: Number of settlements archived
        """
        settlements = self.find_settlements_to_archive()
        archived_count = 0
        
        for settlement in settlements:
            settlement_id = settlement.pop("id")
            if self.archive_settlement(settlement_id, settlement):
                archived_count += 1
        
        return archived_count
    
    # ==================== PDF GENERATION ====================
    
    def generate_settlement_pdf(
        self,
        group_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> Optional[BytesIO]:
        """
        Generate PDF report for settlements in a group
        
        Args:
            group_id: Group ID
            start_date: Start date for report
            end_date: End date for report
            
        Returns:
            BytesIO: PDF file buffer or None
        """
        if not self.db or not SimpleDocTemplate:
            return None
        
        try:
            # Get group details
            group_ref = self.db.collection(self.groups_collection).document(group_id)
            group_doc = group_ref.get()
            
            if not group_doc.exists:
                return None
            
            group_data = group_doc.to_dict()
            group_name = group_data.get("name", "Unknown Group")
            
            # Get settlements
            settlements = self._get_settlements_for_period(
                group_id,
                start_date,
                end_date
            )
            
            if not settlements:
                return None
            
            # Create PDF
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=letter)
            story = []
            styles = getSampleStyleSheet()
            
            # Title
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                textColor=colors.HexColor('#1a73e8'),
                spaceAfter=30,
                alignment=TA_CENTER
            )
            
            title = Paragraph(f"Settlement Report: {group_name}", title_style)
            story.append(title)
            
            # Date range
            date_text = f"{start_date.strftime('%B %d, %Y')} - {end_date.strftime('%B %d, %Y')}"
            date_para = Paragraph(date_text, styles['Normal'])
            story.append(date_para)
            story.append(Spacer(1, 0.3 * inch))
            
            # Summary statistics
            total_settled = sum(s.amount for s in settlements)
            summary_data = [
                ["Total Settlements:", str(len(settlements))],
                ["Total Amount Settled:", f"${total_settled:.2f}"],
                ["Report Generated:", datetime.utcnow().strftime("%B %d, %Y %I:%M %p")]
            ]
            
            summary_table = Table(summary_data, colWidths=[3 * inch, 3 * inch])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 12),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            
            story.append(summary_table)
            story.append(Spacer(1, 0.5 * inch))
            
            # Settlement details
            story.append(Paragraph("Settlement Details", styles['Heading2']))
            story.append(Spacer(1, 0.2 * inch))
            
            for settlement in settlements:
                self._add_settlement_to_pdf(story, settlement, styles)
            
            # Build PDF
            doc.build(story)
            buffer.seek(0)
            
            return buffer
        
        except Exception as e:
            print(f"Error generating PDF: {e}")
            return None
    
    def _get_settlements_for_period(
        self,
        group_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[SettlementSummary]:
        """Get settlements for a specific period"""
        if not self.db:
            return []
        
        try:
            # Query both active and archived settlements
            all_settlements = []
            
            for collection in [self.settlements_collection, self.archived_settlements_collection]:
                settlements_ref = self.db.collection(collection)
                docs = settlements_ref.where(
                    "group_id", "==", group_id
                ).where(
                    "settled_at", ">=", start_date
                ).where(
                    "settled_at", "<=", end_date
                ).stream()
                
                for doc in docs:
                    data = doc.to_dict()
                    all_settlements.append(SettlementSummary(
                        settlement_id=doc.id,
                        group_id=group_id,
                        group_name=data.get("group_name", "Unknown"),
                        payer_name=data.get("payer_name", "Unknown"),
                        payee_name=data.get("payee_name", "Unknown"),
                        amount=data.get("amount", 0),
                        currency=data.get("currency", "USD"),
                        settled_at=data.get("settled_at"),
                        description=data.get("description")
                    ))
            
            return sorted(all_settlements, key=lambda x: x.settled_at)
        
        except Exception as e:
            print(f"Error getting settlements: {e}")
            return []
    
    def _add_settlement_to_pdf(
        self,
        story: List,
        settlement: SettlementSummary,
        styles
    ):
        """Add a settlement entry to PDF"""
        # Settlement header
        header_text = f"{settlement.payer_name} paid {settlement.payee_name}"
        story.append(Paragraph(header_text, styles['Heading3']))
        
        # Settlement details
        details_data = [
            ["Amount:", f"${settlement.amount:.2f} {settlement.currency}"],
            ["Date:", settlement.settled_at.strftime("%B %d, %Y")],
        ]
        
        if settlement.description:
            details_data.append(["Description:", settlement.description])
        
        details_table = Table(details_data, colWidths=[1.5 * inch, 4.5 * inch])
        details_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        story.append(details_table)
        story.append(Spacer(1, 0.3 * inch))
    
    # ==================== EMAIL & STORAGE ====================
    
    def save_pdf_to_storage(
        self,
        pdf_buffer: BytesIO,
        group_id: str,
        filename: str
    ) -> Optional[str]:
        """
        Save PDF to Firebase Storage
        
        Args:
            pdf_buffer: PDF file buffer
            group_id: Group ID
            filename: File name
            
        Returns:
            str: Public URL or None
        """
        if not self.bucket:
            return None
        
        try:
            blob = self.bucket.blob(f"settlement_reports/{group_id}/{filename}")
            blob.upload_from_string(
                pdf_buffer.read(),
                content_type='application/pdf'
            )
            
            # Make publicly accessible
            blob.make_public()
            
            return blob.public_url
        
        except Exception as e:
            print(f"Error saving PDF to storage: {e}")
            return None
    
    def send_settlement_report_email(
        self,
        group_id: str,
        pdf_url: str,
        member_emails: List[str]
    ) -> bool:
        """
        Send settlement report email to group members
        
        Args:
            group_id: Group ID
            pdf_url: URL to PDF report
            member_emails: List of member email addresses
            
        Returns:
            bool: Success status
        """
        try:
            from services.email_service import EmailService
            
            email_service = EmailService()
            
            subject = "Your Monthly Settlement Report"
            body = f"""
            <html>
            <body>
                <h2>Monthly Settlement Report</h2>
                <p>Hi there,</p>
                <p>Your monthly settlement report is ready. This report includes all settlements 
                completed in the past month.</p>
                <p><a href="{pdf_url}" style="background-color: #1a73e8; color: white; padding: 10px 20px; 
                text-decoration: none; border-radius: 5px;">Download Report (PDF)</a></p>
                <p>The report will be available for download for the next 30 days.</p>
                <p>Thank you for using our expense tracking service!</p>
            </body>
            </html>
            """
            
            for email in member_emails:
                email_service.send_email(
                    to_email=email,
                    subject=subject,
                    body=body
                )
            
            return True
        
        except Exception as e:
            print(f"Error sending settlement report email: {e}")
            return False
    
    # ==================== SCHEDULED TASKS ====================
    
    def monthly_archiving_job(self) -> Dict[str, Any]:
        """
        Monthly job to archive settlements and send reports
        
        Returns:
            Dict with job results
        """
        results = {
            "archived_count": 0,
            "reports_generated": 0,
            "errors": []
        }
        
        try:
            # Archive old settlements
            archived_count = self.archive_all_old_settlements()
            results["archived_count"] = archived_count
            
            # Get all groups with completed settlements from last month
            last_month_start = (datetime.utcnow() - timedelta(days=30)).replace(day=1, hour=0, minute=0, second=0)
            last_month_end = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0) - timedelta(seconds=1)
            
            # TODO: Get groups with settlements in this period
            # For each group, generate PDF and send email
            
            print(f"Monthly archiving completed: {archived_count} settlements archived")
        
        except Exception as e:
            results["errors"].append(str(e))
            print(f"Error in monthly archiving job: {e}")
        
        return results


# ==================== HELPER FUNCTIONS ====================

def generate_and_send_monthly_report(
    db,
    bucket,
    group_id: str,
    member_emails: List[str]
) -> bool:
    """
    Generate monthly settlement report and send to members
    
    Args:
        db: Firestore database
        bucket: Firebase Storage bucket
        group_id: Group ID
        member_emails: List of member emails
        
    Returns:
        bool: Success status
    """
    archiver = SettlementArchiver(db, bucket)
    
    # Calculate last month date range
    today = datetime.utcnow()
    first_day_this_month = today.replace(day=1, hour=0, minute=0, second=0)
    last_day_last_month = first_day_this_month - timedelta(seconds=1)
    first_day_last_month = last_day_last_month.replace(day=1, hour=0, minute=0, second=0)
    
    # Generate PDF
    pdf_buffer = archiver.generate_settlement_pdf(
        group_id,
        first_day_last_month,
        last_day_last_month
    )
    
    if not pdf_buffer:
        return False
    
    # Save to storage
    filename = f"settlement_report_{first_day_last_month.strftime('%Y_%m')}.pdf"
    pdf_url = archiver.save_pdf_to_storage(pdf_buffer, group_id, filename)
    
    if not pdf_url:
        return False
    
    # Send email
    return archiver.send_settlement_report_email(group_id, pdf_url, member_emails)
