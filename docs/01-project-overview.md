# 01. Project Overview & Assessment Context

> **Source**: Intern Assessment: Ed-Tech App (6-page specification document, dated October 30, 2026)

---

## 🎯 Project Purpose

The goal of this project is to engineer a production-ready, full-stack educational digital store. The platform allows students to browse hierarchical academic materials and purchase access under various licensing structures (per-chapter notes, complete subject packs, time-bound class passes, or custom bundles).

Payments are integrated using **Razorpay Test Mode**. Access to content is granted strictly after server-side cryptographic payment verification.

---

## 📐 Catalogue Hierarchy

Academic content is structured into a 5-level hierarchy:

```
Board (e.g. CBSE, ICSE, State Board)
 └── Class (e.g. Class 9, Class 10, Class 12)
      └── Subject (e.g. Mathematics, Physics, Chemistry)
           └── Chapter (e.g. Chemical Reactions, Quadratic Equations)
                └── Study Material (PDF notes, formula sheets, problem sets)
```

### Hierarchy Constraints
- Every **Study Material** belongs to exactly one **Chapter**.
- Every **Chapter** belongs to a **Subject**.
- Every **Subject** belongs to a **Class**.
- Every **Class** belongs to an education **Board**.
- Administrative users can manage every tier of this hierarchy and upload study notes (PDFs) to chapters.

---

## 🛡️ Ground Rules & Guidelines

1. **Independent Work**:
   - You may utilize documentation, third-party libraries, and AI coding assistants.
   - You **must** be prepared to explain every design choice, architectural decision, and line of code during the technical interview.
2. **Razorpay Test Mode Exclusively**:
   - Only test credentials (`rzp_test_*`) and test card/UPI handles (`success@razorpay`, `failure@razorpay`) may be used.
   - **Never** introduce live Razorpay keys, real credit card details, or real bank/UPI IDs.
3. **Secret Management**:
   - Never commit sensitive configuration or secrets to Git.
   - Commit a well-documented `.env.example` file. Keep `.env` git-ignored.
4. **Scope & Execution Philosophy**:
   - **A smaller, completely functioning, rock-solid application is significantly better than a large, buggy, unfinished one.**
   - Focus on core business logic, correct payment handling, and robust security before cosmetic frontend styling.

---

## 📊 Evaluation Focus Areas

The assessment directly evaluates end-to-end full-stack product engineering across seven core dimensions:

1. **Data Model**:
   - Clean relational database design with foreign keys, data normalization, proper indexing, and integer currency representations.
2. **API Design**:
   - RESTful patterns, consistent HTTP status codes, robust payload validation, and clean separation of concerns.
3. **User Interface**:
   - Clean, intuitive, responsive user and admin flows in React/TypeScript with proper error states and loading states.
4. **Payment Correctness**:
   - Accurate backend calculation of prices, upgrade discounts, coupons, and 18% GST.
   - Strict cryptographic signature verification (HMAC-SHA256).
5. **Failure & Concurrency Handling**:
   - Idempotent processing of webhooks and checkout callbacks.
   - Handling network failures, out-of-order deliveries, and customer dropouts during payment.
6. **Security & Access Control**:
   - Role-Based Access Control (RBAC), password hashing (Argon2/bcrypt), prevention of direct PDF link sharing, and rate limiting.
7. **Automated Testing**:
   - Automated Pytest test suite covering pricing algorithms, payment verification, webhook idempotency, and access restrictions.
