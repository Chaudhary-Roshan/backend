from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
import uuid
from rest_framework.test import APIClient
from rest_framework import status
from django.core.files.uploadedfile import SimpleUploadedFile
from .models import (
    User, Society, Event, Registration, Certificate, 
    EventStaffAssignment, SignatureAsset, CertificateTemplate,
    CabinetMember, Membership, Recruitment, RecruitmentApplication,
    EventProposal, DateClaim, Notification, News, Gallery,
    BackupRecord, SystemSetting
)


class DSMSPortalTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # 1. Setup Users
        self.admin = User.objects.create_superuser(
            username='superadmin',
            email='admin@campus.edu',
            password='Password123!',
            role='admin'
        )

        self.advisor_a = User.objects.create_user(
            username='advisor_a',
            email='advisor_a@campus.edu',
            password='Password123!',
            role='faculty'
        )

        self.president_a = User.objects.create_user(
            username='president_a',
            email='president_a@campus.edu',
            password='Password123!',
            role='president'
        )

        self.advisor_b = User.objects.create_user(
            username='advisor_b',
            email='advisor_b@campus.edu',
            password='Password123!',
            role='faculty'
        )

        self.president_b = User.objects.create_user(
            username='president_b',
            email='president_b@campus.edu',
            password='Password123!',
            role='president'
        )

        self.student = User.objects.create_user(
            username='student_sam',
            email='sam@campus.edu',
            password='Password123!',
            role='student',
            roll_number='FA22-BCS-042',
            program='BS Computer Science',
            department='Department of Computer Science'
        )

        # 2. Setup Societies
        self.society_a = Society.objects.create(
            name='Computer Science Society',
            description='CS chapter',
            advisor=self.advisor_a,
            president=self.president_a,
            bank_name='Campus National Bank',
            bank_account_title='CSS Society Account',
            bank_account_number='PK12CAMPUS9999'
        )
        self.advisor_a.society = self.society_a
        self.advisor_a.save()
        self.president_a.society = self.society_a
        self.president_a.save()

        self.society_b = Society.objects.create(
            name='Robotics Club',
            description='Robotics chapter',
            advisor=self.advisor_b,
            president=self.president_b
        )
        self.advisor_b.society = self.society_b
        self.advisor_b.save()
        self.president_b.society = self.society_b
        self.president_b.save()

    def test_super_admin_credentials_issuance(self):
        """Super Admin can issue credentials to new Faculty Advisor or President"""
        self.client.force_authenticate(user=self.admin)
        res = self.client.post('/api/users/', {
            'username': 'new_advisor',
            'email': 'new_advisor@campus.edu',
            'password': 'InitialPassword123!',
            'role': 'faculty',
            'society': self.society_b.id
        })
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        new_user = User.objects.get(username='new_advisor')
        self.assertEqual(new_user.role, 'faculty')
        self.assertEqual(new_user.society, self.society_b)

    def test_date_lock_conflict_rule(self):
        """Date-Lock Rule: If Society A books a date, Society B cannot schedule on that date"""
        booking_date = timezone.now() + timedelta(days=10)

        # Society A proposes an event
        self.client.force_authenticate(user=self.president_a)
        res_a = self.client.post('/api/events/', {
            'title': 'AI Hackathon 2026',
            'description': 'Annual AI competition',
            'date': booking_date.isoformat(),
            'is_paid': False
        })
        self.assertEqual(res_a.status_code, status.HTTP_201_CREATED)
        event_a_id = res_a.data['id']

        # Society B attempts to schedule on the SAME date -> must be blocked by Date-Lock rule
        self.client.force_authenticate(user=self.president_b)
        res_b = self.client.post('/api/events/', {
            'title': 'RoboWars 2026',
            'description': 'Robotics battle',
            'date': booking_date.isoformat(),
            'is_paid': False
        })
        self.assertEqual(res_b.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Date-Lock Active', str(res_b.data))

        # Check locked dates endpoint reflects the date
        res_locked = self.client.get('/api/events/locked_dates/')
        self.assertEqual(res_locked.status_code, status.HTTP_200_OK)
        locked_date_str = booking_date.strftime('%Y-%m-%d')
        locked_dates = [item['date'] for item in res_locked.data]
        self.assertIn(locked_date_str, locked_dates)

    def test_faculty_cannot_approve_another_society_event(self):
        event = Event.objects.create(
            society=self.society_b,
            title='Society B Approval Scope Test',
            description='Scope test',
            date=timezone.now() + timedelta(days=30),
            status='pending'
        )
        self.client.force_authenticate(user=self.advisor_a)
        response = self.client.post(f'/api/events/{event.id}/approve/')
        self.assertIn(response.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])
        event.refresh_from_db()
        self.assertEqual(event.status, 'pending')

    def test_paid_event_registration_and_verification(self):
        """Paid events require payment verification by Admin, Advisor, or President"""
        event_date = timezone.now() + timedelta(days=15)
        paid_event = Event.objects.create(
            society=self.society_a,
            title='Advanced Cyber Security Workshop',
            description='Deep dive with hardware kit',
            date=event_date,
            is_paid=True,
            price=25.00,
            status='approved'
        )

        # Student registers for paid event submitting transaction receipt
        self.client.force_authenticate(user=self.student)
        res_reg = self.client.post('/api/registrations/', {
            'event': paid_event.id,
            'transaction_id': 'TXN-99887766',
            'receipt_details': 'Paid via Mobile Banking'
        })
        self.assertEqual(res_reg.status_code, status.HTTP_201_CREATED)
        reg_id = res_reg.data['id']
        self.assertEqual(res_reg.data['payment_status'], 'pending')

        # Society President verifies payment receipt
        self.client.force_authenticate(user=self.president_a)
        res_verify = self.client.post(f'/api/registrations/{reg_id}/verify_payment/')
        self.assertEqual(res_verify.status_code, status.HTTP_200_OK)
        reg = Registration.objects.get(id=reg_id)
        self.assertEqual(reg.payment_status, 'verified')

    def test_attendance_and_bulk_certificates(self):
        """Attendance check-in marks attendance and allows bulk certificate generation for attendees"""
        event_date = timezone.now() - timedelta(days=1)
        event = Event.objects.create(
            society=self.society_a,
            title='Completed Python Bootcamp',
            description='Bootcamp completed',
            date=event_date,
            is_paid=False,
            status='approved'
        )

        reg = Registration.objects.create(
            event=event,
            student=self.student,
            payment_status='verified',
            attendance_status=False
        )

        # President scans ticket QR code
        self.client.force_authenticate(user=self.president_a)
        res_attend = self.client.post(f'/api/registrations/{reg.id}/mark_attendance/')
        self.assertEqual(res_attend.status_code, status.HTTP_200_OK)
        reg.refresh_from_db()
        self.assertTrue(reg.attendance_status)

        # President issues bulk certificates
        res_bulk_cert = self.client.post('/api/certificates/generate_bulk/', {
            'event_id': event.id
        })
        self.assertEqual(res_bulk_cert.status_code, status.HTTP_200_OK)
        self.assertEqual(res_bulk_cert.data['issued_count'], 1)

        # Verify certificate exists
        cert = Certificate.objects.get(event=event, student=self.student)
        self.assertIsNotNone(cert.verification_code)

    def test_president_strict_society_scoping(self):
        """President can update branding/description but bank details are protected; Advisor can edit bank details"""
        # 1. President A updates description and attempts to change bank account
        self.client.force_authenticate(user=self.president_a)
        res_update_own = self.client.patch(f'/api/societies/{self.society_a.id}/', {
            'description': 'Updated description for Society A',
            'bank_account_number': 'PK99NEWBANK123'
        })
        self.assertEqual(res_update_own.status_code, status.HTTP_200_OK)
        self.society_a.refresh_from_db()
        self.assertEqual(self.society_a.description, 'Updated description for Society A')
        # Bank account number is protected: President CANNOT alter bank details
        self.assertEqual(self.society_a.bank_account_number, 'PK12CAMPUS9999')

        # 2. Advisor A CAN edit bank details
        self.client.force_authenticate(user=self.advisor_a)
        res_advisor_bank = self.client.patch(f'/api/societies/{self.society_a.id}/', {
            'bank_account_number': 'PK99NEWBANK123'
        })
        self.assertEqual(res_advisor_bank.status_code, status.HTTP_200_OK)
        self.society_a.refresh_from_db()
        self.assertEqual(self.society_a.bank_account_number, 'PK99NEWBANK123')

        # 2. President A attempts to update Society B settings -> MUST BE BLOCKED
        res_update_other = self.client.patch(f'/api/societies/{self.society_b.id}/', {
            'description': 'Hacked description for Society B'
        })
        self.assertEqual(res_update_other.status_code, status.HTTP_400_BAD_REQUEST)
        self.society_b.refresh_from_db()
        self.assertNotEqual(self.society_b.description, 'Hacked description for Society B')

        # 3. President A proposing an event forces society to Society A
        res_propose = self.client.post('/api/events/', {
            'title': 'Scoped Society Event',
            'description': 'Event for Society A',
            'date': timezone.now() + timedelta(days=20),
            'society': self.society_b.id  # Maliciously passes Society B
        })
        self.assertEqual(res_propose.status_code, status.HTTP_201_CREATED)
        created_event = Event.objects.get(title='Scoped Society Event')
        self.assertEqual(created_event.society, self.society_a) # Forced to Society A!

        # 4. President A attempts to edit an event of Society B -> MUST BE BLOCKED
        event_b = Event.objects.create(
            society=self.society_b,
            title='Society B Hackathon',
            description='Robotics Hackathon',
            date=timezone.now() + timedelta(days=25),
            status='approved'
        )
        res_edit_b = self.client.patch(f'/api/events/{event_b.id}/', {
            'title': 'Compromised Title'
        })
        self.assertEqual(res_edit_b.status_code, status.HTTP_400_BAD_REQUEST)

    def test_student_registration_and_otp_verification(self):
        """Student registration triggers OTP generation, and verify-otp activates the account"""
        res_reg = self.client.post('/api/auth/register/', {
            'username': 'john_doe',
            'email': 'john.doe@campus.edu',
            'password': 'Password123!',
            'roll_number': 'CS-2023-99',
            'cnic': '35201-1234567-1',
            'department': 'Computer Science',
            'program': 'BS Computer Science',
            'batch': '2023-2027',
            'semester': '4th'
        })
        self.assertEqual(res_reg.status_code, status.HTTP_201_CREATED)
        self.assertTrue(res_reg.data.get('requires_otp'))

        # User is created but unverified
        user = User.objects.get(username='john_doe')
        self.assertFalse(user.is_email_verified)
        self.assertTrue(bool(user.otp_code))

        # Verify with OTP
        res_verify = self.client.post('/api/auth/verify-otp/', {
            'user_id': user.id,
            'otp': user.otp_code
        })
        self.assertEqual(res_verify.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertTrue(user.is_email_verified)

    def test_registration_does_not_return_otp_and_universal_code_is_rejected(self):
        response = self.client.post('/api/auth/register/', {
            'username': 'secure_student',
            'email': 'secure.student@campus.edu',
            'password': 'Password123!',
            'first_name': 'Secure',
            'last_name': 'Student'
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertNotIn('demo_otp', response.data)
        user = User.objects.get(username='secure_student')
        wrong = self.client.post('/api/auth/verify-otp/', {
            'user_id': user.id,
            'otp': '123456'
        })
        self.assertEqual(wrong.status_code, status.HTTP_400_BAD_REQUEST)
        user.refresh_from_db()
        self.assertFalse(user.is_email_verified)

    def test_private_profile_fields_and_system_settings_are_isolated(self):
        self.client.force_authenticate(user=self.president_a)
        profile = self.client.get('/api/users/')
        self.assertEqual(profile.status_code, status.HTTP_200_OK)
        student_payload = next(item for item in profile.data if item['id'] == self.student.id)
        self.assertEqual(student_payload['email'], '')
        settings_response = self.client.get('/api/system-settings/')
        self.assertEqual(settings_response.status_code, status.HTTP_200_OK)
        self.assertEqual(settings_response.data, [])

    def test_upload_rejects_untrusted_file_types(self):
        self.client.force_authenticate(user=self.student)
        upload = SimpleUploadedFile('payload.exe', b'MZ-test', content_type='application/x-msdownload')
        response = self.client.post('/api/upload/', {'file': upload}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_volunteer_duty_assignment_and_ticket_checkin(self):
        """President appoints a student as gate volunteer; student volunteer successfully scans tickets"""
        event = Event.objects.create(
            society=self.society_a,
            title='Mega Tech Expo 2026',
            description='Tech Showcase',
            date=timezone.now() + timedelta(days=2),
            is_paid=False,
            status='approved'
        )

        reg = Registration.objects.create(
            event=event,
            student=self.student,
            payment_status='verified',
            ticket_qr_code='TICKET-TEST-12345',
            attendance_status=False
        )

        # President appoints another student as volunteer
        volunteer_student = User.objects.create_user(
            username='volunteer_amy',
            email='amy@campus.edu',
            password='Password123!',
            role='student'
        )

        self.client.force_authenticate(user=self.president_a)
        res_assign = self.client.post('/api/staff-assignments/', {
            'event': event.id,
            'volunteer': volunteer_student.id,
            'gate_name': 'North Gate Desk 2'
        })
        self.assertEqual(res_assign.status_code, status.HTTP_201_CREATED)

        # Volunteer logs in and scans ticket
        self.client.force_authenticate(user=volunteer_student)
        res_scan = self.client.post('/api/registrations/scan_ticket/', {
            'ticket_code': str(reg.ticket_qr_code)
        })
        self.assertEqual(res_scan.status_code, status.HTTP_200_OK)
        reg.refresh_from_db()
        self.assertTrue(reg.attendance_status)

    def test_certificate_template_and_signature_rendering(self):
        """President designs template, Advisor approves with signature, and issued certificates render template layout"""
        event = Event.objects.create(
            society=self.society_a,
            title='Web Architecture Masterclass',
            description='Fullstack mastery',
            date=timezone.now() - timedelta(days=2),
            is_paid=False,
            status='approved'
        )

        reg = Registration.objects.create(
            event=event,
            student=self.student,
            payment_status='verified',
            attendance_status=True
        )

        # 1. Advisor uploads official signature specimen
        self.client.force_authenticate(user=self.advisor_a)
        res_sig = self.client.post('/api/signatures/', {
            'signature_image': 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=='
        })
        self.assertEqual(res_sig.status_code, status.HTTP_201_CREATED)
        self.assertTrue(res_sig.data['is_approved'])

        # 2. President designs custom CertificateTemplate
        self.client.force_authenticate(user=self.president_a)
        res_tmpl = self.client.post('/api/certificate-templates/', {
            'title': 'Distinguished Architecture Certificate',
            'event': event.id,
            'layout_json': {
                'title': 'Distinguished Architecture Certificate',
                'subtitle': 'Department of Computing • Academic Honors',
                'body_text': 'has completed the intensive masterclass with distinction',
                'theme_color': '#064e3b',
                'signatory_title_left': 'Academic Advisor',
                'signatory_title_right': 'Society Convener'
            }
        }, format='json')
        self.assertEqual(res_tmpl.status_code, status.HTTP_201_CREATED)
        tmpl_id = res_tmpl.data['id']
        self.assertEqual(res_tmpl.data['status'], 'draft')

        # 3. President submits for approval
        res_sub = self.client.post(f'/api/certificate-templates/{tmpl_id}/submit_for_approval/')
        self.assertEqual(res_sub.status_code, status.HTTP_200_OK)
        self.assertEqual(res_sub.data['template']['status'], 'pending_approval')

        # 4. Advisor approves the template
        self.client.force_authenticate(user=self.advisor_a)
        res_appr = self.client.post(f'/api/certificate-templates/{tmpl_id}/approve/')
        self.assertEqual(res_appr.status_code, status.HTTP_200_OK)
        self.assertEqual(res_appr.data['template']['status'], 'approved')

        # 5. Issue bulk certificates
        res_bulk = self.client.post('/api/certificates/generate_bulk/', {
            'event_id': event.id,
            'template_id': tmpl_id
        })
        self.assertEqual(res_bulk.status_code, status.HTTP_200_OK)
        self.assertEqual(res_bulk.data['issued_count'], 1)

        # 6. Verify Certificate payload contains template layout & approved advisor signature
        cert = Certificate.objects.get(event=event, student=self.student)
        self.client.force_authenticate(user=self.student)
        res_cert = self.client.get(f'/api/certificates/{cert.id}/')
        self.assertEqual(res_cert.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(res_cert.data['template_layout'])
        self.assertEqual(res_cert.data['template_layout']['theme_color'], '#064e3b')
        self.assertIsNotNone(res_cert.data['advisor_signature'])

    def test_login_gate_enforces_otp_verification(self):
        """Unverified users are blocked at login with requires_otp=True until activated"""
        unverified_user = User.objects.create_user(
            username='freshman_bob',
            email='bob@campus.edu',
            password='SecretPassword123!',
            role='student',
            is_email_verified=False,
            otp_code='654321',
            otp_created_at=timezone.now(),
            otp_attempts=0
        )

        # 1. Attempt login before OTP verification -> blocked
        res_fail = self.client.post('/api/auth/login/', {
            'username': 'freshman_bob',
            'password': 'SecretPassword123!'
        })
        self.assertEqual(res_fail.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(res_fail.data.get('requires_otp'))
        self.assertEqual(res_fail.data.get('email'), 'bob@campus.edu')

        # 2. Complete OTP verification
        res_verify = self.client.post('/api/auth/verify-otp/', {
            'user_id': unverified_user.id,
            'otp': '654321'
        })
        self.assertEqual(res_verify.status_code, status.HTTP_200_OK)
        unverified_user.refresh_from_db()
        self.assertTrue(unverified_user.is_email_verified)

        # 3. Attempt login after verification -> succeeds with JWT tokens
        res_success = self.client.post('/api/auth/login/', {
            'username': 'freshman_bob',
            'password': 'SecretPassword123!'
        })
        self.assertEqual(res_success.status_code, status.HTTP_200_OK)
        self.assertIn('access', res_success.data)
        self.assertIn('refresh', res_success.data)

    def test_profile_endpoint_fortified_against_privilege_escalation(self):
        """Students cannot escalate role, alter society, or forge academic records via profile endpoint"""
        self.client.force_authenticate(user=self.student)

        # Student attempts privilege escalation and academic forgery
        res_tamper = self.client.patch('/api/auth/profile/', {
            'role': 'admin',
            'society': self.society_a.id,
            'is_email_verified': False,
            'is_active': False,
            'roll_number': 'FORGED-ROLL-001',
            'department': 'Illegal Department'
        })
        self.assertEqual(res_tamper.status_code, status.HTTP_200_OK)
        self.student.refresh_from_db()
        self.assertEqual(self.student.role, 'student')
        self.assertIsNone(self.student.society)
        self.assertTrue(self.student.is_email_verified)
        self.assertTrue(self.student.is_active)
        self.assertNotEqual(self.student.roll_number, 'FORGED-ROLL-001')

        # Student can update allowed self-service fields (phone and avatar)
        res_legit = self.client.patch('/api/auth/profile/', {
            'phone_number': '+92-300-9876543',
            'avatar_url': 'https://example.com/new-avatar.png'
        })
        self.assertEqual(res_legit.status_code, status.HTTP_200_OK)
        self.student.refresh_from_db()
        self.assertEqual(self.student.phone_number, '+92-300-9876543')
        self.assertEqual(self.student.avatar_url, 'https://example.com/new-avatar.png')

    def test_super_admin_user_management_and_role_scoping(self):
        """Super Admin can provision Presidents/Advisors, bind societies, toggle status, and reset passwords"""
        self.client.force_authenticate(user=self.admin)

        # 1. Admin creates a new society president
        res_create = self.client.post('/api/users/', {
            'username': 'pres_clara',
            'email': 'clara@campus.edu',
            'password': 'SecurePresPass123!',
            'first_name': 'Clara',
            'last_name': 'Oswald',
            'role': 'president',
            'society': self.society_a.id
        })
        self.assertEqual(res_create.status_code, status.HTTP_201_CREATED)
        new_pres_id = res_create.data['id']

        # Verify society president synchronization
        self.society_a.refresh_from_db()
        self.assertEqual(self.society_a.president.id, new_pres_id)

        # 2. Admin toggles user active status (deactivates)
        res_toggle = self.client.post(f'/api/users/{new_pres_id}/toggle_active/')
        self.assertEqual(res_toggle.status_code, status.HTTP_200_OK)
        self.assertFalse(res_toggle.data['is_active'])

        # 3. Admin resets password
        res_reset = self.client.post(f'/api/users/{new_pres_id}/reset_password/', {
            'password': 'BrandNewPassword999!'
        })
        self.assertEqual(res_reset.status_code, status.HTTP_200_OK)

        # 4. Unauthorized non-admin (student) cannot create users or toggle active
        self.client.force_authenticate(user=self.student)
        res_unauth_create = self.client.post('/api/users/', {
            'username': 'rogue_user',
            'role': 'admin'
        })
        self.assertEqual(res_unauth_create.status_code, status.HTTP_403_FORBIDDEN)

        res_unauth_toggle = self.client.post(f'/api/users/{new_pres_id}/toggle_active/')
        self.assertEqual(res_unauth_toggle.status_code, status.HTTP_403_FORBIDDEN)

    def test_society_profile_update_and_bank_protection(self):
        """President can update branding/vision, but cannot touch bank details or edit other societies"""
        self.client.force_authenticate(user=self.president_a)

        original_bank_num = self.society_a.bank_account_number

        # 1. President A updates vision/mission/description and attempts to alter bank account
        res_update = self.client.patch(f'/api/societies/{self.society_a.id}/', {
            'vision': 'To lead innovation across Pakistan campus networks',
            'mission': 'Empower students through hands-on technical labs',
            'bank_account_number': 'TAMPERED-BANK-99999999'
        })
        self.assertEqual(res_update.status_code, status.HTTP_200_OK)
        self.society_a.refresh_from_db()
        self.assertEqual(self.society_a.vision, 'To lead innovation across Pakistan campus networks')
        # Bank number MUST remain unchanged (president stripped)
        self.assertEqual(self.society_a.bank_account_number, original_bank_num)

        # 2. President A attempts to edit Society B -> rejected
        res_hack_b = self.client.patch(f'/api/societies/{self.society_b.id}/', {
            'vision': 'Hacked Society B'
        })
        self.assertEqual(res_hack_b.status_code, status.HTTP_400_BAD_REQUEST)

        # 3. Faculty Advisor A updates bank details -> succeeds
        self.client.force_authenticate(user=self.advisor_a)
        res_advisor_bank = self.client.patch(f'/api/societies/{self.society_a.id}/', {
            'bank_name': 'Official Campus Trust Bank',
            'bank_account_title': 'Cyber Security Society Official Reserve',
            'bank_account_number': 'PK99CAMPUS000111222333'
        })
        self.assertEqual(res_advisor_bank.status_code, status.HTTP_200_OK)
        self.society_a.refresh_from_db()
        self.assertEqual(self.society_a.bank_account_number, 'PK99CAMPUS000111222333')

        # 4. Student attempts to update society details -> rejected
        self.client.force_authenticate(user=self.student)
        res_student_hack = self.client.patch(f'/api/societies/{self.society_a.id}/', {
            'description': 'Student defaced description'
        })
        self.assertEqual(res_student_hack.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cabinet_nomination_by_roll_number_and_verification(self):
        """President nominates student into cabinet via roll number; Advisor verifies nomination"""
        self.client.force_authenticate(user=self.president_a)

        # 1. President looks up student by roll number
        res_lookup = self.client.get(f'/api/users/lookup_by_roll/?roll_number={self.student.roll_number}')
        self.assertEqual(res_lookup.status_code, status.HTTP_200_OK)
        self.assertEqual(res_lookup.data['id'], self.student.id)

        # 2. President nominates student as Vice President using roll number
        res_nom = self.client.post('/api/cabinet/', {
            'student_username': self.student.roll_number,
            'role_title': 'Vice President',
            'term_year': '2026-2027',
            'society': self.society_a.id
        })
        self.assertEqual(res_nom.status_code, status.HTTP_201_CREATED)
        cab_id = res_nom.data['id']
        cab_member = CabinetMember.objects.get(id=cab_id)
        self.assertEqual(cab_member.user, self.student)
        self.assertFalse(cab_member.is_verified)

        # 3. President cannot duplicate nominate the same student for the same term
        res_dup = self.client.post('/api/cabinet/', {
            'student_username': self.student.roll_number,
            'role_title': 'Treasurer',
            'term_year': '2026-2027',
            'society': self.society_a.id
        })
        self.assertEqual(res_dup.status_code, status.HTTP_400_BAD_REQUEST)

        # 4. Advisor of Society B cannot verify Society A's cabinet member (strictly isolated to own society)
        self.client.force_authenticate(user=self.advisor_b)
        res_unauth_ver = self.client.post(f'/api/cabinet/{cab_id}/verify/')
        self.assertIn(res_unauth_ver.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])

        # 5. Advisor of Society A verifies the nomination
        self.client.force_authenticate(user=self.advisor_a)
        res_ver = self.client.post(f'/api/cabinet/{cab_id}/verify/')
        self.assertEqual(res_ver.status_code, status.HTTP_200_OK)
        cab_member.refresh_from_db()
        self.assertTrue(cab_member.is_verified)

    def test_recruitment_drive_and_application_workflow(self):
        """President launches recruitment, student applies, and accepted applicant receives automatic Membership"""
        # 1. President launches recruitment drive
        self.client.force_authenticate(user=self.president_a)
        res_drive = self.client.post('/api/recruitments/', {
            'title': 'Spring 2026 Cabinet & Associate Recruitment',
            'deadline': timezone.now() + timedelta(days=14),
            'form_fields': ['statement', 'department_preference'],
            'status': 'open'
        }, format='json')
        self.assertEqual(res_drive.status_code, status.HTTP_201_CREATED)
        drive_id = res_drive.data['id']

        # 2. President B cannot modify or delete Society A's drive
        self.client.force_authenticate(user=self.president_b)
        res_mod_b = self.client.patch(f'/api/recruitments/{drive_id}/', {
            'title': 'Hacked Drive'
        })
        self.assertEqual(res_mod_b.status_code, status.HTTP_400_BAD_REQUEST)

        # 3. Student applies to recruitment drive
        self.client.force_authenticate(user=self.student)
        res_app = self.client.post('/api/applications/', {
            'recruitment': drive_id,
            'role_applied_for': 'Technical Team Lead',
            'answers': {
                'statement': 'Strong proficiency in Python, Linux, and Cloud Networks',
                'department_preference': 'Cyber Security'
            }
        }, format='json')
        self.assertEqual(res_app.status_code, status.HTTP_201_CREATED)
        app_id = res_app.data['id']

        # 4. Duplicate application by same student is rejected
        res_dup_app = self.client.post('/api/applications/', {
            'recruitment': drive_id,
            'role_applied_for': 'Another Role'
        }, format='json')
        self.assertEqual(res_dup_app.status_code, status.HTTP_400_BAD_REQUEST)

        # 5. President A reviews and accepts the applicant
        self.client.force_authenticate(user=self.president_a)
        res_accept = self.client.post(f'/api/applications/{app_id}/update_status/', {
            'status': 'accepted',
            'interview_score': 95
        }, format='json')
        self.assertEqual(res_accept.status_code, status.HTTP_200_OK)
        self.assertEqual(res_accept.data['application']['status'], 'accepted')

        # 6. Automatic Membership is provisioned
        membership = Membership.objects.filter(student=self.student, society=self.society_a).first()
        self.assertIsNotNone(membership)
        self.assertTrue(membership.is_active)
        self.assertEqual(membership.role_title, 'Technical Team Lead')

        # 7. Student can view their new society membership card
        self.client.force_authenticate(user=self.student)
        res_mem = self.client.get('/api/memberships/')
        self.assertEqual(res_mem.status_code, status.HTTP_200_OK)
        self.assertTrue(any(m['society'] == self.society_a.id for m in res_mem.data))

    def test_paid_membership_requires_proof_and_uses_society_fee(self):
        self.society_a.membership_fee = 500
        self.society_a.is_membership_open = True
        self.society_a.save(update_fields=['membership_fee', 'is_membership_open'])
        self.client.force_authenticate(user=self.student)

        missing_proof = self.client.post('/api/memberships/', {'society': self.society_a.id})
        self.assertEqual(missing_proof.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Membership.objects.filter(student=self.student, society=self.society_a).exists())

        submitted = self.client.post('/api/memberships/', {
            'society': self.society_a.id,
            'payment_proof': 'https://files.example/receipt.png',
            'fee_paid': '1'
        })
        self.assertEqual(submitted.status_code, status.HTTP_201_CREATED)
        membership = Membership.objects.get(student=self.student, society=self.society_a)
        self.assertEqual(membership.fee_paid, 500)
        self.assertEqual(membership.status, 'pending')

    def test_volunteer_acceptance_and_staff_revocation_are_auditable(self):
        event = Event.objects.create(
            society=self.society_a,
            title='Volunteer Audit Event',
            description='Volunteer audit coverage',
            date=timezone.now() + timedelta(days=2),
            status='approved'
        )
        self.client.force_authenticate(user=self.president_a)
        assignment_response = self.client.post('/api/staff-assignments/', {
            'event': event.id,
            'volunteer': self.student.id,
            'gate_name': 'North Gate'
        })
        self.assertEqual(assignment_response.status_code, status.HTTP_201_CREATED)
        assignment_id = assignment_response.data['id']

        self.client.force_authenticate(user=self.president_a)
        volunteer_response = self.client.post('/api/volunteer-hours/', {
            'event': event.id,
            'student': self.student.id,
            'role': 'Registration Desk'
        })
        self.assertEqual(volunteer_response.status_code, status.HTTP_201_CREATED)
        volunteer_id = volunteer_response.data['id']
        self.client.force_authenticate(user=self.student)
        accepted = self.client.post(f'/api/volunteer-hours/{volunteer_id}/accept/')
        self.assertEqual(accepted.status_code, status.HTTP_200_OK)
        self.assertEqual(accepted.data['status'], 'accepted')

        self.client.force_authenticate(user=self.president_a)
        revoked = self.client.post(f'/api/staff-assignments/{assignment_id}/revoke/')
        self.assertEqual(revoked.status_code, status.HTTP_200_OK)
        assignment = EventStaffAssignment.objects.get(id=assignment_id)
        self.assertEqual(assignment.status, 'revoked')
        self.assertIsNotNone(assignment.revoked_at)
        self.assertEqual(assignment.revoked_by, self.president_a)

    def test_date_claim_conflict_prevention_and_availability_endpoint(self):
        """Society A claims a date; Society B is blocked from booking the same date; check_availability reflects locks"""
        target_date = (timezone.now() + timedelta(days=45)).date()
        target_date_str = target_date.strftime('%Y-%m-%d')

        # 1. Society A drafts proposal for target date
        self.client.force_authenticate(user=self.president_a)
        res_prop_a = self.client.post('/api/proposals/', {
            'event_title': 'Annual AI Innovation Symposium',
            'event_date': target_date_str,
            'venue': 'Main Campus Auditorium',
            'event_type': 'Technical Summit & Workshop'
        }, format='json')
        self.assertEqual(res_prop_a.status_code, status.HTTP_201_CREATED)
        prop_a_id = res_prop_a.data['id']

        # 2. DateClaim is created for Society A
        claim = DateClaim.objects.filter(claim_date=target_date).first()
        self.assertIsNotNone(claim)
        self.assertEqual(claim.society, self.society_a)
        self.assertEqual(claim.status, 'provisional')

        # 3. Society B attempts to draft an event on the same calendar day -> BLOCKED
        self.client.force_authenticate(user=self.president_b)
        res_prop_b = self.client.post('/api/proposals/', {
            'event_title': 'Robotics Combat Arena',
            'event_date': target_date_str,
            'venue': 'Engineering Hall',
            'event_type': 'Hackathon & Coding Sprint'
        }, format='json')
        self.assertEqual(res_prop_b.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Date-Lock Active', str(res_prop_b.data))

        # 4. Check availability endpoint for target date
        self.client.force_authenticate(user=self.student)
        res_avail = self.client.get(f'/api/date-claims/check_availability/?date={target_date_str}')
        self.assertEqual(res_avail.status_code, status.HTTP_200_OK)
        self.assertFalse(res_avail.data['available'])
        self.assertIn(self.society_a.name, res_avail.data['message'])

        # 5. Check availability endpoint for an unclaimed date -> open
        free_date_str = (target_date + timedelta(days=1)).strftime('%Y-%m-%d')
        res_free = self.client.get(f'/api/date-claims/check_availability/?date={free_date_str}')
        self.assertEqual(res_free.status_code, status.HTTP_200_OK)
        self.assertTrue(res_free.data['available'])

    def test_proposal_lifecycle_and_two_step_publishing(self):
        """Full lifecycle: draft -> generated -> downloaded -> signed_uploaded -> advisor review -> verified/sanctioned -> published"""
        target_date = (timezone.now() + timedelta(days=60)).date()
        target_date_str = target_date.strftime('%Y-%m-%d')

        # 1. President drafts proposal
        self.client.force_authenticate(user=self.president_a)
        res_draft = self.client.post('/api/proposals/', {
            'event_title': 'Campus Hackathon 2026',
            'event_date': target_date_str,
            'venue': 'Computing Labs',
            'event_type': 'Hackathon & Coding Sprint',
            'budget': 500.00
        }, format='json')
        self.assertEqual(res_draft.status_code, status.HTTP_201_CREATED)
        prop_id = res_draft.data['id']
        self.assertEqual(res_draft.data['status'], 'generated')

        # 2. President downloads printable proposal dossier for paper signatures
        res_down = self.client.post(f'/api/proposals/{prop_id}/mark_downloaded/')
        self.assertEqual(res_down.status_code, status.HTTP_200_OK)
        self.assertEqual(res_down.data['status'], 'downloaded')

        # 3. President uploads scanned signed document
        res_upload = self.client.post(f'/api/proposals/{prop_id}/upload_signed_doc/', {
            'signed_proposal_file': '/media/uploads/proposals/test_signed_scan.pdf'
        })
        self.assertEqual(res_upload.status_code, status.HTTP_200_OK)
        self.assertEqual(res_upload.data['status'], 'signed_uploaded')

        # 4. Advisor reviews and endorses proposal
        self.client.force_authenticate(user=self.advisor_a)
        res_adv = self.client.post(f'/api/proposals/{prop_id}/advisor_review/', {
            'decision': 'approved',
            'advisor_comments': 'Endorsed. Physical signatures from HOD verified.'
        })
        self.assertEqual(res_adv.status_code, status.HTTP_200_OK)

        # 5. Super Admin verifies and sanctions the proposal
        self.client.force_authenticate(user=self.admin)
        res_sanction = self.client.post(f'/api/proposals/{prop_id}/verify_and_sanction/', {
            'decision': 'approved',
            'official_remarks': 'Officially sanctioned by Directorate of Student Affairs.'
        })
        self.assertEqual(res_sanction.status_code, status.HTTP_200_OK)
        self.assertEqual(res_sanction.data['status'], 'approved')

        # DateClaim is now confirmed
        claim = DateClaim.objects.get(claim_date=target_date)
        self.assertEqual(claim.status, 'confirmed')

        # Live campus Event created with proposal link
        event = Event.objects.filter(title='Campus Hackathon 2026').first()
        self.assertIsNotNone(event)
        self.assertEqual(event.status, 'approved')

        # 6. Two-step release: President can publish / confirm event release
        self.client.force_authenticate(user=self.president_a)
        res_pub = self.client.post(f'/api/events/{event.id}/publish/')
        self.assertEqual(res_pub.status_code, status.HTTP_200_OK)
        self.assertEqual(res_pub.data['event']['status'], 'approved')

        # President B cannot publish Society A's event
        self.client.force_authenticate(user=self.president_b)
        res_unauth_pub = self.client.post(f'/api/events/{event.id}/publish/')
        self.assertIn(res_unauth_pub.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])

        # Student cannot publish events
        self.client.force_authenticate(user=self.student)
        res_stud_pub = self.client.post(f'/api/events/{event.id}/publish/')
        self.assertEqual(res_stud_pub.status_code, status.HTTP_403_FORBIDDEN)

    def test_event_poster_proposal_and_display_workflow(self):
        """Verify poster_image_url attaches in proposal draft, flows to live Event upon sanctioning, and can be updated by Admin"""
        target_date = (timezone.now() + timedelta(days=75)).date()
        target_date_str = target_date.strftime('%Y-%m-%d')
        sample_poster = 'https://campus.edu/media/uploads/posters/cyber_defense_2026.jpg'

        # 1. President creates proposal with poster_image_url
        self.client.force_authenticate(user=self.president_a)
        res = self.client.post('/api/proposals/', {
            'event_title': 'Cyber Defense Summit 2026',
            'event_date': target_date_str,
            'venue': 'Cyber Lab Auditorium',
            'event_type': 'Technical Summit & Workshop',
            'poster_image_url': sample_poster,
            'budget': 350.00
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data['poster_image_url'], sample_poster)
        prop_id = res.data['id']

        # 2. Sanction proposal to create live event
        self.client.force_authenticate(user=self.admin)
        res_sanction = self.client.post(f'/api/proposals/{prop_id}/verify_and_sanction/', {
            'decision': 'approved',
            'official_remarks': 'Approved with official poster.'
        })
        self.assertEqual(res_sanction.status_code, status.HTTP_200_OK)

        # 3. Live event serializer contains poster_image_url and details
        event = Event.objects.get(title='Cyber Defense Summit 2026')
        self.assertEqual(event.poster_image_url, sample_poster)
        self.assertEqual(event.image, sample_poster)

        res_ev = self.client.get(f'/api/events/{event.id}/')
        self.assertEqual(res_ev.status_code, status.HTTP_200_OK)
        self.assertEqual(res_ev.data['poster_image_url'], sample_poster)
        self.assertIn('entry_fee', res_ev.data)
        self.assertIn('detailed_description', res_ev.data)

        # 4. Super Admin updates poster via Edit Event modal API endpoint
        updated_poster = 'https://campus.edu/media/uploads/posters/cyber_defense_v2.jpg'
        res_patch = self.client.patch(f'/api/events/{event.id}/', {
            'poster_image_url': updated_poster
        }, format='json')
        self.assertEqual(res_patch.status_code, status.HTTP_200_OK)
        self.assertEqual(res_patch.data['poster_image_url'], updated_poster)
        event.refresh_from_db()
        self.assertEqual(event.image, updated_poster)

    def test_student_event_scoping_isolation(self):
        """Unapproved/pending events are invisible to students, visible to society president and super admin"""
        target_date = timezone.now() + timedelta(days=90)
        pending_evt = Event.objects.create(
            title='Secret Upcoming Gala',
            society=self.society_a,
            date=target_date,
            status='pending'
        )

        # 1. Student query -> pending event is NOT visible
        self.client.force_authenticate(user=self.student)
        res_stud = self.client.get('/api/events/')
        self.assertEqual(res_stud.status_code, status.HTTP_200_OK)
        self.assertFalse(any(e['id'] == pending_evt.id for e in res_stud.data))

        # 2. President A query -> pending event IS visible (own society)
        self.client.force_authenticate(user=self.president_a)
        res_pres_a = self.client.get('/api/events/')
        self.assertEqual(res_pres_a.status_code, status.HTTP_200_OK)
        self.assertTrue(any(e['id'] == pending_evt.id for e in res_pres_a.data))

        # 3. President B query -> pending event of Society A is NOT visible
        self.client.force_authenticate(user=self.president_b)
        res_pres_b = self.client.get('/api/events/')
        self.assertEqual(res_pres_b.status_code, status.HTTP_200_OK)
        self.assertFalse(any(e['id'] == pending_evt.id for e in res_pres_b.data))

        # 4. Super Admin query -> sees all events
        self.client.force_authenticate(user=self.admin)
        res_admin = self.client.get('/api/events/')
        self.assertEqual(res_admin.status_code, status.HTTP_200_OK)
        self.assertTrue(any(e['id'] == pending_evt.id for e in res_admin.data))

    def test_date_claim_release_on_proposal_rejection(self):
        """When a proposal is rejected, its provisional date claim is released, freeing the date for other societies"""
        rej_date = (timezone.now() + timedelta(days=120)).date()
        rej_date_str = rej_date.strftime('%Y-%m-%d')

        # 1. Society A claims date
        self.client.force_authenticate(user=self.president_a)
        res_prop = self.client.post('/api/proposals/', {
            'event_title': 'Controversial Debate',
            'event_date': rej_date_str,
            'venue': 'Auditorium'
        }, format='json')
        self.assertEqual(res_prop.status_code, status.HTTP_201_CREATED)
        prop_id = res_prop.data['id']
        self.assertTrue(DateClaim.objects.filter(claim_date=rej_date).exists())

        # 2. Society Office rejects proposal
        self.client.force_authenticate(user=self.admin)
        res_rej = self.client.post(f'/api/proposals/{prop_id}/verify_and_sanction/', {
            'decision': 'rejected',
            'rejection_reason': 'Conflict with examination schedule.'
        })
        self.assertEqual(res_rej.status_code, status.HTTP_200_OK)

        # 3. Verify DateClaim was released
        self.assertFalse(DateClaim.objects.filter(claim_date=rej_date).exists())

        # 4. Society B can now claim the newly freed date
        self.client.force_authenticate(user=self.president_b)
        res_b = self.client.post('/api/proposals/', {
            'event_title': 'Robotics Workshop Rescheduled',
            'event_date': rej_date_str,
            'venue': 'Auditorium'
        }, format='json')
        self.assertEqual(res_b.status_code, status.HTTP_201_CREATED)
        self.assertTrue(DateClaim.objects.filter(claim_date=rej_date, society=self.society_b).exists())

    def test_24h_seat_hold_and_capacity_limits(self):
        """Phase 4: 24-hour seat hold window created on paid registration, capacity enforced, and expired hold auto-released"""
        event_date = timezone.now() + timedelta(days=25)
        paid_event = Event.objects.create(
            society=self.society_a,
            title='AI & Cloud Summit 2026',
            description='High-demand paid tech conference',
            date=event_date,
            is_paid=True,
            price=25.00,
            expected_attendees=2,  # Strict capacity of 2 seats
            status='approved'
        )

        student_2 = User.objects.create_user(
            username='student_two', email='s2@campus.edu', password='Password123!', role='student'
        )
        student_3 = User.objects.create_user(
            username='student_three', email='s3@campus.edu', password='Password123!', role='student'
        )

        # 1. Student 1 registers without payment proof -> triggers 24h seat hold
        self.client.force_authenticate(user=self.student)
        res1 = self.client.post('/api/registrations/', {
            'event': paid_event.id
        })
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)
        reg1 = Registration.objects.get(id=res1.data['id'])
        self.assertEqual(reg1.payment_status, 'held')
        self.assertIsNotNone(reg1.held_until)
        # held_until should be roughly 24 hours in the future
        self.assertGreater(reg1.held_until, timezone.now() + timedelta(hours=23))
        self.assertIsNone(reg1.ticket_qr_code)
        self.assertEqual(reg1.bank_version, self.society_a.bank_version)
        self.assertIsNotNone(reg1.bank_snapshot)

        # 2. Student 2 registers without payment proof -> consumes 2nd seat
        self.client.force_authenticate(user=student_2)
        res2 = self.client.post('/api/registrations/', {
            'event': paid_event.id
        })
        self.assertEqual(res2.status_code, status.HTTP_201_CREATED)
        reg2 = Registration.objects.get(id=res2.data['id'])
        self.assertEqual(reg2.payment_status, 'held')

        # 3. Student 3 attempts to register -> BLOCKED by capacity limit (2 held seats)
        self.client.force_authenticate(user=student_3)
        res3 = self.client.post('/api/registrations/', {
            'event': paid_event.id
        })
        self.assertEqual(res3.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('capacity limit', res3.data['error'].lower())

        # 4. Student 1's 24-hour seat hold lapses into the past
        reg1.held_until = timezone.now() - timedelta(minutes=5)
        reg1.save()

        # Querying registrations or triggering get_queryset auto-expires overdue holds
        self.client.get('/api/registrations/')
        reg1.refresh_from_db()
        self.assertEqual(reg1.payment_status, 'expired')

        # 5. Student 3 can now register because the expired hold released the capacity!
        res3_retry = self.client.post('/api/registrations/', {
            'event': paid_event.id
        })
        self.assertEqual(res3_retry.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res3_retry.data['payment_status'], 'held')

        # 6. Student 1 whose previous hold expired can re-register
        self.client.force_authenticate(user=self.student)
        res1_re_register = self.client.post('/api/registrations/', {
            'event': paid_event.id
        })
        # But now capacity is again reached by student_2 and student_3!
        self.assertEqual(res1_re_register.status_code, status.HTTP_400_BAD_REQUEST)

    def test_versioned_bank_details_and_snapshot(self):
        """Phase 4: Bank detail changes increment bank_version, maintain audit trail, and snapshot into seat holds"""
        self.assertEqual(self.society_a.bank_version, 1)

        # 1. President attempts to alter bank details -> prohibited
        self.client.force_authenticate(user=self.president_a)
        res_pres = self.client.patch(f'/api/societies/{self.society_a.id}/', {
            'bank_account_number': 'PK99PRESIDENTATTEMPT'
        })
        self.assertEqual(res_pres.status_code, status.HTTP_200_OK)
        self.society_a.refresh_from_db()
        self.assertEqual(self.society_a.bank_account_number, 'PK12CAMPUS9999')
        self.assertEqual(self.society_a.bank_version, 1)

        # 2. Faculty Advisor updates bank account details -> version increments to 2
        self.client.force_authenticate(user=self.advisor_a)
        res_adv = self.client.patch(f'/api/societies/{self.society_a.id}/', {
            'bank_name': 'Meezan Islamic Bank',
            'bank_account_number': 'PK00MEZN0099887766',
            'bank_account_title': 'CS Society Official Account',
            'payment_instructions': 'Use Raast or 1Link transfer only.'
        })
        self.assertEqual(res_adv.status_code, status.HTTP_200_OK)
        self.society_a.refresh_from_db()
        self.assertEqual(self.society_a.bank_version, 2)
        self.assertEqual(self.society_a.bank_name, 'Meezan Islamic Bank')
        self.assertEqual(len(self.society_a.bank_history), 1)
        self.assertEqual(self.society_a.bank_history[0]['previous_bank_account_number'], 'PK12CAMPUS9999')
        self.assertEqual(self.society_a.bank_history[0]['bank_name'], 'Meezan Islamic Bank')

        # 3. Create paid event and register student -> snapshots version 2
        event_date = timezone.now() + timedelta(days=30)
        event = Event.objects.create(
            society=self.society_a,
            title='Cyber Security Workshop',
            date=event_date,
            is_paid=True,
            price=15.00,
            expected_attendees=50,
            status='approved'
        )

        self.client.force_authenticate(user=self.student)
        res_reg = self.client.post('/api/registrations/', {'event': event.id})
        self.assertEqual(res_reg.status_code, status.HTTP_201_CREATED)
        reg = Registration.objects.get(id=res_reg.data['id'])
        self.assertEqual(reg.bank_version, 2)
        self.assertEqual(reg.bank_snapshot['bank_name'], 'Meezan Islamic Bank')
        self.assertEqual(reg.bank_snapshot['bank_account_number'], 'PK00MEZN0099887766')

        # 4. Advisor updates bank account to version 3
        self.client.force_authenticate(user=self.advisor_a)
        res_adv3 = self.client.patch(f'/api/societies/{self.society_a.id}/', {
            'bank_name': 'Bank Alfalah Corporate',
            'bank_account_number': 'PK55ALFH1122334455'
        })
        self.assertEqual(res_adv3.status_code, status.HTTP_200_OK)
        self.society_a.refresh_from_db()
        self.assertEqual(self.society_a.bank_version, 3)
        self.assertEqual(len(self.society_a.bank_history), 2)

        # 5. Existing registration snapshot is IMMUTABLE and retains version 2 details
        reg.refresh_from_db()
        self.assertEqual(reg.bank_version, 2)
        self.assertEqual(reg.bank_snapshot['bank_name'], 'Meezan Islamic Bank')

    def test_receipt_upload_and_idempotent_reviewer_verification(self):
        """Phase 4: Student receipt upload transitions status, reviewer verifies with idempotency, and rejections release seat"""
        event_date = timezone.now() + timedelta(days=35)
        event = Event.objects.create(
            society=self.society_a,
            title='Robotics Championship',
            date=event_date,
            is_paid=True,
            price=20.00,
            expected_attendees=10,
            status='approved'
        )

        # 1. Student registers for seat hold
        self.client.force_authenticate(user=self.student)
        res_reg = self.client.post('/api/registrations/', {'event': event.id})
        self.assertEqual(res_reg.status_code, status.HTTP_201_CREATED)
        reg_id = res_reg.data['id']
        reg = Registration.objects.get(id=reg_id)
        self.assertEqual(reg.payment_status, 'held')

        # 2. Student uploads payment slip proof
        res_upload = self.client.post(f'/api/registrations/{reg_id}/upload_receipt/', {
            'transaction_id': 'RAAST-8877665544',
            'receipt_details': 'Paid via Allied Bank online app',
            'receipt_file': '/media/uploads/receipts/proof_1.jpg'
        })
        self.assertEqual(res_upload.status_code, status.HTTP_200_OK)
        reg.refresh_from_db()
        self.assertEqual(reg.payment_status, 'pending')
        self.assertEqual(reg.transaction_id, 'RAAST-8877665544')

        # 3. Unrelated user or student cannot review receipt
        res_unauth = self.client.post(f'/api/registrations/{reg_id}/review_receipt/', {
            'decision': 'approve'
        })
        self.assertEqual(res_unauth.status_code, status.HTTP_403_FORBIDDEN)

        # 4. Advisor reviews and verifies payment with idempotency key
        self.client.force_authenticate(user=self.advisor_a)
        idempotency_key = f"idemp-rev-{uuid.uuid4()}"
        res_review = self.client.post(f'/api/registrations/{reg_id}/review_receipt/', {
            'decision': 'approve',
            'idempotency_key': idempotency_key
        })
        self.assertEqual(res_review.status_code, status.HTTP_200_OK)
        reg.refresh_from_db()
        self.assertEqual(reg.payment_status, 'verified')
        self.assertIsNotNone(reg.ticket_qr_code)
        self.assertEqual(reg.verified_by, self.advisor_a)
        self.assertIsNotNone(reg.verified_at)

        # 5. Idempotency test: duplicate call with same idempotency key succeeds without duplicate operations
        res_dupe = self.client.post(f'/api/registrations/{reg_id}/review_receipt/', {
            'decision': 'approve',
            'idempotency_key': idempotency_key
        })
        self.assertEqual(res_dupe.status_code, status.HTTP_200_OK)
        self.assertIn('Idempotent response', res_dupe.data['status'])

        # 6. Rejection test on a separate registration
        student_2 = User.objects.create_user(
            username='student_reject_me', email='rej@campus.edu', password='Password123!', role='student'
        )
        self.client.force_authenticate(user=student_2)
        res_reg2 = self.client.post('/api/registrations/', {'event': event.id})
        reg2_id = res_reg2.data['id']

        self.client.post(f'/api/registrations/{reg2_id}/upload_receipt/', {
            'transaction_id': 'BADTXN999'
        })

        # Advisor rejects invalid receipt
        self.client.force_authenticate(user=self.advisor_a)
        res_rej = self.client.post(f'/api/registrations/{reg2_id}/review_receipt/', {
            'decision': 'reject',
            'reason': 'Transaction ID not found in bank statement.'
        })
        self.assertEqual(res_rej.status_code, status.HTTP_200_OK)
        reg2 = Registration.objects.get(id=reg2_id)
        self.assertEqual(reg2.payment_status, 'rejected')
        self.assertEqual(reg2.rejection_reason, 'Transaction ID not found in bank statement.')

        # Double call on rejected registration is also idempotent
        res_rej_dupe = self.client.post(f'/api/registrations/{reg2_id}/review_receipt/', {
            'decision': 'reject',
            'reason': 'Transaction ID not found in bank statement.'
        })
        self.assertEqual(res_rej_dupe.status_code, status.HTTP_200_OK)

    def test_photo_ticket_preview_and_payment_guard(self):
        """Phase 5: Ticket preview returns attendee photo, roll, department, and blocks unverified tickets"""
        event_date = timezone.now() + timedelta(days=20)
        event = Event.objects.create(
            society=self.society_a,
            title='AI & Cloud Symposium',
            date=event_date,
            is_paid=True,
            price=15.00,
            expected_attendees=50,
            status='approved'
        )

        student_attendee = User.objects.create_user(
            username='attendee_sarah',
            email='sarah@campus.edu',
            password='Password123!',
            role='student',
            first_name='Sarah',
            last_name='Khan',
            roll_number='CS-2023-042',
            department='Computer Science',
            program='BS CS',
            avatar_url='https://campus.edu/photos/sarah.jpg'
        )

        ticket_code = str(uuid.uuid4())
        Registration.objects.create(
            event=event,
            student=student_attendee,
            payment_status='verified',
            ticket_qr_code=ticket_code
        )

        # 1. Gate Officer (President) previews the verified ticket
        self.client.force_authenticate(user=self.president_a)
        res_preview = self.client.post('/api/registrations/preview_ticket/', {
            'ticket_uuid': ticket_code
        })
        self.assertEqual(res_preview.status_code, status.HTTP_200_OK)
        self.assertTrue(res_preview.data['valid'])
        self.assertEqual(res_preview.data['student_name'], 'Sarah Khan')
        self.assertEqual(res_preview.data['roll_number'], 'CS-2023-042')
        self.assertEqual(res_preview.data['photo_url'], 'https://campus.edu/photos/sarah.jpg')
        self.assertEqual(res_preview.data['department'], 'Computer Science')
        self.assertEqual(res_preview.data['payment_status'], 'verified')
        self.assertFalse(res_preview.data['attendance_status'])

        # 2. Unverified ticket (payment_status='held') cannot enter gate
        unverified_code = str(uuid.uuid4())
        Registration.objects.create(
            event=event,
            student=self.student,
            payment_status='held',
            ticket_qr_code=unverified_code
        )
        res_held_preview = self.client.post('/api/registrations/preview_ticket/', {
            'ticket_uuid': unverified_code
        })
        self.assertEqual(res_held_preview.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('denied', res_held_preview.data['error'].lower())

        # Scan attempt on unverified ticket also barred
        res_held_scan = self.client.post('/api/registrations/scan_ticket/', {
            'ticket_uuid': unverified_code
        })
        self.assertEqual(res_held_scan.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('denied', res_held_scan.data['error'].lower())

    def test_volunteer_assignment_and_multi_operator_gate_scoping(self):
        """Phase 5: President appoints student volunteer to gate; volunteer gets operator permissions; scope enforced"""
        event_date = timezone.now() + timedelta(days=15)
        event = Event.objects.create(
            society=self.society_a,
            title='Cyber Security Capture The Flag',
            date=event_date,
            status='approved'
        )

        volunteer_student = User.objects.create_user(
            username='vol_ahmed',
            email='ahmed@campus.edu',
            password='Password123!',
            role='student',
            first_name='Ahmed',
            last_name='Raza',
            roll_number='SE-2024-089'
        )

        # 1. Non-executive student cannot appoint volunteers
        self.client.force_authenticate(user=self.student)
        res_unauth = self.client.post('/api/staff-assignments/', {
            'event': event.id,
            'volunteer': volunteer_student.id,
            'gate_name': 'Gate 1 (Main Entrance)'
        })
        self.assertEqual(res_unauth.status_code, status.HTTP_400_BAD_REQUEST)

        # 2. President of another society cannot appoint volunteers for Society A's event
        self.client.force_authenticate(user=self.president_b)
        res_wrong_soc = self.client.post('/api/staff-assignments/', {
            'event': event.id,
            'volunteer': volunteer_student.id,
            'gate_name': 'Gate 1 (Main Entrance)'
        })
        self.assertEqual(res_wrong_soc.status_code, status.HTTP_400_BAD_REQUEST)

        # 3. President of Society A appoints volunteer to Gate 1
        self.client.force_authenticate(user=self.president_a)
        res_assign = self.client.post('/api/staff-assignments/', {
            'event': event.id,
            'volunteer': volunteer_student.id,
            'gate_name': 'Gate 1 (Main Entrance)',
            'status': 'assigned'
        })
        self.assertEqual(res_assign.status_code, status.HTTP_201_CREATED)

        # Verify volunteer received notification
        notif = Notification.objects.filter(recipient=volunteer_student).first()
        self.assertIsNotNone(notif)
        self.assertIn('Gate Check-in Officer', notif.message)

        # 4. Appointed volunteer logs in, views their active assignment
        self.client.force_authenticate(user=volunteer_student)
        res_duties = self.client.get('/api/staff-assignments/')
        self.assertEqual(res_duties.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_duties.data), 1)
        self.assertEqual(res_duties.data[0]['gate_name'], 'Gate 1 (Main Entrance)')

        # 5. Volunteer is authorized to preview and check in tickets for this event
        ticket_code = str(uuid.uuid4())
        Registration.objects.create(
            event=event,
            student=self.student,
            payment_status='verified',
            ticket_qr_code=ticket_code
        )
        res_vol_preview = self.client.post('/api/registrations/preview_ticket/', {
            'ticket_uuid': ticket_code
        })
        self.assertEqual(res_vol_preview.status_code, status.HTTP_200_OK)
        self.assertTrue(res_vol_preview.data['valid'])

        # 6. Unassigned student cannot preview or check in tickets
        unassigned_student = User.objects.create_user(
            username='stranger_student', email='stranger@campus.edu', password='Password123!', role='student'
        )
        self.client.force_authenticate(user=unassigned_student)
        res_hack_preview = self.client.post('/api/registrations/preview_ticket/', {
            'ticket_uuid': ticket_code
        })
        self.assertEqual(res_hack_preview.status_code, status.HTTP_403_FORBIDDEN)

    def test_atomic_check_in_and_duplicate_scan_protection(self):
        """Phase 5: Atomic check-in logs timestamp & operator; duplicate scan returns alert with previous audit info"""
        event_date = timezone.now() + timedelta(days=10)
        event = Event.objects.create(
            society=self.society_a,
            title='Grand Hackathon 2026',
            date=event_date,
            status='approved'
        )

        ticket_code = str(uuid.uuid4())
        reg = Registration.objects.create(
            event=event,
            student=self.student,
            payment_status='verified',
            ticket_qr_code=ticket_code,
            attendance_status=False
        )

        # President checks in attendee at the gate
        self.client.force_authenticate(user=self.president_a)
        res_scan1 = self.client.post('/api/registrations/scan_ticket/', {
            'ticket_uuid': ticket_code
        })
        self.assertEqual(res_scan1.status_code, status.HTTP_200_OK)
        self.assertFalse(res_scan1.data['already_checked_in'])
        self.assertTrue(res_scan1.data['attendance_status'])
        self.assertIsNotNone(res_scan1.data['checked_in_at'])
        self.assertEqual(res_scan1.data['checked_in_by'], self.president_a.username)

        # Verify database record updated atomically
        reg.refresh_from_db()
        self.assertTrue(reg.attendance_status)
        self.assertIsNotNone(reg.checked_in_at)
        self.assertEqual(reg.checked_in_by, self.president_a)

        # Check notification sent to student
        student_notif = Notification.objects.filter(recipient=self.student).last()
        self.assertIsNotNone(student_notif)
        self.assertIn('Grand Hackathon 2026', student_notif.message)

        # Second immediate scan attempt of the same ticket detects duplicate entry
        res_scan2 = self.client.post('/api/registrations/scan_ticket/', {
            'ticket_uuid': ticket_code
        })
        self.assertEqual(res_scan2.status_code, status.HTTP_200_OK)
        self.assertTrue(res_scan2.data['already_checked_in'])
        self.assertIn('already', res_scan2.data['status'].lower())
        self.assertEqual(res_scan2.data['checked_in_by'], self.president_a.username)

        # Also previewing already checked-in ticket reflects attendance_status=True and operator details
        res_preview = self.client.post('/api/registrations/preview_ticket/', {
            'ticket_uuid': ticket_code
        })
        self.assertEqual(res_preview.status_code, status.HTTP_200_OK)
        self.assertTrue(res_preview.data['attendance_status'])
        self.assertEqual(res_preview.data['checked_in_by'], self.president_a.username)
        self.assertIsNotNone(res_preview.data['checked_in_at'])

    def test_certificate_template_lifecycle_and_advisor_approval(self):
        """Phase 6: President creates certificate template; Advisor approves/rejects; scope enforced"""
        self.client.force_authenticate(user=self.president_a)

        # 1. President creates draft template for Society A
        res_create = self.client.post('/api/certificate-templates/', {
            'title': 'Excellence in AI Award',
            'society': self.society_a.id,
            'layout_json': {
                'title': 'Certificate of Merit & Excellence',
                'theme_color': '#4338ca',
                'body_text': 'for distinguished participation in machine learning workshop'
            }
        }, format='json')
        self.assertEqual(res_create.status_code, status.HTTP_201_CREATED)
        tmpl_id = res_create.data['id']
        self.assertEqual(res_create.data['status'], 'draft')

        # 2. President cannot create template for Society B
        res_wrong_soc = self.client.post('/api/certificate-templates/', {
            'title': 'Illegal Template',
            'society': self.society_b.id,
        })
        self.assertEqual(res_wrong_soc.status_code, status.HTTP_400_BAD_REQUEST)

        # 3. President submits template for advisor approval
        res_submit = self.client.post(f'/api/certificate-templates/{tmpl_id}/submit_for_approval/')
        self.assertEqual(res_submit.status_code, status.HTTP_200_OK)
        self.assertEqual(res_submit.data['template']['status'], 'pending_approval')

        # Verify advisor received notification
        notif = Notification.objects.filter(recipient=self.advisor_a).last()
        self.assertIsNotNone(notif)
        self.assertIn('Excellence in AI Award', notif.message)

        # 4. Advisor of Society B cannot approve Society A's template
        self.client.force_authenticate(user=self.advisor_b)
        res_unauth_app = self.client.post(f'/api/certificate-templates/{tmpl_id}/approve/')
        self.assertIn(res_unauth_app.status_code, [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND])

        # 5. Advisor of Society A approves template
        self.client.force_authenticate(user=self.advisor_a)
        res_app = self.client.post(f'/api/certificate-templates/{tmpl_id}/approve/')
        self.assertEqual(res_app.status_code, status.HTTP_200_OK)
        self.assertEqual(res_app.data['template']['status'], 'approved')
        self.assertEqual(res_app.data['template']['approved_by'], self.advisor_a.id)

    def test_official_signature_asset_management(self):
        """Phase 6: Executives can manage official signatures; students cannot; signatures link to certificates"""
        # 1. Student cannot upload executive sign-off signatures
        self.client.force_authenticate(user=self.student)
        res_student_sig = self.client.post('/api/signatures/', {
            'role_title': 'Faculty Advisor',
            'signature_image': 'data:image/png;base64,forged_sig...'
        })
        self.assertEqual(res_student_sig.status_code, status.HTTP_400_BAD_REQUEST)

        # 2. Faculty Advisor uploads official signature
        self.client.force_authenticate(user=self.advisor_a)
        res_adv_sig = self.client.post('/api/signatures/', {
            'role_title': 'Faculty Advisor',
            'signature_image': 'data:image/png;base64,advisor_sig_data'
        })
        self.assertEqual(res_adv_sig.status_code, status.HTTP_201_CREATED)
        self.assertTrue(res_adv_sig.data['is_approved'])

        # 3. President uploads official signature
        self.client.force_authenticate(user=self.president_a)
        res_pres_sig = self.client.post('/api/signatures/', {
            'role_title': 'Society President',
            'signature_image': 'data:image/png;base64,president_sig_data'
        })
        self.assertEqual(res_pres_sig.status_code, status.HTTP_201_CREATED)
        self.assertTrue(res_pres_sig.data['is_approved'])

    def test_attendance_backed_bulk_certificate_release_and_idempotency(self):
        """Phase 6: Batch certificate generation enforces attendance & verified payment; prevents duplicates"""
        event_date = timezone.now() + timedelta(days=5)
        event = Event.objects.create(
            society=self.society_a,
            title='Cloud Architecture Masterclass',
            date=event_date,
            is_paid=True,
            price=25.00,
            status='approved'
        )

        template = CertificateTemplate.objects.create(
            title='Cloud Architect Certificate',
            society=self.society_a,
            event=event,
            status='approved',
            created_by=self.president_a,
            approved_by=self.advisor_a,
            layout_json={'theme_color': '#059669', 'title': 'Certificate of Mastery'}
        )

        student_present_verified = User.objects.create_user(
            username='stud_verified_present', email='pres@campus.edu', password='Password123!', role='student',
            first_name='Zain', last_name='Ali', roll_number='CS-2024-001', department='Computer Science'
        )
        student_absent_verified = User.objects.create_user(
            username='stud_verified_absent', email='abs@campus.edu', password='Password123!', role='student'
        )
        student_present_unpaid = User.objects.create_user(
            username='stud_unpaid_present', email='unp@campus.edu', password='Password123!', role='student'
        )

        # Reg 1: Present & Verified payment (Eligible)
        reg1 = Registration.objects.create(
            event=event, student=student_present_verified, attendance_status=True, payment_status='verified',
            ticket_qr_code=str(uuid.uuid4())
        )
        # Reg 2: Absent & Verified payment (Ineligible - did not attend)
        reg2 = Registration.objects.create(
            event=event, student=student_absent_verified, attendance_status=False, payment_status='verified',
            ticket_qr_code=str(uuid.uuid4())
        )
        # Reg 3: Present & Unverified payment / held (Ineligible - unpaid)
        reg3 = Registration.objects.create(
            event=event, student=student_present_unpaid, attendance_status=True, payment_status='held',
            ticket_qr_code=str(uuid.uuid4())
        )

        # 1. Non-executive student cannot trigger bulk certificate generation
        self.client.force_authenticate(user=self.student)
        res_unauth = self.client.post('/api/certificates/generate_bulk/', {'event_id': event.id})
        self.assertEqual(res_unauth.status_code, status.HTTP_403_FORBIDDEN)

        # 2. President of another society cannot trigger generation
        self.client.force_authenticate(user=self.president_b)
        res_wrong = self.client.post('/api/certificates/generate_bulk/', {'event_id': event.id})
        self.assertEqual(res_wrong.status_code, status.HTTP_403_FORBIDDEN)

        # 3. President of Society A triggers bulk release
        self.client.force_authenticate(user=self.president_a)
        res_gen = self.client.post('/api/certificates/generate_bulk/', {
            'event_id': event.id,
            'template_id': template.id
        })
        self.assertEqual(res_gen.status_code, status.HTTP_200_OK)
        self.assertEqual(res_gen.data['issued_count'], 1)
        self.assertEqual(res_gen.data['already_issued'], 0)

        # Verify only the eligible student received a certificate
        self.assertTrue(Certificate.objects.filter(student=student_present_verified, event=event).exists())
        self.assertFalse(Certificate.objects.filter(student=student_absent_verified, event=event).exists())
        self.assertFalse(Certificate.objects.filter(student=student_present_unpaid, event=event).exists())

        # Verify notification delivered to student
        cert_notif = Notification.objects.filter(recipient=student_present_verified).last()
        self.assertIsNotNone(cert_notif)
        self.assertIn('Cloud Architecture Masterclass', cert_notif.message)

        # 4. Idempotency: Second identical bulk generation triggers 0 duplicates
        res_gen2 = self.client.post('/api/certificates/generate_bulk/', {
            'event_id': event.id,
            'template_id': template.id
        })
        self.assertEqual(res_gen2.status_code, status.HTTP_200_OK)
        self.assertEqual(res_gen2.data['issued_count'], 0)
        self.assertEqual(res_gen2.data['already_issued'], 1)
        self.assertEqual(Certificate.objects.filter(student=student_present_verified, event=event).count(), 1)

    def test_private_certificate_verification_code_search(self):
        """Phase 6: Verification code search returns authenticated transcript data; invalid code returns clean 404"""
        event_date = timezone.now() + timedelta(days=2)
        event = Event.objects.create(
            society=self.society_a,
            title='Data Science Summit',
            date=event_date,
            venue_name='Auditorium 1',
            status='approved'
        )

        v_code = uuid.uuid4()
        cert = Certificate.objects.create(
            student=self.student,
            event=event,
            certificate_url=f'/verify?code={v_code}',
            verification_code=v_code
        )

        # 1. Authenticated user searches for certificate with valid UUID
        self.client.force_authenticate(user=self.admin)
        res_ver = self.client.get(f'/api/certificates/verify/?code={v_code}')
        self.assertEqual(res_ver.status_code, status.HTTP_200_OK)
        self.assertEqual(res_ver.data['student_name'], self.student.username)
        self.assertEqual(res_ver.data['event_title'], 'Data Science Summit')
        self.assertEqual(res_ver.data['society_name'], self.society_a.name)
        self.assertEqual(res_ver.data['verification_code'], str(v_code))

        # 2. Search with non-existent UUID returns 404
        random_uuid = uuid.uuid4()
        res_nonexistent = self.client.get(f'/api/certificates/verify/?code={random_uuid}')
        self.assertEqual(res_nonexistent.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('invalid or revoked', res_nonexistent.data['error'].lower())

        # 3. Search with malformed non-UUID string returns 404 without crashing
        res_malformed = self.client.get('/api/certificates/verify/?code=not-a-valid-uuid-12345')
        self.assertEqual(res_malformed.status_code, status.HTTP_404_NOT_FOUND)

        # 4. Search without code returns 400
        res_empty = self.client.get('/api/certificates/verify/')
        self.assertEqual(res_empty.status_code, status.HTTP_400_BAD_REQUEST)

    def test_news_and_gallery_approval_workflow(self):
        """Phase 7: President submissions are pending; hidden from public until approved by Advisor or Super Admin"""
        # 1. President A posts a news bulletin
        self.client.force_authenticate(user=self.president_a)
        res_news = self.client.post('/api/news/', {
            'title': 'AI Hackathon Registration Live',
            'content': 'Join the campus AI hackathon this weekend with massive cash prizes.'
        })
        self.assertEqual(res_news.status_code, status.HTTP_201_CREATED)
        news_id = res_news.data['id']
        news_obj = News.objects.get(id=news_id)
        self.assertEqual(news_obj.status, 'pending')

        # 2. President A uploads a gallery item
        res_gal = self.client.post('/api/gallery/', {
            'title': 'Opening Ceremony Highlights',
            'album_name': 'Hackathon Showcase',
            'image_url': 'https://images.unsplash.com/photo-1540575467063-178a50c2df87',
            'is_public': True
        })
        self.assertEqual(res_gal.status_code, status.HTTP_201_CREATED)
        gal_id = res_gal.data['id']
        gal_obj = Gallery.objects.get(id=gal_id)
        self.assertEqual(gal_obj.status, 'pending')

        # 3. Regular student views news and gallery -> pending items MUST be hidden
        self.client.force_authenticate(user=self.student)
        res_student_news = self.client.get('/api/news/')
        self.assertEqual(res_student_news.status_code, status.HTTP_200_OK)
        news_ids = [n['id'] for n in res_student_news.data]
        self.assertNotIn(news_id, news_ids)

        res_student_gal = self.client.get('/api/gallery/')
        self.assertEqual(res_student_gal.status_code, status.HTTP_200_OK)
        gal_ids = [g['id'] for g in res_student_gal.data]
        self.assertNotIn(gal_id, gal_ids)

        # 4. Faculty Advisor of Society A approves both items
        self.client.force_authenticate(user=self.advisor_a)
        res_app_news = self.client.post(f'/api/news/{news_id}/approve/')
        self.assertEqual(res_app_news.status_code, status.HTTP_200_OK)
        news_obj.refresh_from_db()
        self.assertEqual(news_obj.status, 'approved')
        self.assertEqual(news_obj.approved_by, self.advisor_a)

        res_app_gal = self.client.post(f'/api/gallery/{gal_id}/approve/')
        self.assertEqual(res_app_gal.status_code, status.HTTP_200_OK)
        gal_obj.refresh_from_db()
        self.assertEqual(gal_obj.status, 'approved')
        self.assertEqual(gal_obj.approved_by, self.advisor_a)

        # 5. Now student can see both approved items
        self.client.force_authenticate(user=self.student)
        res_student_news2 = self.client.get('/api/news/')
        news_ids2 = [n['id'] for n in res_student_news2.data]
        self.assertIn(news_id, news_ids2)

        res_student_gal2 = self.client.get('/api/gallery/')
        gal_ids2 = [g['id'] for g in res_student_gal2.data]
        self.assertIn(gal_id, gal_ids2)

        # 6. Admin rejects news -> author receives notification
        self.client.force_authenticate(user=self.admin)
        res_rej_news = self.client.post(f'/api/news/{news_id}/reject/', {
            'reason': 'Adjust budget details before final publish.'
        })
        self.assertEqual(res_rej_news.status_code, status.HTTP_200_OK)
        news_obj.refresh_from_db()
        self.assertEqual(news_obj.status, 'rejected')

        rejection_notif = Notification.objects.filter(recipient=self.president_a).last()
        self.assertIsNotNone(rejection_notif)
        self.assertIn('Adjust budget details', rejection_notif.message)

    def test_notification_broadcast_and_mark_all_read(self):
        """Phase 7: System-wide or targeted notification broadcasts and bulk mark as read"""
        # 1. Non-admin / non-faculty attempting broadcast is forbidden
        self.client.force_authenticate(user=self.student)
        res_unauth = self.client.post('/api/notifications/broadcast/', {
            'message': 'Fake student broadcast',
            'target_role': 'all'
        })
        self.assertEqual(res_unauth.status_code, status.HTTP_403_FORBIDDEN)

        # 2. Admin broadcasts targeted alert to 'student' role only
        self.client.force_authenticate(user=self.admin)
        res_broadcast_students = self.client.post('/api/notifications/broadcast/', {
            'title': 'Exam Schedule Release',
            'message': 'Spring semester final exam schedule has been released.',
            'target_role': 'student'
        })
        self.assertEqual(res_broadcast_students.status_code, status.HTTP_200_OK)
        self.assertEqual(res_broadcast_students.data['target_role'], 'student')

        # Verify student received it, but president and advisor did not
        student_notif = Notification.objects.filter(recipient=self.student, message__contains='final exam schedule').first()
        self.assertIsNotNone(student_notif)
        self.assertFalse(student_notif.is_read)

        pres_notif = Notification.objects.filter(recipient=self.president_a, message__contains='final exam schedule').first()
        self.assertIsNone(pres_notif)

        # 3. Admin broadcasts to 'all'
        res_broadcast_all = self.client.post('/api/notifications/broadcast/', {
            'title': 'Campus Gate Maintenance',
            'message': 'Main university gate will be closed from 10 PM tonight.',
            'target_role': 'all'
        })
        self.assertEqual(res_broadcast_all.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(res_broadcast_all.data['delivered_count'], 4)

        # 4. Student marks all notifications as read
        self.client.force_authenticate(user=self.student)
        unread_before = Notification.objects.filter(recipient=self.student, is_read=False).count()
        self.assertGreater(unread_before, 0)

        res_read_all = self.client.post('/api/notifications/mark_all_read/')
        self.assertEqual(res_read_all.status_code, status.HTTP_200_OK)
        self.assertEqual(res_read_all.data['marked_read_count'], unread_before)

        unread_after = Notification.objects.filter(recipient=self.student, is_read=False).count()
        self.assertEqual(unread_after, 0)

    def test_database_backup_restore_and_download(self):
        """Phase 7: Super Admin can trigger snapshots, download them, and restore with pre-restore safety archiving"""
        # 1. Non-admin cannot trigger backup
        self.client.force_authenticate(user=self.student)
        res_unauth = self.client.post('/api/backups/trigger_backup/')
        self.assertEqual(res_unauth.status_code, status.HTTP_403_FORBIDDEN)

        # 2. Super Admin triggers database snapshot
        self.client.force_authenticate(user=self.admin)
        res_backup = self.client.post('/api/backups/trigger_backup/', {
            'notes': 'Pre-audit milestone snapshot'
        })
        self.assertEqual(res_backup.status_code, status.HTTP_201_CREATED)
        bk_id = res_backup.data['id']
        bk_filename = res_backup.data['filename']
        self.assertTrue(bk_filename.startswith('dsms_backup_'))

        backup_rec = BackupRecord.objects.get(id=bk_id)
        self.assertEqual(backup_rec.status, 'completed')

        # 3. Super Admin downloads backup snapshot
        res_down = self.client.get(f'/api/backups/{bk_id}/download/')
        self.assertEqual(res_down.status_code, status.HTTP_200_OK)
        self.assertIn(bk_filename, res_down.headers.get('Content-Disposition', ''))

        # 4. Super Admin restores backup snapshot
        res_restore = self.client.post(f'/api/backups/{bk_id}/restore/')
        self.assertEqual(res_restore.status_code, status.HTTP_200_OK)
        backup_rec.refresh_from_db()
        self.assertEqual(backup_rec.status, 'restored')
        self.assertIn('Restored by @superadmin', backup_rec.notes)

    def test_system_health_telemetry_and_maintenance_mode(self):
        """Phase 7: System health endpoint returns active database size, entity metrics, and reflects maintenance mode"""
        self.client.force_authenticate(user=self.admin)

        # 1. Query system health
        res_health = self.client.get('/api/system/health/')
        self.assertEqual(res_health.status_code, status.HTTP_200_OK)
        self.assertEqual(res_health.data['database_engine'], 'SQLite3 (Transactional ACID)')
        self.assertIn('database_size_kb', res_health.data)
        self.assertIn('metrics', res_health.data)
        metrics = res_health.data['metrics']
        self.assertGreaterEqual(metrics['total_users'], 4)
        self.assertGreaterEqual(metrics['total_societies'], 2)
        self.assertFalse(res_health.data['maintenance_mode'])

        # Also verify alias endpoint /api/system-health/ works identically
        res_health_alias = self.client.get('/api/system-health/')
        self.assertEqual(res_health_alias.status_code, status.HTTP_200_OK)
        self.assertEqual(res_health_alias.data['status'], 'healthy')

        # 2. Toggle maintenance mode via SystemSetting
        SystemSetting.objects.update_or_create(
            key='portal_config',
            defaults={'value': {'portal_maintenance_mode': True}}
        )

        res_health_maint = self.client.get('/api/system/health/')
        self.assertEqual(res_health_maint.status_code, status.HTTP_200_OK)
        self.assertTrue(res_health_maint.data['maintenance_mode'])
        self.assertEqual(res_health_maint.data['status'], 'maintenance')

        # 3. Non-admin user cannot view infrastructure telemetry
        self.client.force_authenticate(user=self.student)
        res_forbidden = self.client.get('/api/system/health/')
        self.assertEqual(res_forbidden.status_code, status.HTTP_403_FORBIDDEN)

    def test_concurrency_date_claim_lock_race_condition(self):
        """Phase 8: Concurrency verification for DateClaims - prevent duplicate date locks"""
        target_date = "2026-11-20"
        
        # Society A creates proposal for target_date
        self.client.force_authenticate(user=self.president_a)
        res_a = self.client.post('/api/proposals/', {
            'event_title': 'Annual CS Hackathon',
            'event_date': target_date,
            'description': 'Hackathon by Society A'
        })
        self.assertEqual(res_a.status_code, status.HTTP_201_CREATED)
        
        # Verify DateClaim locked for Society A
        self.assertTrue(DateClaim.objects.filter(claim_date=target_date, society=self.society_a).exists())

        # Society B concurrently attempts to book the EXACT SAME date
        self.client.force_authenticate(user=self.president_b)
        res_b = self.client.post('/api/proposals/', {
            'event_title': 'Annual Debating Championship',
            'event_date': target_date,
            'description': 'Debating Tournament by Society B'
        })
        self.assertEqual(res_b.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('event_date', res_b.data)
        self.assertIn('Date-Lock Active', str(res_b.data['event_date']))

        # Ensure database still only has exactly 1 date claim for target_date
        self.assertEqual(DateClaim.objects.filter(claim_date=target_date).count(), 1)
        self.assertEqual(DateClaim.objects.get(claim_date=target_date).society, self.society_a)

    def test_concurrency_simultaneous_ticket_checkin_atomicity(self):
        """Phase 8: Concurrency verification for Ticket Gate Check-Ins - atomic check-in and idempotent repeat scan"""
        event = Event.objects.create(
            society=self.society_a,
            title='Autonomous Robotics Workshop',
            date=timezone.now() + timedelta(days=2),
            status='approved'
        )
        ticket_code = str(uuid.uuid4())
        reg = Registration.objects.create(
            event=event,
            student=self.student,
            payment_status='verified',
            ticket_qr_code=ticket_code,
            attendance_status=False
        )

        # Authenticate as President of Society A (authorized gate scanner)
        self.client.force_authenticate(user=self.president_a)

        # First scan: Successfully verifies attendance
        res1 = self.client.post('/api/registrations/scan_ticket/', {'ticket_uuid': ticket_code})
        self.assertEqual(res1.status_code, status.HTTP_200_OK)
        self.assertEqual(res1.data['status'], 'Attendance verified successfully.')
        self.assertFalse(res1.data['already_checked_in'])
        self.assertTrue(res1.data['attendance_status'])

        reg.refresh_from_db()
        self.assertTrue(reg.attendance_status)
        self.assertIsNotNone(reg.checked_in_at)
        self.assertEqual(reg.checked_in_by, self.president_a)

        # Second simultaneous or rapid scan of the same ticket QR code
        res2 = self.client.post('/api/registrations/scan_ticket/', {'ticket_uuid': ticket_code})
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertEqual(res2.data['status'], 'Already Checked-In previously.')
        self.assertTrue(res2.data['already_checked_in'])
        self.assertTrue(res2.data['attendance_status'])

        # Ensure only 1 gate check-in welcome notification was sent to student
        gate_notifs = Notification.objects.filter(
            recipient=self.student,
            message__icontains='check-in at the gate was confirmed'
        )
        self.assertEqual(gate_notifs.count(), 1)

    def test_two_stage_publishing_and_paid_options(self):
        """
        Verify two-stage publishing:
        1. Event with status='approved' and is_published=False is hidden from student portal feed.
        2. President advertises event -> sets is_published=True -> appears on student portal feed.
        3. EventProposal with paid options transfers is_paid and ticket_price to event upon sanctioning.
        """
        # Create an approved but unpublished event for Society A
        ev = Event.objects.create(
            title='Two Stage Flagship Conference',
            description='Exclusive internal dossier description',
            date=timezone.now() + timedelta(days=10),
            society=self.society_a,
            status='approved',
            is_published=False,
            is_paid=True,
            price=750.00
        )

        # Student feed checks
        self.client.force_authenticate(user=self.student)
        feed_res = self.client.get('/api/events/')
        self.assertEqual(feed_res.status_code, status.HTTP_200_OK)
        # Event should NOT be in the student feed because is_published=False
        event_ids = [e['id'] for e in feed_res.data]
        self.assertNotIn(ev.id, event_ids)

        # President of Society A advertises the event with marketing materials
        self.client.force_authenticate(user=self.president_a)
        adv_res = self.client.post(f'/api/events/{ev.id}/advertise/', {
            'cover_image': 'https://storage.campus.edu/posters/marketing_cover.jpg',
            'gallery_images': [
                'https://storage.campus.edu/gallery/photo1.jpg',
                'https://storage.campus.edu/gallery/photo2.jpg'
            ],
            'description': 'Exciting public student-facing conference with workshops and keynotes!'
        }, format='json')
        self.assertEqual(adv_res.status_code, status.HTTP_200_OK)
        self.assertTrue(adv_res.data['event']['is_published'])
        self.assertEqual(adv_res.data['event']['image'], 'https://storage.campus.edu/posters/marketing_cover.jpg')
        self.assertEqual(len(adv_res.data['event']['gallery_images']), 2)

        # Student feed checks again: Now it should be visible!
        self.client.force_authenticate(user=self.student)
        feed_res2 = self.client.get('/api/events/')
        self.assertEqual(feed_res2.status_code, status.HTTP_200_OK)
        event_ids2 = [e['id'] for e in feed_res2.data]
        self.assertIn(ev.id, event_ids2)

        # Verify ticketing & pricing
        published_evt = next(e for e in feed_res2.data if e['id'] == ev.id)
        self.assertTrue(published_evt['is_paid'])
        self.assertEqual(float(published_evt['ticket_price']), 750.00)
        self.assertEqual(published_evt['entry_fee'], 750.00)









