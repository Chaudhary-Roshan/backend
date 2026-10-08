from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenRefreshView,
)
from .views import (
    RegisterView, VerifyOTPView, ResendOTPView, ProfileView, CustomTokenObtainPairView,
    ChangePasswordView, ForgotPasswordView, ResetPasswordView,
    FileUploadView, UserViewSet, SocietyViewSet, EventViewSet, 
    RegistrationViewSet, NewsViewSet, GalleryViewSet, CertificateViewSet, NotificationViewSet, 
    RecruitmentViewSet, RecruitmentApplicationViewSet, CabinetMemberViewSet, VenueViewSet, 
    MembershipViewSet, MessageViewSet, EventFeedbackViewSet, EventResourceViewSet, BudgetViewSet, 
    SponsorshipViewSet, VolunteerHourViewSet, EquipmentViewSet, EventEquipmentRequestViewSet, 
    ComplaintViewSet, EventProposalViewSet, DateClaimViewSet, EventStaffAssignmentViewSet,
    SignatureAssetViewSet, CertificateTemplateViewSet,
    SystemSettingViewSet, BackupRecordViewSet, SystemHealthView,
    VerifyMembershipView, VerifyTicketView,
    VerifyUserByRollNumberView, ManualTicketIssueView, BulkTicketIssueView,
    PendingRegistrationsView, PayRegistrationView, VerifyRegistrationView
)

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'societies', SocietyViewSet)
router.register(r'events', EventViewSet)
router.register(r'registrations', RegistrationViewSet)
router.register(r'news', NewsViewSet)
router.register(r'gallery', GalleryViewSet)
router.register(r'certificates', CertificateViewSet)
router.register(r'notifications', NotificationViewSet, basename='notification')
router.register(r'recruitments', RecruitmentViewSet)
router.register(r'applications', RecruitmentApplicationViewSet)
router.register(r'cabinet', CabinetMemberViewSet)
router.register(r'venues', VenueViewSet)
router.register(r'memberships', MembershipViewSet)
router.register(r'messages', MessageViewSet)
router.register(r'feedbacks', EventFeedbackViewSet)
router.register(r'resources', EventResourceViewSet)
router.register(r'budgets', BudgetViewSet)
router.register(r'sponsorships', SponsorshipViewSet)
router.register(r'volunteer-hours', VolunteerHourViewSet)
router.register(r'equipment', EquipmentViewSet)
router.register(r'equipment-requests', EventEquipmentRequestViewSet)
router.register(r'complaints', ComplaintViewSet)
router.register(r'proposals', EventProposalViewSet)
router.register(r'date-claims', DateClaimViewSet)
router.register(r'staff-assignments', EventStaffAssignmentViewSet)
router.register(r'signatures', SignatureAssetViewSet)
router.register(r'certificate-templates', CertificateTemplateViewSet)
router.register(r'system-settings', SystemSettingViewSet)
router.register(r'backups', BackupRecordViewSet)

urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='auth_register'),
    path('auth/verify-otp/', VerifyOTPView.as_view(), name='auth_verify_otp'),
    path('auth/resend-otp/', ResendOTPView.as_view(), name='auth_resend_otp'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify_otp'),
    path('verify-otp', VerifyOTPView.as_view(), name='verify_otp_no_slash'),
    path('auth/login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('login/', CustomTokenObtainPairView.as_view(), name='login_direct'),
    path('login', CustomTokenObtainPairView.as_view(), name='login_direct_no_slash'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/profile/', ProfileView.as_view(), name='auth_profile'),
    path('auth/change-password/', ChangePasswordView.as_view(), name='auth_change_password'),
    path('auth/forgot-password/', ForgotPasswordView.as_view(), name='auth_forgot_password'),
    path('auth/reset-password/', ResetPasswordView.as_view(), name='auth_reset_password'),
    path('upload/', FileUploadView.as_view(), name='file_upload'),
    path('system/health/', SystemHealthView.as_view(), name='system_health'),
    path('system-health/', SystemHealthView.as_view(), name='system_health_alt'),
    # Public QR verification endpoints (no authentication required)
    path('verify/member/<str:card_qr_code>/', VerifyMembershipView.as_view(), name='verify_membership'),
    path('verify/ticket/<str:ticket_qr_code>/', VerifyTicketView.as_view(), name='verify_ticket'),
    
    # User Verification for Ticketing
    path('users/verify/<str:roll_number>/', VerifyUserByRollNumberView.as_view(), name='verify_user_roll'),
    path('users/verify/<str:roll_number>', VerifyUserByRollNumberView.as_view(), name='verify_user_roll_no_slash'),

    # Manual Single and Bulk Ticketing
    path('tickets/manual-issue/', ManualTicketIssueView.as_view(), name='tickets_manual_issue'),
    path('tickets/manual-issue', ManualTicketIssueView.as_view(), name='tickets_manual_issue_no_slash'),
    path('tickets/bulk-issue/', BulkTicketIssueView.as_view(), name='tickets_bulk_issue'),
    path('tickets/bulk-issue', BulkTicketIssueView.as_view(), name='tickets_bulk_issue_no_slash'),

    # Student Payment Submission & Verification Desk Endpoints
    path('registrations/pending/', PendingRegistrationsView.as_view(), name='registrations_pending'),
    path('registrations/pending', PendingRegistrationsView.as_view(), name='registrations_pending_no_slash'),
    path('registrations/pay/', PayRegistrationView.as_view(), name='registrations_pay'),
    path('registrations/pay', PayRegistrationView.as_view(), name='registrations_pay_no_slash'),
    path('registrations/<int:pk>/verify/', VerifyRegistrationView.as_view(), name='registrations_verify'),
    path('registrations/<int:pk>/verify', VerifyRegistrationView.as_view(), name='registrations_verify_no_slash'),

    path('', include(router.urls)),
]
