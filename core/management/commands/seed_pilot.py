import os
import uuid
import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import (
    User, Society, Venue, Equipment, Event, Registration, News, Gallery,
    Certificate, CertificateTemplate, SignatureAsset, Notification,
    CabinetMember, EventProposal, DateClaim, Budget, VolunteerHour,
    EventStaffAssignment, Membership, Recruitment, RecruitmentApplication
)

class Command(BaseCommand):
    help = "Seed realistic pilot dataset for 3 university societies (ACM, IEEE, Debating Society)"

    def handle(self, *args, **kwargs):
        self.stdout.write("Initializing Pilot Dataset for 3 Campus Societies...")

        # 1. Super Admin
        admin, _ = User.objects.get_or_create(
            username="admin",
            defaults={"email": "admin@campus.edu", "role": "admin", "is_staff": True, "is_superuser": True}
        )
        admin.set_password("admin123")
        admin.first_name = "Chief"
        admin.last_name = "Administrator"
        admin.save()

        # 2. Venues & Equipment
        v_aud, _ = Venue.objects.get_or_create(name="Main Campus Auditorium", defaults={"capacity": 600})
        v_lab, _ = Venue.objects.get_or_create(name="CS Advanced Lab 301", defaults={"capacity": 60})
        v_sports, _ = Venue.objects.get_or_create(name="Indoor Sports Complex Arena", defaults={"capacity": 800})
        v_hall, _ = Venue.objects.get_or_create(name="Executive Conference Hall", defaults={"capacity": 250})
        v_amphi, _ = Venue.objects.get_or_create(name="Open-Air Amphitheater", defaults={"capacity": 400})

        eq_proj, _ = Equipment.objects.get_or_create(name="4K Cinema Projector & Screen", defaults={"total_quantity": 4})
        eq_sound, _ = Equipment.objects.get_or_create(name="JBL Wireless PA & Podium Mics", defaults={"total_quantity": 6})
        eq_lights, _ = Equipment.objects.get_or_create(name="Stage Floodlights & Truss Rig", defaults={"total_quantity": 10})
        eq_stands, _ = Equipment.objects.get_or_create(name="Debate Rostrums & Timers", defaults={"total_quantity": 8})

        # 3. Students
        students_data = [
            ("roshan2", "Muhammad Roshan", "Ashraf", "roshan@campus.edu", "FA22-BCS-001", "BS Computer Science", "Department of Computer Science", "Ashraf Ali", "+92 300 1234567", "35201-1234567-1"),
            ("student_sam", "Sam", "Altman", "sam@campus.edu", "FA22-BCS-042", "BS Computer Science", "Department of Computer Science", "David Altman", "+92 300 8765432", "35201-9876543-3"),
            ("student_zara", "Zara", "Khan", "zara@campus.edu", "FA22-BEE-019", "BS Electrical Engineering", "Department of Electrical Engineering", "Tariq Khan", "+92 300 5544332", "35201-5544332-5"),
            ("student_ali", "Ali", "Hassan", "ali@campus.edu", "SP23-BSE-088", "BS Software Engineering", "Department of Computer Science", "Hassan Raza", "+92 301 9988776", "35201-9988776-7"),
            ("student_fatima", "Fatima", "Noor", "fatima@campus.edu", "FA23-BBA-015", "BBA Business Administration", "Department of Management Sciences", "Noor Alam", "+92 302 1122334", "35201-1122334-9"),
            ("student_bilal", "Bilal", "Raza", "bilal@campus.edu", "SP22-BDS-031", "BS Data Science", "Department of Computer Science", "Raza Ahmad", "+92 303 6677889", "35201-6677889-1"),
        ]
        students = {}
        for item in students_data:
            uname, fname, lname, email, roll, prog, dept, father, phone, cnic = item
            st, _ = User.objects.get_or_create(
                username=uname,
                defaults={"email": email, "role": "student", "first_name": fname, "last_name": lname, "roll_number": roll, "program": prog, "department": dept}
            )
            st.first_name = fname
            st.last_name = lname
            st.email = email
            st.roll_number = roll
            st.program = prog
            st.department = dept
            st.father_name = father
            st.phone_number = phone
            st.cnic = cnic
            st.faculty_name = "Faculty of Computing & Information Technology" if "Computer" in dept or "Software" in prog or "Data" in prog else ("Faculty of Electrical & Mechanical Engineering" if "Electrical" in dept else "Faculty of Management Sciences")
            st.is_email_verified = True
            st.is_active = True
            st.avatar_url = f"https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=400&auto=format&fit=crop&q=80" if uname == "roshan2" else "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=400&auto=format&fit=crop&q=80"
            st.save()
            students[uname] = st

        now = timezone.now()

        # =========================================================================
        # SOCIETY 1: ACM Student Chapter (Computing & AI)
        # =========================================================================
        acm_advisor, _ = User.objects.get_or_create(
            username="acm_advisor",
            defaults={"email": "tariq.cs@campus.edu", "role": "faculty", "first_name": "Dr. Tariq", "last_name": "Mahmood", "department": "Department of Computer Science"}
        )
        acm_advisor.set_password("advisor12345")
        acm_advisor.first_name = "Dr. Tariq"
        acm_advisor.last_name = "Mahmood"
        acm_advisor.save()

        acm_pres, _ = User.objects.get_or_create(
            username="acm_president",
            defaults={"email": "acm.pres@campus.edu", "role": "president", "first_name": "Hamza", "last_name": "Sheikh", "roll_number": "FA21-BCS-007", "department": "Department of Computer Science"}
        )
        acm_pres.set_password("acm12345")
        acm_pres.first_name = "Hamza"
        acm_pres.last_name = "Sheikh"
        acm_pres.save()

        soc_acm, _ = Society.objects.get_or_create(
            name="ACM Student Chapter",
            defaults={
                "president": acm_pres,
                "advisor": acm_advisor,
                "description": "Premier computing society empowering student software engineers, competitive programmers, and AI researchers through hackathons and bootcamps.",
                "bank_name": "Habib Bank Limited (HBL)",
                "bank_account_title": "ACM Campus Chapter Student Fund",
                "bank_account_number": "PK72HABB0001234567890123",
                "payment_instructions": "Please transfer delegate fees via HBL Mobile / Raast to the above account title. Upload the digital payment screenshot.",
                "bank_version": 1,
                "social_links": {"instagram": "https://instagram.com/acm_campus", "linkedin": "https://linkedin.com/company/acm-campus"}
            }
        )
        acm_pres.society = soc_acm; acm_pres.save()
        acm_advisor.society = soc_acm; acm_advisor.save()

        CabinetMember.objects.get_or_create(society=soc_acm, user=acm_pres, defaults={"role_title": "President", "term_year": "2025-2026", "is_verified": True})

        # Signatures for ACM
        sig_acm_adv, _ = SignatureAsset.objects.get_or_create(
            user=acm_advisor,
            defaults={"role_title": "Faculty Advisor", "signature_image": "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='120' height='40'><text y='25' font-family='cursive' font-size='20'>Dr. Tariq</text></svg>", "is_approved": True, "approved_by": admin}
        )
        sig_acm_pres, _ = SignatureAsset.objects.get_or_create(
            user=acm_pres,
            defaults={"role_title": "President", "signature_image": "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='120' height='40'><text y='25' font-family='cursive' font-size='20'>Hamza Sheikh</text></svg>", "is_approved": True, "approved_by": acm_advisor}
        )

        # ACM Certificate Template
        tpl_acm, _ = CertificateTemplate.objects.get_or_create(
            society=soc_acm,
            title="ACM Hackathon Certificate of Excellence",
            defaults={
                "layout_json": {
                    "header_title": "ASSOCIATION FOR COMPUTING MACHINERY",
                    "sub_title": "CERTIFICATE OF PARTICIPATION & ACHIEVEMENT",
                    "body_text": "This certificate is proudly awarded to {student_name} ({roll_number}) from {department} for exemplary participation and outstanding software demonstration in {event_title}.",
                    "primary_color": "#0ea5e9",
                    "signatures": [
                        {"role": "Faculty Advisor", "name": "Dr. Tariq Mahmood", "asset_id": sig_acm_adv.id},
                        {"role": "President", "name": "Hamza Sheikh", "asset_id": sig_acm_pres.id}
                    ]
                },
                "status": "approved",
                "created_by": acm_pres,
                "approved_by": acm_advisor
            }
        )

        # ACM Event 1: National Hackathon
        event_acm_hack, _ = Event.objects.get_or_create(
            title="National Collegiate AI Hackathon 2026",
            defaults={
                "society": soc_acm,
                "description": "36-hour continuous software engineering & AI sprint. Build production agentic workflows, compete for cash prizes, and connect with top tech recruiters.",
                "date": now + datetime.timedelta(days=7),
                "venue": v_aud,
                "status": "approved",
                "is_paid": True,
                "price": 15.00
            }
        )

        # ACM Event 2: PyTorch AI Bootcamp
        event_acm_boot, _ = Event.objects.get_or_create(
            title="Hands-on PyTorch & LLM Fine-Tuning Bootcamp",
            defaults={
                "society": soc_acm,
                "description": "Accelerate your deep learning journey. Hands-on GPU-accelerated code lab exploring Transformer architectures and LoRA fine-tuning.",
                "date": now + datetime.timedelta(days=14),
                "venue": v_lab,
                "status": "approved",
                "is_paid": False,
                "price": 0.00
            }
        )

        # ACM Proposal & DateClaim
        prop_acm, _ = EventProposal.objects.get_or_create(
            proposal_no="PROP-2026-001-ACMHACK",
            defaults={
                "society": soc_acm,
                "president": acm_pres,
                "advisor": acm_advisor,
                "event_title": "National Collegiate AI Hackathon 2026",
                "event_date": (now + datetime.timedelta(days=7)).date(),
                "venue": v_aud,
                "budget": 2000.00,
                "status": "approved",
                "approved_by": admin
            }
        )
        DateClaim.objects.update_or_create(
            claim_date=(now + datetime.timedelta(days=7)).date(),
            defaults={"society": soc_acm, "event": event_acm_hack, "proposal": prop_acm, "status": "confirmed"}
        )

        # ACM Registrations & Certificates
        reg_sam, _ = Registration.objects.get_or_create(
            student=students["student_sam"],
            event=event_acm_hack,
            defaults={
                "payment_status": "verified",
                "ticket_qr_code": str(uuid.uuid4()),
                "attendance_status": True,
                "checked_in_at": now - datetime.timedelta(hours=2),
                "checked_in_by": acm_pres
            }
        )
        reg_ali, _ = Registration.objects.get_or_create(
            student=students["student_ali"],
            event=event_acm_hack,
            defaults={
                "payment_status": "verified",
                "ticket_qr_code": str(uuid.uuid4()),
                "attendance_status": True,
                "checked_in_at": now - datetime.timedelta(hours=1),
                "checked_in_by": acm_pres
            }
        )
        reg_bilal, _ = Registration.objects.get_or_create(
            student=students["student_bilal"],
            event=event_acm_hack,
            defaults={
                "payment_status": "held",
                "held_until": now + datetime.timedelta(hours=22),
                "attendance_status": False
            }
        )

        # Issue Certificate for Sam
        Certificate.objects.get_or_create(
            event=event_acm_hack,
            student=students["student_sam"],
            defaults={
                "verification_code": str(uuid.uuid4()),
                "template": tpl_acm
            }
        )

        # ACM Budgets
        Budget.objects.get_or_create(society=soc_acm, title="University Annual Technology Grant", amount=2500.00, is_expense=False)
        Budget.objects.get_or_create(society=soc_acm, title="AWS Cloud Infrastructure & Server Credits", amount=400.00, is_expense=True)
        Budget.objects.get_or_create(society=soc_acm, title="Hackathon Catering & Midnight Snacks", amount=650.00, is_expense=True)

        # ACM News & Gallery
        News.objects.get_or_create(
            title="Registrations Live for National Collegiate AI Hackathon 2026",
            defaults={
                "content": "Official registrations for the annual 36-hour National AI Hackathon are now live! Open to teams of 2 to 4. Over $3,000 in prizes.",
                "author": acm_pres,
                "society": soc_acm,
                "status": "approved",
                "approved_by": acm_advisor
            }
        )
        Gallery.objects.get_or_create(
            society=soc_acm,
            event=event_acm_hack,
            title="Hackathon Keynote & Team Pitch Sessions",
            album_name="National Hackathon 2026",
            defaults={
                "image_url": "https://images.unsplash.com/photo-1504384308090-c894fdcc538d?w=800&auto=format&fit=crop&q=80",
                "status": "approved",
                "approved_by": acm_advisor,
                "is_public": True
            }
        )

        # =========================================================================
        # SOCIETY 2: IEEE Student Branch (Robotics & Engineering)
        # =========================================================================
        ieee_advisor, _ = User.objects.get_or_create(
            username="ieee_advisor",
            defaults={"email": "sarah.ee@campus.edu", "role": "faculty", "first_name": "Engr. Sarah", "last_name": "Ahmad", "department": "Department of Electrical Engineering"}
        )
        ieee_advisor.set_password("advisor12345")
        ieee_advisor.first_name = "Engr. Sarah"
        ieee_advisor.last_name = "Ahmad"
        ieee_advisor.save()

        ieee_pres, _ = User.objects.get_or_create(
            username="ieee_president",
            defaults={"email": "ieee.pres@campus.edu", "role": "president", "first_name": "Danyal", "last_name": "Qureshi", "roll_number": "FA21-BEE-012", "department": "Department of Electrical Engineering"}
        )
        ieee_pres.set_password("ieee12345")
        ieee_pres.first_name = "Danyal"
        ieee_pres.last_name = "Qureshi"
        ieee_pres.save()

        soc_ieee, _ = Society.objects.get_or_create(
            name="IEEE Student Branch",
            defaults={
                "president": ieee_pres,
                "advisor": ieee_advisor,
                "description": "Advancing technology for humanity through robotics competitions, embedded hardware workshops, and industrial engineering expos.",
                "bank_name": "Allied Bank Limited (ABL)",
                "bank_account_title": "IEEE Student Branch Campus Activity Fund",
                "bank_account_number": "PK45ABPA0009876543210987",
                "payment_instructions": "Send participation fee via ABL Raast ID or direct transfer. Include Team Name in transaction remarks.",
                "bank_version": 1,
                "social_links": {"instagram": "https://instagram.com/ieee_campus", "linkedin": "https://linkedin.com/company/ieee-campus"}
            }
        )
        ieee_pres.society = soc_ieee; ieee_pres.save()
        ieee_advisor.society = soc_ieee; ieee_advisor.save()

        CabinetMember.objects.get_or_create(society=soc_ieee, user=ieee_pres, defaults={"role_title": "President", "term_year": "2025-2026", "is_verified": True})

        # Signatures for IEEE
        sig_ieee_adv, _ = SignatureAsset.objects.get_or_create(
            user=ieee_advisor,
            defaults={"role_title": "Faculty Counselor", "signature_image": "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='120' height='40'><text y='25' font-family='cursive' font-size='20'>Engr. Sarah</text></svg>", "is_approved": True, "approved_by": admin}
        )
        sig_ieee_pres, _ = SignatureAsset.objects.get_or_create(
            user=ieee_pres,
            defaults={"role_title": "Chairperson", "signature_image": "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='120' height='40'><text y='25' font-family='cursive' font-size='20'>Danyal Qureshi</text></svg>", "is_approved": True, "approved_by": ieee_advisor}
        )

        # IEEE Certificate Template
        tpl_ieee, _ = CertificateTemplate.objects.get_or_create(
            society=soc_ieee,
            title="IEEE Robotics & Technical Excellence Certificate",
            defaults={
                "layout_json": {
                    "header_title": "INSTITUTE OF ELECTRICAL AND ELECTRONICS ENGINEERS",
                    "sub_title": "CERTIFICATE OF TECHNICAL EXCELLENCE",
                    "body_text": "This credential affirms that {student_name} ({roll_number}) of {department} has completed rigorous engineering evaluation and demonstrated technical proficiency at {event_title}.",
                    "primary_color": "#10b981",
                    "signatures": [
                        {"role": "Faculty Counselor", "name": "Engr. Sarah Ahmad", "asset_id": sig_ieee_adv.id},
                        {"role": "Chairperson", "name": "Danyal Qureshi", "asset_id": sig_ieee_pres.id}
                    ]
                },
                "status": "approved",
                "created_by": ieee_pres,
                "approved_by": ieee_advisor
            }
        )

        # IEEE Event 1: RoboWars
        event_ieee_robo, _ = Event.objects.get_or_create(
            title="Campus RoboWars Sumo Wrestling Championship",
            defaults={
                "society": soc_ieee,
                "description": "Autonomous and RC combat robots clash in the steel arena. Weight categories: 3kg Sumo, Line Follower, and Obstacle Avoider.",
                "date": now + datetime.timedelta(days=10),
                "venue": v_sports,
                "status": "approved",
                "is_paid": True,
                "price": 20.00
            }
        )

        # IEEE Proposal & DateClaim
        prop_ieee, _ = EventProposal.objects.get_or_create(
            proposal_no="PROP-2026-002-ROBOWAR",
            defaults={
                "society": soc_ieee,
                "president": ieee_pres,
                "advisor": ieee_advisor,
                "event_title": "Campus RoboWars Sumo Wrestling Championship",
                "event_date": (now + datetime.timedelta(days=10)).date(),
                "venue": v_sports,
                "budget": 3500.00,
                "status": "approved",
                "approved_by": admin
            }
        )
        DateClaim.objects.update_or_create(
            claim_date=(now + datetime.timedelta(days=10)).date(),
            defaults={"society": soc_ieee, "event": event_ieee_robo, "proposal": prop_ieee, "status": "confirmed"}
        )

        # IEEE Registrations & Certificates
        reg_zara, _ = Registration.objects.get_or_create(
            student=students["student_zara"],
            event=event_ieee_robo,
            defaults={
                "payment_status": "verified",
                "ticket_qr_code": str(uuid.uuid4()),
                "attendance_status": True,
                "checked_in_at": now - datetime.timedelta(minutes=45),
                "checked_in_by": ieee_pres
            }
        )
        Certificate.objects.get_or_create(
            event=event_ieee_robo,
            student=students["student_zara"],
            defaults={
                "verification_code": str(uuid.uuid4()),
                "template": tpl_ieee
            }
        )

        # IEEE Budgets
        Budget.objects.get_or_create(society=soc_ieee, title="Robotics Industry Sponsorship", amount=3500.00, is_expense=False)
        Budget.objects.get_or_create(society=soc_ieee, title="Arena Lexan Glass Shielding & Timer Clocks", amount=1200.00, is_expense=True)

        # IEEE News & Gallery
        News.objects.get_or_create(
            title="RoboWars 2026 Combat Rules & Weight Restrictions Published",
            defaults={
                "content": "All engineering teams must review the updated Sumo robot specs. Scrutiny inspection begins at 09:00 AM on match day.",
                "author": ieee_pres,
                "society": soc_ieee,
                "status": "approved",
                "approved_by": ieee_advisor
            }
        )
        Gallery.objects.get_or_create(
            society=soc_ieee,
            event=event_ieee_robo,
            title="Combat Arena Construction & Telemetry Setup",
            album_name="RoboWars Championship",
            defaults={
                "image_url": "https://images.unsplash.com/photo-1485827404703-89b55fcc595e?w=800&auto=format&fit=crop&q=80",
                "status": "approved",
                "approved_by": ieee_advisor,
                "is_public": True
            }
        )

        # =========================================================================
        # SOCIETY 3: Campus Debating Society (Arts & Humanities)
        # =========================================================================
        deb_advisor, _ = User.objects.get_or_create(
            username="debate_advisor",
            defaults={"email": "bilal.hum@campus.edu", "role": "faculty", "first_name": "Prof. Bilal", "last_name": "Siddiqui", "department": "Department of Humanities & Social Sciences"}
        )
        deb_advisor.set_password("advisor12345")
        deb_advisor.first_name = "Prof. Bilal"
        deb_advisor.last_name = "Siddiqui"
        deb_advisor.save()

        deb_pres, _ = User.objects.get_or_create(
            username="debate_president",
            defaults={"email": "debate.pres@campus.edu", "role": "president", "first_name": "Ayesha", "last_name": "Malik", "roll_number": "FA21-BSS-034", "department": "Department of Humanities & Social Sciences"}
        )
        deb_pres.set_password("debate12345")
        deb_pres.first_name = "Ayesha"
        deb_pres.last_name = "Malik"
        deb_pres.save()

        soc_deb, _ = Society.objects.get_or_create(
            name="Campus Debating Society",
            defaults={
                "president": deb_pres,
                "advisor": deb_advisor,
                "description": "Cultivating critical rhetoric, public discourse, parliamentary debate, and oratorical mastery across national collegiate circuits.",
                "bank_name": "Meezan Bank Limited",
                "bank_account_title": "Campus Debating Society Parliamentary Fund",
                "bank_account_number": "PK88MEZN0005544332211009",
                "payment_instructions": "Send team adjudication fee via Meezan Bank mobile app. Ensure team institutional code is mentioned in notes.",
                "bank_version": 1,
                "social_links": {"instagram": "https://instagram.com/debates_campus"}
            }
        )
        deb_pres.society = soc_deb; deb_pres.save()
        deb_advisor.society = soc_deb; deb_advisor.save()

        CabinetMember.objects.get_or_create(society=soc_deb, user=deb_pres, defaults={"role_title": "President", "term_year": "2025-2026", "is_verified": True})

        # Signatures for Debate
        sig_deb_adv, _ = SignatureAsset.objects.get_or_create(
            user=deb_advisor,
            defaults={"role_title": "Faculty Patron", "signature_image": "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='120' height='40'><text y='25' font-family='cursive' font-size='20'>Prof. Bilal</text></svg>", "is_approved": True, "approved_by": admin}
        )
        sig_deb_pres, _ = SignatureAsset.objects.get_or_create(
            user=deb_pres,
            defaults={"role_title": "President", "signature_image": "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='120' height='40'><text y='25' font-family='cursive' font-size='20'>Ayesha Malik</text></svg>", "is_approved": True, "approved_by": deb_advisor}
        )

        # Debate Certificate Template
        tpl_deb, _ = CertificateTemplate.objects.get_or_create(
            society=soc_deb,
            title="Parliamentary Debate Championship Distinction",
            defaults={
                "layout_json": {
                    "header_title": "CAMPUS PARLIAMENTARY DEBATING UNION",
                    "sub_title": "CERTIFICATE OF ORATORICAL EXCELLENCE",
                    "body_text": "Presented to {student_name} ({roll_number}) of {department} for displaying exceptional analytical eloquence, rhetoric, and sportsmanship during {event_title}.",
                    "primary_color": "#8b5cf6",
                    "signatures": [
                        {"role": "Faculty Patron", "name": "Prof. Bilal Siddiqui", "asset_id": sig_deb_adv.id},
                        {"role": "President", "name": "Ayesha Malik", "asset_id": sig_deb_pres.id}
                    ]
                },
                "status": "approved",
                "created_by": deb_pres,
                "approved_by": deb_advisor
            }
        )

        # Debate Event: All-Pakistan Parliamentary Cup
        event_deb_cup, _ = Event.objects.get_or_create(
            title="All-Pakistan Parliamentary Debating Cup 2026",
            defaults={
                "society": soc_deb,
                "description": "3 days of high-stakes British Parliamentary (BP) debating rounds. Over 40 collegiate delegations debating geopolitics, economics, and ethics.",
                "date": now + datetime.timedelta(days=18),
                "venue": v_hall,
                "status": "approved",
                "is_paid": True,
                "price": 10.00
            }
        )

        # Debate Proposal & DateClaim
        prop_deb, _ = EventProposal.objects.get_or_create(
            proposal_no="PROP-2026-003-DEBATE",
            defaults={
                "society": soc_deb,
                "president": deb_pres,
                "advisor": deb_advisor,
                "event_title": "All-Pakistan Parliamentary Debating Cup 2026",
                "event_date": (now + datetime.timedelta(days=18)).date(),
                "venue": v_hall,
                "budget": 1800.00,
                "status": "approved",
                "approved_by": admin
            }
        )
        DateClaim.objects.update_or_create(
            claim_date=(now + datetime.timedelta(days=18)).date(),
            defaults={"society": soc_deb, "event": event_deb_cup, "proposal": prop_deb, "status": "confirmed"}
        )

        # Registrations & Certificates
        reg_fatima, _ = Registration.objects.get_or_create(
            student=students["student_fatima"],
            event=event_deb_cup,
            defaults={
                "payment_status": "verified",
                "ticket_qr_code": str(uuid.uuid4()),
                "attendance_status": True,
                "checked_in_at": now - datetime.timedelta(hours=3),
                "checked_in_by": deb_pres
            }
        )
        Certificate.objects.get_or_create(
            event=event_deb_cup,
            student=students["student_fatima"],
            defaults={
                "verification_code": str(uuid.uuid4()),
                "template": tpl_deb
            }
        )

        # Debate Budgets
        Budget.objects.get_or_create(society=soc_deb, title="Delegation Registration Collection", amount=1800.00, is_expense=False)
        Budget.objects.get_or_create(society=soc_deb, title="Trophies, Speaker Medals & Chief Adjudicator Honoraria", amount=900.00, is_expense=True)

        # Debate News & Gallery
        News.objects.get_or_create(
            title="Adjudication Core & Motion Guidelines for Parliamentary Cup",
            defaults={
                "content": "The Chief Adjudication Panel has released the official briefing guide for the 2026 Parliamentary Cup. Read the motion guidelines.",
                "author": deb_pres,
                "society": soc_deb,
                "status": "approved",
                "approved_by": deb_advisor
            }
        )
        Gallery.objects.get_or_create(
            society=soc_deb,
            event=event_deb_cup,
            title="Championship Grand Final Debate in Conference Hall",
            album_name="Parliamentary Debating Cup",
            defaults={
                "image_url": "https://images.unsplash.com/photo-1475721027785-f74eccf877e2?w=800&auto=format&fit=crop&q=80",
                "status": "approved",
                "approved_by": deb_advisor,
                "is_public": True
            }
        )

        # =========================================================================
        # RECRUITMENT DRIVES
        # =========================================================================
        rec_acm, _ = Recruitment.objects.get_or_create(
            society=soc_acm,
            title="ACM Annual Fall Cabinet & Associate Executive Recruitment",
            defaults={
                "form_fields": [{"name": "experience", "label": "Technical Experience", "type": "textarea"}],
                "deadline": now + datetime.timedelta(days=14),
                "status": "open"
            }
        )
        rec_ieee, _ = Recruitment.objects.get_or_create(
            society=soc_ieee,
            title="IEEE Robotics Wing & Hardware Team Technical Induction",
            defaults={
                "form_fields": [{"name": "hardware_projects", "label": "Hardware Projects", "type": "textarea"}],
                "deadline": now + datetime.timedelta(days=10),
                "status": "open"
            }
        )

        # =========================================================================
        # SEED COMPREHENSIVE RECORDS FOR KEY STUDENTS (roshan2 & student_sam)
        # =========================================================================
        target_student_keys = ["roshan2", "student_sam"]
        for skey in target_student_keys:
            st_user = students[skey]

            # 1. Digital Society Membership Cards
            Membership.objects.update_or_create(
                society=soc_acm,
                student=st_user,
                defaults={
                    "is_active": True,
                    "membership_id": f"DSMS-ACM-2026-{st_user.id:04d}",
                    "role_title": "Executive Lead - Technical Wing",
                    "issued_by_role": "President",
                    "issued_by_name": f"{acm_pres.get_full_name() or acm_pres.username} (President)",
                    "approved_by_advisor": f"{acm_advisor.get_full_name() or acm_advisor.username} (Faculty Advisor)",
                    "valid_until": "Academic Session 2026-2027"
                }
            )
            Membership.objects.update_or_create(
                society=soc_ieee,
                student=st_user,
                defaults={
                    "is_active": True,
                    "membership_id": f"DSMS-IEEE-2026-{st_user.id:04d}",
                    "role_title": "Associate Member - Robotics & Embedded Systems",
                    "issued_by_role": "Chairperson",
                    "issued_by_name": f"{ieee_pres.get_full_name() or ieee_pres.username} (Chairperson)",
                    "approved_by_advisor": f"{ieee_advisor.get_full_name() or ieee_advisor.username} (Faculty Counselor)",
                    "valid_until": "Academic Session 2026-2027"
                }
            )

            # 2. Event Registrations (Passes: Attended, Confirmed, 24h Seat Hold)
            Registration.objects.update_or_create(
                student=st_user,
                event=event_acm_hack,
                defaults={
                    "payment_status": "verified",
                    "ticket_qr_code": f"TICK-ACM-HACK-{st_user.id:03d}-{uuid.uuid4().hex[:8].upper()}",
                    "attendance_status": True,
                    "checked_in_at": now - datetime.timedelta(hours=2),
                    "checked_in_by": acm_pres
                }
            )
            Registration.objects.update_or_create(
                student=st_user,
                event=event_acm_boot,
                defaults={
                    "payment_status": "verified",
                    "ticket_qr_code": f"TICK-ACM-BOOT-{st_user.id:03d}-{uuid.uuid4().hex[:8].upper()}",
                    "attendance_status": False
                }
            )
            Registration.objects.update_or_create(
                student=st_user,
                event=event_deb_cup,
                defaults={
                    "payment_status": "held",
                    "held_until": now + datetime.timedelta(hours=20),
                    "attendance_status": False,
                    "bank_snapshot": {
                        "version": 1,
                        "bank_name": "Habib Bank Limited (HBL)",
                        "bank_account_title": "Debating Society Student Fund",
                        "bank_account_number": "PK44HABB0003344556677889",
                        "payment_instructions": "Transfer delegate fee of $12.00 via Raast and upload payment receipt."
                    }
                }
            )

            # 3. Verified Certificates
            Certificate.objects.update_or_create(
                event=event_acm_hack,
                student=st_user,
                defaults={
                    "verification_code": uuid.uuid4(),
                    "template": tpl_acm
                }
            )
            Certificate.objects.update_or_create(
                event=event_ieee_robo,
                student=st_user,
                defaults={
                    "verification_code": uuid.uuid4(),
                    "template": tpl_ieee
                }
            )

            # 4. Volunteer Service Hours
            VolunteerHour.objects.update_or_create(
                student=st_user,
                event=event_acm_hack,
                defaults={
                    "hours": 6.5,
                    "verified_by": acm_advisor
                }
            )
            VolunteerHour.objects.update_or_create(
                student=st_user,
                event=event_ieee_robo,
                defaults={
                    "hours": 4.0,
                    "verified_by": ieee_advisor
                }
            )

            # 5. Recruitment Applications
            RecruitmentApplication.objects.update_or_create(
                recruitment=rec_acm,
                student=st_user,
                defaults={
                    "role_applied_for": "Executive Lead - Web & AI Systems",
                    "status": "shortlisted",
                    "interview_slot": now + datetime.timedelta(days=2, hours=4),
                    "interview_score": 94,
                    "answers": {"experience": "3 years full-stack and React/Django development"}
                }
            )
            RecruitmentApplication.objects.update_or_create(
                recruitment=rec_ieee,
                student=st_user,
                defaults={
                    "role_applied_for": "Robotics Hardware Associate",
                    "status": "accepted",
                    "interview_slot": now - datetime.timedelta(days=3),
                    "interview_score": 88,
                    "answers": {"hardware_projects": "Built Arduino sumo bot with ultrasonic sensors"}
                }
            )

            # 6. Assigned Gate Check-in Duties
            EventStaffAssignment.objects.update_or_create(
                event=event_acm_hack,
                volunteer=st_user,
                defaults={
                    "gate_name": "Main Auditorium - Gate 1 (North Entrance)",
                    "duty_start": now - datetime.timedelta(hours=2),
                    "duty_end": now + datetime.timedelta(hours=8),
                    "status": "assigned",
                    "assigned_by": acm_pres
                }
            )

        self.stdout.write(self.style.SUCCESS("Pilot Dataset and complete student profiles seeded successfully for ACM, IEEE, and Debating Society!"))
