# Premium AI Regeneration Feature

## Overview
The Premium AI Regeneration feature is a monetization strategy that allows users to upgrade their free Ollama-generated letters to premium GPT-4 letters with custom prompts.

## How It Works

### Free Tier (Default)
- All letters initially generated with **Ollama** (llama3.2 model, local, $0 cost)
- Fast, reasonable quality
- Good enough for most users

### Premium Tier ($1.99 per letter)
- **GPT-4** powered regeneration (higher quality, more sophisticated)
- **Customizable prompts** with 4 parameters:
  1. **Tone**: Professional, Assertive, Formal, Urgent
  2. **Additional Details**: Free-text field for context (e.g., "Mention police report filed")
  3. **Special Emphasis**: What to focus on (e.g., "FCRA violations", "Mortgage denial impact")
  4. **Length**: Concise (300-400), Standard (400-500), Detailed (500-600 words)

## User Flow

```
1. User adds account → auto-generates dispute with Ollama (FREE)
2. User reviews PDF in review_batch.html
3. If unhappy → Click "Premium AI" button next to letter
4. Modal opens with customization form
5. User fills out preferences (tone, details, emphasis, length)
6. Clicks "Regenerate with GPT-4 ($1.99)"
7. Payment processed (Stripe - TODO)
8. New PDF generated with GPT-4
9. Old PDF replaced with premium version
10. Database updated with new pdf_path
```

## Technical Implementation

### Frontend (`review_batch.html`)
- Added "Premium AI" button next to each Download button
- Bootstrap modal for each dispute (unique ID: `premiumRegenModal{{ dispute.id }}`)
- Form fields:
  - `tone`: dropdown (professional/assertive/formal/urgent)
  - `additional_details`: textarea (custom context)
  - `emphasis`: textarea (focus areas)
  - `length`: dropdown (concise/standard/detailed)
- Submit to `/regenerate-with-premium-ai` route

### Backend (`app.py`)
**Route**: `/regenerate-with-premium-ai` (POST)
- Extracts form data (dispute_id, tone, additional_details, emphasis, length)
- Fetches dispute from database
- TODO: Verify Stripe payment ($1.99)
- Builds `custom_instructions` string with user preferences
- Calls `generate_dispute_letter_premium()` from ai_generator.py
- Generates new PDF with `generate_pdf()`
- Updates `disputes.pdf_path` with premium version
- Flash success message

### AI Layer (`ai_generator.py`)
**Function**: `generate_dispute_letter_premium(account_info, personal_info, custom_instructions)`
- Uses **GPT-4** (not gpt-4o-mini) for highest quality
- Temperature: 0.8 (higher creativity)
- Max tokens: 1000 (longer letters allowed)
- System prompt: "Elite credit repair specialist with 20+ years experience"
- Injects `custom_instructions` into prompt
- Returns generated letter text or None on failure

## Cost Analysis

### OpenAI API Costs (GPT-4)
- Input: ~$0.03 per 1K tokens
- Output: ~$0.06 per 1K tokens
- Average letter: ~500 input tokens (prompt) + 600 output tokens = 1100 tokens
- Cost per generation: ~$0.05-$0.08

### Pricing Strategy
- Charge: **$1.99 per regeneration**
- API cost: ~$0.08
- **Profit margin: ~96%** ($1.91 per regeneration)

### Revenue Projections
- 100 users/month
- 10% conversion rate (10 users upgrade)
- Average 2 letters per user = 20 regenerations
- Monthly revenue: **$39.80**
- Monthly profit: **$38.20** (after API costs)

## Payment Integration (TODO)

### Stripe Setup
1. Create Stripe account
2. Get API keys (test + live)
3. Add to `.env`:
   ```
   STRIPE_SECRET_KEY=sk_test_...
   STRIPE_PUBLISHABLE_KEY=pk_test_...
   ```

### Implementation
```python
import stripe
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

# In regenerate_with_premium_ai route:
try:
    charge = stripe.Charge.create(
        amount=199,  # $1.99 in cents
        currency='usd',
        source=request.form['stripeToken'],
        description=f'Premium AI Regeneration - Dispute #{dispute_id}'
    )
    # Proceed with regeneration
except stripe.error.CardError as e:
    flash('❌ Payment failed!', 'danger')
    return redirect(url_for('review_batch'))
```

### Frontend Payment Form
Add Stripe.js to `review_batch.html`:
```html
<script src="https://js.stripe.com/v3/"></script>
<script>
var stripe = Stripe('{{ stripe_publishable_key }}');
var elements = stripe.elements();
var cardElement = elements.create('card');
cardElement.mount('#card-element');

// Handle form submission
form.addEventListener('submit', async (e) => {
  e.preventDefault();
  const {token, error} = await stripe.createToken(cardElement);
  if (error) {
    // Show error
  } else {
    // Add token to form and submit
    var hiddenInput = document.createElement('input');
    hiddenInput.setAttribute('type', 'hidden');
    hiddenInput.setAttribute('name', 'stripeToken');
    hiddenInput.setAttribute('value', token.id);
    form.appendChild(hiddenInput);
    form.submit();
  }
});
</script>
```

## A/B Testing Ideas

### Pricing Tests
- **Test A**: $1.99 per letter (current)
- **Test B**: $2.99 per letter (higher margin)
- **Test C**: $0.99 per letter (volume play)
- **Test D**: Bundle pricing ($4.99 for 3 regenerations)

### Conversion Optimization
- Show quality comparison (Free vs Premium samples)
- Add testimonials: "Premium letters got results faster!"
- Limited-time offer: "First regeneration $0.99"
- Urgency: "24-hour flash sale: 50% off premium"

## Analytics Tracking

### Events to Track (PostHog)
```javascript
posthog.capture('premium_modal_opened', {
  dispute_id: dispute.id,
  creditor: dispute.creditor_name,
  bureau: dispute.bureau
});

posthog.capture('premium_regeneration_purchased', {
  dispute_id: dispute.id,
  tone: tone,
  custom_details_added: additional_details.length > 0,
  emphasis_added: emphasis.length > 0,
  length_preference: length,
  price: 1.99
});

posthog.capture('premium_regeneration_completed', {
  dispute_id: dispute.id,
  success: true
});
```

### Metrics Dashboard
- **Conversion Rate**: (Premium purchases / Review page views)
- **Revenue Per User**: (Total premium revenue / Total users)
- **Quality Satisfaction**: Survey after premium generation
- **Time to Purchase**: How long users wait before upgrading

## Future Enhancements

### Tiered Pricing
- **Basic Premium**: $1.99 - GPT-4o-mini with custom prompts
- **Pro Premium**: $4.99 - GPT-4 with legal review checklist
- **Elite Premium**: $9.99 - GPT-4 + human lawyer review

### Subscription Model
- **Monthly**: $9.99/month - Unlimited premium regenerations
- **Annual**: $99/year - Save 17%, unlimited premium

### Additional Upsells
- **Letter Templates Library**: $14.99 - 50+ pre-written templates
- **Legal Consultation**: $29.99 - 15-min call with credit specialist
- **Credit Score Tracking**: $4.99/month - Monitor all 3 bureaus

## Files Modified

1. **templates/review_batch.html**
   - Added "Premium AI" button in actions column
   - Created modal forms for each dispute
   - Pricing display: $1.99
   - Custom prompt form fields

2. **app.py**
   - New route: `/regenerate-with-premium-ai` (POST)
   - Payment verification placeholder (TODO: Stripe)
   - PDF regeneration with premium content
   - Database update for new pdf_path

3. **ai_generator.py**
   - New function: `generate_dispute_letter_premium()`
   - Uses GPT-4 (not gpt-4o-mini)
   - Custom instructions injection
   - Higher creativity (temp 0.8)

## Testing Checklist

- [ ] Modal opens when "Premium AI" clicked
- [ ] Form fields populate correctly
- [ ] Custom instructions pass to backend
- [ ] GPT-4 generates letter successfully
- [ ] PDF saved with `_premium.pdf` suffix
- [ ] Database updates with new pdf_path
- [ ] Download button shows new PDF
- [ ] Payment integration (Stripe) working
- [ ] Error handling for failed generations
- [ ] Analytics events tracked (PostHog)

## Next Steps

1. **Integrate Stripe payment** (priority)
2. **Add quality comparison** (side-by-side Free vs Premium)
3. **A/B test pricing** ($1.99 vs $2.99 vs $0.99)
4. **Add PostHog tracking** for conversion funnel
5. **Build metrics dashboard** in admin panel
6. **Add testimonials** to modal
7. **Create email campaign** for existing users
8. **Add "Upgrade" badge** next to premium-generated letters
