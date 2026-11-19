# 02. Products & Business Rules Engine

This document defines the product catalog, licensing models, pricing calculations, and core business rules that govern the EdTech store.

---

## 📦 1. Product Types & Inclusions

The system supports six distinct product types. Prices are configured by administrators in **paise** (1 INR = 100 paise) and displayed inclusive of 18% GST.

| # | Product Type | Scope & Inclusions | Access Duration | Example Price |
| :--- | :--- | :--- | :--- | :--- |
| **1** | **Chapter Notes** | All study materials within a single chapter. | **Lifetime** | ₹49 (4,900 paise) |
| **2** | **Subject Pack** | All chapters within one subject, including any chapters added in the future. | **Lifetime** | ₹499 (49,900 paise) |
| **3** | **Monthly Pass** | All subjects and chapters belonging to a specific class. | **30 Days** | ₹299 (29,900 paise) |
| **4** | **Annual Pass** | All subjects and chapters belonging to a specific class. | **365 Days** | ₹2,499 (249,900 paise) |
| **5** | **Custom Bundle** | Hand-picked combination of chapters or subjects curated by admin. | **Lifetime** | Admin-defined |
| **6** | **Free Sample** | One chapter per subject designated by admin as a free preview. Requires user sign-in. | **Lifetime** | ₹0 (0 paise) |

---

## ⚙️ 2. Core Business Rules

### A. Overlapping Purchase Protection
To protect students from paying twice for the same content:
1. **Subject Pack Ownership**:
   - If a student owns a Subject Pack, they must **not** be allowed to purchase individual chapters inside that subject.
   - The UI must display `"Owned (via Subject Pack)"` and disable the purchase button.
2. **Active Class Pass**:
   - An active Monthly or Annual Class Pass automatically unlocks all subjects and chapters in that class.
   - While the pass is active, the student cannot buy individual chapters or subject packs within that class. The UI should display `"Unlocked with Class Pass"`.
3. **Existing Entitlement**:
   - If an item has already been purchased, the UI must mark it as `"Owned"` and prevent re-adding to the cart.

---

### B. Subject Pack Upgrade Credit Calculation
When a student has previously purchased one or more individual chapters within a subject and later decides to purchase the full **Subject Pack**, the system grants credit for the prior purchases.

#### Upgrade Rule Formula:
$$\text{Upgrade Price} = \max\left(0, \; \text{Subject Pack Base Price} - \sum \text{Amount Paid for Owned Chapters in Subject}\right)$$

#### Example:
- Student previously bought **Chapter 1** (₹49) and **Chapter 2** (₹49). Total paid = ₹98.
- Subject Pack full price = ₹499.
- **Payable Subject Pack Price** = ₹499 − ₹98 = **₹401**.
- If previously paid amounts exceed or equal the Subject Pack price, the payable price floors at **₹0** (no negative billing).

---

### C. Time-Bound Passes & Early Renewal Logic
Monthly (30 days) and Annual (365 days) passes are governed by strict timestamps (`valid_from` and `valid_until`).

1. **Standard Activation**:
   - If a student has no active pass:
     $$\text{valid\_until} = \text{current\_timestamp} + \text{Duration (30 or 365 days)}$$
2. **Early Renewal (Pass Stacking)**:
   - If a student purchases a renewal pass **before** their current pass expires, access must **not** reset to today.
   - Access is extended from the **existing expiry date**:
     $$\text{new\_valid\_until} = \text{existing\_valid\_until} + \text{Pass Duration}$$
3. **Pass Expiration**:
   - Once $\text{current\_timestamp} > \text{valid\_until}$, entitlements associated with that pass transition to `EXPIRED`.
   - The backend immediately refuses access to materials unless another valid entitlement exists.

---

### D. Coupons & Discount Rules
Coupons can be applied at cart/checkout level with strict validation:
1. **Coupon Types**:
   - **Flat Discount**: A fixed amount deducted in paise (e.g., ₹50 off).
   - **Percentage Discount**: A percentage discount applied to the cart subtotal (e.g., 10% off).
2. **Validation Checks**:
   - Expiration date check: $\text{current\_timestamp} \le \text{valid\_until}$.
   - Max usage limit check: Total times coupon has been redeemed $<$ `usage_limit`.
   - Active status: `is_active == True`.
   - Minimum cart value: (optional threshold validation).
3. **Calculation Precedence**:
   $$\text{Subtotal} = \sum \text{Item Prices (after Upgrade Credits)}$$
   $$\text{Discounted Total} = \max\left(0, \; \text{Subtotal} - \text{Coupon Discount}\right)$$

---

### E. 18% GST Breakdown & Calculation
All prices displayed to students are **inclusive of 18% Goods and Services Tax (GST)**. The backend and invoice must compute and display the exact tax split.

#### Mathematical Split Formula:
Given an inclusive price $P_{\text{inclusive}}$ (in paise):
$$\text{Base Taxable Amount} = \operatorname{round}\left( \frac{P_{\text{inclusive}}}{1 + 0.18} \right) = \operatorname{round}\left( \frac{P_{\text{inclusive}}}{1.18} \right)$$
$$\text{Total GST (18\%)} = P_{\text{inclusive}} - \text{Base Taxable Amount}$$

#### CGST / SGST Split (for intra-state):
$$\text{CGST (9\%)} = \operatorname{round}\left( \frac{\text{Total GST}}{2} \right)$$
$$\text{SGST (9\%)} = \text{Total GST} - \text{CGST}$$

#### Example (₹499 Subject Pack):
- Inclusive Price: **₹499.00** (49,900 paise)
- Base Taxable Amount: $\frac{49900}{1.18} = \mathbf{42,288\text{ paise}}$ (₹422.88)
- Total 18% GST: $49900 - 42288 = \mathbf{7,612\text{ paise}}$ (₹76.12)
  - CGST (9%): **₹38.06** (3,806 paise)
  - SGST (9%): **₹38.06** (3,806 paise)

---

## 💰 3. Financial Data Integrity
- **Paise Rule**: Store all monetary values as positive 64-bit integers (`BIGINT` or `INTEGER` in paise).
- **Never use floating-point types (`FLOAT`, `DOUBLE`)** for currency in database tables or arithmetic operations to prevent rounding drift.
- **Server-Side Authority**: The frontend cart calculates an estimate for UI feedback, but the **backend recomputes all prices, discounts, and taxes from source database records** during order generation. Browser-sent prices are strictly ignored.
