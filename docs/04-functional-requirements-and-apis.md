# 04. Functional Requirements & REST API Specifications

This document outlines the student and administrative user requirements along with the RESTful API endpoints and authorization rules.

---

## 🧑‍🎓 1. Student Functional Requirements

| Code | Priority | Requirement | Details |
| :--- | :--- | :--- | :--- |
| **S1** | **[MUST]** | Authentication | Sign up and log in via email/password (or mock OTP). Password hashed via Argon2/bcrypt. JWT tokens issued. |
| **S2** | **[MUST]** | Catalogue Browsing | Hierarchical navigation (Board -> Class -> Subject -> Chapter) and keyword search by title. |
| **S3** | **[MUST]** | Product Display | Product page displaying price, inclusions, duration, and dynamic state: `Buy`, `Owned`, `Upgrade`, or `Unlocked via Pass`. |
| **S4** | **[MUST]** | Cart & Pricing Breakdown | Multi-item cart supporting coupon code application and itemized 18% GST breakdown. |
| **S5** | **[MUST]** | Razorpay Checkout | Native modal checkout supporting UPI (`success@razorpay`, `failure@razorpay`), test cards, and netbanking. |
| **S6** | **[MUST]** | My Library | Personalized dashboard listing all active entitlements and time-bound pass expiry countdowns. |
| **S7** | **[MUST]** | Protected In-Browser Reader | Securely stream and view PDF notes in the browser. Server must refuse un-entitled requests with HTTP 403. |
| **S8** | **[SHOULD]** | Order History & Invoices | View previous orders with downloadable PDF invoices or printable HTML receipts. |

---

## 🛠️ 2. Admin Functional Requirements

| Code | Priority | Requirement | Details |
| :--- | :--- | :--- | :--- |
| **A1** | **[MUST]** | Hierarchy Management | Full CRUD operations for Boards, Classes, Subjects, and Chapters. |
| **A2** | **[MUST]** | Study Material Upload | Upload PDF notes to chapters; designate specific chapters as Free Samples. |
| **A3** | **[MUST]** | Product & Price Configuration | Create products (Chapter notes, Subject pack, Passes, Bundles) and assign prices in paise. |
| **A4** | **[MUST]** | Order & Payment Monitoring | View all orders and payment attempts with filtering by status and date range. |
| **A5** | **[SHOULD]** | Coupon Management | Create, activate, and deactivate coupon codes with usage caps and date bounds. |
| **A6** | **[SHOULD]** | Manual Access Control | Manually grant or revoke content entitlements with mandatory audit reason logging. |
| **A7** | **[SHOULD]** | Revenue Dashboard | Visual analytics showing daily revenue, top-selling products, and active pass counts. |

---

## 🌐 3. REST API Endpoint Specifications

All endpoints return JSON responses. Protected endpoints require the `Authorization: Bearer <jwt_token>` header or authenticated HTTP-only cookie.

### A. Authentication & User Profile
```http
POST /api/v1/auth/register/          # Register new student
POST /api/v1/auth/login/             # Authenticate, returns access & refresh tokens
POST /api/v1/auth/refresh/           # Refresh expired access token
POST /api/v1/auth/logout/            # Invalidate refresh token / clear cookie
GET  /api/v1/auth/me/                # Fetch authenticated user profile & role
```

### B. Catalogue (Public / Student)
```http
GET  /api/v1/catalog/boards/                    # List education boards
GET  /api/v1/catalog/boards/{id}/classes/       # List classes under board
GET  /api/v1/catalog/classes/{id}/subjects/     # List subjects under class
GET  /api/v1/catalog/subjects/{id}/chapters/    # List chapters with free sample flags
GET  /api/v1/catalog/search/?q={query}          # Search subjects and chapters by keyword
```

### C. Products, Pricing & Upgrades
```http
GET  /api/v1/products/                          # List active products with filters
GET  /api/v1/products/{id}/                     # Product details with inclusions
POST /api/v1/products/{id}/calculate-price/     # Returns user-tailored price after upgrade credit
```

### D. Cart & Order Creation
```http
POST /api/v1/cart/validate/          # Validates items, calculates credits & 18% GST split
POST /api/v1/coupons/apply/          # Validates coupon code and returns discount amount
POST /api/v1/orders/create/          # Server validates cart, saves Order, creates Razorpay Order
```

### E. Razorpay Payment & Webhook
```http
POST /api/v1/payments/verify/        # Validates HMAC-SHA256 signature from Checkout modal
POST /api/v1/payments/webhook/       # Public webhook endpoint; verifies X-Razorpay-Signature
```

### F. Student Library & Protected Content Delivery
```http
GET  /api/v1/library/                # List active entitlements, purchased items & passes
GET  /api/v1/materials/{id}/stream/  # Stream PDF notes (403 if user lacks active entitlement)
GET  /api/v1/orders/history/         # List user order history
GET  /api/v1/orders/{id}/invoice/    # Generate printable HTML or PDF invoice
```

### G. Admin APIs (Enforces Role = ADMIN, HTTP 403 on Student)
```http
# Catalogue Management
POST/PUT/DELETE /api/v1/admin/boards/
POST/PUT/DELETE /api/v1/admin/classes/
POST/PUT/DELETE /api/v1/admin/subjects/
POST/PUT/DELETE /api/v1/admin/chapters/
POST            /api/v1/admin/chapters/{id}/upload-material/   # Multipart PDF upload

# Products & Pricing
POST/PUT/DELETE /api/v1/admin/products/
POST            /api/v1/admin/products/{id}/price/             # Set or update price

# Coupons
POST/PUT/DELETE /api/v1/admin/coupons/

# Orders & Analytics
GET  /api/v1/admin/orders/?status={s}&date_from={d1}&date_to={d2}
GET  /api/v1/admin/analytics/dashboard/                       # Revenue & active passes

# Manual Entitlements
POST /api/v1/admin/entitlements/manual-grant/                  # Grant access with reason
POST /api/v1/admin/entitlements/manual-revoke/                 # Revoke access with reason
```
