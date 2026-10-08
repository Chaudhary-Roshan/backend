from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
import uuid

class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Super Admin'),
        ('faculty', 'Faculty Advisor'),
        ('president', 'Society President'),
        ('student', 'Student'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    society = models.ForeignKey('Society', on_delete=models.SET_NULL, null=True, blank=True, related_name='members')
    
    # Extended Student Profile fields
    roll_number = models.CharField(max_length=50, blank=True, default='')
    father_name = models.CharField(max_length=100, blank=True, default='')
    cnic = models.CharField(max_length=30, blank=True, default='')
    program = models.CharField(max_length=100, blank=True, default='')
    department = models.CharField(max_length=100, blank=True, default='')
    batch = models.CharField(max_length=50, blank=True, default='')
    semester = models.CharField(max_length=50, blank=True, default='')
    faculty_name = models.CharField(max_length=100, blank=True, default='')
    phone_number = models.CharField(max_length=30, blank=True, default='')
    gender = models.CharField(max_length=20, blank=True, default='')
    date_of_birth = models.DateField(null=True, blank=True)
    profile_photo_url = models.TextField(blank=True, default='')
    student_designation = models.CharField(max_length=100, blank=True, default='')
    password_reset_version = models.PositiveIntegerField(default=0)
    avatar_url = models.TextField(blank=True, default='')
    university_email = models.CharField(max_length=255, blank=True, default='')
    is_email_verified = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    otp_code = models.CharField(max_length=10, blank=True, default='')
    otp_created_at = models.DateTimeField(null=True, blank=True)
    otp_attempts = models.IntegerField(default=0)
    is_cabinet_member = models.BooleanField(default=False)
    cabinet_role = models.CharField(max_length=100, blank=True, default='')
    cabinet_society_name = models.CharField(max_length=255, blank=True, default='')

    def __str__(self):
        return f"{self.username} - {self.role}"

class Society(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    cover_image = models.TextField(blank=True, default='')
    logo = models.TextField(blank=True, default='')
    logo_version = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    vision = models.TextField(blank=True, default='')
    mission = models.TextField(blank=True, default='')
    contact_email = models.EmailField(blank=True, default='')
    contact_phone = models.CharField(max_length=30, blank=True, default='')
    social_links = models.JSONField(default=dict, blank=True)
    advisor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='advised_societies')
    president = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='presided_societies')
    bank_name = models.CharField(max_length=255, default='National University Bank')
    bank_account_title = models.CharField(max_length=255, default='DSMS Campus Activity Fund')
    bank_account_number = models.CharField(max_length=100, default='PK82UNIV000192837465')
    payment_instructions = models.TextField(default='Please transfer the registration fee to the society bank account or scan the payment QR code. Enter your Transaction Reference ID after payment.', blank=True)
    payment_qr = models.TextField(blank=True, default='')
    bank_version = models.IntegerField(default=1)
    bank_history = models.JSONField(default=list, blank=True)
    # Membership settings
    membership_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    is_membership_open = models.BooleanField(default=False)
    membership_description = models.TextField(blank=True, default='Join our society to access exclusive events, workshops, and networking opportunities.')

    def __str__(self):
        return self.name

class Venue(models.Model):
    name = models.CharField(max_length=255)
    capacity = models.IntegerField(default=50)

    def __str__(self):
        return self.name

class Event(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    society = models.ForeignKey(Society, on_delete=models.CASCADE, related_name='events')
    title = models.CharField(max_length=255)
    description = models.TextField()
    date = models.DateTimeField()
    is_paid = models.BooleanField(default=False)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    venue = models.ForeignKey(Venue, on_delete=models.SET_NULL, null=True, blank=True)
    venue_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # Detailed Event Proposal & Multi-Tier Physical Sign-Off Dossier
    event_type = models.CharField(max_length=100, default='Workshop & Seminar')
    tagline = models.CharField(max_length=255, blank=True, default='')
    venue_name = models.CharField(max_length=255, blank=True, default='Campus Main Auditorium')
    expected_attendees = models.IntegerField(default=100)
    agenda = models.TextField(blank=True, default='')
    budget_estimate = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    chief_guest = models.CharField(max_length=255, blank=True, default='')
    equipment_needed = models.TextField(blank=True, default='')
    proposal_doc_number = models.CharField(max_length=50, blank=True, default='')
    signed_proposal_doc = models.TextField(blank=True, default='')
    payment_qr = models.TextField(blank=True, default='')
    advisor_approved = models.BooleanField(default=False)
    chairman_approved = models.BooleanField(default=False)
    hod_approved = models.BooleanField(default=False)
    verification_notes = models.TextField(blank=True, default='')
    image = models.TextField(blank=True, default='')  # Event cover / advertisement poster image
    is_published = models.BooleanField(default=False)
    gallery_images = models.JSONField(default=list, blank=True)

    @property
    def poster_image_url(self):
        return self.image

    @poster_image_url.setter
    def poster_image_url(self, value):
        self.image = value

    @property
    def ticket_price(self):
        return self.price

    @ticket_price.setter
    def ticket_price(self, value):
        self.price = value

    def __str__(self):
        return self.title

class Membership(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending Approval'),
        ('active', 'Active Member'),
        ('rejected', 'Rejected'),
        ('suspended', 'Suspended'),
    )
    society = models.ForeignKey(Society, on_delete=models.CASCADE, related_name='memberships')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='memberships')
    joined_date = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=False)  # True only when status='active'
    card_qr_code = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    public_token_hash = models.CharField(max_length=64, blank=True, null=True, unique=True)
    membership_id = models.CharField(max_length=50, blank=True, default='')
    role_title = models.CharField(max_length=100, default='General Member')
    issued_by_role = models.CharField(max_length=50, default='President')
    issued_by_name = models.CharField(max_length=150, blank=True, default='')
    approved_by_advisor = models.CharField(max_length=150, blank=True, default='')
    valid_until = models.CharField(max_length=50, default='Academic Session 2026-2027')
    issued_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='revoked_memberships')
    # New fields for payment-based membership
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_proof = models.TextField(blank=True, default='')  # URL to uploaded payment screenshot
    transaction_id = models.CharField(max_length=255, blank=True, default='')
    fee_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    applied_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, default='')
    # Designations
    designation = models.CharField(max_length=100, blank=True, default='')

    def __str__(self):
        return f"{self.student.username} - {self.society.name} ({self.status})"

class Message(models.Model):
    society = models.ForeignKey(Society, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Msg by {self.sender.username} in {self.society.name}"

class EventFeedback(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='feedbacks')
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(default=5)
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback for {self.event.title}"

class EventResource(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='resources')
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='resources/')

    def __str__(self):
        return self.title

class Registration(models.Model):
    PAYMENT_CHOICES = (
        ('pending', 'Pending Review'),
        ('held', 'Seat Held (24h Window)'),
        ('verified', 'Verified & Confirmed'),
        ('rejected', 'Receipt Rejected'),
        ('expired', 'Hold Expired'),
    )
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='registrations')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='registrations')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default='pending')
    ticket_qr_code = models.CharField(max_length=255, blank=True, null=True)
    public_token_hash = models.CharField(max_length=64, blank=True, null=True, unique=True)
    ticket_number = models.CharField(max_length=80, blank=True, default='')
    ticket_status = models.CharField(max_length=20, default='issued')
    attendance_status = models.BooleanField(default=False)
    transaction_id = models.CharField(max_length=255, blank=True, null=True)
    receipt_details = models.TextField(blank=True, null=True)
    receipt_file = models.TextField(blank=True, default='')
    held_until = models.DateTimeField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_registrations')
    rejection_reason = models.TextField(blank=True, default='')
    bank_version = models.IntegerField(default=1)
    bank_snapshot = models.JSONField(default=dict, blank=True)
    idempotency_key = models.CharField(max_length=128, blank=True, default='')
    checked_in_at = models.DateTimeField(null=True, blank=True)
    checked_in_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='checked_in_registrations')
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    def __str__(self):
        return f"{self.student.username} - {self.event.title} ({self.payment_status})"


class PasswordResetToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='password_reset_tokens')
    token_hash = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    requested_ip = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class AuditLog(models.Model):
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_events')
    action = models.CharField(max_length=100)
    target_type = models.CharField(max_length=100, blank=True, default='')
    target_id = models.CharField(max_length=100, blank=True, default='')
    metadata = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Recruitment(models.Model):
    STATUS_CHOICES = (
        ('open', 'Open'),
        ('closed', 'Closed'),
    )
    society = models.ForeignKey(Society, on_delete=models.CASCADE, related_name='recruitments')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    form_fields = models.JSONField(default=list)  # Legacy: general questions
    positions = models.JSONField(default=list)  # [{title, description, questions: [{label, type, required}]}]
    deadline = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    max_applicants = models.IntegerField(default=0, help_text='0 = unlimited')

    def __str__(self):
        return self.title

import uuid

class Certificate(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='certificates')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='certificates')
    certificate_url = models.URLField(max_length=500)
    issued_at = models.DateTimeField(auto_now_add=True)
    verification_code = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    template = models.ForeignKey('CertificateTemplate', on_delete=models.SET_NULL, null=True, blank=True, related_name='issued_certificates')

    def __str__(self):
        return f"Certificate for {self.student.username} - {self.event.title}"

class Gallery(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    society = models.ForeignKey(Society, on_delete=models.CASCADE, related_name='galleries')
    event = models.ForeignKey(Event, on_delete=models.SET_NULL, null=True, blank=True, related_name='galleries')
    title = models.CharField(max_length=255, blank=True, default='')
    album_name = models.CharField(max_length=255, blank=True, default='')
    image = models.ImageField(upload_to='galleries/', null=True, blank=True)
    image_url = models.URLField(max_length=500, blank=True, null=True) # Keep for backward compatibility with seeded data
    uploaded_at = models.DateTimeField(default=timezone.now)
    is_public = models.BooleanField(default=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='approved')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_galleries')

    def __str__(self):
        return f"Gallery Image ({self.album_name or self.title}) for {self.society.name}"

class News(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    title = models.CharField(max_length=255)
    content = models.TextField()
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    society = models.ForeignKey(Society, on_delete=models.SET_NULL, null=True, blank=True, related_name='news')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='approved')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_news')

    def __str__(self):
        return self.title

class Budget(models.Model):
    society = models.ForeignKey(Society, on_delete=models.CASCADE, related_name='budgets')
    event = models.ForeignKey(Event, on_delete=models.SET_NULL, null=True, blank=True, related_name='budgets')
    title = models.CharField(max_length=255)
    category = models.CharField(max_length=100, default='Logistics & Operations')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    is_expense = models.BooleanField(default=True)
    description = models.TextField(blank=True)
    receipt_doc = models.TextField(blank=True, default='')
    payment_method = models.CharField(max_length=50, default='Bank Transfer')
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.society.name} - {self.title} - PKR {self.amount}"

class Sponsorship(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='sponsorships', null=True, blank=True)
    society = models.ForeignKey(Society, on_delete=models.CASCADE, related_name='sponsorships')
    sponsor_name = models.CharField(max_length=255)
    sponsor_tier = models.CharField(max_length=50, default='Gold Sponsor')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    details = models.TextField(blank=True)
    status = models.CharField(max_length=30, default='Received')

    def __str__(self):
        return f"{self.sponsor_name} - PKR {self.amount}"

class VolunteerHour(models.Model):
    STATUS_CHOICES = (
        ('assigned', 'Assigned'),
        ('accepted', 'Accepted'),
        ('completed', 'Completed'),
        ('verified', 'Verified'),
    )
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='volunteer_hours')
    society = models.ForeignKey('Society', on_delete=models.CASCADE, related_name='volunteer_hours', null=True, blank=True)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, null=True, blank=True)
    role = models.CharField(max_length=150, default='General Volunteer')  # e.g., 'Decorator', 'Registration Desk'
    description = models.TextField(blank=True, default='')
    hours = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='assigned')
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_hours')
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    def __str__(self):
        return f"{self.student.username} - {self.role} - {self.hours} hrs"

class Equipment(models.Model):
    name = models.CharField(max_length=255)
    total_quantity = models.IntegerField(default=1)
    
    def __str__(self):
        return self.name

class EventEquipmentRequest(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='equipment_requests')
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    def __str__(self):
        return f"{self.quantity}x {self.equipment.name} for {self.event.title}"

class Complaint(models.Model):
    STATUS_CHOICES = (
        ('open', 'Open'),
        ('investigating', 'Investigating'),
        ('resolved', 'Resolved'),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    society = models.ForeignKey(Society, on_delete=models.CASCADE, null=True, blank=True)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, null=True, blank=True)
    subject = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Complaint by {self.user.username} - {self.subject}"

class Notification(models.Model):
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification for {self.recipient.username}"

class RecruitmentApplication(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('shortlisted', 'Shortlisted'),
        ('interview_scheduled', 'Interview Scheduled'),
        ('rejected', 'Rejected'),
        ('accepted', 'Accepted'),
    )
    recruitment = models.ForeignKey(Recruitment, on_delete=models.CASCADE, related_name='applications')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recruitment_applications')
    role_applied_for = models.CharField(max_length=255, blank=True)
    answers = models.JSONField(default=dict)
    cv_file = models.FileField(upload_to='cvs/', null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    interview_slot = models.DateTimeField(null=True, blank=True)
    interview_score = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.username} - {self.recruitment.title}"

class CabinetMember(models.Model):
    society = models.ForeignKey(Society, on_delete=models.CASCADE, related_name='cabinet_members')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cabinet_positions')
    role_title = models.CharField(max_length=255)
    term_year = models.CharField(max_length=20) # e.g., '2023-2024'
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} - {self.role_title} ({self.society.name})"

class EventProposal(models.Model):
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('generated', 'Generated'),
        ('downloaded', 'Downloaded / Awaiting Physical Signature'),
        ('signed_uploaded', 'Signed Document Uploaded / Pending Verification'),
        ('approved', 'Approved'),
        ('returned', 'Returned for Correction'),
        ('rejected', 'Rejected'),
        ('archived', 'Archived'),
    )

    proposal_no = models.CharField(max_length=100, unique=True)
    society = models.ForeignKey(Society, on_delete=models.CASCADE, related_name='proposals')
    president = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='submitted_proposals')
    advisor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='advised_proposals')

    # 1. Event Information
    event_title = models.CharField(max_length=255)
    event_type = models.CharField(max_length=100, default='Seminar & Workshop')
    event_date = models.DateField()
    start_time = models.CharField(max_length=50, default='10:00 AM')
    end_time = models.CharField(max_length=50, default='01:00 PM')
    venue = models.CharField(max_length=255, default='Campus Main Auditorium')
    academic_year = models.CharField(max_length=50, default='2026-2027')
    event_image = models.TextField(blank=True, default='')
    is_paid = models.BooleanField(default=False)
    ticket_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    @property
    def poster_image_url(self):
        return self.event_image

    @poster_image_url.setter
    def poster_image_url(self, value):
        self.event_image = value

    # 2. Objectives & 3. Description
    objectives = models.TextField(blank=True, default='')
    event_description = models.TextField(blank=True, default='')

    # 4. Expected Participation
    expected_participants = models.IntegerField(default=100)
    target_audience = models.CharField(max_length=255, default='University Students & Faculty')
    guests = models.TextField(blank=True, default='')

    # 5. Requirements
    required_facilities = models.TextField(blank=True, default='Auditorium, Sound system, Projector, Media coverage, Certificates')

    # 6. Budget Estimate
    budget_items = models.JSONField(default=list, blank=True)
    budget = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    # 7. Funding Source & 8. Expected Outcome
    funding_source = models.CharField(max_length=255, default='Society Annual Budget Allocation')
    expected_outcome = models.TextField(blank=True, default='')

    # 9. Prepared By
    president_contact = models.CharField(max_length=50, blank=True, default='')

    # Advisor Review & Office Remarks
    advisor_comments = models.TextField(blank=True, default='')
    official_remarks = models.TextField(blank=True, default='')
    rejection_reason = models.TextField(blank=True, default='')

    # Stored Files
    original_proposal_file = models.TextField(blank=True, default='')
    signed_proposal_file = models.TextField(blank=True, default='')

    # Workflow Status & Timestamps
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='draft')
    generated_at = models.DateTimeField(null=True, blank=True)
    downloaded_at = models.DateTimeField(null=True, blank=True)
    uploaded_at = models.DateTimeField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_proposals')

    # Linked Live Event
    event = models.OneToOneField(Event, on_delete=models.SET_NULL, null=True, blank=True, related_name='official_proposal')

    # Audit Log History
    status_history = models.JSONField(default=list, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.proposal_no} - {self.event_title} ({self.society.name})"


class DateClaim(models.Model):
    STATUS_CHOICES = (
        ('provisional', 'Provisional'),
        ('confirmed', 'Confirmed'),
        ('released', 'Released'),
    )
    claim_date = models.DateField(unique=True)
    society = models.ForeignKey(Society, on_delete=models.CASCADE, related_name='date_claims')
    event = models.ForeignKey(Event, on_delete=models.SET_NULL, null=True, blank=True, related_name='date_claims')
    proposal = models.ForeignKey(EventProposal, on_delete=models.SET_NULL, null=True, blank=True, related_name='date_claims')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='provisional')
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.claim_date} - {self.society.name} ({self.status})"


class EventStaffAssignment(models.Model):
    STATUS_CHOICES = (
        ('assigned', 'Assigned'),
        ('revoked', 'Revoked'),
        ('completed', 'Completed'),
    )
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='volunteer_assignments')
    volunteer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='duty_assignments')
    duty_start = models.DateTimeField(null=True, blank=True)
    duty_end = models.DateTimeField(null=True, blank=True)
    gate_name = models.CharField(max_length=100, blank=True, default='Gate 1')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='assigned')
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_staff_assignments')
    created_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='revoked_staff_assignments')

    class Meta:
        unique_together = ('event', 'volunteer')

    def __str__(self):
        return f"{self.volunteer.username} @ {self.event.title} ({self.gate_name})"


class SignatureAsset(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='signatures')
    role_title = models.CharField(max_length=100) # e.g. 'Faculty Advisor', 'President', 'Super Admin'
    signature_image = models.TextField() # data URL or media path
    is_approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_signatures')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Signature of {self.user.username} - {self.role_title}"


class CertificateTemplate(models.Model):
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('pending_approval', 'Pending Advisor Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    title = models.CharField(max_length=255)
    society = models.ForeignKey(Society, on_delete=models.CASCADE, related_name='certificate_templates')
    event = models.ForeignKey(Event, on_delete=models.SET_NULL, null=True, blank=True, related_name='certificate_templates')
    layout_json = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='draft')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_templates')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_templates')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} ({self.society.name})"


class SystemSetting(models.Model):
    key = models.CharField(max_length=100, unique=True)
    value = models.JSONField(default=dict)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.key


class BackupRecord(models.Model):
    filename = models.CharField(max_length=255)
    file_size_bytes = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=50, default='completed') # completed, restored, failed
    notes = models.TextField(blank=True, default='')

    def __str__(self):
        return f"{self.filename} ({self.status})"


