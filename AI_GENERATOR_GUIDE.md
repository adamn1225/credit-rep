# AI Letter Generation System 🤖

## Overview

The credit disputer uses **OpenAI GPT-4o-mini** to generate personalized, professional credit dispute letters automatically. This provides better quality than templates and requires zero manual letter writing.

## How It Works

### 1. **Preview Letter (Per-Account)**
When you click "Preview Letter" on any account:

1. System fetches account details (bureau, creditor, account number, dispute reason)
2. Sends data to OpenAI GPT-4o-mini via API
3. AI analyzes the situation and generates a professional dispute letter
4. Letter appears in the preview window with options to:
   - Copy to clipboard
   - Regenerate (get a different version)
   - Use in PDF generation

**Route:** `/preview-letter/<account_id>`  
**API Endpoint:** `/api/generate-letter` (AJAX call)  
**Code:** `ai_generator.py` → `generate_dispute_letter_ai()`

### 2. **Batch Generation (Multiple Accounts)**
When generating PDFs in bulk via "Send Batch":

1. System iterates through all queued accounts
2. For each account, AI generates a unique letter
3. Letters are rendered into PDFs using ReportLab
4. PDFs are saved to `disputes/generated/<bureau>/`

**Code:** `generator.py` → `render_letter()` → `generate_dispute_letter_ai()`

### 3. **Fallback System**
If AI generation fails (API down, rate limit, error):

1. System automatically falls back to Jinja2 template
2. Template is located at: `disputes/templates/dispute_letter.j2`
3. Variables are filled in from account data
4. User sees flash message indicating fallback was used

**Template Editing:** Settings → Letter Template tab

## Architecture

```
User Action
    ↓
Flask Route (/preview-letter or /add_dispute)
    ↓
generator.py → render_letter(use_ai=True)
    ↓
ai_generator.py → generate_dispute_letter_ai()
    ↓
OpenAI API (GPT-4o-mini)
    ↓
    ├─ Success → Return AI-generated letter
    └─ Failure → Fallback to Jinja2 template
    ↓
PDF Generation (ReportLab)
    ↓
Save to disputes/generated/
```

## Key Files

### `ai_generator.py` (263 lines)
Main AI integration module:
- `generate_dispute_letter_ai()` - Initial dispute letters
- `generate_followup_letter_ai()` - Escalation letters (Phase 2)
- Error handling and fallback logic
- API key validation

### `generator.py` (100+ lines)
Letter generation coordinator:
- `render_letter()` - Chooses AI or template
- `generate_pdf()` - Creates PDF from text
- `build_letters()` - Batch generation

### `app.py`
Flask routes:
- `/api/generate-letter` - AJAX endpoint for real-time generation
- `/preview-letter/<id>` - Preview page with AI integration
- `/add_dispute` - Creates dispute and generates PDF

### `templates/preview_letter.html`
Frontend UI:
- "Generate Letter" button triggers AJAX call
- Loading spinner during AI generation
- Copy to clipboard functionality
- Regenerate button for new versions

## Configuration

### Environment Variables (.env)
```env
OPENAI_API_KEY=sk-proj-...    # Required for AI generation
LOB_API_KEY=live_...           # For physical mail sending
FLASK_SECRET_KEY=...           # Session security
```

### Cost Settings
- **Model:** GPT-4o-mini (most cost-effective)
- **Cost per letter:** ~$0.01-0.02
- **Token limits:** ~1500 tokens per letter
- **Rate limits:** Handled by OpenAI SDK (automatic retries)

## AI Prompt Structure

The AI receives:
1. **Account Information:**
   - Credit bureau name
   - Creditor name
   - Account number
   - Account type
   - Balance amount
   - Dispute reason
   - Additional notes

2. **Instructions:**
   - Be professional and legally compliant
   - Use FCRA/FDCPA language
   - Include specific account details
   - Request investigation and removal
   - Format as business letter

3. **Tone Guidelines:**
   - Formal but assertive
   - Factual and evidence-based
   - Respectful to credit bureau
   - Clear call-to-action

## Example AI Output

```
[Current Date]

[Credit Bureau Address]

Re: Dispute of Inaccurate Information on Credit Report

Dear Sir/Madam,

I am writing to formally dispute an inaccurate entry on my credit report. 
Pursuant to the Fair Credit Reporting Act (FCRA), I am requesting a thorough 
investigation of the following account:

Creditor: Capital One
Account Number: ****1234
Dispute Reason: Account does not belong to me

I have carefully reviewed my credit report and confirmed that this account 
is not mine. This inaccurate information is damaging my credit score and 
must be corrected immediately.

Under the FCRA, you are required to investigate this dispute within 30 days 
and remove any information that cannot be verified. I request that you:

1. Conduct a thorough investigation of this disputed item
2. Remove the account from my credit report if it cannot be verified
3. Provide written confirmation of the results

Please confirm receipt of this dispute and provide updates on your investigation.

Sincerely,
[User Name]
```

## Advantages Over Templates

### ✅ AI Generation
- **Personalized:** Each letter is unique to the situation
- **Context-aware:** AI understands nuances of dispute reasons
- **Professional:** Better grammar, tone, and persuasiveness
- **Adaptive:** Adjusts language based on account type and balance
- **Legal compliance:** Automatically includes FCRA/FDCPA references

### ❌ Static Templates
- Same wording for all disputes
- Generic placeholders
- Less persuasive
- Manual updates needed
- No context awareness

## Testing the AI Generator

### Test Individual Letter:
1. Go to "My Accounts"
2. Click "Preview Letter" on any account
3. Click "Generate Letter" button
4. Verify letter is personalized and professional
5. Try "Regenerate" to get alternative version

### Test Batch Generation:
1. Add multiple accounts to "Draft" status
2. Go to "Send Batch"
3. Select accounts to generate
4. Click "Generate PDFs"
5. Check `disputes/generated/<bureau>/` for PDFs

### Test Fallback:
1. Temporarily remove/invalidate OpenAI API key
2. Try generating a letter
3. Should see flash message: "Using fallback template"
4. Letter should use Jinja2 template instead

## Troubleshooting

### "OpenAI API key not found"
- Check `.env` file has `OPENAI_API_KEY=sk-proj-...`
- Restart Flask app after adding key
- Verify key is valid on OpenAI dashboard

### "Rate limit exceeded"
- Wait 60 seconds and try again
- Reduce batch size
- Upgrade OpenAI plan if needed

### "AI generation failed"
- System automatically uses fallback template
- Check Flask logs for error details
- Verify internet connection
- Check OpenAI status page

### Poor quality letters
- Review dispute reason (more detail = better AI output)
- Add notes field with additional context
- Try regenerating for different version

## Future Enhancements (Phase 2)

- [ ] Followup letter generation for 30+ day disputes
- [ ] Escalation letters for stubborn accounts
- [ ] Custom AI prompts per user
- [ ] Letter versioning (save multiple versions)
- [ ] AI-powered dispute reason suggestions
- [ ] Automatic tone adjustment (firm vs. polite)
- [ ] Multi-language support
- [ ] Letter effectiveness tracking

## API Usage Statistics

Track your OpenAI costs:
- View usage: https://platform.openai.com/usage
- Cost per 1M tokens: ~$0.15 (input) + $0.60 (output)
- Average letter: ~1500 tokens = $0.01-0.02
- 100 letters/month = ~$1-2

## Best Practices

1. **Provide detailed dispute reasons** - Better input = better AI output
2. **Use notes field** for additional context
3. **Review before sending** - AI is good but not perfect
4. **Save favorites** - Copy exceptional letters for reference
5. **Test fallback** - Ensure Jinja2 template is up-to-date
6. **Monitor costs** - Check OpenAI dashboard monthly
7. **Keep API key secure** - Never commit to git

---

**Status:** ✅ AI Generation ACTIVE  
**Model:** GPT-4o-mini  
**Cost:** ~$0.01-0.02 per letter  
**Fallback:** Jinja2 template system  

The AI letter generation system is production-ready and actively generating high-quality dispute letters!
