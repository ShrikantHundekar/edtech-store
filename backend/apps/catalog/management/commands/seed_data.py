import os
import uuid
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.conf import settings
from django.utils.text import slugify
from apps.catalog.models import Board, ClassLevel, Subject, Chapter, Material
from apps.products.models import Product, Price, BundleItem

User = get_user_model()


class Command(BaseCommand):
    help = "Seeds the database with required demonstration catalog, users, products, and study materials."

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("==> Seeding EdTech Store Database..."))

        # 1. Create Users
        admin_user, created = User.objects.get_or_create(
            email="admin@edtechstore.local",
            defaults={
                "full_name": "System Administrator",
                "role": "ADMIN",
                "is_staff": True,
                "is_superuser": True,
            }
        )
        if created:
            admin_user.set_password("AdminPassword123!")
            admin_user.save()
            self.stdout.write(self.style.SUCCESS("  [+] Created Admin: admin@edtechstore.local (Password: AdminPassword123!)"))
        else:
            self.stdout.write("  [*] Admin user already exists.")

        student_user, created = User.objects.get_or_create(
            email="student@edtechstore.local",
            defaults={
                "full_name": "Demo Student",
                "role": "STUDENT",
            }
        )
        if created:
            student_user.set_password("StudentPassword123!")
            student_user.save()
            self.stdout.write(self.style.SUCCESS("  [+] Created Student: student@edtechstore.local (Password: StudentPassword123!)"))
        else:
            self.stdout.write("  [*] Student user already exists.")

        # 2. Board
        board, _ = Board.objects.get_or_create(
            slug="cbse",
            defaults={
                "name": "CBSE",
                "description": "Central Board of Secondary Education curriculum"
            }
        )

        # 3. Classes
        class_10, _ = ClassLevel.objects.get_or_create(
            board=board,
            slug="class-10",
            defaults={"name": "Class 10"}
        )
        class_12, _ = ClassLevel.objects.get_or_create(
            board=board,
            slug="class-12",
            defaults={"name": "Class 12"}
        )

        # 4. Subjects for Class 10
        subjects_data = [
            ("Mathematics", "mathematics"),
            ("Physics", "physics"),
            ("Chemistry", "chemistry"),
        ]
        created_subjects = {}
        for sub_name, sub_slug in subjects_data:
            subj, _ = Subject.objects.get_or_create(
                academic_class=class_10,
                slug=sub_slug,
                defaults={"name": sub_name}
            )
            created_subjects[sub_name] = subj

        # 5. Chapters (5 per subject, exactly 1 free sample per subject)
        chapter_definitions = {
            "Mathematics": [
                (1, "Real Numbers", True),
                (2, "Polynomials", False),
                (3, "Pair of Linear Equations in Two Variables", False),
                (4, "Quadratic Equations", False),
                (5, "Arithmetic Progressions", False),
            ],
            "Physics": [
                (1, "Light - Reflection and Refraction", True),
                (2, "Human Eye and the Colourful World", False),
                (3, "Electricity", False),
                (4, "Magnetic Effects of Electric Current", False),
                (5, "Sources of Energy", False),
            ],
            "Chemistry": [
                (1, "Chemical Reactions and Equations", True),
                (2, "Acids, Bases and Salts", False),
                (3, "Metals and Non-metals", False),
                (4, "Carbon and Its Compounds", False),
                (5, "Periodic Classification of Elements", False),
            ]
        }

        protected_root = getattr(settings, 'PROTECTED_MEDIA_ROOT', settings.BASE_DIR / 'protected_media')
        materials_dir = os.path.join(protected_root, 'materials')
        os.makedirs(materials_dir, exist_ok=True)

        created_chapters = []
        for sub_name, chapters in chapter_definitions.items():
            subj = created_subjects[sub_name]
            for num, title, is_free in chapters:
                ch, ch_created = Chapter.objects.get_or_create(
                    subject=subj,
                    chapter_number=num,
                    defaults={
                        "title": title,
                        "slug": slugify(f"{sub_name[:4]}-{num}-{title}")[:200],
                        "is_free_sample": is_free
                    }
                )
                created_chapters.append(ch)

                # Attach dummy PDF study note
                if not ch.materials.exists():
                    file_uuid = uuid.uuid4().hex
                    rel_path = f"materials/{file_uuid}.pdf"
                    abs_path = os.path.join(materials_dir, f"{file_uuid}.pdf")
                    pdf_dummy = (
                        b"%PDF-1.4\n"
                        b"%EdTech Store Study Note: " + title.encode('utf-8') + b"\n"
                        b"1 0 obj << /Type /Catalog >> endobj\n"
                        b"trailer << >>\n"
                        b"%%EOF\n"
                    )
                    with open(abs_path, 'wb') as f:
                        f.write(pdf_dummy)

                    Material.objects.create(
                        chapter=ch,
                        title=f"{title} - Complete Formula Sheet & Notes",
                        file_path=rel_path,
                        file_size_bytes=len(pdf_dummy),
                        mime_type="application/pdf"
                    )

        self.stdout.write(self.style.SUCCESS(f"  [+] Seeded 1 Board, 2 Classes, 3 Subjects, and 15 Chapters with Study Materials."))

        # 6. Commercial Products & Prices
        # A. Chapter Notes
        for ch in created_chapters:
            if not ch.is_free_sample:
                p_slug = slugify(f"notes-{ch.subject.name}-ch-{ch.chapter_number}")
                prod, p_created = Product.objects.get_or_create(
                    slug=p_slug,
                    defaults={
                        "title": f"{ch.subject.name} Ch {ch.chapter_number}: {ch.title} Notes",
                        "product_type": Product.PRODUCT_TYPE_CHAPTER_NOTES,
                        "board": board,
                        "academic_class": class_10,
                        "subject": ch.subject,
                        "chapter": ch,
                        "description": f"Comprehensive PDF study notes for Chapter {ch.chapter_number} ({ch.title}). Lifetime digital access.",
                        "is_active": True,
                    }
                )
                if p_created:
                    Price.objects.create(product=prod, amount_paise=4900, is_current=True)
            else:
                p_slug = slugify(f"free-sample-{ch.subject.name}-ch-{ch.chapter_number}")
                Product.objects.get_or_create(
                    slug=p_slug,
                    defaults={
                        "title": f"FREE SAMPLE: {ch.subject.name} Ch {ch.chapter_number} ({ch.title})",
                        "product_type": Product.PRODUCT_TYPE_FREE_SAMPLE,
                        "board": board,
                        "academic_class": class_10,
                        "subject": ch.subject,
                        "chapter": ch,
                        "description": f"Free preview chapter notes for {ch.title}. Read immediately online.",
                        "is_active": True,
                    }
                )

        # B. Subject Packs (₹499)
        for sub_name, subj in created_subjects.items():
            p_slug = slugify(f"pack-class-10-{sub_name}")
            prod, p_created = Product.objects.get_or_create(
                slug=p_slug,
                defaults={
                    "title": f"Class 10 {sub_name} Subject Pack",
                    "product_type": Product.PRODUCT_TYPE_SUBJECT_PACK,
                    "board": board,
                    "academic_class": class_10,
                    "subject": subj,
                    "description": f"Complete {sub_name} bundle including all 5 chapter study notes with lifetime access and future updates.",
                    "is_active": True,
                }
            )
            if p_created:
                Price.objects.create(product=prod, amount_paise=49900, is_current=True)

        # C. Monthly Pass (₹299)
        monthly_slug = "class-10-monthly-pass"
        p_monthly, p_created = Product.objects.get_or_create(
            slug=monthly_slug,
            defaults={
                "title": "Class 10 All-Subjects Monthly Pass",
                "product_type": Product.PRODUCT_TYPE_MONTHLY_PASS,
                "board": board,
                "academic_class": class_10,
                "description": "Unlimited 30-day all-access pass unlocking Mathematics, Physics, and Chemistry for Class 10.",
                "is_active": True,
            }
        )
        if p_created:
            Price.objects.create(product=p_monthly, amount_paise=29900, is_current=True)

        # D. Annual Pass (₹2,499)
        annual_slug = "class-10-annual-pass"
        p_annual, p_created = Product.objects.get_or_create(
            slug=annual_slug,
            defaults={
                "title": "Class 10 Full-Year All-Access Pass",
                "product_type": Product.PRODUCT_TYPE_ANNUAL_PASS,
                "board": board,
                "academic_class": class_10,
                "description": "Full academic year (365 days) unrestricted access to all Class 10 subjects and chapters.",
                "is_active": True,
            }
        )
        if p_created:
            Price.objects.create(product=p_annual, amount_paise=249900, is_current=True)

        # E. Custom Bundle (Science Super Bundle - Physics + Chemistry, ₹699)
        bundle_slug = "class-10-science-super-bundle"
        p_bundle, p_created = Product.objects.get_or_create(
            slug=bundle_slug,
            defaults={
                "title": "Class 10 Science Super Bundle (Physics + Chemistry)",
                "product_type": Product.PRODUCT_TYPE_BUNDLE,
                "board": board,
                "academic_class": class_10,
                "description": "Curated bundle containing both Physics and Chemistry complete subject notes at a discounted combo price.",
                "is_active": True,
            }
        )
        if p_created:
            Price.objects.create(product=p_bundle, amount_paise=69900, is_current=True)
            BundleItem.objects.create(bundle_product=p_bundle, target_type='SUBJECT', subject=created_subjects["Physics"])
            BundleItem.objects.create(bundle_product=p_bundle, target_type='SUBJECT', subject=created_subjects["Chemistry"])

        self.stdout.write(self.style.SUCCESS(f"  [+] Seeded Products across all 6 product types with 18% inclusive GST prices."))
        self.stdout.write(self.style.SUCCESS("==> Database seeding complete!"))
