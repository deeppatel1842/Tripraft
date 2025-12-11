# Tripraft Pricing Tiers - Detailed Explanation

## Overview

Tripraft uses a **freemium + tiered pricing model** designed to:
1. Acquire users cheaply (free tier)
2. Convert to paid (Plus tier)
3. Capture power users (Pro tier)
4. Monetize businesses (Business tier)

---

## 1. Free Tier (Ad-Supported)

### Purpose
User acquisition funnel - get users hooked, then convert to paid

### How It Works
```
User signs up → Uses free features → Hits limits → Sees upgrade prompt → Converts to Plus
```

### Limits Explained

| Limit | Why This Number | User Experience |
|-------|-----------------|-----------------|
| **2 expenses/day** | Enough to try, frustrating on actual trips | On a 5-day trip, they can only log 10 expenses total |
| **3 groups** | Can test with 1-2 friend groups | Can't plan multiple trips simultaneously |
| **5 members/group** | Small friend circle only | Larger groups forced to upgrade |
| **10 AI messages/day** | Taste the feature | Heavy users hit wall quickly |
| **50 places searches/day** | Enough for planning | Blocks power users from searching extensively |

### Ad Revenue Math

**Banner Ads**:
```
CPM (Cost Per Mille) = $1.50 means advertiser pays $1.50 per 1,000 views
If user sees 100 banner ads/month:
100 ÷ 1000 × $1.50 = $0.15 per user
```

**Interstitial Ads (full screen)**:
```
CPM = $4.00 (higher because more intrusive)
20 views/month: 
20 ÷ 1000 × $4.00 = $0.08 per user
```

**Native Ads (blends with content)**:
```
CPM = $2.50
30 views/month:
30 ÷ 1000 × $2.50 = $0.075 per user
```

### Total Ad Revenue Per User

```
$0.15 + $0.08 + $0.075 = ~$0.30/user/month

Year 1: 12,000 free users × $0.30 = $3,600/month = $43,200/year
Year 2: 56,000 free users × $0.30 = $16,800/month = $201,600/year
```

### Reality Check
**Ad revenue is LOW**. The free tier exists to convert users to paid, not to make money directly.

### Where Ads Appear
1. **Banner at bottom of expense list** - Seen every time user checks expenses
2. **Interstitial after creating 2nd expense** - Full screen ad between actions
3. **Native ad in places search results** - Blends with place recommendations

---

## 2. Plus Tier ($4.99/month)

### Purpose
Main revenue driver - convert casual users to paying customers

### Target User Profile
- Plans 2-4 trips per year
- Travels with friend groups of 6-15 people
- Wants hassle-free expense splitting
- Values no ads
- Willing to pay for convenience

### Value Proposition

**Free vs Plus**:
```
Free:  2 expenses/day = 14 expenses/week trip = FRUSTRATING on actual trips
Plus:  50 expenses/day = Unlimited for any trip = PEACE OF MIND
```

**Real World Example**:
```
Trip with 10 people, 7 days, multiple activities:
- Restaurant: 1 expense
- Hotel split: 1 expense  
- Activities: 2 expenses
- Transport: 1 expense
- Groceries: 1 expense
= 6 expenses/day needed

Free tier: Only 2/day = CAN'T track everything
Plus tier: 50/day = Plenty of room
```

### Pricing Psychology

| Factor | Strategy | Result |
|--------|----------|--------|
| **Price point** | $4.99 (not $5) | Under psychological barrier |
| **Comparison** | Same as Splitwise Pro | Familiar anchor |
| **Cost** | Less than coffee | Impulse buy mentality |
| **Savings** | $39.99/year = 33% discount | Encourages annual commitment |

### Revenue Per User

**Monthly Subscription**:
```
Revenue per subscriber: $4.99
- Stripe processing fee (2.9% + $0.30): -$0.44
- Net revenue to you: $4.55
```

**Yearly Subscription ($39.99/year)**:
```
Revenue per subscriber: $39.99
- Stripe processing fee (2.9% + $0.30): -$1.46
- Net revenue to you: $38.53
- Monthly equivalent: $38.53 ÷ 12 = $3.21/month
```

**Blended Average** (assuming 70% monthly, 30% yearly):
```
$4.55 × 0.70 + $3.21 × 0.30 = $3.19 + $0.96 = ~$4.15/user/month average
```

### Conversion Triggers

When free users hit limits, show upgrade prompts:

1. **Creating 4th group**:
   ```
   "You've created 3 groups. Upgrade to Plus for 20 groups →"
   ```

2. **Adding 6th member to group**:
   ```
   "You've added 5 members. Plus tier allows 20 members per group →"
   ```

3. **2nd expense today**:
   ```
   "You've reached your 2 expenses today limit. 
   Plus users can add 50/day →"
   ```

4. **Viewing ad after action**:
   ```
   "Ad is loading... Upgrade to Plus for ad-free experience →"
   ```

### Features Included

| Feature | Limit | Why |
|---------|-------|-----|
| Expenses per day | 50 | Enough for complex trips |
| Total groups | 20 | Multiple trip planning |
| Members per group | 20 | Larger friend groups |
| Trip plans saved | 25 | Archive past trips |
| AI messages/day | 100 | Regular usage of chatbot |
| Places search/day | Unlimited | Explore all options |
| Export to PDF | Yes | Share trip summary |
| Email notifications | Yes | Get updates |
| Ads | None | Clean experience |

---

## 3. Pro Tier ($9.99/month)

### Purpose
Capture high-value power users willing to pay more

### Target User Profile
- Frequent travelers (10+ trips/year)
- Travel bloggers/influencers
- Families coordinating multiple trips
- Digital nomads
- Power users frustrated by Plus limits

### Why 2x Price?

Even though Pro and Plus use **same infrastructure**, higher price works because:

1. **Price Anchoring**: Makes Plus look like a deal
2. **Captures Willingness to Pay**: Power users are less price-sensitive
3. **Funds Features**: Higher revenue supports development
4. **Psychological Segmentation**: Rich feature set commands premium

### Additional Features Explained

#### 1. Unlimited Everything
```
Plus:  Expenses/day = 50
Pro:   Expenses/day = Unlimited

Cost to provide: $0 (just remove a database check)
Value to user: Infinite - never worry about limits
```

#### 2. Multi-Currency Support
```
How it works:
- User adds expense in EUR (Euro)
- System auto-converts to USD (group's base currency)
- Shows both amounts

Cost to implement:
- API: exchangerate-api.com (free, 1500 requests/month)
- Your cost: $0
- User value: $10+ (saves manual conversion)
```

**Example**:
```
Trip to Paris:
- User adds €50 restaurant expense
- System shows: €50 = $54.50 USD
- Balance automatically calculated in USD
```

#### 3. Receipt Scanning (OCR)
```
How it works:
- User takes photo of receipt
- AI extracts: Amount, date, merchant, items
- Auto-fills new expense form

Cost to provide:
- Option A: Tesseract (free, lower accuracy ~70%)
- Option B: Google Vision API ($1.50 per 1K images)
- Your cost per user: ~$0.01-0.02

User value: Saves time entering expenses, accuracy
```

#### 4. Calendar Sync
```
How it works:
- Pro user exports trip to Google/Apple Calendar
- Event appears on user's phone/desktop calendar
- Shows trip dates, location, activity schedule

Cost to provide:
- Google Calendar API: Free
- Your cost: $0

User value: Integration with daily life
```

#### 5. Priority Support
```
What it means:
- Email response within 24 hours (vs 48-72 hours)
- Direct support queue (not waiting behind hundreds)
- Escalation for complex issues

Cost to you:
- Your time managing support queue
- ~1-2 hours/week initially
```

#### 6. API Access (Basic)
```
What it means:
- Pro users can build integrations
- Example: Auto-import expenses from another app
- Documented API with rate limits

Cost to provide:
- No direct cost
- Supports future B2B deals
```

#### 7. Advanced Analytics
```
What it includes:
- Who spends most in group?
- Monthly spending trends
- Category breakdown (food, transport, activities)
- Per-person settlement history

Cost to provide:
- Simple queries on existing data: $0
- Reporting UI development: ~3 days work (one-time)
```

### Revenue Per User

**Monthly Subscription**:
```
Revenue per subscriber: $9.99
- Stripe fee (2.9% + $0.30): -$0.59
- OCR cost (if 20 receipts/month @ $0.0015 each): -$0.03
- Net revenue to you: $9.37
```

**Yearly Subscription ($79.99/year)**:
```
Revenue per subscriber: $79.99
- Stripe fee: -$2.62
- OCR annual cost: -$0.36
- Net revenue to you: $77.01
- Monthly equivalent: $6.42/month
```

### Upgrade Path from Plus

**Reasons user upgrades from Plus to Pro**:

1. **Traveling frequently** - Unlimited features matter
2. **Using multi-currency** - International trips
3. **Receipt scanning** - Don't want to manually type
4. **Larger groups** - 20+ person trips
5. **AI dependency** - Exceeding 100 messages/day limit
6. **Analytics** - Wants spending breakdown

---

## 4. Business Tier ($19.99/seat/month)

### Purpose
B2B revenue - higher margins, longer retention, predictable contracts

### Target Customer Profile
- Corporate travel departments (5-50 employees)
- Travel agencies managing client groups
- Tour operators coordinating trips
- Event planning companies
- Corporate retreat organizers

### Per-Seat Pricing Model

**How It Works**:
```
Team of 10 employees:
- 10 seats × $19.99/month = $199.90/month
- Annual: $199.90 × 12 = $2,399/year

Why "per-seat"?
- Usage-based (more employees = more cost)
- Prevents individuals from gaming system
- Scales with company size
```

### Minimum 5 Seats Rule

**Why minimum 5?**
```
Prevents abuse:
- Individual: "I'll create 5 accounts to each get Business benefits"
- Solution: Minimum 5 people enforces it's truly a team

Also: Minimum commitment ensures viable deal
- 5 × $19.99 = $99.95/month = $1,200/year
- Profitable even with 1 customer
```

### Business Features Explained

#### 1. Admin Dashboard
```
Allows manager to:
- See all team members and their usage
- Manage who has access
- View spending across all employees
- Generate company-wide reports

Cost: ~1 week development (one-time)
Value: $5,000+ (vs building custom tool)
```

#### 2. SSO/SAML Authentication
```
What it means:
- Employees login with company email (john@company.com)
- No separate password to remember
- Admin controls access centrally
- When employee leaves, just deactivate in directory

Example flow:
Employee clicks "Login with Google Workspace"
→ Google verifies john@company.com
→ Auto-logged into Tripraft
→ Never sees Tripraft login screen

Cost: Use Auth0 (free tier handles most companies)
Value: Major security requirement for IT departments
```

#### 3. Approval Workflows
```
How it works:
Manager → Reviews → Approves → Settlement

Example:
1. Employee adds $150 hotel expense
2. Manager sees notification
3. Manager reviews in dashboard
4. Manager approves or requests change
5. Expense locked for settlement

Why businesses need it:
- Finance controls spending
- Prevents fraud
- Audit trail for accounting
```

#### 4. Audit Logs
```
System records:
- Who accessed what data
- When expense was created/modified
- Who approved it
- Full history of changes

Why it matters:
- Finance team compliance requirement
- IRS/tax audits need documentation
- Fraud prevention
- Employee accountability
```

#### 5. Custom Branding
```
Travel agency can:
- Change logo in dashboard
- Use agency colors
- Add agency name
- White-label for clients

Benefit: Agencies can resell to clients with their branding
```

#### 6. Full API Access
```
Travel agency integrates with:
- Their accounting software (QuickBooks, Xero)
- Their CRM (Salesforce)
- Automated reporting to clients

Example:
Client's expenses auto-sync to accountant's system
```

### Why B2B is Valuable

**LTV Comparison**:
```
Plus user (individual):
- Pays: $4.99/month
- Churn rate: ~10%/month (switches to free or competitor)
- Expected lifetime: 10 months
- LTV: $4.99 × 10 = $49.90

Business user (company of 10):
- Pays: $199.90/month
- Churn rate: ~2%/month (high switching costs)
- Expected lifetime: 50 months (4+ years)
- LTV: $199.90 × 50 = $9,995

B2B is 200x MORE VALUABLE!
```

**Other B2B Advantages**:
1. **Predictable revenue**: Annual contracts
2. **Lower churn**: Switching costs are high
3. **Account expansion**: Buy more seats over time
4. **Reference customers**: Use for case studies

### B2B Sales Cycle

```
Month 1: Employee uses free/Plus personally
         ↓
Month 2: Suggests to manager for team travel
         ↓
Month 3: Manager requests demo
         ↓
Month 4: IT evaluates security (SSO, audit logs)
         ↓
Month 5: Finance approves budget
         ↓
Month 6: Contract signed, 12-month deal
         ↓
Month 7-18: Active use, potential upsell to more seats

Total sales cycle: 6 months typical (longer than typical SaaS)
But once signed: highly predictable, low churn
```

---

## Revenue Projections Explained

### Conservative Year 1 (Month 12)

#### User Acquisition Funnel

```
Marketing/Viral Growth → Sign-ups → Active Users → Paid Conversions

Assumptions:
- 50 sign-ups per day average
- 80% become active users
- Sign-ups accumulate: 50 × 365 = 18,250
- Active: 18,250 × 80% = 14,600 ≈ 15,000 total

Actual path varies:
- Month 1: 500 sign-ups (you + friends + early adopters)
- Month 2: 1,000 new sign-ups (15% MoM growth)
- Month 6: 10,000 cumulative users
- Month 12: 15,000 cumulative users
```

#### Distribution Rationale

| Tier | Count | % | Why |
|------|-------|---|-----|
| Free | 12,000 | 80% | Most people try before buying |
| Plus | 2,250 | 15% | Main conversion target |
| Pro | 675 | 4.5% | ~30% of paid (converts from Plus) |
| Business | 75 | 0.5% | B2B is slow, needs dedicated sales |

**Conversion rates**:
```
100 sign-ups
↓ (80% active)
80 active users
↓ (25% convert to paid)
20 paying customers
↓ (75% Plus, 20% Pro, 5% Business)
- 15 Plus users
- 4 Pro users
- 1 Business user (5 seats)
```

#### Month 12 Revenue Breakdown

```
Plus:   2,250 users × $4.99 = $11,228/month
Pro:      675 users × $9.99 =  $6,743/month
Business:  75 users × $19.99 = $1,499/month
                              -----------
Gross MRR:                     $19,470/month

Stripe fees (estimate ~5%):     -$974/month
Ad revenue (12K free users):   +$3,600/month

NET MRR: $19,470 + $3,600 - $974 = $22,096/month

Annual Run Rate: $22,096 × 12 = $265,152/year
```

### Year 2 Growth (Month 24)

#### Why 80K Users is Achievable

```
Growth drivers:

1. Viral loops: Each group invites 5+ friends
   - User creates expense group
   - Invites 5 friends to settle up
   - Each friend sees value, recommends to others

2. SEO: Travel content ranks in Google
   - Blog about "How to split expenses with friends"
   - People search this, find Tripraft
   - Organic monthly traffic grows

3. Word of mouth: Happy users tell friends
   - "This app made our trip so easy"
   - Friend signs up, growth loop repeats

4. Product Hunt / Hacker News
   - Launch when ready
   - 1,000+ upvotes possible
   - 5,000+ sign-ups in one day

5. App store presence (if mobile)
   - iPhone App Store
   - Google Play
   - Discovery tabs (Travel, Productivity)

Math:
15,000 (Month 12) → 80,000 (Month 24) = 5.3x growth
That's 15% month-over-month growth (aggressive but achievable)

Month 12: +1,000 new users/month
Month 18: +3,000 new users/month
Month 24: +5,000 new users/month
```

#### Improved Conversion Rates

| Tier | Year 1 | Year 2 | Why Improvement |
|------|--------|--------|-----------------|
| Plus | 15% | 20% | Better onboarding, clearer value |
| Pro | 4.5% | 8% | Receipt scanning, analytics live |
| Business | 0.5% | 2% | Sales team active, case studies |

**Why rates improve**:
- Smoother onboarding (learned from Year 1)
- More features complete
- Case studies prove value
- User reviews build trust

#### Month 24 Revenue

```
Free:      56,000 users × $0.30/month ad rev =  $16,800
Plus:      16,000 users × $4.99/month       =   $79,840
Pro:        6,400 users × $9.99/month       =   $63,936
Business:   1,600 users × $19.99/month*     =   $31,984
            (* = 320 companies × 5 seats)
                                            -----------
Total MRR:                                    $192,560

Minus Stripe fees (5%):                        -$9,628
Net MRR:                                      $182,932

Annual Run Rate: $182,932 × 12 = $2,195,184/year
```

---

## Revenue Stack Summary

### Your Total Revenue Sources

| Stream | Year 1 | Year 2 | Priority |
|--------|--------|--------|----------|
| **Plus subscriptions** | $135K | $960K | 🔴 #1 |
| **Pro subscriptions** | $81K | $768K | 🟡 #2 |
| **Business subscriptions** | $18K | $384K | 🟡 #2 |
| **Ad revenue** | $43K | $202K | 🟢 #3 |
| **TOTAL** | **$277K** | **$2.3M** | |

### Key Insight

**Focus on Plus conversions first.**
- 80% of your revenue comes from Plus
- Lower friction to implement
- Faster ROI
- Pro and Business follow naturally

---

## Cost Analysis for Comparison

### Infrastructure Cost

| Item | Monthly | Note |
|------|---------|------|
| Firebase Firestore | $0-25 | Free tier covers most |
| Firebase Auth | $0 | Unlimited |
| Redis | $5-15 | Caching layer |
| Backend hosting | $7-50 | Render or Railway |
| Frontend hosting | $0-20 | Vercel or Netlify |
| Domain + SSL | $1.25 | Cloudflare |
| **Total** | **$13-111/month** | Grows with scale |

### Cost Per User

```
Year 1:
- 15,000 users
- Infrastructure cost: $50/month
- Cost per user: $50 ÷ 15,000 = $0.003 per user per month

Year 2:
- 80,000 users
- Infrastructure cost: $200/month (more load)
- Cost per user: $200 ÷ 80,000 = $0.0025 per user per month

Revenue per user (blended):
- Year 1: $277,000 ÷ 15,000 = $18.47 per user per year
- Year 2: $2,300,000 ÷ 80,000 = $28.75 per user per year

Margins:
- Year 1: ($277K - $600) ÷ $277K = 99.8% gross margin
- Year 2: ($2.3M - $2.4K) ÷ $2.3M = 99.9% gross margin

You keep >99% of revenue!
```

---

## Pricing Comparison with Competitors

### How You Compare

| Feature | Tripraft Plus | Splitwise Pro | Wanderlog |
|---------|---------------|---------------|-----------|
| Price | $4.99/mo | $4.99/mo | $9.99/mo |
| Expense splitting | ✅ | ✅ | ❌ |
| Trip planning | ✅ | ❌ | ✅ |
| AI assistant | ✅ | ❌ | ❌ |
| Groups/projects | 20 | 4 | Unlimited |
| Group voting | ✅ | ❌ | Limited |
| Itineraries | ✅ | ❌ | ✅ |
| Value | **Best** | Good | Good |

**Your Advantage**: Only solution combining ALL three (expenses + planning + AI)

---

## Next Steps

### Immediate (This Week)
1. Set up Stripe account
2. Decide: Solo or LLC (see launch plan)

### Week 2-3
1. Implement usage limits middleware
2. Build Stripe checkout integration
3. Create pricing page UI

### Before Launch (Week 4)
1. Test all payment flows
2. Verify Stripe webhooks work
3. Deploy to production

---

*Document Version: 1.0*  
*Created: December 4, 2025*  
*For: Tripraft Startup Launch Planning*
