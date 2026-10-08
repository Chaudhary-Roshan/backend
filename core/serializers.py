from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.db import models
from .models import User, Society, Event

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        resolved_id = self.initial_data.get('_resolved_user_id')
        user_candidate = None

        if resolved_id:
            user_candidate = User.objects.filter(id=resolved_id).first()

        if not user_candidate:
            identity = (
                self.initial_data.get('identifier') or 
                self.initial_data.get('email') or 
                self.initial_data.get('roll_number') or
                attrs.get(self.username_field) or 
                self.initial_data.get('username')
            )
            if identity:
                ident_clean = str(identity).strip()
                # Query strictly against email and roll_number. Ignore username column.
                user_candidate = User.objects.filter(
                    models.Q(email__iexact=ident_clean.lower()) |
                    models.Q(university_email__iexact=ident_clean.lower()) |
                    models.Q(roll_number__iexact=ident_clean.upper())
                ).first()

        if not user_candidate:
            raise serializers.ValidationError({
                'detail': 'Account not found. Please use your registered Email or Roll Number.'
            })

        password = attrs.get('password', '') or self.initial_data.get('password', '')
        if not user_candidate.check_password(password):
            raise serializers.ValidationError({
                'detail': 'Invalid credentials.'
            })

        if not user_candidate.is_active:
            raise serializers.ValidationError({
                'detail': 'This university account has been deactivated or suspended. Please contact the administrator.',
                'is_active': False
            })
        if not user_candidate.is_email_verified or not getattr(user_candidate, 'is_verified', True):
            raise serializers.ValidationError({
                'detail': 'Account verification required. Please verify your OTP to activate your account.',
                'requires_otp': True,
                'email': user_candidate.email,
                'username': user_candidate.username,
                'user_id': user_candidate.id
            })
        attrs[self.username_field] = user_candidate.username

        data = super().validate(attrs)
        if not self.user.is_email_verified or not getattr(self.user, 'is_verified', True):
            raise serializers.ValidationError({
                'detail': 'Account verification required. Please verify your OTP to activate your account.',
                'requires_otp': True,
                'email': self.user.email,
                'username': self.user.username,
                'user_id': self.user.id
            })

        data['user'] = UserSerializer(self.user).data
        return data

class UserSerializer(serializers.ModelSerializer):
    society_name = serializers.SerializerMethodField()
    society_logo = serializers.CharField(source='society.logo', read_only=True, default='')
    society = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    is_cabinet_member = serializers.SerializerMethodField()
    cabinet_role = serializers.SerializerMethodField()
    cabinet_society_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name', 'name',
            'role', 'gender', 'date_of_birth', 'profile_photo_url', 'student_designation',
            'society', 'society_name', 'society_logo',
            'roll_number', 'university_email', 'father_name', 'cnic', 'program', 'department', 'batch', 'semester',
            'faculty_name', 'phone_number', 'avatar_url',
            'is_cabinet_member', 'cabinet_role', 'cabinet_society_name',
            'is_active', 'is_email_verified', 'is_verified', 'date_joined', 'last_login'
        ]
        read_only_fields = [
            'role', 'society', 'is_active', 'is_email_verified', 'is_verified', 'date_joined', 'last_login',
            'roll_number', 'university_email', 'student_designation'
        ]

    def get_society(self, obj):
        if obj.society:
            return obj.society.id
        if obj.role == 'president' and hasattr(obj, 'presided_societies'):
            first_pres = obj.presided_societies.first()
            if first_pres:
                return first_pres.id
        if obj.role == 'faculty' and hasattr(obj, 'advised_societies'):
            first_adv = obj.advised_societies.first()
            if first_adv:
                return first_adv.id
        return None

    def get_society_name(self, obj):
        if obj.society:
            return obj.society.name
        if obj.role == 'president' and hasattr(obj, 'presided_societies'):
            first_pres = obj.presided_societies.first()
            if first_pres:
                return first_pres.name
        if obj.role == 'faculty' and hasattr(obj, 'advised_societies'):
            first_adv = obj.advised_societies.first()
            if first_adv:
                return first_adv.name
        return None

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username

    def get_name(self, obj):
        return obj.get_full_name() or obj.first_name or obj.username

    def get_is_cabinet_member(self, obj):
        if obj.role == 'president':
            return True
        if hasattr(obj, 'cabinet_positions') and obj.cabinet_positions.filter(is_active=True, is_verified=True).exists():
            return True
        return False

    def get_cabinet_role(self, obj):
        if obj.role == 'president':
            return 'President'
        if hasattr(obj, 'cabinet_positions'):
            active_cab = obj.cabinet_positions.filter(is_active=True, is_verified=True).first()
            if active_cab and active_cab.role_title:
                return active_cab.role_title
        return ''

    def get_cabinet_society_name(self, obj):
        if hasattr(obj, 'cabinet_positions'):
            active_cab = obj.cabinet_positions.filter(is_active=True, is_verified=True).select_related('society').first()
            if active_cab and active_cab.society:
                return active_cab.society.name
        if obj.society:
            return obj.society.name
        if obj.role == 'president' and hasattr(obj, 'presided_societies'):
            first_pres = obj.presided_societies.first()
            if first_pres:
                return first_pres.name
        return ''

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        can_view_private_fields = bool(
            request and request.user.is_authenticated and
            (request.user.role == 'admin' or request.user == instance)
        )
        if not can_view_private_fields:
            for field in ['email', 'date_of_birth', 'father_name', 'cnic', 'phone_number']:
                data[field] = None if field == 'date_of_birth' else ''
        return data


class UserAdminCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    society_name = serializers.CharField(source='society.name', read_only=True)
    is_active = serializers.BooleanField(default=True)
    is_email_verified = serializers.BooleanField(default=True)
    is_verified = serializers.BooleanField(default=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'password', 'first_name', 'last_name', 
            'role', 'gender', 'date_of_birth', 'profile_photo_url', 'student_designation', 'society', 'society_name',
            'roll_number', 'father_name', 'cnic', 'program', 'department', 'batch', 'semester',
            'faculty_name', 'phone_number', 'avatar_url',
            'is_cabinet_member', 'cabinet_role', 'cabinet_society_name',
            'is_active', 'is_email_verified', 'is_verified', 'date_joined', 'last_login'
        ]
        read_only_fields = ['date_joined', 'last_login']

    def create(self, validated_data):
        password = validated_data.pop('password', None) or 'P@ssword123'
        if 'is_active' not in validated_data:
            validated_data['is_active'] = True
        if 'is_email_verified' not in validated_data:
            validated_data['is_email_verified'] = True
        if 'is_verified' not in validated_data:
            validated_data['is_verified'] = True
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        if password:
            instance.set_password(password)
        instance.save()
        return instance

import random
from django.utils import timezone

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    gender = serializers.CharField(required=False, allow_blank=True, default='')
    roll_number = serializers.CharField(required=False, allow_blank=True, default='')
    university_email = serializers.CharField(required=False, allow_blank=True, default='')
    cnic = serializers.CharField(required=False, allow_blank=True, default='')
    department = serializers.CharField(required=False, allow_blank=True, default='Department Of information and Communication Engineering')
    program = serializers.CharField(required=False, allow_blank=True, default='')
    batch = serializers.CharField(required=False, allow_blank=True, default='')
    semester = serializers.CharField(required=False, allow_blank=True, default='')
    phone_number = serializers.CharField(required=False, allow_blank=True, default='')
    avatar_url = serializers.CharField(required=False, allow_blank=True, default='')
    profile_photo_url = serializers.CharField(required=False, allow_blank=True, default='')
    date_of_birth = serializers.DateField(required=False, allow_null=True, default=None)
    username = serializers.CharField(required=False, allow_blank=True)
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'first_name', 'last_name', 'gender',
            'roll_number', 'university_email', 'cnic', 'department', 'program', 'batch', 'semester',
            'phone_number', 'avatar_url', 'profile_photo_url', 'date_of_birth'
        ]
        
    def validate_email(self, value):
        normalized = value.strip().lower()
        return normalized

    def create(self, validated_data):
        # Strict security constraint: Public self-registration ALWAYS creates a student account only.
        # President, Faculty, and Admin accounts MUST be provisioned exclusively by Super Admin.
        otp_code = f"{random.randint(100000, 999999)}"
        roll = (validated_data.get('roll_number') or '').strip().upper()
        uni_email = (validated_data.get('university_email') or '').strip().lower()
        if not uni_email and roll:
            uni_email = f"{roll}@iub.edu.pk".lower()

        dept = validated_data.get('department') or 'Department Of information and Communication Engineering'
        
        username = validated_data.get('username')
        if not username:
            if roll:
                base_username = roll.replace(' ', '').lower()
            else:
                base_username = validated_data.get('email', '').split('@')[0]
                
            username = base_username
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{random.randint(100, 9999)}"

        user = User.objects.create_user(
            username=username,
            email=validated_data.get('email', '').strip().lower(),
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            role='student',
            gender=validated_data.get('gender', ''),
            roll_number=roll,
            university_email=uni_email,
            cnic=validated_data.get('cnic', ''),
            department=dept,
            program=validated_data.get('program', ''),
            batch=validated_data.get('batch', ''),
            semester=validated_data.get('semester', ''),
            phone_number=validated_data.get('phone_number', ''),
            avatar_url=validated_data.get('avatar_url', ''),
            profile_photo_url=validated_data.get('profile_photo_url', ''),
            date_of_birth=validated_data.get('date_of_birth'),
            is_email_verified=False,
            is_verified=False,
            otp_code=otp_code,
            otp_created_at=timezone.now(),
            otp_attempts=0
        )
        return user


from .models import (
    Registration, News, Gallery, Certificate, Notification, 
    Recruitment, RecruitmentApplication, CabinetMember,
    Venue, Membership, Message, EventFeedback, EventResource,
    Budget, Sponsorship, VolunteerHour, Equipment, EventEquipmentRequest, Complaint,
    EventProposal, DateClaim, EventStaffAssignment, SignatureAsset, CertificateTemplate,
    SystemSetting, BackupRecord
)

class CabinetMemberSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    student_username = serializers.CharField(write_only=True, required=True)
    society_name = serializers.CharField(source='society.name', read_only=True)
    full_name = serializers.SerializerMethodField()
    roll_number = serializers.CharField(source='user.roll_number', read_only=True)
    father_name = serializers.SerializerMethodField()
    program = serializers.SerializerMethodField()
    faculty_name = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    phone_number = serializers.SerializerMethodField()
    department = serializers.CharField(source='user.department', read_only=True)
    semester = serializers.CharField(source='user.semester', read_only=True)
    cnic = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    student_id = serializers.IntegerField(source='user.id', read_only=True)

    class Meta:
        model = CabinetMember
        fields = '__all__'
        read_only_fields = ['is_verified', 'user', 'society']

    def get_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username

    def can_view_private_profile(self):
        request = self.context.get('request')
        return bool(request and request.user.is_authenticated and request.user.role in ['admin', 'faculty', 'president'])

    def get_cnic(self, obj):
        return obj.user.cnic if self.can_view_private_profile() else ''

    def get_father_name(self, obj):
        return obj.user.father_name if self.can_view_private_profile() else ''

    def get_program(self, obj):
        return obj.user.program if self.can_view_private_profile() else ''

    def get_faculty_name(self, obj):
        return obj.user.faculty_name if self.can_view_private_profile() else ''

    def get_email(self, obj):
        return obj.user.email if self.can_view_private_profile() else ''

    def get_phone_number(self, obj):
        return obj.user.phone_number if self.can_view_private_profile() else ''

    def get_avatar_url(self, obj):
        return obj.user.avatar_url or getattr(obj.user, 'profile_photo_url', '') or ''

    def create(self, validated_data):
        username = validated_data.pop('student_username').strip()
        user = User.objects.filter(username__iexact=username).first()
        if not user:
            user = User.objects.filter(roll_number__iexact=username).first()
        if not user:
            user = User.objects.filter(roll_number__icontains=username).first()
        if not user:
            raise serializers.ValidationError({'student_username': f"No student found with username or roll number '{username}'."})
        
        society = validated_data.get('society')
        
        # Check if the student is an active member of this society
        if not Membership.objects.filter(student=user, society=society, status='active').exists():
            raise serializers.ValidationError({'student_username': f"Cannot induct: Student '{user.full_name or user.username}' is not an active verified member of this society."})
            
        term_year = validated_data.get('term_year', '')
        if society and CabinetMember.objects.filter(society=society, user=user, term_year=term_year).exists():
            raise serializers.ValidationError({'student_username': f"Student '{user.username}' is already an inducted cabinet member for term {term_year}."})
            
        return CabinetMember.objects.create(user=user, **validated_data)

class SocietySerializer(serializers.ModelSerializer):
    advisor_name = serializers.CharField(source='advisor.username', read_only=True)
    advisor_full_name = serializers.SerializerMethodField()
    advisor_avatar_url = serializers.SerializerMethodField()
    advisor_profile_picture_url = serializers.SerializerMethodField()
    advisor_email = serializers.CharField(source='advisor.email', read_only=True, default='')
    advisor_department = serializers.CharField(source='advisor.department', read_only=True, default='')
    president_name = serializers.CharField(source='president.username', read_only=True)
    president_full_name = serializers.SerializerMethodField()
    president_avatar_url = serializers.SerializerMethodField()
    president_profile_picture_url = serializers.SerializerMethodField()
    president_email = serializers.CharField(source='president.email', read_only=True, default='')
    president_department = serializers.CharField(source='president.department', read_only=True, default='')
    payment_qr_url = serializers.CharField(source='payment_qr', read_only=True, default='')
    account_title = serializers.CharField(source='bank_account_title', read_only=True, default='')
    account_iban = serializers.CharField(source='bank_account_number', read_only=True, default='')
    cabinet_members = CabinetMemberSerializer(many=True, read_only=True)

    class Meta:
        model = Society
        fields = '__all__'

    def to_internal_value(self, data):
        # Convert QueryDict to a plain dict to avoid mutability/stringification issues
        parsed_data = {}
        for key in data:
            if hasattr(data, 'getlist') and len(data.getlist(key)) > 1:
                parsed_data[key] = data.getlist(key)
            else:
                parsed_data[key] = data[key]

        if 'social_links' in parsed_data and isinstance(parsed_data['social_links'], str):
            import json
            try:
                parsed_data['social_links'] = json.loads(parsed_data['social_links'])
            except Exception:
                pass
        
        if 'president' in parsed_data and parsed_data['president'] == '':
            parsed_data.pop('president')
        if 'advisor' in parsed_data and parsed_data['advisor'] == '':
            parsed_data.pop('advisor')

        if 'payment_qr' in parsed_data and not isinstance(parsed_data['payment_qr'], str):
            parsed_data.pop('payment_qr')

        return super().to_internal_value(parsed_data)

    def get_president_full_name(self, obj):
        if obj.president:
            return obj.president.get_full_name() or obj.president.username
        return ""

    def get_president_avatar_url(self, obj):
        if obj.president:
            return obj.president.avatar_url or getattr(obj.president, 'profile_photo_url', '') or ""
        return ""

    def get_president_profile_picture_url(self, obj):
        return self.get_president_avatar_url(obj)

    def get_advisor_full_name(self, obj):
        if obj.advisor:
            return obj.advisor.get_full_name() or obj.advisor.username
        return ""

    def get_advisor_avatar_url(self, obj):
        if obj.advisor:
            return obj.advisor.avatar_url or getattr(obj.advisor, 'profile_photo_url', '') or ""
        return ""

    def get_advisor_profile_picture_url(self, obj):
        return self.get_advisor_avatar_url(obj)

class EventSerializer(serializers.ModelSerializer):
    society_name = serializers.CharField(source='society.name', read_only=True)
    society_logo = serializers.CharField(source='society.logo', read_only=True, default='')
    effective_payment_qr = serializers.SerializerMethodField()
    society = serializers.PrimaryKeyRelatedField(queryset=Society.objects.all(), required=False)
    society_advisor = serializers.CharField(source='society.advisor.username', read_only=True)
    society_advisor_name = serializers.SerializerMethodField()
    society_president_name = serializers.SerializerMethodField()
    poster_image_url = serializers.CharField(source='image', required=False, allow_blank=True)
    entry_fee = serializers.SerializerMethodField()
    date_time = serializers.SerializerMethodField()
    speakers = serializers.SerializerMethodField()
    detailed_description = serializers.CharField(source='description', read_only=True)
    ticket_price = serializers.DecimalField(source='price', max_digits=10, decimal_places=2, required=False)

    class Meta:
        model = Event
        fields = '__all__'

    def get_entry_fee(self, obj):
        if not obj.is_paid:
            return 0
        try:
            return float(obj.price)
        except Exception:
            return 0

    def get_date_time(self, obj):
        if obj.date:
            try:
                return obj.date.strftime("%b %d, %Y at %I:%M %p")
            except Exception:
                return str(obj.date)
        return "To be announced"

    def get_speakers(self, obj):
        if obj.chief_guest:
            return [s.strip() for s in obj.chief_guest.split(',') if s.strip()]
        return ["Distinguished Guest Speakers"]

    def get_effective_payment_qr(self, obj):
        return obj.payment_qr or (obj.society.payment_qr if obj.society else '')

    def get_society_advisor_name(self, obj):
        if obj.society.advisor:
            return obj.society.advisor.get_full_name() or obj.society.advisor.username
        return "Dr. Sarah Ahmed"

    def get_society_president_name(self, obj):
        if obj.society.president:
            return obj.society.president.get_full_name() or obj.society.president.username
        return "Muhammad Roshan Ashraf"

class RegistrationSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    student_username = serializers.CharField(source='student.username', read_only=True)
    student_email = serializers.CharField(source='student.email', read_only=True)
    student_roll_number = serializers.CharField(source='student.roll_number', read_only=True)
    student_program = serializers.CharField(source='student.program', read_only=True)
    student_department = serializers.CharField(source='student.department', read_only=True)
    student_faculty = serializers.CharField(source='student.faculty_name', read_only=True)
    student_phone = serializers.CharField(source='student.phone_number', read_only=True)
    student_avatar = serializers.CharField(source='student.avatar_url', read_only=True)
    
    event_title = serializers.CharField(source='event.title', read_only=True)
    event_description = serializers.CharField(source='event.description', read_only=True)
    event_date = serializers.DateTimeField(source='event.date', read_only=True)
    event_price = serializers.DecimalField(source='event.price', max_digits=10, decimal_places=2, read_only=True)
    event_is_paid = serializers.BooleanField(source='event.is_paid', read_only=True)
    event_venue = serializers.SerializerMethodField()
    society_id = serializers.IntegerField(source='event.society.id', read_only=True)
    society_name = serializers.CharField(source='event.society.name', read_only=True)
    society_logo = serializers.CharField(source='event.society.logo', read_only=True, default='')
    effective_payment_qr = serializers.SerializerMethodField()
    student_cnic = serializers.CharField(source='student.cnic', read_only=True, default='')
    student_gender = serializers.CharField(source='student.gender', read_only=True, default='')
    student_batch = serializers.CharField(source='student.batch', read_only=True, default='')
    student_semester = serializers.CharField(source='student.semester', read_only=True, default='')
    student_father = serializers.CharField(source='student.father_name', read_only=True, default='')
    
    verified_by_name = serializers.SerializerMethodField()
    checked_in_by_name = serializers.SerializerMethodField()
    is_hold_expired = serializers.SerializerMethodField()
    seconds_remaining = serializers.SerializerMethodField()
    
    class Meta:
        model = Registration
        fields = '__all__'
        read_only_fields = [
            'payment_status', 'ticket_qr_code', 'attendance_status', 'student',
            'public_token_hash', 'ticket_number', 'ticket_status',
            'held_until', 'verified_at', 'verified_by', 'bank_version', 'bank_snapshot',
            'checked_in_at', 'checked_in_by', 'created_at'
        ]

    def get_student_name(self, obj):
        return obj.student.get_full_name() or obj.student.username

    def get_event_venue(self, obj):
        return obj.event.venue.name if obj.event.venue else "Main Campus Auditorium"

    def get_verified_by_name(self, obj):
        if obj.verified_by:
            return obj.verified_by.get_full_name() or obj.verified_by.username
        return ""

    def get_checked_in_by_name(self, obj):
        if obj.checked_in_by:
            return obj.checked_in_by.get_full_name() or obj.checked_in_by.username
        return ""

    def get_is_hold_expired(self, obj):
        if obj.held_until and obj.payment_status in ['held', 'pending', 'expired']:
            return bool(obj.held_until < timezone.now())
        return False

    def get_seconds_remaining(self, obj):
        if obj.held_until and obj.payment_status in ['held', 'pending']:
            now = timezone.now()
            if obj.held_until > now:
                return int((obj.held_until - now).total_seconds())
        return 0

    def get_effective_payment_qr(self, obj):
        return obj.event.payment_qr or (obj.event.society.payment_qr if obj.event.society else '')

class NewsSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.username', read_only=True)
    author_role = serializers.CharField(source='author.role', read_only=True)
    author_society = serializers.CharField(source='author.society.name', read_only=True, default=None)
    approved_by_name = serializers.SerializerMethodField()
    society_name = serializers.CharField(source='society.name', read_only=True, default=None)
    society_logo = serializers.CharField(source='society.logo', read_only=True, default='')
    
    class Meta:
        model = News
        fields = '__all__'
        read_only_fields = ['author', 'approved_by']

    def get_approved_by_name(self, obj):
        if obj.approved_by:
            return obj.approved_by.get_full_name() or obj.approved_by.username
        return ""

class GallerySerializer(serializers.ModelSerializer):
    society_name = serializers.CharField(source='society.name', read_only=True)
    society_logo = serializers.CharField(source='society.logo', read_only=True, default='')
    event_title = serializers.CharField(source='event.title', read_only=True, default=None)
    approved_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Gallery
        fields = '__all__'
        read_only_fields = ['approved_by']
        extra_kwargs = {
            'society': {'required': False},
            'is_public': {'default': True, 'required': False}
        }

    def get_approved_by_name(self, obj):
        if obj.approved_by:
            return obj.approved_by.get_full_name() or obj.approved_by.username
        return ""

class CertificateSerializer(serializers.ModelSerializer):
    event_title = serializers.CharField(source='event.title', read_only=True)
    student_name = serializers.SerializerMethodField()
    student_roll_number = serializers.CharField(source='student.roll_number', read_only=True)
    student_department = serializers.CharField(source='student.department', read_only=True)
    student_program = serializers.CharField(source='student.program', read_only=True)
    student_batch = serializers.CharField(source='student.batch', read_only=True)
    society_name = serializers.CharField(source='event.society.name', read_only=True)
    society_logo = serializers.CharField(source='event.society.logo', read_only=True, default='')
    event_date = serializers.DateTimeField(source='event.date', read_only=True)
    event_location = serializers.SerializerMethodField()
    advisor_name = serializers.SerializerMethodField()
    president_name = serializers.SerializerMethodField()
    advisor_signature = serializers.SerializerMethodField()
    president_signature = serializers.SerializerMethodField()
    template_layout = serializers.SerializerMethodField()

    class Meta:
        model = Certificate
        fields = '__all__'

    def get_student_name(self, obj):
        full_name = obj.student.get_full_name()
        return full_name if full_name else obj.student.username

    def get_event_location(self, obj):
        if obj.event.venue:
            return obj.event.venue.name
        return obj.event.venue_name or 'Main Campus Auditorium'

    def get_advisor_name(self, obj):
        advisor = getattr(obj.event.society, 'advisor', None)
        if advisor:
            return advisor.get_full_name() or advisor.username
        return 'Faculty Advisor'

    def get_president_name(self, obj):
        president = getattr(obj.event.society, 'president', None)
        if president:
            return president.get_full_name() or president.username
        return 'Society President'

    def get_advisor_signature(self, obj):
        advisor = getattr(obj.event.society, 'advisor', None)
        if advisor:
            sig = SignatureAsset.objects.filter(user=advisor, is_approved=True).order_by('-created_at').first()
            if sig:
                return sig.signature_image
        return None

    def get_president_signature(self, obj):
        president = getattr(obj.event.society, 'president', None)
        if president:
            sig = SignatureAsset.objects.filter(user=president, is_approved=True).order_by('-created_at').first()
            if sig:
                return sig.signature_image
        return None

    def get_template_layout(self, obj):
        if obj.template and obj.template.layout_json:
            return obj.template.layout_json
        # Check if event has an approved template
        tmpl = CertificateTemplate.objects.filter(event=obj.event, status='approved').first()
        if not tmpl:
            tmpl = CertificateTemplate.objects.filter(society=obj.event.society, status='approved').first()
        if tmpl and tmpl.layout_json:
            return tmpl.layout_json
        return None


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'
        read_only_fields = ['recipient']

class RecruitmentSerializer(serializers.ModelSerializer):
    society_name = serializers.CharField(source='society.name', read_only=True)
    society_logo = serializers.CharField(source='society.logo', read_only=True, default='')
    application_count = serializers.SerializerMethodField()

    class Meta:
        model = Recruitment
        fields = '__all__'  # includes positions, description, max_applicants, created_at
        extra_kwargs = {
            'society': {'required': False}
        }

    def get_application_count(self, obj):
        return obj.applications.count()

class RecruitmentApplicationSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.username', read_only=True)
    student_full_name = serializers.SerializerMethodField()
    student_email = serializers.CharField(source='student.email', read_only=True)
    student_roll_number = serializers.CharField(source='student.roll_number', read_only=True)
    student_program = serializers.CharField(source='student.program', read_only=True)
    student_department = serializers.CharField(source='student.department', read_only=True)
    student_semester = serializers.CharField(source='student.semester', read_only=True)
    student_batch = serializers.CharField(source='student.batch', read_only=True)
    student_phone = serializers.CharField(source='student.phone_number', read_only=True)
    student_avatar = serializers.CharField(source='student.avatar_url', read_only=True)
    recruitment_title = serializers.CharField(source='recruitment.title', read_only=True)
    recruitment_society = serializers.IntegerField(source='recruitment.society.id', read_only=True)
    society_name = serializers.CharField(source='recruitment.society.name', read_only=True)
    
    class Meta:
        model = RecruitmentApplication
        fields = '__all__'
        read_only_fields = ['student', 'status', 'interview_slot', 'interview_score']

    def get_student_full_name(self, obj):
        return obj.student.get_full_name() or obj.student.username


class VenueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Venue
        fields = '__all__'

class MembershipSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    student_username = serializers.CharField(source='student.username', read_only=True)
    student_email = serializers.CharField(source='student.email', read_only=True)
    student_roll_number = serializers.CharField(source='student.roll_number', read_only=True)
    student_program = serializers.CharField(source='student.program', read_only=True)
    student_department = serializers.CharField(source='student.department', read_only=True)
    student_semester = serializers.CharField(source='student.semester', read_only=True, default='')
    student_faculty = serializers.CharField(source='student.faculty_name', read_only=True)
    student_phone = serializers.CharField(source='student.phone_number', read_only=True)
    student_avatar = serializers.CharField(source='student.avatar_url', read_only=True)
    student_gender = serializers.CharField(source='student.gender', read_only=True, default='')
    student_cnic = serializers.CharField(source='student.cnic', read_only=True, default='')
    student_father = serializers.CharField(source='student.father_name', read_only=True, default='')
    student_batch = serializers.CharField(source='student.batch', read_only=True, default='')

    society_name = serializers.CharField(source='society.name', read_only=True)
    society_logo = serializers.SerializerMethodField()
    society_president = serializers.SerializerMethodField()
    society_advisor = serializers.SerializerMethodField()
    society_bank_name = serializers.CharField(source='society.bank_name', read_only=True)
    society_bank_account_number = serializers.CharField(source='society.bank_account_number', read_only=True)
    society_bank_account_title = serializers.CharField(source='society.bank_account_title', read_only=True)

    class Meta:
        model = Membership
        fields = '__all__'  # includes status, payment_proof, transaction_id, fee_paid, designation
        read_only_fields = [
            'student', 'society', 'card_qr_code', 'public_token_hash', 'membership_id',
            'status', 'is_active', 'designation', 'issued_by_role', 'issued_by_name',
            'approved_by_advisor', 'joined_date', 'applied_at', 'approved_at',
            'issued_at', 'expires_at', 'revoked_at', 'revoked_by'
        ]

    def get_student_name(self, obj):
        return obj.student.get_full_name() or obj.student.username

    def get_society_logo(self, obj):
        logo = obj.society.logo
        if logo:
            request = self.context.get('request')
            if request and hasattr(logo, 'url'):
                return request.build_absolute_uri(logo.url)
            return str(logo)
        return ''

    def get_society_president(self, obj):
        if obj.society.president:
            return obj.society.president.get_full_name() or obj.society.president.username
        return 'Society President'

    def get_society_advisor(self, obj):
        if obj.society.advisor:
            return obj.society.advisor.get_full_name() or obj.society.advisor.username
        return 'Faculty Advisor'

class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.username', read_only=True)
    class Meta:
        model = Message
        fields = '__all__'
        read_only_fields = ['sender', 'society']

class EventFeedbackSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.username', read_only=True)
    class Meta:
        model = EventFeedback
        fields = '__all__'
        read_only_fields = ['student']

class EventResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventResource
        fields = '__all__'

class BudgetSerializer(serializers.ModelSerializer):
    society_name = serializers.CharField(source='society.name', read_only=True)
    event_title = serializers.CharField(source='event.title', read_only=True, default='')

    class Meta:
        model = Budget
        fields = '__all__'

class SponsorshipSerializer(serializers.ModelSerializer):
    society_name = serializers.CharField(source='society.name', read_only=True)
    event_title = serializers.CharField(source='event.title', read_only=True, default='')

    class Meta:
        model = Sponsorship
        fields = '__all__'

class VolunteerHourSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    student_username = serializers.CharField(source='student.username', read_only=True)
    student_roll_number = serializers.CharField(source='student.roll_number', read_only=True)
    student_avatar = serializers.CharField(source='student.avatar_url', read_only=True)
    student_department = serializers.CharField(source='student.department', read_only=True)
    event_title = serializers.SerializerMethodField()
    society_name = serializers.SerializerMethodField()
    society_logo = serializers.SerializerMethodField()
    verified_by_name = serializers.SerializerMethodField()

    class Meta:
        model = VolunteerHour
        fields = '__all__'  # includes role, description, date, status, society, verified_at, created_at

    def get_student_name(self, obj):
        return obj.student.get_full_name() or obj.student.username

    def get_event_title(self, obj):
        return obj.event.title if obj.event else ''

    def get_society_name(self, obj):
        if obj.society:
            return obj.society.name
        if obj.event:
            return obj.event.society.name
        return ''

    def get_society_logo(self, obj):
        soc = obj.society or (obj.event.society if obj.event else None)
        if soc and soc.logo:
            return str(soc.logo)
        return ''

    def get_verified_by_name(self, obj):
        if obj.verified_by:
            return obj.verified_by.get_full_name() or obj.verified_by.username
        return None

class EquipmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Equipment
        fields = '__all__'

class EventEquipmentRequestSerializer(serializers.ModelSerializer):
    equipment_name = serializers.CharField(source='equipment.name', read_only=True)
    class Meta:
        model = EventEquipmentRequest
        fields = '__all__'

class ComplaintSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    class Meta:
        model = Complaint
        fields = '__all__'
        read_only_fields = ['user']

class EventProposalSerializer(serializers.ModelSerializer):
    proposal_id = serializers.IntegerField(source='id', read_only=True)
    society_name = serializers.CharField(source='society.name', read_only=True)
    society_category = serializers.CharField(source='society.category', read_only=True, default='')
    president_name = serializers.SerializerMethodField()
    advisor_name = serializers.SerializerMethodField()
    approved_by_name = serializers.SerializerMethodField()
    poster_image_url = serializers.CharField(source='event_image', required=False, allow_blank=True)

    class Meta:
        model = EventProposal
        fields = '__all__'
        read_only_fields = [
            'proposal_no', 'society', 'president', 'advisor', 'status',
            'generated_at', 'downloaded_at', 'uploaded_at', 'verified_at',
            'approved_at', 'approved_by', 'status_history', 'event'
        ]
        extra_kwargs = {
            'society': {'required': False},
            'proposal_no': {'required': False}
        }

    def get_president_name(self, obj):
        if obj.president:
            return obj.president.get_full_name() or obj.president.username
        return ""

    def get_advisor_name(self, obj):
        if obj.advisor:
            return obj.advisor.get_full_name() or obj.advisor.username
        elif obj.society and obj.society.advisor:
            return obj.society.advisor.get_full_name() or obj.society.advisor.username
        return ""

    def get_approved_by_name(self, obj):
        if obj.approved_by:
            return obj.approved_by.get_full_name() or obj.approved_by.username
        return ""


class DateClaimSerializer(serializers.ModelSerializer):
    society_name = serializers.CharField(source='society.name', read_only=True)
    society_logo = serializers.CharField(source='society.logo', read_only=True, default='')
    event_title = serializers.CharField(source='event.title', read_only=True)

    class Meta:
        model = DateClaim
        fields = '__all__'


class EventStaffAssignmentSerializer(serializers.ModelSerializer):
    volunteer_name = serializers.CharField(source='volunteer.get_full_name', read_only=True)
    volunteer_username = serializers.CharField(source='volunteer.username', read_only=True)
    volunteer_roll = serializers.CharField(source='volunteer.roll_number', read_only=True)
    volunteer_photo = serializers.CharField(source='volunteer.avatar_url', read_only=True)
    event_title = serializers.CharField(source='event.title', read_only=True)

    class Meta:
        model = EventStaffAssignment
        fields = '__all__'
        read_only_fields = ['assigned_by', 'revoked_at', 'revoked_by']


class SignatureAssetSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)

    class Meta:
        model = SignatureAsset
        fields = '__all__'
        read_only_fields = ['user', 'role_title', 'is_approved', 'approved_by']


class CertificateTemplateSerializer(serializers.ModelSerializer):
    society_name = serializers.CharField(source='society.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)

    class Meta:
        model = CertificateTemplate
        fields = '__all__'
        read_only_fields = ['created_by', 'approved_by', 'status']
        extra_kwargs = {
            'society': {'required': False}
        }


class SystemSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemSetting
        fields = '__all__'


class BackupRecordSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)

    class Meta:
        model = BackupRecord
        fields = '__all__'

