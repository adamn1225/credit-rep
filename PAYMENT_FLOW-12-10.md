# Payment Flow Architecture

## User Type Overview

### 1. **Logged-In Users** (Dashboard Flow)
- Full account access with saved payment methods
- Persistent data (disputes, PDFs, tracking)
- Multi-letter management
- Premium regeneration available

### 2. **Guest Users** (Public Landing Page Flow)
- No account required to generate & send letters
- Pay-per-letter basis (no saved data)
- Optional account creation AFTER checkout
- Limited to session-based data (localStorage)

---

## User Journeys

### Journey 1: Premium AI Regeneration ($1.99) - Logged-In Users
```
User clicks "Premium AI" button
  ↓
Modal opens with customization form
  ↓
User fills preferences & clicks "Continue to Payment ($1.99)"
  ↓
Check if payment method saved:
  - YES → Show confirmation modal with saved card (last 4 digits)
  - NO → Redirect to Stripe Checkout page
  ↓
Process payment ($1.99)
  ↓
Generate premium letter with GPT-4
  ↓
Update PDF & redirect to review_batch with success message
```

### Journey 2: Send Letters via Lob ($1.50-$2.00 per letter) - Logged-In Users
```
User clicks "Proceed to Checkout ($X.XX)"
  ↓
Redirect to checkout page with order summary
  ↓
Show breakdown:
  - X letters × $1.50 each = $XX.XX
  - Processing fee: $X.XX
  - Total: $XX.XX
  ↓
Check if payment method saved:
  - YES → Show "Pay with •••• 4242" button + "Use different card" link
  - NO → Show Stripe payment form (card, PayPal, CashApp, etc.)
  ↓
User confirms payment
  ↓
Process via Stripe ($XX.XX)
  ↓
Trigger Lob API to send letters
  ↓
Update dispute statuses to "sent"
  ↓
Redirect to dashboard with tracking info
```

### Journey 3: **GUEST CHECKOUT FLOW** (No Account Required) 🆕
```
User visits public landing page (www.nextcredit.com)
  ↓
Clicks "Get Started" or "Dispute Now"
  ↓
Simplified form: Bureau + Creditor + Account + Reason
  ↓
Store in localStorage (temporary, session-based)
  ↓
AI generates FREE preview letter (Ollama)
  ↓
User reviews letter → "Send This Letter" button
  ↓
CHECKOUT PAGE (no login required):
  - Collect: Email + Name + Address (for Lob mailing)
  - Show: Letter preview, $2.50 total
  - Payment: Stripe Checkout (one-time)
  ↓
Payment processed via Stripe
  ↓
Send letter via Lob API (using provided address)
  ↓
POST-PURCHASE UPSELL:
  ┌─────────────────────────────────────┐
  │ "Want to track your letter?"        │
  │ [Create Free Account]               │
  │ - Save this dispute                 │
  │ - Track delivery status             │
  │ - Send more letters later           │
  │ - Access your history               │
  └─────────────────────────────────────┘
  ↓
IF user creates account:
  - Migrate localStorage data to database
  - Create user_id
  - Link transaction to user
  - Save dispute record
  - Redirect to dashboard
  ↓
IF user skips:
  - Show confirmation page with tracking ID
  - Send email receipt with "Create Account" link
  - Data discarded after session
```

---

## 🚨 CRITICAL CONCERNS & SOLUTIONS

### Problem 1: **Abuse Prevention (Free AI Regeneration)**
**Risk:** Guest users spam Premium AI regeneration to get free GPT-4 letters without paying.

**Solutions:**
1. **Disable Premium AI for Guests**
   - Only show "Free Ollama Preview" for guests
   - Require account creation to access GPT-4 premium
   - Message: "Create account to unlock Premium AI ($1.99)"

2. **Rate Limiting** (if allowing guest premium)
   - Limit to 1 premium regeneration per IP/session
   - Use fingerprinting (IP + User-Agent hash)
   - After 1 free trial → require account

3. **Payment-First for Premium** (recommended)
   - Guest premium regeneration requires immediate payment
   - No saved card = must pay upfront
   - Store customization in Stripe metadata, regenerate after payment

**Recommended Approach:**
```
Guest Flow:
  - FREE: Ollama letter generation (unlimited previews)
  - PAID: Premium AI requires account creation first
  - CHECKOUT: Only at "Send Letter" stage
```

### Problem 2: **localStorage to Database Migration**
**Risk:** Data loss, inconsistency, duplicate records.

**Solution: Session-Based Guest Data with Migration Path**

**Backend: Store guest data in encrypted session or temp table**
```python
# When guest generates letter
if not session.get('user_id'):
    # Guest user - store in session or temp table
    session['guest_dispute'] = {
        'bureau': bureau,
        'creditor': creditor,
        'account_number': account_number,
        'reason': reason,
        'pdf_path': pdf_path,
        'created_at': datetime.now().isoformat()
    }
    session['guest_email'] = None  # Will be collected at checkout
```

**At Checkout:**
```python
@app.route('/guest-checkout', methods=['POST'])
def guest_checkout():
    email = request.form.get('email')
    name = request.form.get('name')
    address = request.form.get('address')
    
    # Get guest dispute from session
    guest_dispute = session.get('guest_dispute')
    
    # Process payment via Stripe
    charge = stripe.Charge.create(
        amount=250,  # $2.50
        currency='usd',
        source=request.form['stripeToken'],
        receipt_email=email,
        metadata={
            'type': 'guest_checkout',
            'email': email,
            'creditor': guest_dispute['creditor']
        }
    )
    
    # Send via Lob
    lob_response = send_letter_lob(guest_dispute, name, address)
    
    # Store in temporary "guest_orders" table
    guest_order_id = save_guest_order(
        email=email,
        dispute_data=guest_dispute,
        stripe_charge_id=charge.id,
        lob_tracking_id=lob_response['id']
    )
    
    # Send confirmation email with account creation link
    send_guest_confirmation_email(
        email=email,
        tracking_id=lob_response['id'],
        account_creation_link=f"/claim-order/{guest_order_id}"
    )
    
    # Show post-purchase upsell
    return render_template('guest_success.html', 
                         tracking_id=lob_response['id'],
                         guest_order_id=guest_order_id)
```

**Account Creation After Purchase:**
```python
@app.route('/claim-order/<guest_order_id>', methods=['GET', 'POST'])
def claim_order(guest_order_id):
    """Convert guest order into user account"""
    guest_order = get_guest_order(guest_order_id)
    
    if request.method == 'POST':
        password = request.form.get('password')
        
        # Create user account
        user_id = create_user_with_email(
            email=guest_order['email'],
            password=password
        )
        
        # Migrate guest order to user account
        migrate_guest_to_user(guest_order_id, user_id)
        
        # Log user in
        session['user_id'] = user_id
        
        flash('✅ Account created! Your order has been saved.', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('claim_order.html', order=guest_order)
```

### Problem 3: **Data Retention & Privacy**
**Risk:** GDPR/CCPA compliance - storing guest emails without consent.

**Solution:**
- Only store email for transactional purposes (receipt, tracking)
- Auto-delete guest orders after 90 days (configurable)
- Include opt-in checkbox: "Save my info for account creation"
- Clear privacy notice at checkout

```python
# Scheduled cleanup job (cron or Celery)
def cleanup_guest_orders():
    """Delete unclaimed guest orders older than 90 days"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        DELETE FROM guest_orders 
        WHERE created_at < NOW() - INTERVAL '90 days'
        AND user_id IS NULL  -- Not claimed
    """)
    conn.commit()
```

### Problem 4: **Duplicate Template Management**
**Risk:** Maintaining two identical flows (logged-in vs guest) = tech debt.

**Solution: Shared Component Architecture**

**Template Structure:**
```
templates/
├── base.html                    # Base layout (header, footer)
├── base_app.html               # Logged-in app (extends base, includes nav)
├── base_public.html            # Public pages (extends base, no nav)
│
├── auth/
│   ├── login.html
│   ├── signup.html
│   └── claim_order.html        # Convert guest → user
│
├── dashboard/                   # Logged-in user pages
│   ├── dashboard.html
│   ├── accounts.html
│   ├── send_batch.html
│   ├── review_batch.html
│   └── settings.html
│
├── public/                      # Guest-accessible pages
│   ├── landing.html            # Marketing landing page
│   ├── dispute_form.html       # Guest dispute entry (no login)
│   ├── preview_letter.html     # Guest letter preview
│   ├── guest_checkout.html     # Guest payment page
│   └── guest_success.html      # Post-purchase (with upsell)
│
└── shared/                      # Reusable components
    ├── _dispute_form.html      # Form fields (used by both flows)
    ├── _letter_preview.html    # PDF preview card
    ├── _payment_form.html      # Stripe Elements form
    └── _checkout_summary.html  # Order summary table
```

**Shared Component Example:**
```html
<!-- templates/shared/_dispute_form.html -->
<div class="dispute-form">
    <div class="mb-3">
        <label class="form-label">Credit Bureau</label>
        <select class="form-select" name="bureau" required>
            <option value="Experian">Experian</option>
            <option value="TransUnion">TransUnion</option>
            <option value="Equifax">Equifax</option>
        </select>
    </div>
    <!-- ... more fields ... -->
</div>

<!-- Used in both: -->
<!-- dashboard/accounts.html (logged-in) -->
{% include 'shared/_dispute_form.html' %}

<!-- public/dispute_form.html (guest) -->
{% include 'shared/_dispute_form.html' %}
```

---

## Database Schema Updates

### `guest_orders` Table (NEW)
```sql
CREATE TABLE guest_orders (
    id SERIAL PRIMARY KEY,
    email TEXT NOT NULL,
    full_name TEXT,
    address_line1 TEXT,
    city TEXT,
    state TEXT,
    zip_code TEXT,
    
    -- Dispute data (JSON)
    dispute_data JSONB NOT NULL,
    
    -- Transaction info
    stripe_charge_id TEXT UNIQUE,
    lob_tracking_id TEXT,
    amount_cents INTEGER,
    
    -- Migration tracking
    user_id INTEGER REFERENCES users(id), -- NULL until claimed
    claimed_at TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP DEFAULT (CURRENT_TIMESTAMP + INTERVAL '90 days')
);

CREATE INDEX idx_guest_orders_email ON guest_orders(email);
CREATE INDEX idx_guest_orders_expires ON guest_orders(expires_at);
```

---

## Route Structure: Guest vs Logged-In

## Database Schema Additions Needed

### `payment_methods` Table
```sql
CREATE TABLE payment_methods (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    stripe_payment_method_id TEXT NOT NULL,
    card_brand TEXT, -- 'visa', 'mastercard', 'amex', etc.
    card_last4 TEXT,
    is_default BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### `transactions` Table
```sql
CREATE TABLE transactions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    stripe_charge_id TEXT UNIQUE,
    amount_cents INTEGER NOT NULL, -- Store in cents (199 = $1.99)
    transaction_type TEXT, -- 'premium_regen', 'lob_send'
    status TEXT, -- 'pending', 'succeeded', 'failed', 'refunded'
    dispute_ids INTEGER[], -- Array of dispute IDs affected
    metadata JSONB, -- Store details (letter count, customization, etc.)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Environment Variables (.env)

```bash
# Stripe API Keys
STRIPE_SECRET_KEY=sk_test_...  # Test key
STRIPE_PUBLISHABLE_KEY=pk_test_...  # Test key
STRIPE_WEBHOOK_SECRET=whsec_...  # For webhook verification

# Production (when ready)
# STRIPE_SECRET_KEY=sk_live_...
# STRIPE_PUBLISHABLE_KEY=pk_live_...
```

## Route Structure

### **GUEST ROUTES** (No Authentication Required) 🆕

```python
# Public landing page
GET /
- Marketing page with "Get Started" CTA
- SEO optimized, conversion-focused
- Renders: templates/public/landing.html

# Guest dispute entry
GET /dispute
POST /dispute
- Simple form: Bureau, Creditor, Account, Reason
- Store in session (not database)
- Generate FREE Ollama preview
- Renders: templates/public/dispute_form.html

# Guest letter preview
GET /preview
- Show generated letter (from session data)
- Download PDF button
- "Send This Letter" → checkout
- Renders: templates/public/preview_letter.html

# Guest checkout
GET /checkout
POST /checkout
- Collect email, name, address
- Show $2.50 total
- Stripe payment form
- Process payment → Send via Lob
- Renders: templates/public/guest_checkout.html

# Guest success page (post-purchase)
GET /success/<order_id>
- Show tracking ID
- Upsell: "Create account to track delivery"
- Email receipt sent
- Renders: templates/public/guest_success.html

# Claim guest order (convert to account)
GET /claim/<order_id>
POST /claim/<order_id>
- Show order details
- Password creation form
- Migrate data to user account
- Auto-login after creation
- Renders: templates/auth/claim_order.html
```

### Premium Regeneration Flow (Logged-In Users Only)

**Step 1: Form Submission** (existing)
```python
POST /regenerate-with-premium-ai
- Gets dispute_id, tone, details, etc.
- Check if user has payment method saved
- If YES → Charge saved card & regenerate
- If NO → Redirect to /premium-payment/{dispute_id}
```

**Step 2: Payment Page** (NEW)
```python
GET /premium-payment/<dispute_id>
- Show Stripe Elements form
- Display: "Premium AI Regeneration - $1.99"
- Show customization summary (tone, details)
- Submit to /process-premium-payment
```

**Step 3: Process Payment** (NEW)
```python
POST /process-premium-payment
- Create Stripe charge ($1.99)
- Save payment method if "Save card" checked
- Call generate_dispute_letter_premium()
- Update PDF
- Redirect to /review-batch with success
```

### Lob Send Flow

**Step 1: Checkout Page** (NEW)
```python
GET /checkout
- Show order summary table
- Letter count, cost breakdown
- Payment form (if no saved method)
- Or "Pay with saved card" button
```

**Step 2: Process Payment** (NEW)
```python
POST /process-lob-payment
- Calculate total: letters × $1.50
- Create Stripe charge
- If successful → Call Lob API
- Update disputes to "sent"
- Record transaction
- Redirect to dashboard
```

## Stripe Integration Code Snippets

### Initialize Stripe
```python
import stripe
import os

stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
```

### Create Payment Intent (Recommended Modern Method)
```python
@app.route('/create-payment-intent', methods=['POST'])
@login_required
def create_payment_intent():
    try:
        amount = request.json.get('amount')  # in cents (199 = $1.99)
        
        intent = stripe.PaymentIntent.create(
            amount=amount,
            currency='usd',
            metadata={
                'user_id': session['user_id'],
                'type': 'premium_regen',
                'dispute_id': request.json.get('dispute_id')
            }
        )
        
        return jsonify({
            'clientSecret': intent.client_secret
        })
    except Exception as e:
        return jsonify(error=str(e)), 403
```

### Save Payment Method
```python
def save_payment_method(user_id, payment_method_id):
    """Save payment method to user account"""
    # Get payment method details from Stripe
    pm = stripe.PaymentMethod.retrieve(payment_method_id)
    
    # Save to database
    from db import get_db_connection
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO payment_methods 
        (user_id, stripe_payment_method_id, card_brand, card_last4, is_default)
        VALUES (%s, %s, %s, %s, true)
        ON CONFLICT (user_id) WHERE is_default = true
        DO UPDATE SET 
            stripe_payment_method_id = EXCLUDED.stripe_payment_method_id,
            card_brand = EXCLUDED.card_brand,
            card_last4 = EXCLUDED.card_last4,
            updated_at = CURRENT_TIMESTAMP
    """, (user_id, payment_method_id, pm.card.brand, pm.card.last4))
    
    conn.commit()
    cursor.close()
    conn.close()
```

### Charge Saved Payment Method
```python
def charge_saved_card(user_id, amount_cents, description):
    """Charge user's saved payment method"""
    # Get saved payment method
    from db import get_db_connection
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT stripe_payment_method_id 
        FROM payment_methods 
        WHERE user_id = %s AND is_default = true
    """, (user_id,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not result:
        return None, "No payment method saved"
    
    payment_method_id = result['stripe_payment_method_id']
    
    try:
        # Create payment intent with saved method
        intent = stripe.PaymentIntent.create(
            amount=amount_cents,
            currency='usd',
            payment_method=payment_method_id,
            confirm=True,
            description=description,
            metadata={'user_id': user_id}
        )
        
        return intent, None
    except stripe.error.CardError as e:
        return None, e.user_message
```

## Frontend: Stripe Elements Integration

### Add to `base.html`
```html
<!-- Stripe.js -->
<script src="https://js.stripe.com/v3/"></script>
```

### Payment Form Template
```html
<!-- templates/payment.html -->
<form id="payment-form">
    <div id="card-element" class="form-control"></div>
    <div id="card-errors" class="text-danger mt-2"></div>
    
    <div class="form-check mt-3">
        <input type="checkbox" class="form-check-input" id="saveCard" name="save_card">
        <label class="form-check-label" for="saveCard">
            Save card for future purchases
        </label>
    </div>
    
    <button type="submit" class="btn btn-primary mt-3">
        Pay $<span id="amount"></span>
    </button>
</form>

<script>
var stripe = Stripe('{{ stripe_publishable_key }}');
var elements = stripe.elements();
var cardElement = elements.create('card', {
    style: {
        base: {
            fontSize: '16px',
            color: '#32325d',
        }
    }
});
cardElement.mount('#card-element');

// Handle form submission
var form = document.getElementById('payment-form');
form.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    // Create payment method
    const {paymentMethod, error} = await stripe.createPaymentMethod({
        type: 'card',
        card: cardElement,
    });
    
    if (error) {
        document.getElementById('card-errors').textContent = error.message;
    } else {
        // Send to backend
        const response = await fetch('/process-payment', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                payment_method_id: paymentMethod.id,
                save_card: document.getElementById('saveCard').checked,
                dispute_id: '{{ dispute_id }}',
                amount: {{ amount }}
            })
        });
        
        const result = await response.json();
        if (result.success) {
            window.location.href = result.redirect_url;
        } else {
            document.getElementById('card-errors').textContent = result.error;
        }
    }
});
</script>
```

## Payment Method Display (Saved Cards)

```html
<!-- Show saved card option -->
{% if user_has_saved_card %}
<div class="card mb-3">
    <div class="card-body">
        <h6>Payment Method</h6>
        <div class="d-flex align-items-center justify-content-between">
            <div>
                <i class="bi bi-credit-card fs-4 me-2"></i>
                <strong>{{ card_brand|title }}</strong> •••• {{ card_last4 }}
            </div>
            <button type="button" class="btn btn-sm btn-outline-primary" 
                    onclick="togglePaymentForm()">
                Use Different Card
            </button>
        </div>
    </div>
</div>

<!-- Hidden payment form (shown when "Use Different Card" clicked) -->
<div id="new-card-form" style="display: none;">
    <!-- Stripe Elements form here -->
</div>

<script>
function togglePaymentForm() {
    document.getElementById('new-card-form').style.display = 'block';
}
</script>
{% else %}
<!-- Show Stripe Elements form immediately -->
<div id="new-card-form">
    <!-- Stripe Elements form here -->
</div>
{% endif %}
```

## Testing with Stripe Test Cards

```
Successful payment:
4242 4242 4242 4242

Decline:
4000 0000 0000 0002

Require 3D Secure:
4000 0025 0000 3155

Insufficient funds:
4000 0000 0000 9995
```

## Error Handling

```python
try:
    charge = stripe.PaymentIntent.create(...)
except stripe.error.CardError as e:
    # Card declined
    flash(f'❌ Payment declined: {e.user_message}', 'danger')
except stripe.error.RateLimitError as e:
    flash('❌ Too many requests. Please try again.', 'danger')
except stripe.error.InvalidRequestError as e:
    flash('❌ Invalid payment request.', 'danger')
except stripe.error.AuthenticationError as e:
    flash('❌ Payment system error.', 'danger')
except stripe.error.StripeError as e:
    flash(f'❌ Payment error: {str(e)}', 'danger')
except Exception as e:
    flash(f'❌ Unexpected error: {str(e)}', 'danger')
```

## Implementation Phases

### Phase 1: Stripe Integration (Weekend)
1. **Sign up for Stripe** → https://dashboard.stripe.com/register
2. **Get API keys** → Developers → API keys
3. **Add to `.env`** → STRIPE_SECRET_KEY, STRIPE_PUBLISHABLE_KEY
4. **Create migrations** → payment_methods & transactions tables
5. **Build checkout page** → `/checkout` route & template (logged-in users)
6. **Integrate Stripe Elements** → Add to base.html, create payment form
7. **Test with test cards** → Use 4242... card for testing
8. **Add webhook handler** → Listen for payment events

### Phase 2: Guest Checkout Flow (Next Sprint)
1. **Create guest_orders table** → Migration script
2. **Build public landing page** → Marketing copy + CTAs
3. **Build guest dispute form** → Simplified, no login
4. **Implement session-based storage** → localStorage + Flask session
5. **Create guest checkout page** → Email + address collection
6. **Build post-purchase upsell** → "Create Account" CTA
7. **Implement order claiming** → /claim/<order_id> route
8. **Add guest order cleanup job** → Auto-delete after 90 days

### Phase 3: Template Refactoring
1. **Create base_public.html** → Public pages layout
2. **Create base_app.html** → Logged-in app layout
3. **Extract shared components** → _dispute_form.html, _payment_form.html
4. **Duplicate key flows** → Guest vs logged-in versions
5. **Test both user types** → Ensure feature parity
6. **Add conversion tracking** → Guest → User conversion rate

### Phase 4: Abuse Prevention & Security
1. **Implement rate limiting** → IP-based limits for guests
2. **Add fingerprinting** → Prevent multi-account abuse
3. **Disable guest premium AI** → Require account for GPT-4
4. **Add CAPTCHA** → reCAPTCHA on guest forms
5. **Monitor fraud** → Stripe Radar + custom alerts
6. **GDPR compliance** → Cookie consent, data retention policy

## Alternative Payment Methods (Future)

Stripe supports:
- **PayPal** (via Stripe)
- **CashApp** (via Stripe)
- **Apple Pay**
- **Google Pay**
- **ACH Direct Debit** (bank transfer)
- **Afterpay/Klarna** (buy now, pay later)

All can be added with minimal code changes using Stripe Payment Element.

---

## 📊 Conversion Funnel Metrics to Track

### Guest Flow
```
Landing Page Visits
  ↓ (Click "Get Started")
Dispute Form Started
  ↓ (Form completion rate)
Letter Preview Viewed
  ↓ (Click "Send Letter")
Checkout Page Reached
  ↓ (Payment completion rate)
Order Completed
  ↓ (Account creation rate)
Guest → User Conversion
```

**Key Metrics:**
- **Guest checkout conversion**: (Orders / Previews) × 100
- **Account creation rate**: (Claimed Orders / Total Guest Orders) × 100
- **Guest LTV**: Average revenue per guest user
- **Time to conversion**: Guest order → Account creation

### Logged-In Flow
```
Dashboard Visit
  ↓
Add Account
  ↓
Generate Letter
  ↓
Review Batch
  ↓ (Premium AI conversion)
Premium Regeneration (optional)
  ↓
Checkout
  ↓
Order Completed
```

**Key Metrics:**
- **Premium AI conversion**: (Premium regens / Total letters) × 100
- **Multi-letter users**: Users sending 2+ letters
- **Repeat purchase rate**: Users with multiple transactions
- **Logged-in LTV**: Average revenue per account holder

---

## 🔐 Security Considerations

### Guest User Risks
1. **Spam/Abuse**: Rate limit to 3 letters per IP per day
2. **Fake Emails**: Verify email before sending receipt (send verification code)
3. **Payment Fraud**: Use Stripe Radar, block high-risk countries
4. **Data Scraping**: CAPTCHA on guest forms
5. **Session Hijacking**: Use HTTPS, secure session cookies

### Mitigation Strategies
```python
# Rate limiting (Flask-Limiter)
from flask_limiter import Limiter

limiter = Limiter(app, key_func=lambda: request.remote_addr)

@app.route('/dispute', methods=['POST'])
@limiter.limit("3 per day")  # Max 3 guest disputes per IP per day
def guest_dispute():
    # ...
```

```python
# Email verification before checkout
@app.route('/checkout', methods=['POST'])
def guest_checkout():
    email = request.form.get('email')
    
    # Send verification code
    code = generate_verification_code()
    send_verification_email(email, code)
    
    # Store code in session
    session['verification_code'] = code
    session['pending_email'] = email
    
    return render_template('verify_email.html')

@app.route('/verify-code', methods=['POST'])
def verify_code():
    user_code = request.form.get('code')
    if user_code == session.get('verification_code'):
        # Proceed to payment
        return redirect(url_for('process_payment'))
    else:
        flash('Invalid code', 'danger')
        return redirect(url_for('guest_checkout'))
```

---

## 💡 UX Best Practices

### Guest Flow UX
- **Progress indicator**: Show steps (1. Info → 2. Preview → 3. Payment)
- **Exit intent popup**: Offer discount if user tries to leave checkout
- **Trust signals**: "256-bit SSL encryption", "100% money-back guarantee"
- **Social proof**: "Join 10,000+ users who've fixed their credit"
- **Live chat**: Offer support during checkout (Intercom/Drift)

### Post-Purchase Upsell
```html
<!-- templates/public/guest_success.html -->
<div class="container text-center py-5">
    <i class="bi bi-check-circle-fill text-success" style="font-size: 4rem;"></i>
    <h2 class="mt-3">Your Letter is on the Way! 📬</h2>
    <p class="lead">Tracking ID: <code>{{ tracking_id }}</code></p>
    
    <!-- Upsell Card -->
    <div class="card shadow-lg mt-5 mx-auto" style="max-width: 500px;">
        <div class="card-body">
            <h4>Want to Track Your Letter?</h4>
            <p>Create a free account to:</p>
            <ul class="text-start">
                <li>✅ Track delivery status in real-time</li>
                <li>✅ Store all your disputes in one place</li>
                <li>✅ Send more letters later</li>
                <li>✅ Get notified when bureaus respond</li>
            </ul>
            <a href="{{ url_for('claim_order', order_id=order_id) }}" 
               class="btn btn-primary btn-lg w-100">
                Create Free Account
            </a>
            <p class="text-muted mt-3 mb-0">
                <small>We've sent tracking info to {{ email }}</small>
            </p>
        </div>
    </div>
</div>
```

---

## 🎯 Recommended Implementation Order

1. ✅ **Phase 1**: Stripe integration for logged-in users (this weekend)
2. 🔄 **Phase 2**: Guest checkout flow (week 1-2)
3. 🔄 **Phase 3**: Template refactoring & shared components (week 2-3)
4. 🔄 **Phase 4**: Abuse prevention & rate limiting (week 3-4)
5. 📊 **Phase 5**: Analytics & conversion tracking (ongoing)

**Quick Win:** Start with logged-in Stripe checkout first, then add guest flow. This validates payment infrastructure before adding complexity.
