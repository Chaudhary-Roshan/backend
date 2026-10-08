import os
import django
from datetime import datetime, timedelta
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import User, Society, Venue, Equipment, Event, Membership, Recruitment, Budget, VolunteerHour, News

def seed_db():
    print("Seeding robust test data...")

    # Users
    admin, _ = User.objects.get_or_create(username="admin", defaults={"role": "admin", "is_staff": True, "is_superuser": True})
    admin.set_password("admin123"); admin.save()

    faculty, _ = User.objects.get_or_create(username="faculty", defaults={"role": "faculty", "first_name": "Dr. Alan", "last_name": "Turing"})
    faculty.set_password("faculty123"); faculty.save()

    pres1, _ = User.objects.get_or_create(username="president", defaults={"role": "president", "first_name": "Alice"})
    pres1.set_password("president123"); pres1.save()
    
    pres2, _ = User.objects.get_or_create(username="pres2", defaults={"role": "president", "first_name": "Charlie"})
    pres2.set_password("pres2123"); pres2.save()

    student1, _ = User.objects.get_or_create(username="student", defaults={"role": "student", "first_name": "Bob"})
    student1.set_password("student123"); student1.save()

    # Venues & Equipment
    v1, _ = Venue.objects.get_or_create(name="Main Auditorium", capacity=500)
    v2, _ = Venue.objects.get_or_create(name="CS Lab 301", capacity=50)
    eq1, _ = Equipment.objects.get_or_create(name="Projector 4K", total_quantity=5)
    eq2, _ = Equipment.objects.get_or_create(name="PA System", total_quantity=2)

    # Societies
    soc1, _ = Society.objects.get_or_create(name="Computer Science Society", defaults={
        "president": pres1, 
        "advisor": faculty, 
        "description": "The premier computing and technology society on campus.",
        "bank_name": "Campus Trust Bank",
        "bank_account_title": "Computer Science Society Event Fund",
        "bank_account_number": "PK90CTB000492817263",
        "social_links": {"instagram": "https://instagram.com/cs_society", "linkedin": "https://linkedin.com/company/cs-society"}
    })
    soc2, _ = Society.objects.get_or_create(name="Drama & Performing Arts Club", defaults={
        "president": pres2, 
        "advisor": faculty, 
        "description": "Acting, theater, and stagecraft.",
        "bank_name": "Campus Trust Bank",
        "bank_account_title": "Drama Club Fund",
        "bank_account_number": "PK90CTB000781294821",
        "social_links": {"instagram": "https://instagram.com/dramaclub"}
    })

    # Link user models
    pres1.society = soc1; pres1.save()
    pres2.society = soc2; pres2.save()
    faculty.society = soc1; faculty.save()

    # News
    News.objects.get_or_create(title="Welcome to the University DSMS Portal", content="The new unified society management portal is officially live for all students, advisors, and presidents!", author=admin)
    News.objects.get_or_create(title="Annual Club Rush Week 2026", content="Meet society executive cabinets, explore open recruitment drives, and discover upcoming workshops in the student quad.", author=admin)

    # Memberships
    Membership.objects.get_or_create(student=student1, society=soc1, defaults={"is_active": True})

    # Events
    now = timezone.now()
    e1, _ = Event.objects.get_or_create(title="National Hackathon 2026", defaults={
        "society": soc1, "description": "24 hours of coding, mentorship, lightning workshops, and team challenges.", 
        "date": now + timedelta(days=5), "venue": v1, "status": "approved", "is_paid": True, "price": 10.00
    })
    e2, _ = Event.objects.get_or_create(title="Intro to React & Tailwind Workshop", defaults={
        "society": soc1, "description": "Hands-on beginner workshop for modern frontend web application development.", 
        "date": now + timedelta(days=2), "venue": v2, "status": "approved", "is_paid": False, "price": 0.00
    })
    e3, _ = Event.objects.get_or_create(title="Spring Stage Play Auditions", defaults={
        "society": soc2, "description": "Open casting call for the campus annual theatrical production.", 
        "date": now + timedelta(days=3), "venue": v1, "status": "approved", "is_paid": False, "price": 0.00
    })

    # Registrations (Free event with QR code, and Paid event pending verification)
    from core.models import Registration, Gallery, CabinetMember
    import uuid
    reg_free, _ = Registration.objects.get_or_create(
        student=student1, event=e2,
        defaults={"payment_status": "verified", "ticket_qr_code": str(uuid.uuid4()), "attendance_status": False}
    )
    reg_paid, _ = Registration.objects.get_or_create(
        student=student1, event=e1,
        defaults={"payment_status": "pending", "transaction_id": "TXN-8829103-CAMPUS", "receipt_details": "Paid via Online Bank Transfer from student Bob account", "ticket_qr_code": None}
    )

    # Galleries
    Gallery.objects.get_or_create(
        society=soc1, event=e2,
        defaults={"image_url": "https://images.unsplash.com/photo-1540575467063-178a50c2df87?w=800&auto=format&fit=crop&q=80"}
    )
    Gallery.objects.get_or_create(
        society=soc1, event=e1,
        defaults={"image_url": "https://images.unsplash.com/photo-1517245386807-bb43f82c33c4?w=800&auto=format&fit=crop&q=80"}
    )
    Gallery.objects.get_or_create(
        society=soc2, event=e3,
        defaults={"image_url": "https://images.unsplash.com/photo-1507676184212-d03ab07a01bf?w=800&auto=format&fit=crop&q=80"}
    )

    # Cabinet
    CabinetMember.objects.get_or_create(
        society=soc1, user=pres1,
        defaults={"role_title": "President", "term_year": "2025-2026", "is_verified": True}
    )

    # Recruitments
    Recruitment.objects.get_or_create(
        society=soc1, 
        title="Executive Cabinet Recruitment Drive 2026", 
        defaults={"deadline": now + timedelta(days=10), "status": "open"}
    )
    
    # Budgets
    Budget.objects.get_or_create(society=soc1, title="University Activity Grant", amount=1500.00, is_expense=False)
    Budget.objects.get_or_create(society=soc1, title="Workshop Refreshments & Badges", amount=250.00, is_expense=True)

    # Volunteer Hours
    VolunteerHour.objects.get_or_create(student=student1, event=e2, hours=4.5)

    print("Robust database seeding completed successfully!")

    from django.core.management import call_command
    print("Seeding full 3-Society Pilot Dataset...")
    call_command('seed_pilot')

if __name__ == '__main__':
    seed_db()
