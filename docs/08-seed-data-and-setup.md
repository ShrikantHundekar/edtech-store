# 08. Seed Data & Local Setup Guide

This document defines the seed data requirements mandated by the assessment, local development setup steps, and environment configuration.

---

## 🌾 1. Mandatory Seed Data Specifications

The application must be capable of launching locally with a comprehensive, pre-populated dataset:

| Entity | Quantity | Specification / Details |
| :--- | :--- | :--- |
| **Boards** | 1 | e.g., `CBSE (Central Board of Secondary Education)` |
| **Classes** | 2 | e.g., `Class 10` and `Class 12` |
| **Subjects** | 3 | e.g., `Mathematics`, `Physics`, and `Chemistry` |
| **Chapters** | 5 per Subject | 15 chapters total across the 3 subjects. |
| **Free Samples** | 1 per Subject | Exactly 1 chapter per subject designated with `is_free_sample = True`. |
| **Study Materials** | 1+ per Chapter | Sample PDF note attached to every chapter for viewing. |
| **Products & Prices** | Multiple | Configured Chapter Notes (₹49), Subject Packs (₹499), Monthly Passes (₹299), and Annual Passes (₹2,499). |
| **Admin Account** | 1 | Pre-seeded with `role = 'ADMIN'`. |
| **Student Account**| 1 | Pre-seeded with `role = 'STUDENT'`. |

### Default Seed Credentials

| Account Role | Email | Password |
| :--- | :--- | :--- |
| **Admin User** | `admin@edtechstore.local` | `Admin@123456` |
| **Student User** | `student@edtechstore.local` | `Student@123456` |

---

## 💻 2. Local Setup Guide (Without Docker)

### Prerequisites
- Python 3.11+
- Node.js 18+ and npm
- MySQL Server 8.0+

### Step 1: Database Setup
```sql
CREATE DATABASE edtech_store CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### Step 2: Backend Setup
```bash
# Navigate to backend directory
cd backend

# Create and activate virtual environment
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment variables
cp .env.example .env

# Apply migrations
python manage.py migrate

# Seed database with sample data
python manage.py seed_data

# Start Django development server
python manage.py runserver 8000
```

### Step 3: Frontend Setup
```bash
# Navigate to frontend directory
cd frontend

# Install Node dependencies
npm install

# Start Vite development server
npm run dev
```

---

## 🐳 3. Docker Compose Setup (Recommended)

To run the entire stack with a single command, use Docker Compose:

```bash
docker-compose up --build
```

### `docker-compose.yml` Architecture:
- `db`: MySQL 8.0 service with persistent volume.
- `backend`: Django REST API running on port 8000 (auto-runs migrations & seed script).
- `frontend`: React + Vite development server running on port 5173.

---

## 📄 4. Environment Variables Specification (`.env.example`)

Create a `.env.example` in the backend root containing all required variables with placeholder values. **Never commit real keys.**

```env
# ==========================================
# Django Core Settings
# ==========================================
DEBUG=True
SECRET_KEY=django-insecure-change-this-in-production-demo-key-123456789
ALLOWED_HOSTS=localhost,127.0.0.1

# ==========================================
# Database Configuration (MySQL)
# ==========================================
DB_NAME=edtech_store
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_HOST=127.0.0.1
DB_PORT=3306

# ==========================================
# JWT Authentication Settings
# ==========================================
JWT_SECRET_KEY=super-secret-jwt-signing-key-for-development-purposes
JWT_ACCESS_LIFETIME_MINUTES=30
JWT_REFRESH_LIFETIME_DAYS=7

# ==========================================
# Razorpay Test Credentials (Test Mode Only)
# ==========================================
# Get these from your Razorpay Dashboard under Settings -> API Keys (Test Mode)
RAZORPAY_KEY_ID=rzp_test_YourTestKeyIdHere
RAZORPAY_KEY_SECRET=YourRazorpayTestKeySecretHere
RAZORPAY_WEBHOOK_SECRET=YourRazorpayWebhookSecretHere

# ==========================================
# Frontend Configuration
# ==========================================
FRONTEND_URL=http://localhost:5173
```
