# Tripraft Feature Enhancement & Improvement Plan

## Current State Analysis

### What You Have (Production Ready)

| Engine | Status | Performance | Coverage |
|--------|--------|-------------|----------|
| **Expense Engine** | Production | 5ms cached, 92% hit rate | Full CRUD + settlements |
| **Group Planner** | Production | Real-time sync | Polls, itineraries, members |
| **Places Engine** | Production | 97% cache hit | 16,885 places, 82 countries |
| **AI Chatbot** | Architecture Only | - | Zero implementation |

---

## Recommended Improvements

### Priority 1: Critical (Revenue Impact)

#### 1.1 Usage Limits Middleware
**Why**: Required for freemium model

```python
# Add to expense_engine/middleware/usage_limiter.py

from functools import wraps
from flask import g, jsonify
from datetime import datetime, timedelta

TIER_LIMITS = {
    'free': {
        'expenses_per_day': 2,
        'groups_total': 3,
        'members_per_group': 5,
        'ai_messages_per_day': 10
    },
    'plus': {
        'expenses_per_day': 50,
        'groups_total': 20,
        'members_per_group': 20,
        'ai_messages_per_day': 100
    },
    'pro': {
        'expenses_per_day': -1,  # Unlimited
        'groups_total': -1,
        'members_per_group': 50,
        'ai_messages_per_day': 500
    }
}

def check_usage_limit(limit_type):
    """Decorator to check usage limits before action."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user_tier = get_user_tier(g.user_id)
            limits = TIER_LIMITS.get(user_tier, TIER_LIMITS['free'])
            
            current_usage = get_current_usage(g.user_id, limit_type)
            limit = limits.get(limit_type, 0)
            
            if limit != -1 and current_usage >= limit:
                return jsonify({
                    'success': False,
                    'error': f'Daily {limit_type} limit reached',
                    'upgrade_url': '/pricing',
                    'current': current_usage,
                    'limit': limit
                }), 429
            
            return f(*args, **kwargs)
        return decorated
    return decorator
```

**Firestore Collections Needed**:
```
user_subscriptions/
  {uid}/
    tier: "free" | "plus" | "pro" | "business"
    expires_at: timestamp
    stripe_customer_id: string
    
user_usage/
  {uid}/
    expenses_today: number
    expenses_reset_at: timestamp
    ai_messages_today: number
    ai_reset_at: timestamp
```

---

#### 1.2 Payment Integration (Stripe)
**Why**: Required for paid tiers

```python
# Add to web/backend/payments/stripe_service.py

import stripe
from flask import Blueprint, request, jsonify

payments_bp = Blueprint('payments', __name__, url_prefix='/api/payments')

PRICE_IDS = {
    'plus_monthly': 'price_xxx',
    'plus_yearly': 'price_yyy',
    'pro_monthly': 'price_zzz',
    'pro_yearly': 'price_aaa'
}

@payments_bp.route('/create-checkout', methods=['POST'])
def create_checkout():
    """Create Stripe checkout session."""
    data = request.json
    plan = data.get('plan')
    
    session = stripe.checkout.Session.create(
        customer_email=g.user_email,
        payment_method_types=['card'],
        line_items=[{
            'price': PRICE_IDS[plan],
            'quantity': 1
        }],
        mode='subscription',
        success_url='https://tripraft.com/success?session_id={CHECKOUT_SESSION_ID}',
        cancel_url='https://tripraft.com/pricing',
        metadata={'user_id': g.user_id}
    )
    
    return jsonify({'checkout_url': session.url})

@payments_bp.route('/webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhooks."""
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    
    event = stripe.Webhook.construct_event(payload, sig_header, WEBHOOK_SECRET)
    
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        user_id = session['metadata']['user_id']
        upgrade_user_tier(user_id, session['subscription'])
    
    return jsonify({'status': 'success'})
```

---

#### 1.3 Ad Integration (Free Tier)
**Why**: Revenue from free users

**Frontend Implementation** (React):
```jsx
// Add to web/frontend/src/components/common/AdBanner.jsx

import React, { useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';

const AdBanner = ({ slot, format = 'auto' }) => {
  const { user, tier } = useAuth();
  
  // Don't show ads to paid users
  if (tier !== 'free') return null;
  
  useEffect(() => {
    try {
      (window.adsbygoogle = window.adsbygoogle || []).push({});
    } catch (e) {
      console.error('Ad failed to load');
    }
  }, []);
  
  return (
    <div className="ad-container">
      <ins
        className="adsbygoogle"
        style={{ display: 'block' }}
        data-ad-client="ca-pub-XXXXXXXX"
        data-ad-slot={slot}
        data-ad-format={format}
        data-full-width-responsive="true"
      />
    </div>
  );
};

export default AdBanner;
```

**Ad Placement Strategy**:
- Banner at bottom of expense list
- Interstitial after creating 2nd expense
- Native ad in places search results

---

### Priority 2: High Value Features

#### 2.1 AI Chatbot Implementation
**Status**: Architecture complete, needs coding

**Quick Implementation Path**:

```python
# Add to web/backend/places_engine/chatbot/

# chatbot_service.py
from langchain.llms import Ollama
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import Chroma

class TravelChatbot:
    def __init__(self):
        # Free local LLM
        self.llm = Ollama(model="llama3.2:3b")
        
        # Free local embeddings
        self.embeddings = HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2"
        )
        
        # Vector store with places data
        self.vectorstore = Chroma(
            collection_name="places",
            embedding_function=self.embeddings
        )
    
    def chat(self, user_message: str, session_id: str) -> dict:
        # 1. Check if query matches our places DB
        db_results = self._search_places_db(user_message)
        
        if db_results['confidence'] > 0.7:
            # Use our data
            return self._generate_response_from_db(db_results)
        else:
            # Fallback to LLM
            return self._generate_llm_response(user_message)
    
    def _search_places_db(self, query: str) -> dict:
        """Search places in Firestore."""
        # Normalize and search
        results = self.db.collection('places').where(
            'search_text', 'array_contains', query.lower()
        ).limit(10).get()
        
        return {
            'confidence': 0.9 if results else 0.3,
            'places': [doc.to_dict() for doc in results]
        }
```

**Estimated Implementation Time**: 2-3 weeks

---

#### 2.2 Receipt Scanning (OCR)
**Why**: High-value Pro feature

```python
# Use Tesseract OCR (free) or Google Vision API

import pytesseract
from PIL import Image
import re

class ReceiptScanner:
    def scan(self, image_path: str) -> dict:
        """Extract expense data from receipt image."""
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image)
        
        return {
            'amount': self._extract_amount(text),
            'date': self._extract_date(text),
            'merchant': self._extract_merchant(text),
            'items': self._extract_items(text)
        }
    
    def _extract_amount(self, text: str) -> float:
        # Find total amount patterns
        patterns = [
            r'total[:\s]*\$?([\d,]+\.?\d*)',
            r'amount[:\s]*\$?([\d,]+\.?\d*)',
            r'\$\s*([\d,]+\.?\d*)'
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return float(match.group(1).replace(',', ''))
        return 0.0
```

---

#### 2.3 Multi-Currency Support
**Why**: Essential for international travelers

```python
# Add to expense_engine/utils/currency.py

from decimal import Decimal
import requests

class CurrencyConverter:
    # Free API: exchangerate-api.com (1500 requests/month free)
    API_URL = "https://api.exchangerate-api.com/v4/latest/{base}"
    
    def __init__(self):
        self.cache = {}
        self.cache_ttl = 3600  # 1 hour
    
    def convert(
        self, 
        amount: Decimal, 
        from_currency: str, 
        to_currency: str
    ) -> Decimal:
        rate = self._get_rate(from_currency, to_currency)
        return amount * Decimal(str(rate))
    
    def _get_rate(self, from_curr: str, to_curr: str) -> float:
        # Check cache first
        cache_key = f"{from_curr}_{to_curr}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # Fetch from API
        response = requests.get(self.API_URL.format(base=from_curr))
        rates = response.json()['rates']
        rate = rates.get(to_curr, 1.0)
        
        self.cache[cache_key] = rate
        return rate
```

**Database Update**:
```python
# Add to expense model
class Expense:
    currency: str = "USD"  # ISO currency code
    original_amount: Decimal  # Amount in original currency
    converted_amount: Decimal  # Amount in group's base currency
```

---

### Priority 3: Growth Features

#### 3.1 Mobile App (React Native)
**Architecture**:
```
tripraft-mobile/
├── src/
│   ├── screens/
│   │   ├── HomeScreen.tsx
│   │   ├── ExpensesScreen.tsx
│   │   ├── GroupsScreen.tsx
│   │   ├── TripPlannerScreen.tsx
│   │   └── AIAssistantScreen.tsx
│   ├── components/
│   ├── services/
│   │   └── api.ts  # Reuse existing backend APIs
│   ├── hooks/
│   └── navigation/
├── package.json
└── app.json
```

**Key Mobile Features**:
- Offline expense tracking
- Push notifications for settlements
- Camera for receipt scanning
- Location-based place suggestions

---

#### 3.2 Export & Reports
**Why**: Business tier differentiator

```python
# Add to expense_engine/services/export_service.py

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import csv
import io

class ExportService:
    def export_group_expenses_pdf(self, group_id: str) -> bytes:
        """Generate PDF report of group expenses."""
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        
        # Header
        c.setFont("Helvetica-Bold", 20)
        c.drawString(50, 750, f"Expense Report - {group_name}")
        
        # Summary
        c.setFont("Helvetica", 12)
        c.drawString(50, 700, f"Total Expenses: ${total}")
        c.drawString(50, 680, f"Members: {member_count}")
        
        # Expense table
        # ... (table rendering)
        
        c.save()
        return buffer.getvalue()
    
    def export_group_expenses_csv(self, group_id: str) -> str:
        """Export expenses as CSV."""
        output = io.StringIO()
        writer = csv.writer(output)
        
        writer.writerow(['Date', 'Description', 'Amount', 'Paid By', 'Split Type'])
        for expense in expenses:
            writer.writerow([
                expense.expense_date,
                expense.description,
                expense.amount,
                expense.paid_by_name,
                expense.split_type
            ])
        
        return output.getvalue()
```

---

#### 3.3 Booking Integration
**Partner APIs** (for Phase 3):

| Partner | API | Commission |
|---------|-----|------------|
| Booking.com | Affiliate API | 25-40% |
| Airbnb | Not available | - |
| Skyscanner | Affiliate API | $0.10-0.50/click |
| GetYourGuide | Affiliate API | 8% |

```python
# Add to places_engine/integrations/booking.py

class BookingIntegration:
    """Booking.com affiliate integration."""
    
    AFFILIATE_ID = "xxx"
    
    def get_hotels_for_city(self, city: str, checkin: str, checkout: str):
        """Get hotel options with affiliate links."""
        # API call to Booking.com
        # Returns hotels with your affiliate links
        pass
    
    def generate_affiliate_link(self, hotel_id: str) -> str:
        """Generate affiliate tracking link."""
        return f"https://www.booking.com/hotel/{hotel_id}.html?aid={self.AFFILIATE_ID}"
```

---

## New Service Recommendations

### 1. Travel Insurance Integration
**Partner**: SafetyWing, World Nomads (affiliate)
**Revenue**: 10-15% commission
**Implementation**: Simple link/banner integration

### 2. eSIM Service
**Partner**: Airalo, Holafly (affiliate)
**Revenue**: $2-5 per sale
**Implementation**: In-app purchase integration

### 3. Airport Lounge Access
**Partner**: Priority Pass (affiliate)
**Revenue**: $10-20 per signup
**Implementation**: Promotional content in trip plans

### 4. Carbon Offset
**Partner**: Gold Standard, Verra
**Revenue**: 5-10% margin on offsets
**Implementation**: Calculate trip carbon footprint, offer offset purchases

---

## Technical Debt & Improvements

### Performance Optimization

| Area | Current | Target | Action |
|------|---------|--------|--------|
| API Response Time | 50-100ms | <30ms | Add more Redis caching |
| Firestore Reads | 500K/day | 200K/day | Batch operations, denormalization |
| Bundle Size | ~2MB | <500KB | Code splitting, tree shaking |

### Security Enhancements

1. **Rate Limiting Enhancement**
   - Current: Basic rate limiting
   - Needed: Per-endpoint, per-tier limits

2. **Data Encryption**
   - Add field-level encryption for sensitive expense data

3. **Audit Logging**
   - Already have expense_history
   - Add full user action audit trail

### Code Quality

1. **Test Coverage**
   - Current: ~40%
   - Target: 80%
   - Add integration tests for critical flows

2. **API Documentation**
   - Add OpenAPI/Swagger specs
   - Auto-generate from code

---

## Implementation Timeline

### Month 1: Revenue Foundation
- [ ] Week 1-2: Usage limits middleware
- [ ] Week 2-3: Stripe integration
- [ ] Week 3-4: Ad integration

### Month 2: Core Features
- [ ] Week 1-2: AI chatbot basic implementation
- [ ] Week 3: Multi-currency support
- [ ] Week 4: Receipt scanning (basic)

### Month 3: Mobile & Growth
- [ ] Week 1-2: React Native project setup
- [ ] Week 3-4: Core mobile screens

### Month 4-6: Scale & B2B
- [ ] Export & reporting
- [ ] B2B dashboard
- [ ] Booking integrations

---

## Resource Requirements

### Team (Minimum Viable)
- 1 Full-stack Developer (you)
- 1 Part-time Designer (contract)
- 1 Part-time Marketing (contract)

### Tools & Services (Monthly)
- GitHub Pro: $4/month
- Figma: $12/month
- Postman: Free
- Stripe: 2.9% + $0.30 per transaction
- Analytics (Mixpanel): Free tier

### Total Monthly Overhead: ~$50-100

---

## Success Metrics

### Product Metrics
- DAU/MAU ratio: Target >20%
- Expense creation rate: >3/user/week
- Group invitation acceptance: >50%
- Free-to-paid conversion: >5%

### Revenue Metrics
- MRR growth: 20% month-over-month
- Churn rate: <5% monthly
- LTV/CAC ratio: >3:1

### Technical Metrics
- API uptime: 99.9%
- P95 response time: <100ms
- Error rate: <0.1%

---

*Document Version: 1.0*  
*Last Updated: December 4, 2025*
