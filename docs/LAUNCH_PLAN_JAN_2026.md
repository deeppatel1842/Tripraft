# Tripraft Launch Plan - January 1, 2026

## Executive Summary

**Launch Date**: January 1, 2026  
**Timeline**: 27 days (December 4-31, 2025)  
**Launch Tiers**: Free + Plus ($4.99/month)  
**Target**: Soft launch with 100-500 initial users

---

## What You Need to Launch

### Technical Requirements (Must Have)

| Component | Status | Time Needed | Priority |
|-----------|--------|-------------|----------|
| Usage Limits (Free tier) | Not Built | 3-4 days | CRITICAL |
| Stripe Payment Integration | Not Built | 2-3 days | CRITICAL |
| Pricing Page UI | Not Built | 1-2 days | CRITICAL |
| Terms of Service | Not Built | 1 day | CRITICAL |
| Privacy Policy | Not Built | 1 day | CRITICAL |
| Production Deployment | Partial | 2-3 days | CRITICAL |
| SSL Certificate | Need to verify | 1 day | CRITICAL |
| Custom Domain | Need to verify | 1 day | CRITICAL |

**Total Technical Time**: ~12-15 days

### Business Requirements (Must Have)

| Requirement | Time | Cost | Notes |
|-------------|------|------|-------|
| Business Registration | 1-7 days | $50-500 | Depends on state |
| EIN Number | 1-4 weeks | FREE | Can operate without initially |
| Stripe Account | 1-2 days | FREE | Just need bank account |
| Business Bank Account | 1-3 days | FREE-$15/mo | Optional for launch |
| Terms of Service | 1 day | FREE-$500 | Can use templates |
| Privacy Policy | 1 day | FREE-$500 | Can use templates |

---

## Detailed Timeline (27 Days)

### Week 1: December 4-10 (Legal & Setup)

#### Day 1-2: Business Decision
**Choose Your Business Structure:**

| Structure | Pros | Cons | Best For |
|-----------|------|------|----------|
| **Sole Proprietorship** | Simplest, no paperwork | Personal liability | Testing market |
| **LLC** | Liability protection, tax flexibility | $50-500 setup | Recommended |
| **C-Corp** | Best for investors, stock options | Complex, double taxation | Raising VC |

**Recommendation**: Start as **Sole Proprietorship** to launch fast, convert to LLC within 3-6 months.

#### Day 1-3: Register Business (If Going LLC Route)

**Option A: Fast Launch (Sole Proprietorship)**
- No registration needed
- Use your name or file DBA ("Doing Business As")
- DBA cost: $10-50 depending on state
- Time: 1-2 days

**Option B: LLC Registration**
- Best states for online business: **Delaware** or **Wyoming**
- Delaware: $90 state fee + $50-100 registered agent
- Wyoming: $100 state fee + $50 registered agent
- Use: **ZenBusiness** ($0 + state fees) or **LegalZoom** ($79-249)
- Time: 1-7 days (expedited available)

#### Day 3-4: Get EIN Number

**What is EIN?**
- Employer Identification Number (like SSN for business)
- Required for: Business bank account, hiring, Stripe business account

**How to Get:**
1. Go to [IRS EIN Application](https://www.irs.gov/businesses/small-businesses-self-employed/apply-for-an-employer-identification-number-ein-online)
2. Fill online form (15 minutes)
3. Get EIN **instantly** if applying online during business hours
4. **Cost: FREE**

**Can You Launch Without EIN?**
- YES, Stripe accepts individuals with SSN
- Get EIN later for professional setup

#### Day 4-5: Stripe Account Setup

**Requirements:**
- Email address
- Bank account (personal OK for start)
- SSN or EIN
- Business address (can be home)
- Business website URL

**Steps:**
1. Go to [stripe.com](https://stripe.com)
2. Click "Start now"
3. Fill business details
4. Add bank account for payouts
5. Verify identity (instant or 1-2 days)

**Stripe Fees:**
- 2.9% + $0.30 per transaction
- No monthly fee
- Example: $4.99 subscription = $0.44 fee, you keep $4.55

#### Day 5-7: Legal Documents

**Terms of Service (Must Have)**

Use free template from:
- [TermsFeed](https://www.termsfeed.com/blog/sample-terms-of-service-template/) - Free generator
- [Termly](https://termly.io/products/terms-and-conditions-generator/) - Free basic

**Key Sections Needed:**
```
1. Service Description
2. User Accounts & Registration
3. Subscription & Payments
4. Cancellation & Refunds
5. User Conduct
6. Intellectual Property
7. Limitation of Liability
8. Termination
9. Governing Law
10. Contact Information
```

**Privacy Policy (Must Have - Required by Law)**

Use free generator:
- [PrivacyPolicies.com](https://www.privacypolicies.com/privacy-policy-generator/)
- [FreePrivacyPolicy.com](https://www.freeprivacypolicy.com/free-privacy-policy-generator/)

**Key Sections:**
```
1. Information We Collect
2. How We Use Information
3. Data Sharing
4. Cookies
5. Data Security
6. User Rights (GDPR if serving EU)
7. Children's Privacy
8. Contact Information
```

---

### Week 2: December 11-17 (Technical Build)

#### Day 8-11: Usage Limits Implementation

**Backend Changes Needed:**

```python
# 1. Create user_subscriptions collection in Firestore
# Document structure:
{
    "user_id": "uid_xxx",
    "tier": "free",  # or "plus"
    "created_at": timestamp,
    "expires_at": null,  # null for free, date for paid
    "stripe_customer_id": null,
    "stripe_subscription_id": null
}

# 2. Create user_usage collection
{
    "user_id": "uid_xxx",
    "expenses_today": 0,
    "expenses_reset_at": timestamp,
    "groups_count": 0
}
```

**Files to Modify:**

1. `expense_engine/middleware/usage_limiter.py` (NEW)
2. `expense_engine/routes/expense_routes.py` (add decorator)
3. `Group_planner/routes.py` (add decorator)
4. `expense_engine/repositories/subscription_repository.py` (NEW)

**Limits to Implement:**

| Feature | Free | Plus |
|---------|------|------|
| Expenses/day | 2 | 50 |
| Total Groups | 3 | 20 |
| Members/Group | 5 | 20 |
| Trip Plans | 3 | 25 |

#### Day 12-14: Stripe Integration

**Backend Payment Routes:**

```python
# New file: web/backend/payments/routes.py

@payments_bp.route('/create-checkout', methods=['POST'])
def create_checkout():
    # Create Stripe checkout session
    pass

@payments_bp.route('/webhook', methods=['POST'])
def stripe_webhook():
    # Handle subscription events
    pass

@payments_bp.route('/customer-portal', methods=['POST'])
def customer_portal():
    # Let users manage subscription
    pass

@payments_bp.route('/subscription-status', methods=['GET'])
def get_subscription():
    # Return current user's subscription
    pass
```

**Stripe Products to Create:**
1. Login to Stripe Dashboard
2. Products → Add Product
3. Create "Tripraft Plus Monthly" - $4.99/month recurring
4. Create "Tripraft Plus Yearly" - $39.99/year recurring (optional)
5. Copy Price IDs for your code

#### Day 14-15: Frontend Pricing Page

**New Components:**
```
web/frontend/src/
├── pages/
│   └── PricingPage.jsx (NEW)
├── components/
│   ├── pricing/
│   │   ├── PricingCard.jsx (NEW)
│   │   ├── FeatureList.jsx (NEW)
│   │   └── UpgradeModal.jsx (NEW)
```

---

### Week 3: December 18-24 (Polish & Deploy)

#### Day 16-18: Production Deployment

**Recommended Stack:**

| Service | Purpose | Cost | Why |
|---------|---------|------|-----|
| **Vercel** | Frontend hosting | FREE | Easy, fast, auto-deploy |
| **Render** | Backend hosting | $7/mo | Simple Python hosting |
| **Firebase** | Database + Auth | FREE tier | Already using |
| **Redis Cloud** | Caching | FREE 30MB | Already using |
| **Cloudflare** | Domain + SSL | FREE | CDN, security |

**Domain Setup:**
1. Buy domain: Namecheap, Google Domains, Cloudflare (~$10-15/year)
2. Suggested: tripraft.com, tripraft.io, gettripraft.com
3. Point to Cloudflare (free CDN + SSL)
4. Configure DNS to Vercel/Render

#### Day 19-21: Testing & Bug Fixes

**Critical Test Cases:**
- [ ] User can sign up
- [ ] User can create expense (free limit works)
- [ ] User hits limit, sees upgrade prompt
- [ ] User can checkout with Stripe
- [ ] Subscription activates after payment
- [ ] User can cancel subscription
- [ ] Refund flow works

#### Day 22-24: Final Polish

- [ ] Mobile responsive check
- [ ] Error messages are user-friendly
- [ ] Loading states work
- [ ] Email notifications work
- [ ] Analytics tracking (Google Analytics or Mixpanel)

---

### Week 4: December 25-31 (Launch Prep)

#### Day 25-27: Soft Launch Prep

**Pre-Launch Checklist:**
- [ ] All features working
- [ ] Stripe in live mode (not test mode)
- [ ] Legal pages published
- [ ] Contact email set up (support@tripraft.com)
- [ ] Social media accounts created
- [ ] App Store / Play Store listing prepared (if mobile)

#### Day 28-30: Soft Launch

**Soft Launch Strategy:**
1. Share with friends & family (20-50 users)
2. Post on personal social media
3. Monitor for bugs
4. Collect feedback

#### Day 31: January 1, 2026 - LAUNCH

**Launch Day Actions:**
1. Switch to production Stripe keys
2. Post on Product Hunt (schedule in advance)
3. Post on Hacker News
4. Share on Reddit r/travel, r/SideProject
5. Email your network

---

## Plus Tier Business Model Explained

### Revenue Math

**Price:** $4.99/month

**Your Revenue After Fees:**
- Stripe fee: 2.9% + $0.30 = $0.44
- Your net: **$4.55 per subscriber per month**

**Break-Even Analysis:**

| Monthly Costs | Amount |
|---------------|--------|
| Render (Backend) | $7 |
| Domain | $1.25 |
| Email (Resend) | $0 (free tier) |
| Firebase | $0 (free tier) |
| **Total** | ~$10/month |

**Break-even: 3 paying subscribers**

### Revenue Projections

| Scenario | Total Users | Plus Subscribers (10%) | Monthly Revenue |
|----------|-------------|------------------------|-----------------|
| Month 1 | 100 | 10 | $45 |
| Month 3 | 500 | 50 | $227 |
| Month 6 | 2,000 | 200 | $910 |
| Month 12 | 10,000 | 1,000 | $4,550 |

### Why Users Will Pay

**Free Tier Pain Points:**
- Only 2 expenses/day (frustrating during trips)
- Only 3 groups (can't plan multiple trips)
- Small group size (5 members)
- See ads

**Plus Tier Value:**
- 50 expenses/day (plenty for any trip)
- 20 groups (all your trips)
- 20 members/group (larger friend groups)
- No ads
- Email notifications
- Export to PDF

**Conversion Triggers:**
1. User creates 3rd group → "Upgrade to create more groups"
2. User adds 3rd expense today → "Upgrade for unlimited expenses"
3. User invites 6th member → "Upgrade for larger groups"

---

## Business Registration Options

### Option 1: Launch as Individual (Fastest - Recommended for Jan 1)

**What You Need:**
- Personal SSN for Stripe
- Personal bank account
- No business registration

**Pros:**
- Launch immediately
- No paperwork
- No fees

**Cons:**
- Personal liability
- Less professional
- Tax as personal income

**Best for:** Validating market before investing in legal setup

### Option 2: LLC Formation (Recommended within 3 months)

**Best Services:**

| Service | Cost | Time | Includes |
|---------|------|------|----------|
| **ZenBusiness** | $0 + state fee | 2-3 weeks | Basic filing |
| **Northwest Registered Agent** | $39 + state fee | 1-2 weeks | Registered agent 1 year |
| **LegalZoom** | $79-249 + state fee | 2-4 weeks | Support, templates |
| **Incfile** | $0 + state fee | 2-4 weeks | Basic filing |

**Recommended: Delaware or Wyoming LLC**

**Delaware LLC:**
- State fee: $90
- Annual franchise tax: $300
- Best for: Future investors

**Wyoming LLC:**
- State fee: $100
- Annual fee: $50
- No state income tax
- Best for: Bootstrapped businesses

### Option 3: Get Everything Ready Now

**Timeline if starting today:**

| Task | Service | Time | Cost |
|------|---------|------|------|
| LLC Formation | ZenBusiness | 3-7 days | $100-150 |
| EIN | IRS Online | Instant | FREE |
| Business Bank | Mercury/Relay | 1-2 days | FREE |
| Stripe Business | Stripe | 1-2 days | FREE |

**Total: 5-10 days, ~$100-200**

---

## Recommended Service Providers

### Banking

| Service | Monthly Fee | Best For | Link |
|---------|-------------|----------|------|
| **Mercury** | FREE | Startups, online business | mercury.com |
| **Relay** | FREE | Small business | relayfi.com |
| **Novo** | FREE | Freelancers | novo.co |
| **Chase Business** | $15 (waivable) | Traditional banking | chase.com |

**Recommendation:** Mercury or Relay (both free, startup-friendly)

### Payment Processing

| Service | Fee | Best For |
|---------|-----|----------|
| **Stripe** | 2.9% + $0.30 | Subscriptions (BEST) |
| **PayPal** | 2.9% + $0.30 | Brand recognition |
| **Paddle** | 5% + $0.50 | Handle taxes for you |

**Recommendation:** Stripe (best for subscriptions, developer-friendly)

### Hosting

| Service | Cost | Best For |
|---------|------|----------|
| **Vercel** | FREE-$20/mo | Frontend (React) |
| **Render** | $7/mo | Backend (Python/Flask) |
| **Railway** | $5/mo | Backend alternative |
| **Fly.io** | $0-10/mo | Backend alternative |
| **Firebase Hosting** | FREE | Static sites |

**Recommendation:** Vercel (frontend) + Render (backend)

### Domain & SSL

| Service | Domain Cost | SSL | CDN |
|---------|-------------|-----|-----|
| **Cloudflare** | $8-10/year | FREE | FREE |
| **Namecheap** | $8-12/year | Paid | No |
| **Google Domains** | $12/year | FREE | No |

**Recommendation:** Buy on Namecheap, use Cloudflare for DNS/SSL/CDN (all free)

### Email

| Service | Free Tier | Paid |
|---------|-----------|------|
| **Resend** | 3,000/month | $20/mo for 50K |
| **SendGrid** | 100/day | $15/mo |
| **Mailgun** | 5,000/month | $35/mo |

**Recommendation:** Resend (modern, great API, generous free tier)

---

## Launch Checklist

### Before Launch (Must Have)
- [ ] Working product with usage limits
- [ ] Stripe integration (can accept payments)
- [ ] Terms of Service page
- [ ] Privacy Policy page
- [ ] Contact email (support@yourdomain.com)
- [ ] SSL certificate (HTTPS)
- [ ] Error tracking (Sentry free tier)

### Nice to Have
- [ ] Business LLC registered
- [ ] Business bank account
- [ ] EIN number
- [ ] Custom email domain
- [ ] Analytics (Google Analytics / Mixpanel)
- [ ] Social media accounts

### After Launch (Week 1-2)
- [ ] Monitor for bugs
- [ ] Respond to user feedback
- [ ] Fix critical issues
- [ ] Start LLC formation if not done

---

## Cost Summary for Launch

### Minimum Launch Cost (Individual)

| Item | Cost |
|------|------|
| Domain (1 year) | $12 |
| Render Backend (1 month) | $7 |
| **Total** | **$19** |

Everything else can be free tier.

### Professional Launch Cost (LLC)

| Item | Cost |
|------|------|
| Domain (1 year) | $12 |
| Render Backend (1 month) | $7 |
| LLC Formation (Wyoming) | $150 |
| **Total** | **$169** |

### Monthly Operating Cost (Post-Launch)

| Item | Cost |
|------|------|
| Render Backend | $7 |
| Domain (amortized) | $1 |
| Firebase | $0 (free tier) |
| Stripe | % of revenue |
| **Total** | **~$10/month** |

---

## Action Plan Summary

### This Week (Dec 4-10)
1. ✅ Decide: Launch as individual or register LLC
2. ✅ If LLC: Start ZenBusiness/Northwest process today
3. ✅ Apply for EIN (takes 15 minutes, instant)
4. ✅ Create Stripe account
5. ✅ Buy domain name
6. ✅ Generate Terms of Service and Privacy Policy

### Next Week (Dec 11-17)
1. Build usage limits middleware
2. Integrate Stripe payments
3. Create pricing page UI
4. Set up production environment

### Week 3 (Dec 18-24)
1. Deploy to production
2. Test all payment flows
3. Bug fixes
4. Set up monitoring

### Week 4 (Dec 25-31)
1. Soft launch to friends/family
2. Final fixes
3. Prepare launch announcements
4. **LAUNCH January 1, 2026**

---

## Quick Decision Guide

**Q: Should I register an LLC before launch?**
A: No, launch as individual first. Register LLC in January after validating demand.

**Q: Do I need EIN?**
A: Not required for launch. Get it in January.

**Q: Do I need business bank account?**
A: No, use personal account with Stripe initially.

**Q: What's the absolute minimum to launch?**
A: Domain ($12) + Stripe account (free) + Terms/Privacy pages (free) = **$12**

**Q: How long will technical work take?**
A: 12-15 days of focused work for usage limits + Stripe + deployment.

---

## Contact & Resources

### Free Legal Resources
- [Stripe Atlas](https://stripe.com/atlas) - $500 but handles everything
- [Clerky](https://www.clerky.com/) - Startup legal docs
- [LawDepot](https://www.lawdepot.com/) - Free contract templates

### Startup Communities
- [Indie Hackers](https://www.indiehackers.com/)
- [r/SideProject](https://www.reddit.com/r/SideProject/)
- [r/startups](https://www.reddit.com/r/startups/)

### Launch Platforms
- [Product Hunt](https://www.producthunt.com/)
- [Hacker News](https://news.ycombinator.com/)
- [BetaList](https://betalist.com/)

---

*You can do this! 27 days is tight but achievable for Free + Plus launch.*

**Priority Order:**
1. Stripe account (today)
2. Usage limits code (this week)
3. Everything else follows

---

*Document Version: 1.0*  
*Created: December 4, 2025*
