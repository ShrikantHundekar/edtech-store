# 09. User Stories & Acceptance Criteria

This document provides a comprehensive, production-grade backlog of User Stories for the **EdTech Store**. Each story adheres to standard Agile/Scrum formats with explicit preconditions, Gherkin-style (`Given-When-Then`) Acceptance Criteria, edge cases, and technical implementation notes.

---

## 👥 Personas

1. **Student (Unauthenticated / Prospective)**: Browses public catalogues, previews sample chapters, and signs up.
2. **Student (Authenticated / Learner)**: Purchases single notes, subject packs, or class passes, manages cart, reads purchased study materials in-browser, and views pass countdowns.
3. **Administrator**: Manages academic hierarchies, uploads PDFs, configures products, prices, and coupons, reviews orders, and audits access grants.
4. **System (Automated Agent)**: Ingests webhooks, verifies HMAC signatures, and manages the idempotent entitlement engine.

---

## 📑 Epic Index

- [Epic 1: Authentication & Authorization](#epic-1-authentication--authorization)
- [Epic 2: Catalogue Browsing & Discovery](#epic-2-catalogue-browsing--discovery)
- [Epic 3: Products, Upgrades & Pricing Engine](#epic-3-products-upgrades--pricing-engine)
- [Epic 4: Cart, Coupons & GST Breakdown](#epic-4-cart-coupons--gst-breakdown)
- [Epic 5: Razorpay Checkout & Payment Webhooks](#epic-5-razorpay-checkout--payment-webhooks)
- [Epic 6: Entitlements & Secure PDF Delivery](#epic-6-entitlements--secure-pdf-delivery)
- [Epic 7: Student Library & Invoicing](#epic-7-student-library--invoicing)
- [Epic 8: Administration & Content Management](#epic-8-administration--content-management)
- [Epic 9: Administrative Analytics & Auditing](#epic-9-administrative-analytics--auditing)

---

## Epic 1: Authentication & Authorization

### US-AUTH-01: Student Registration
- **As a** prospective student,  
  **I want to** create an account with my email, password, and full name,  
  **So that** I can buy study notes and access personalized educational content.
- **Preconditions**:
  - Email address must not already exist in the `users` table.
- **Acceptance Criteria**:
  - **Given** valid registration details (valid email format, strong password $\ge 8$ chars),  
    **When** I submit the registration form,  
    **Then** the backend hashes my password using **Argon2** or **bcrypt**, saves the user with role `STUDENT`, and returns HTTP 201 with an access/refresh token pair.
  - **Given** an email address that is already registered,  
    **When** I submit registration,  
    **Then** the server returns HTTP 400 Bad Request with an error message `"Email already registered"`.
- **Technical Notes**:
  - Models: `User`.
  - Passwords must never be stored or logged in plaintext.

---

### US-AUTH-02: Student & Admin Login with Rate Limiting
- **As a** registered user (Student or Admin),  
  **I want to** log in with my email and password,  
  **So that** I can access my role-authorized features.
- **Acceptance Criteria**:
  - **Given** correct credentials for an active user,  
    **When** the login endpoint is called,  
    **Then** return HTTP 200 with short-lived JWT access token (15–30 min) and a refresh token (or set secure HTTP-only cookies).
  - **Given** 5 consecutive failed login attempts within 1 minute from the same IP,  
    **When** a 6th attempt is made,  
    **Then** the server throttles the request and returns HTTP 429 Too Many Requests.
- **Technical Notes**:
  - Endpoints: `POST /api/v1/auth/login/`.
  - Apply DRF Throttling (`ScopedRateThrottle`).

---

### US-AUTH-03: Role-Based Access Control (RBAC) Enforcement
- **As a** platform security officer,  
  **I want** administrative routes to reject non-admin users,  
  **So that** students cannot manipulate prices, content, or orders.
- **Acceptance Criteria**:
  - **Given** a user authenticated with `role = 'STUDENT'`,  
    **When** they send a request to any `/api/v1/admin/*` endpoint,  
    **Then** the server must immediately return **HTTP 403 Forbidden**.
  - **Given** an unauthenticated request to a protected endpoint,  
    **When** accessed,  
    **Then** the server returns **HTTP 401 Unauthorized**.

---

## Epic 2: Catalogue Browsing & Discovery

### US-CAT-01: Hierarchical Catalogue Navigation
- **As a** student,  
  **I want to** navigate through Board $\rightarrow$ Class $\rightarrow$ Subject $\rightarrow$ Chapter,  
  **So that** I can locate relevant study materials for my syllabus.
- **Acceptance Criteria**:
  - **Given** active boards, classes, and subjects in the database,  
    **When** I select a Board (e.g. CBSE),  
    **Then** only classes associated with CBSE are displayed.
  - **When** I drill down to a Subject,  
    **Then** all chapters for that subject are listed in sequential order by `chapter_number`.

---

### US-CAT-02: Free Sample Chapter Access
- **As a** prospective student,  
  **I want to** view a designated free sample chapter within a subject,  
  **So that** I can evaluate the quality of the study notes before making a purchase.
- **Acceptance Criteria**:
  - **Given** a chapter with `is_free_sample = True`,  
    **When** an authenticated student opens the chapter notes,  
    **Then** the reader displays the PDF without requiring an active purchase or paid entitlement.
  - **Given** an unauthenticated visitor,  
    **When** they attempt to open the free sample,  
    **Then** they are prompted to sign in first.

---

### US-CAT-03: Keyword Search Across Curriculum
- **As a** student,  
  **I want to** search for topics or chapters using keyword search (e.g. "Quadratic Equations"),  
  **So that** I can quickly find study notes without manually drilling down the hierarchy.
- **Acceptance Criteria**:
  - **Given** a query parameter `?q=Quadratic`,  
    **When** `/api/v1/catalog/search/?q=Quadratic` is requested,  
    **Then** return matching chapters and subjects along with their breadcrumb metadata (Board, Class, Subject).

---

## Epic 3: Products, Upgrades & Pricing Engine

### US-PRC-01: Dynamic Product State & Overlap Prevention
- **As a** student viewing a product page,  
  **I want to** see whether I already own the product or whether it is unlocked by a pass,  
  **So that** I do not mistakenly purchase duplicate content.
- **Acceptance Criteria**:
  - **Given** a student who already owns a **Subject Pack**,  
    **When** they view an individual **Chapter** within that subject,  
    **Then** the button displays `"Owned (via Subject Pack)"` and adding to cart is disabled.
  - **Given** a student with an active **Class Pass**,  
    **When** they view any subject or chapter within that class,  
    **Then** the UI displays `"Unlocked with Class Pass"` and checkout is disabled.
  - **Given** a product the student has already bought directly,  
    **When** they view the item,  
    **Then** the status shows `"Owned"`.

---

### US-PRC-02: Subject Pack Upgrade Credit Calculation
- **As a** student who has already bought individual chapters in a subject,  
  **I want to** have those past payments deducted from the price of the full Subject Pack,  
  **So that** I only pay the fair prorated difference to upgrade.
- **Acceptance Criteria**:
  - **Given** a student previously purchased Chapter 1 (₹49) and Chapter 2 (₹49) of Class 10 Math,  
    **When** they view the Class 10 Math Subject Pack (full price ₹499),  
    **Then** the system calculates:
    $$\text{Payable Price} = \max(0, 499 - (49 + 49)) = ₹401 \text{ (40,100 paise)}$$
  - **Given** a student whose prior chapter purchases total $\ge$ Subject Pack price,  
    **When** they view the Subject Pack,  
    **Then** the payable price is floored at **₹0** (no negative price).
- **Technical Notes**:
  - Upgrade calculation must be performed server-side by summing `order_items.unit_price_paise` where `status = 'PAID'`.

---

### US-PRC-03: Pass Expiry Stacking (Early Renewal)
- **As a** student holding an active 30-day Monthly Pass,  
  **I want** purchasing another Monthly Pass before expiry to extend from my current expiry date,  
  **So that** I don't lose any paid days.
- **Acceptance Criteria**:
  - **Given** a student whose existing class pass expires on `2026-12-15 10:00:00`,  
    **When** they purchase a 30-day renewal on `2026-12-05`,  
    **Then** the new `valid_until` date is set to `2027-01-14 10:00:00` (15th Dec + 30 days).
  - **Given** a student with no active pass,  
    **When** they purchase a pass,  
    **Then** validity is calculated from `now()`.

---

## Epic 4: Cart, Coupons & GST Breakdown

### US-CART-01: Multi-Item Cart & Server-Side Price Verification
- **As a** student,  
  **I want to** add multiple items (e.g. two chapter notes and a subject pack) to my cart,  
  **So that** I can purchase them together in a single transaction.
- **Acceptance Criteria**:
  - **Given** items added to the cart,  
    **When** the cart is validated via `POST /api/v1/cart/validate/`,  
    **Then** the server fetches fresh prices from the `prices` table, applies upgrade credits, and computes subtotals.
  - **Given** a modified client payload that attempts to send a tampered price (e.g. `price: 1`),  
    **When** processed,  
    **Then** the server completely ignores the client price and recomputes the amount from database records.

---

### US-CART-02: Coupon Application & Validation
- **As a** student,  
  **I want to** apply a discount coupon code in the cart,  
  **So that** I receive a legitimate promotional discount.
- **Acceptance Criteria**:
  - **Given** an active coupon with code `DISCOUNT50` (flat ₹50 off),  
    **When** applied to a cart with subtotal ₹200,  
    **Then** the cart total becomes ₹150.
  - **Given** an expired coupon or one exceeding its `usage_limit`,  
    **When** applied,  
    **Then** return HTTP 400 with a specific error message (`"Coupon expired"` or `"Coupon usage limit reached"`).

---

### US-CART-03: 18% Inclusive GST Split Breakdown
- **As a** student,  
  **I want to** see an itemized tax breakdown showing the 18% GST component,  
  **So that** I understand the net taxable amount and government tax split.
- **Acceptance Criteria**:
  - **Given** a final payable inclusive amount $P_{\text{inclusive}}$ (e.g., ₹499.00 / 49,900 paise),  
    **When** the checkout summary is calculated,  
    **Then** display:
    - Base Taxable Amount: $\operatorname{round}(49900 / 1.18) = 42,288 \text{ paise}$ (₹422.88)
    - 18% GST: $49900 - 42288 = 7,612 \text{ paise}$ (₹76.12)
    - CGST (9%): ₹38.06
    - SGST (9%): ₹38.06

---

## Epic 5: Razorpay Checkout & Payment Webhooks

### US-PAY-01: Razorpay Order Creation
- **As a** student initiating checkout,  
  **I want to** generate a Razorpay order from the backend,  
  **So that** the standard Razorpay checkout modal opens with the verified amount.
- **Acceptance Criteria**:
  - **Given** a validated cart with net payable amount $> 0$,  
    **When** `POST /api/v1/orders/create/` is called,  
    **Then** the backend creates an internal `Order` (status `PENDING`), calls the Razorpay API to generate a `razorpay_order_id`, and returns the `order_id`, `amount_paise`, and `key_id` to the frontend.
  - **Given** an order where upgrade credit brings the payable balance to **₹0**,  
    **When** submitted,  
    **Then** mark the order as `PAID` immediately without invoking Razorpay and grant entitlements directly.

---

### US-PAY-02: Cryptographic Checkout Signature Verification
- **As a** payment processing engine,  
  **I want to** verify the HMAC-SHA256 signature returned by Razorpay Checkout,  
  **So that** fraudulent or tampered payment callbacks are rejected.
- **Acceptance Criteria**:
  - **Given** `razorpay_order_id`, `razorpay_payment_id`, and `razorpay_signature`,  
    **When** verified on `/api/v1/payments/verify/`,  
    **Then** the backend computes $\text{HMAC-SHA256}(\text{order\_id} + \text{"\|"} + \text{payment\_id}, \text{RAZORPAY\_KEY\_SECRET})$.
  - **If** the calculated signature matches the received signature,  
    **Then** record the payment and trigger the entitlement fulfillment service.
  - **If** the signature does not match,  
    **Then** reject the request with HTTP 400 and grant zero access.

---

### US-PAY-03: Webhook Verification & Dual-Path Idempotency
- **As a** system reliability architect,  
  **I want** webhook processing and checkout callbacks to be strictly idempotent,  
  **So that** access is granted exactly once, even if both arrive simultaneously or duplicate events are sent.
- **Acceptance Criteria**:
  - **Given** an inbound `payment.captured` webhook at `/api/v1/payments/webhook/`,  
    **When** received,  
    **Then** verify `X-Razorpay-Signature` against the **raw request body**.
  - **When** processing an order that is already marked `PAID`,  
    **Then** do not duplicate `Entitlement` records, do not duplicate revenue counting, and respond with HTTP 200 OK.
  - **Given** a scenario where the student closes the browser before checkout verification completes,  
    **When** the `payment.captured` webhook arrives,  
    **Then** it successfully marks the order as `PAID` and provisions entitlements.

---

### US-PAY-04: Failed Payment Handling
- **As a** student who encounters a payment issue (e.g. using `failure@razorpay`),  
  **I want to** receive clear feedback and have the option to retry,  
  **So that** I know the payment did not succeed and I can try another payment method.
- **Acceptance Criteria**:
  - **Given** a failed payment attempt,  
    **When** Razorpay notifies failure (or webhook `payment.failed` fires),  
    **Then** update `payments.status = 'FAILED'`, leave `orders.status = 'FAILED'` or `'PENDING'`, and grant **no entitlements**.
  - **Then** the UI shows an error notification with a `"Retry Payment"` action.

---

## Epic 6: Entitlements & Secure PDF Delivery

### US-ENT-01: Automatic Entitlement Provisioning
- **As a** student with a newly confirmed payment,  
  **I want to** receive immediate access to my purchased content,  
  **So that** I can study without manual admin intervention.
- **Acceptance Criteria**:
  - **Given** an order transition to `PAID`,  
    **When** the entitlement engine runs,  
    **Then** create rows in `entitlements` matching each `order_item`:
    - Chapter Notes $\rightarrow$ `product_type = 'CHAPTER'`, `access_type = 'LIFETIME'`.
    - Subject Pack $\rightarrow$ `product_type = 'SUBJECT'`, `access_type = 'LIFETIME'`.
    - Monthly/Annual Pass $\rightarrow$ `product_type = 'CLASS_PASS'`, `access_type = 'TIME_BOUND'`.

---

### US-ENT-02: Secure Server-Side PDF Delivery (Anti-Piracy)
- **As a** content copyright holder,  
  **I want** PDF study notes to be accessible only via authenticated streaming endpoints,  
  **So that** un-entitled users cannot download or guess file links.
- **Acceptance Criteria**:
  - **Given** an HTTP request to `GET /api/v1/materials/{id}/stream/`,  
    **When** the user has no active entitlement for that material, chapter, subject, or class,  
    **Then** the server returns **HTTP 403 Forbidden**.
  - **Given** an authorized student or a free sample chapter,  
    **When** requested,  
    **Then** the server streams the PDF binary with headers `Content-Type: application/pdf` and `Content-Disposition: inline`.
  - **Static media URL test**: Requesting `/media/notes/chapter1.pdf` directly from the web server returns HTTP 404 or HTTP 403.

---

## Epic 7: Student Library & Invoicing

### US-LIB-01: My Library Dashboard
- **As a** student,  
  **I want** a centralized "My Library" dashboard,  
  **So that** I can easily access all content I have acquired and monitor active pass validity.
- **Acceptance Criteria**:
  - **Given** an authenticated student with active entitlements,  
    **When** they open `/library`,  
    **Then** display:
    - Owned individual chapter notes with direct `"Read"` buttons.
    - Owned subject packs with complete chapter lists.
    - Active class passes with a countdown timer (e.g. `"Expires in 18 days"`).

---

### US-LIB-02: Order History & Invoices
- **As a** student,  
  **I want to** view my past orders and download official GST invoices,  
  **So that** I have proof of purchase and tax records.
- **Acceptance Criteria**:
  - **Given** completed purchases,  
    **When** the student navigates to `/orders`,  
    **Then** list all past orders with date, order ID, payment status, and net amount.
  - **When** clicking `"Download Invoice"`,  
    **Then** generate a printable HTML view or PDF containing the order number, student name, itemized products, 18% GST split, and Razorpay payment ID.

---

## Epic 8: Administration & Content Management

### US-ADM-01: Academic Catalogue CRUD
- **As an** administrator,  
  **I want to** create, update, and delete Boards, Classes, Subjects, and Chapters,  
  **So that** I can keep curriculum offerings current.
- **Acceptance Criteria**:
  - **Given** admin authentication,  
    **When** creating a new Chapter under a Subject,  
    **Then** validate required fields (`title`, `chapter_number`) and persist to the database.
  - **Given** a non-admin user,  
    **When** calling these endpoints,  
    **Then** return HTTP 403 Forbidden.

---

### US-ADM-02: PDF Material Upload & Free Sample Toggle
- **As an** administrator,  
  **I want to** upload PDF files to a chapter and toggle whether a chapter is a free sample,  
  **So that** students have study materials and preview content.
- **Acceptance Criteria**:
  - **Given** a PDF file $\le 25\text{MB}$,  
    **When** uploaded via `POST /api/v1/admin/chapters/{id}/upload-material/`,  
    **Then** store the file in the protected media directory and save metadata in the `materials` table.
  - **When** the admin toggles `is_free_sample = True`,  
    **Then** that chapter becomes accessible to all authenticated students without payment.

---

### US-ADM-03: Product & Pricing Administration
- **As an** administrator,  
  **I want to** create products (Chapter note, Subject pack, Class passes, Bundles) and assign prices in paise,  
  **So that** they become immediately available for student purchase.
- **Acceptance Criteria**:
  - **Given** product details and an amount in paise (e.g., 29900 paise for ₹299.00),  
    **When** saved,  
    **Then** a new record is created in `products` and an active record in `prices`.

---

### US-ADM-04: Manual Access Grant / Revocation with Audit Logging
- **As an** administrator,  
  **I want to** manually grant or revoke a student's access with a mandatory reason,  
  **So that** customer support can resolve disputes while preserving an audit trail.
- **Acceptance Criteria**:
  - **Given** student ID, product ID, action (`GRANT`/`REVOKE`), and reason text,  
    **When** submitted by an admin,  
    **Then** update `entitlements` accordingly and insert an entry into `manual_access_logs` detailing `admin_id`, `student_id`, `action`, `reason`, and `timestamp`.

---

## Epic 9: Administrative Analytics & Auditing

### US-REP-01: Filterable Order & Payment Audit Log
- **As an** administrator,  
  **I want to** search and filter all orders and payment attempts by status and date range,  
  **So that** I can investigate transaction failures and reconcile payments.
- **Acceptance Criteria**:
  - **Given** query parameters `?status=PAID&date_from=2026-11-01&date_to=2026-11-30`,  
    **When** requested,  
    **Then** return paginated orders matching the criteria, including Razorpay payment ID and payment method.

---

### US-REP-02: Revenue & Performance Dashboard
- **As a** platform executive,  
  **I want** a dashboard displaying daily revenue, top-selling products, and active class passes,  
  **So that** I can assess commercial performance and engagement.
- **Acceptance Criteria**:
  - **Given** the analytics endpoint `GET /api/v1/admin/analytics/dashboard/`,  
    **When** loaded,  
    **Then** return:
    - Total gross and net revenue aggregated by day.
    - Top 5 products ranked by order volume.
    - Total count of active Monthly and Annual class passes.
