# Tripraft Business & Pricing Strategy

## Executive Summary

**Company**: Tripraft  
**Industry**: Travel Tech / SaaS  
**Core Services**: Travel Planning + Expense Splitting + Group Coordination  
**Target Market**: Group travelers, families, corporate teams, digital nomads  
**Date**: December 2025

---

## Current Product Portfolio

### 1. Places Engine
- **16,885 places** across 888 cities in 82 countries
- Own curated database (no dependency on Google Places API for data)
- Smart ranking with `rank_score` algorithm
- 97% cache hit rate for fast responses

### 2. Group Planner
- Collaborative trip planning
- Democratic voting/polls for destinations
- Day-by-day itinerary builder
- Real-time member coordination
- Role-based permissions (Owner/Admin/Member)

### 3. Expense Engine
- Splitwise-style expense splitting
- Multiple split types (equal, percentage, custom, shares)
- Real-time balance calculations
- Debt simplification algorithm
- Settlement tracking with email notifications
- 5ms cached response time

### 4. AI Trip Planner (In Development)
- RAG-based travel chatbot
- Local LLM option (zero API cost)
- Personalized itinerary generation
- Context-aware recommendations

---

## Cost Analysis (Per Month)

### Infrastructure Costs

| Service | Free Tier Limit | Estimated Usage (10K MAU) | Cost/Month |
|---------|-----------------|---------------------------|------------|
| **Firebase Firestore** | 50K reads/day | 500K reads/day | $18-25 |
| **Firebase Auth** | Unlimited | 10K users | $0 (Free) |
| **Redis Cloud** | 30MB | 500MB-1GB | $5-15 |
| **Vercel/Render** | Hobby limits | Pro tier | $20-50 |
| **Email (Resend/SendGrid)** | 100/day | 5K/month | $0-20 |
| **Domain + SSL** | - | 1 domain | $15/year |

**Total Infrastructure**: ~$50-120/month at 10K MAU

### API Costs (If Using Paid APIs)

| API | Cost | Usage Estimate | Monthly Cost |
|-----|------|----------------|--------------|
| **OpenAI GPT-4 Turbo** | $0.01/1K input, $0.03/1K output | 1M tokens | $30-50 |
| **OpenAI Embeddings** | $0.0001/1K tokens | 5M tokens | $0.50 |
| **Google Places API** | $17/1K requests | 10K requests | $170 |
| **Alternative: Ollama** | Free (local) | Unlimited | $0 |

**Recommendation**: Use Ollama + local LLM for zero API cost on AI features.

### Cost Per User Breakdown

| MAU | Infrastructure | API (if used) | Cost/User |
|-----|----------------|---------------|-----------|
| 1,000 | $50 | $20 | $0.07 |
| 10,000 | $100 | $50 | $0.015 |
| 50,000 | $300 | $150 | $0.009 |
| 100,000 | $600 | $300 | $0.009 |

---

## Pricing Strategy

### Tier Structure

#### Free Tier (Ad-Supported)
**Price**: $0/month  
**Revenue**: Ads

| Feature | Limit |
|---------|-------|
| Expenses per day | 2 |
| Groups | 3 total |
| Group members | 5 per group |
| Trip plans saved | 3 |
| AI chat messages | 10/day |
| Places search | 50/day |
| Ads | Displayed |

**Target Users**: Casual travelers, students, testing users

#### Plus Tier
**Price**: $4.99/month (or $39.99/year - 33% savings)

| Feature | Limit |
|---------|-------|
| Expenses per day | 50 |
| Groups | 20 |
| Group members | 20 per group |
| Trip plans saved | 25 |
| AI chat messages | 100/day |
| Places search | Unlimited |
| Ads | None |
| Export to PDF | Yes |
| Email notifications | Yes |

**Target Users**: Regular travelers, small friend groups

#### Pro Tier
**Price**: $9.99/month (or $79.99/year - 33% savings)

| Feature | Limit |
|---------|-------|
| Expenses | Unlimited |
| Groups | Unlimited |
| Group members | 50 per group |
| Trip plans | Unlimited |
| AI chat messages | 500/day |
| Places search | Unlimited |
| Ads | None |
| Priority support | Yes |
| API access | Basic |
| Advanced analytics | Yes |
| Multi-currency | Yes |
| Receipt scanning | Yes |
| Calendar sync | Yes |

**Target Users**: Frequent travelers, travel enthusiasts, families

#### Business/Team Tier
**Price**: $19.99/month per seat (min 5 seats)

| Feature | Limit |
|---------|-------|
| Everything in Pro | Included |
| Team management | Admin dashboard |
| Expense categories | Custom |
| Approval workflows | Yes |
| Integration APIs | Full access |
| SSO/SAML | Yes |
| Dedicated support | Yes |
| Custom branding | Yes |
| Audit logs | Yes |

**Target Users**: Corporate travel teams, travel agencies, tour operators

---

## Revenue Projections

### Conservative Scenario (Year 1)

| Metric | Month 6 | Month 12 |
|--------|---------|----------|
| Total Users | 5,000 | 15,000 |
| Free Users | 4,250 (85%) | 12,000 (80%) |
| Plus Users | 500 (10%) | 2,250 (15%) |
| Pro Users | 225 (4.5%) | 675 (4.5%) |
| Business Users | 25 (0.5%) | 75 (0.5%) |

**Monthly Revenue (Month 12)**:
- Plus: 2,250 × $4.99 = $11,228
- Pro: 675 × $9.99 = $6,743
- Business: 75 × $19.99 = $1,499
- **Total MRR**: $19,470

**Annual Revenue**: ~$234K

### Moderate Scenario (Year 2)

| Metric | Month 18 | Month 24 |
|--------|----------|----------|
| Total Users | 40,000 | 80,000 |
| Free Users | 30,000 (75%) | 56,000 (70%) |
| Plus Users | 7,000 (17.5%) | 16,000 (20%) |
| Pro Users | 2,600 (6.5%) | 6,400 (8%) |
| Business Users | 400 (1%) | 1,600 (2%) |

**Monthly Revenue (Month 24)**:
- Plus: 16,000 × $4.99 = $79,840
- Pro: 6,400 × $9.99 = $63,936
- Business: 1,600 × $19.99 = $31,984
- **Total MRR**: $175,760

**Annual Revenue (Year 2)**: ~$2.1M

### Ad Revenue (Free Tier)

| Metric | CPM | Impressions/User/Month | Revenue/User |
|--------|-----|------------------------|--------------|
| Banner Ads | $1.50 | 100 | $0.15 |
| Interstitial | $4.00 | 20 | $0.08 |
| Native Ads | $2.50 | 30 | $0.075 |

**Est. Ad Revenue per Free User**: $0.30/month

**Year 1 (12K free users)**: $3,600/month = $43,200/year
**Year 2 (56K free users)**: $16,800/month = $201,600/year

---

## Competitive Analysis

### Direct Competitors

| Feature | Tripraft | Splitwise | TripIt | Wanderlog |
|---------|----------|-----------|--------|-----------|
| Expense Splitting | Yes | Yes | No | No |
| Trip Planning | Yes | No | Yes | Yes |
| Group Polls | Yes | No | No | Limited |
| AI Assistant | Yes | No | No | No |
| Places Database | Own (16K+) | No | Partner | Partner |
| Free Tier | Yes (limited) | Yes | Yes | Yes |
| Price (Paid) | $4.99-9.99 | $4.99 | $8.25 | $9.99 |

### Competitive Advantages

1. **All-in-One Platform**: Only solution combining expense splitting + trip planning + AI
2. **Own Database**: No Google Places API dependency = lower costs
3. **Group Democracy**: Unique polling/voting feature
4. **Local AI Option**: Zero API cost with Ollama
5. **Performance**: 5ms cached responses, 97% cache hit rate

---

## Growth Strategies

### Phase 1: Foundation (Months 1-6)

1. **Product-Led Growth**
   - Generous free tier to attract users
   - Viral group invitations (each user invites 3-5 friends)
   - Social sharing of trip plans

2. **Content Marketing**
   - Travel destination guides (SEO)
   - "How to split expenses fairly" articles
   - YouTube tutorials

3. **Community Building**
   - Reddit r/travel, r/backpacking engagement
   - Travel Facebook groups
   - Discord community

### Phase 2: Expansion (Months 7-12)

1. **Mobile App Launch**
   - React Native for iOS/Android
   - Offline support for travelers
   - Push notifications

2. **Partnerships**
   - Travel bloggers/influencers
   - Hostel chains
   - Travel agencies

3. **Premium Features**
   - Receipt OCR scanning
   - Multi-currency conversion
   - Flight/hotel price tracking integration

### Phase 3: Scale (Year 2+)

1. **B2B Focus**
   - Corporate travel management
   - Travel agency white-label
   - API marketplace

2. **International Expansion**
   - Localization (10 languages)
   - Regional payment methods
   - Local partnerships

3. **Platform Extensions**
   - Booking integrations (Booking.com, Airbnb APIs)
   - Insurance partnerships
   - Travel credit cards affiliate

---

## Feature Roadmap

### Q1 2025 (Current)
- [x] Expense Engine (production ready)
- [x] Group Planner (production ready)
- [x] Places Engine (16,885 places)
- [ ] AI Chatbot (architecture complete, implementation pending)

### Q2 2025
- [ ] Mobile app (React Native)
- [ ] Receipt scanning (OCR)
- [ ] Multi-currency real-time conversion
- [ ] Calendar sync (Google/Apple)

### Q3 2025
- [ ] Booking.com integration
- [ ] Flight price alerts
- [ ] Offline mode
- [ ] Advanced analytics dashboard

### Q4 2025
- [ ] B2B dashboard
- [ ] White-label solution
- [ ] API marketplace
- [ ] Travel insurance integration

### 2026
- [ ] Augmented Reality city guides
- [ ] Voice assistant integration
- [ ] Blockchain-based trip receipts
- [ ] Carbon footprint tracking

---

## Risk Assessment

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Firebase scaling costs | Medium | High | Implement aggressive caching, move to self-hosted DB at scale |
| AI API cost explosion | Medium | Medium | Local LLM (Ollama) as default, API only for premium |
| Data loss | Low | Critical | Multi-region backups, Firestore automatic backups |

### Business Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Splitwise competition | High | Medium | Focus on all-in-one value proposition |
| Low conversion rate | Medium | High | Optimize free-to-paid funnel, A/B testing |
| User churn | Medium | High | Engagement features, email campaigns |

---

## Recommended Pricing Summary

| Tier | Monthly | Annual | Target Conversion |
|------|---------|--------|-------------------|
| **Free** | $0 | $0 | 100% (entry point) |
| **Plus** | **$4.99** | $39.99 | 15-20% of active users |
| **Pro** | **$9.99** | $79.99 | 5-8% of active users |
| **Business** | **$19.99/seat** | $199.99/seat | 1-2% of active users |

### Why These Prices?

1. **$4.99 Plus**: Sweet spot below Splitwise ($4.99) with more features
2. **$9.99 Pro**: Competitive with Wanderlog, TripIt; matches market expectations
3. **$19.99 Business**: Standard B2B SaaS pricing for team tools

---

## Next Steps

### Immediate (This Week)
1. Implement usage limits in backend for free tier
2. Set up Stripe/payment integration
3. Create pricing page UI

### Short-term (This Month)
1. Add analytics tracking (Mixpanel/Amplitude)
2. Implement ad integration (Google AdMob)
3. Launch beta to 100 users for feedback

### Medium-term (Next Quarter)
1. Complete AI chatbot implementation
2. Begin mobile app development
3. Start content marketing campaign

---

## Financial Summary

| Metric | Year 1 | Year 2 | Year 3 |
|--------|--------|--------|--------|
| MAU | 15,000 | 80,000 | 250,000 |
| Paid Users | 3,000 | 24,000 | 75,000 |
| MRR (End of Year) | $19,470 | $175,760 | $500,000+ |
| ARR | $234K | $2.1M | $6M+ |
| Infrastructure Cost | $1,500/mo | $8,000/mo | $25,000/mo |
| Gross Margin | 85%+ | 90%+ | 92%+ |

**Break-even Point**: ~Month 4-6 (at $50-100/month infrastructure cost)

---

## Conclusion

Tripraft has a strong technical foundation with a differentiated product offering. The key to success is:

1. **Execute the pricing tiers** with clear value differentiation
2. **Focus on virality** through group invitations
3. **Minimize costs** with local AI and aggressive caching
4. **Build mobile presence** for the traveling user base

With proper execution, Tripraft can reach $2M+ ARR within 2 years while maintaining 85%+ gross margins.

---

*Document Version: 1.0*  
*Last Updated: December 4, 2025*
