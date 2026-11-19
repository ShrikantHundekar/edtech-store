# EdTech Store – Full-Stack Development Documentation

> **Assessment-Based Engineering Plan**  
> Source: Intern Assessment: Ed-Tech App (dated October 30, 2026)  
> Stack: Python (Django + DRF) | MySQL | React.js (TypeScript) | Razorpay (Test Mode)

---

## 📌 Executive Summary

The **EdTech Store** is a full-stack educational digital marketplace where students can explore study materials and purchase access under flexible licensing models:
- **Per Chapter** (Lifetime access)
- **Per Subject** (Lifetime access + future chapters)
- **Monthly or Annual Class Passes** (Time-bound access to all subject content in a class)
- **Custom Bundles** (Curated collections)
- **Free Samples** (Preview chapters)

Payments are processed via **Razorpay Test Mode**. Access is strictly decoupled from order placement: content access is governed by an **Entitlement Engine** that grants permissions only after cryptographically verified payment (handling both frontend checkout callbacks and asynchronous webhooks with strict idempotency).

---

## 🏛 Catalogue Hierarchy

Content is structured in a strict 5-tier relational hierarchy:

```
Board (e.g., CBSE, ICSE)
 └── Class (e.g., Class 10, Class 12)
      └── Subject (e.g., Mathematics, Physics)
           └── Chapter (e.g., Quadratic Equations)
                └── Study Material (PDF notes, secure download/viewer)
```

---

## 📂 Documentation Directory

To keep the development organized and production-grade, the specifications have been decomposed into dedicated markdown files in [`docs/`](file:///c:/Users/Shrikant/Downloads/Assissment_Interview/docs):

| Document | Description |
| :--- | :--- |
| **[01. Project Overview](file:///c:/Users/Shrikant/Downloads/Assissment_Interview/docs/01-project-overview.md)** | Background, assessment rules, constraints, evaluation focus, and ground rules. |
| **[02. Products & Business Rules](file:///c:/Users/Shrikant/Downloads/Assissment_Interview/docs/02-products-and-business-rules.md)** | Product catalog definitions, overlapping purchase protection, upgrade credit math, pass expiry/renewal, coupons, and 18% GST calculation. |
| **[03. System Architecture & Database](file:///c:/Users/Shrikant/Downloads/Assissment_Interview/docs/03-system-architecture-and-database.md)** | Proposed tech stack, security boundaries, 14 mandatory tables + supporting models, and complete Mermaid ER diagram. |
| **[04. Functional Requirements & APIs](file:///c:/Users/Shrikant/Downloads/Assissment_Interview/docs/04-functional-requirements-and-apis.md)** | Student features (S1–S8), Admin features (A1–A7), Must/Should priorities, and REST API route blueprints. |
| **[05. Razorpay & Entitlements](file:///c:/Users/Shrikant/Downloads/Assissment_Interview/docs/05-razorpay-and-entitlements.md)** | Dual-path payment verification (Checkout callback + Webhook), HMAC-SHA256 signature verification, idempotency logic, and server-side PDF lock. |
| **[06. Development Phases & Roadmap](file:///c:/Users/Shrikant/Downloads/Assissment_Interview/docs/06-development-phases.md)** | 10 development phases, task checklists, deliverables, and recommended 4-week execution timeline. |
| **[07. Testing & Security Checklist](file:///c:/Users/Shrikant/Downloads/Assissment_Interview/docs/07-testing-and-security.md)** | Mandatory Pytest suite, tampered signature tests, access control tests, and comprehensive security hardening checklist. |
| **[08. Seed Data & Local Setup](file:///c:/Users/Shrikant/Downloads/Assissment_Interview/docs/08-seed-data-and-setup.md)** | Local startup commands, sample seed catalog (1 board, 2 classes, 3 subjects, 5 chapters/subject), seed credentials, and `.env.example`. |
| **[09. User Stories & Acceptance Criteria](file:///c:/Users/Shrikant/Downloads/Assissment_Interview/docs/09-user-stories.md)** | Comprehensive Agile user stories covering student, admin, and system personas with Gherkin acceptance criteria. |

---

## 🛠 Recommended Technology Stack

| Layer | Technology | Details |
| :--- | :--- | :--- |
| **Frontend** | React.js + TypeScript | Vite / Tailwind CSS / PDF.js or native iframe viewer |
| **Backend** | Python 3.11+ / Django | Django REST Framework (DRF) |
| **Database** | MySQL 8.0+ | Relational schema, Django ORM & Migrations |
| **Authentication** | JWT or HTTP-Only Cookies | Argon2 or bcrypt password hashing, Role-Based Access Control |
| **Payments** | Razorpay SDK (Test Mode) | HMAC-SHA256 verification, Webhook processing |
| **Storage** | Protected Local Disk / S3 | Served via authenticated streaming endpoints (never public URLs) |
| **Testing** | Pytest / Pytest-Django | Automated unit, integration, and payment idempotency tests |

---

## ⚡ Quick Action – Phase 1 Kickoff

To begin Phase 1:
1. Create `backend/` and `frontend/` directories.
2. Initialize Python virtual environment: `python -m venv venv`.
3. Install dependencies: `pip install django djangorestframework django-cors-headers mysqlclient python-dotenv razorpay`.
4. Configure MySQL database and connect Django via `settings.py`.
5. Run initial migrations and verify local API server starts cleanly.

See [`docs/06-development-phases.md`](file:///c:/Users/Shrikant/Downloads/Assissment_Interview/docs/06-development-phases.md) for full phase details.
