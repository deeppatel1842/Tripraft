import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../../context/AuthContext';
import Header from '../../layout/jsx/Header';
import Footer from '../../layout/jsx/Footer';
import '../css/Pricing.css';

const Pricing = () => {
  const { currentUser, signOut } = useAuth();
  const navigate = useNavigate();
  const [billingCycle, setBillingCycle] = useState('monthly'); // monthly or annual
  const [selectedPlan, setSelectedPlan] = useState(null);

  const handleLogout = async () => {
    try {
      await signOut();
      navigate('/');
    } catch (error) {
    }
  };

  const handleSelectPlan = (planName) => {
    if (planName === 'free') {
      navigate('/signup');
    } else {
      setSelectedPlan(planName);
      // Navigate to checkout in future
    }
  };

  const pricingPlans = [
    {
      id: 'free',
      name: 'Free',
      description: 'Perfect for casual travelers',
      monthlyPrice: 0,
      annualPrice: 0,
      highlighted: false,
      cta: 'Get Started',
      comingSoon: false,
      features: [
        { text: 'Up to 2 expenses per day', included: true },
        { text: 'Up to 3 groups', included: true },
        { text: 'Up to 5 members per group', included: true },
        { text: '3 saved trip plans', included: true },
        { text: '10 AI chat messages/day', included: true },
        { text: '50 places searches/day', included: true },
        { text: 'Ads displayed', included: true },
        { text: 'Email notifications', included: false },
        { text: 'PDF export', included: false },
        { text: 'Priority support', included: false }
      ]
    },
    {
      id: 'plus',
      name: 'Plus',
      description: 'For regular travelers & friends',
      monthlyPrice: 4.99,
      annualPrice: 39.99,
      highlighted: true,
      cta: 'Start Free Trial',
      badge: 'Most Popular',
      comingSoon: false,
      features: [
        { text: 'Up to 50 expenses per day', included: true },
        { text: 'Up to 20 groups', included: true },
        { text: 'Up to 20 members per group', included: true },
        { text: '25 saved trip plans', included: true },
        { text: '100 AI chat messages/day', included: true },
        { text: 'Unlimited places searches', included: true },
        { text: 'No ads', included: true },
        { text: 'Email notifications', included: true },
        { text: 'PDF export', included: true },
        { text: 'Priority support', included: false }
      ]
    },
    {
      id: 'pro',
      name: 'Pro',
      description: 'For travel enthusiasts & families',
      monthlyPrice: 9.99,
      annualPrice: 79.99,
      highlighted: false,
      cta: 'Notify Me',
      badge: 'Coming Soon',
      comingSoon: true,
      features: [
        { text: 'Unlimited expenses', included: true },
        { text: 'Unlimited groups', included: true },
        { text: 'Up to 50 members per group', included: true },
        { text: 'Unlimited trip plans', included: true },
        { text: '500 AI chat messages/day', included: true },
        { text: 'Unlimited places searches', included: true },
        { text: 'No ads', included: true },
        { text: 'Email notifications', included: true },
        { text: 'PDF export', included: true },
        { text: '24/7 priority support', included: true }
      ]
    },
    {
      id: 'business',
      name: 'Business',
      description: 'For teams & travel agencies',
      monthlyPrice: 19.99,
      annualPrice: 199.99,
      highlighted: false,
      cta: 'Notify Me',
      comingSoon: true,
      features: [
        { text: 'Everything in Pro', included: true },
        { text: 'Admin dashboard', included: true },
        { text: 'Custom expense categories', included: true },
        { text: 'Approval workflows', included: true },
        { text: 'Full API access', included: true },
        { text: 'SSO/SAML authentication', included: true },
        { text: 'Dedicated support', included: true },
        { text: 'Custom branding', included: true },
        { text: 'Audit logs', included: true },
        { text: 'Multi-team management', included: true }
      ]
    }
  ];

  const getPrice = (plan) => {
    if (billingCycle === 'annual') {
      return plan.annualPrice;
    }
    return plan.monthlyPrice;
  };

  const getSavings = (plan) => {
    if (plan.annualPrice === 0) return null;
    const monthlyTotal = plan.monthlyPrice * 12;
    const savings = monthlyTotal - plan.annualPrice;
    const percent = Math.round((savings / monthlyTotal) * 100);
    return { savings, percent };
  };

  return (
    <div className="pricing-page">
      <Header 
        isAuthenticated={!!currentUser}
        user={currentUser}
        onLogout={handleLogout}
      />

      {/* Hero Section */}
      <section className="pricing-hero reveal">
        <div className="pricing-hero-content">
          <h1>Simple, Transparent Pricing</h1>
          <p className="pricing-subtitle">Choose the plan that fits your travel needs</p>
          <p className="pricing-description">
            All plans include access to our curated places database, group coordination tools, and expense splitting features.
          </p>
        </div>
      </section>

      {/* Billing Toggle */}
      <section className="pricing-section">
        <div className="container">
          <div className="billing-toggle-wrapper">
            <div className="billing-toggle">
              <button 
                className={`toggle-btn ${billingCycle === 'monthly' ? 'active' : ''}`}
                onClick={() => setBillingCycle('monthly')}
              >
                Monthly Billing
              </button>
              <button 
                className={`toggle-btn ${billingCycle === 'annual' ? 'active' : ''}`}
                onClick={() => setBillingCycle('annual')}
              >
                Annual Billing
                <span className="savings-badge">Save 33%</span>
              </button>
            </div>
          </div>

          {/* Pricing Cards */}
          <div className="pricing-grid">
            {pricingPlans.filter(plan => !plan.comingSoon).map((plan, index) => (
              <div 
                key={plan.id}
                className={`pricing-card reveal`}
                style={{ animationDelay: `${index * 0.1}s` }}
              >
                {plan.badge && <div className="plan-badge">{plan.badge}</div>}
                
                <div className="plan-header">
                  <h2 className="plan-name">{plan.name}</h2>
                  <p className="plan-description">{plan.description}</p>
                </div>

                <div className="plan-pricing">
                  {plan.monthlyPrice === 0 ? (
                    <>
                      <span className="currency">$</span>
                      <span className="amount">0</span>
                      <span className="period">/month</span>
                    </>
                  ) : (
                    <>
                      <span className="currency">$</span>
                      <span className="amount">{getPrice(plan).toFixed(2)}</span>
                      <span className="period">
                        {billingCycle === 'monthly' ? '/month' : '/year'}
                      </span>
                    </>
                  )}
                  
                  {billingCycle === 'annual' && getSavings(plan) && (
                    <div className="annual-savings">
                      Save ${getSavings(plan).savings.toFixed(2)} ({getSavings(plan).percent}%)
                    </div>
                  )}
                </div>

                <button 
                  className={`plan-cta`}
                  onClick={() => handleSelectPlan(plan.id)}
                >
                  <i className="fas fa-arrow-right"></i>
                  {plan.cta === 'Start Free Trial' ? 'Get Started' : plan.cta}
                </button>

                <div className="plan-features">
                  {plan.features.map((feature, idx) => (
                    <div key={idx} className="feature-item">
                      <i className={`fas ${feature.included ? 'fa-check' : 'fa-times'}`}></i>
                      <span>{feature.text}</span>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Coming Soon Section */}
      <section className="pricing-section coming-soon-wrapper reveal">
        <div className="container">
          <h3 className="coming-soon-title">More Plans Coming Soon</h3>
          <p className="coming-soon-subtitle">We're working on even more powerful features for advanced travelers and teams</p>
          <div className="coming-soon-grid">
            {pricingPlans.filter(plan => plan.comingSoon).map((plan, index) => (
              <div 
                key={plan.id}
                className="coming-soon-card reveal"
                style={{ animationDelay: `${index * 0.1}s` }}
              >
                <div className="coming-soon-badge">Coming Soon</div>
                <h4>{plan.name}</h4>
                <p>{plan.description}</p>
                <div className="coming-soon-price">
                  <span className="currency">$</span>
                  <span className="amount">{plan.monthlyPrice}</span>
                  <span className="period">/month</span>
                </div>
                <button className="coming-soon-notify" onClick={() => {}}>
                  <i className="fas fa-bell"></i>
                  Notify Me
                </button>
              </div>
            ))}
          </div>
        </div>
      </section>
      <section className="pricing-section comparison-section reveal">
        <div className="container">
          <h2 className="section-title">Feature Comparison</h2>
          
          <div className="comparison-table-wrapper">
            <table className="comparison-table">
              <thead>
                <tr>
                  <th>Feature</th>
                  <th>Free</th>
                  <th>Plus</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td className="feature-name">Daily Expenses Limit</td>
                  <td>2</td>
                  <td>50</td>
                </tr>
                <tr>
                  <td className="feature-name">Groups Allowed</td>
                  <td>3</td>
                  <td>20</td>
                </tr>
                <tr>
                  <td className="feature-name">Members per Group</td>
                  <td>5</td>
                  <td>20</td>
                </tr>
                <tr>
                  <td className="feature-name">Saved Trip Plans</td>
                  <td>3</td>
                  <td>25</td>
                </tr>
                <tr>
                  <td className="feature-name">AI Chat Messages/Day</td>
                  <td>10</td>
                  <td>100</td>
                </tr>
                <tr>
                  <td className="feature-name">Places Searches</td>
                  <td>50/day</td>
                  <td>Unlimited</td>
                </tr>
                <tr>
                  <td className="feature-name">Advertising</td>
                  <td>Yes</td>
                  <td>No</td>
                </tr>
                <tr>
                  <td className="feature-name">Email Notifications</td>
                  <td>No</td>
                  <td>Yes</td>
                </tr>
                <tr>
                  <td className="feature-name">PDF Export</td>
                  <td>No</td>
                  <td>Yes</td>
                </tr>
                <tr>
                  <td className="feature-name">Receipt Scanning (OCR)</td>
                  <td>No</td>
                  <td>Coming soon</td>
                </tr>
                <tr>
                  <td className="feature-name">Multi-Currency</td>
                  <td>No</td>
                  <td>No</td>
                </tr>
                <tr>
                  <td className="feature-name">Calendar Sync</td>
                  <td>No</td>
                  <td>No</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* FAQ Section */}
      <section className="pricing-section faq-section reveal">
        <div className="container">
          <h2 className="section-title">Frequently Asked Questions</h2>
          
          <div className="faq-grid">
            <div className="faq-card reveal">
              <h3>
                <i className="fas fa-question-circle"></i>
                Can I upgrade or downgrade anytime?
              </h3>
              <p>
                Yes! You can change your plan at any time. If you upgrade, you'll be charged the difference prorated. 
                If you downgrade, your account will adjust accordingly.
              </p>
            </div>

            <div className="faq-card reveal">
              <h3>
                <i className="fas fa-question-circle"></i>
                Is there a free trial for paid plans?
              </h3>
              <p>
                Absolutely! Plus and Pro plans include a 14-day free trial. No credit card required to start. 
                Business plans include a custom trial period.
              </p>
            </div>

            <div className="faq-card reveal">
              <h3>
                <i className="fas fa-question-circle"></i>
                What payment methods do you accept?
              </h3>
              <p>
                We accept all major credit cards (Visa, Mastercard, American Express), Apple Pay, Google Pay, 
                and bank transfers for Business plans.
              </p>
            </div>

            <div className="faq-card reveal">
              <h3>
                <i className="fas fa-question-circle"></i>
                Do you offer discounts for annual billing?
              </h3>
              <p>
                Yes! Annual plans save you 33% compared to monthly billing. Plus get access to exclusive annual features 
                and priority support.
              </p>
            </div>

            <div className="faq-card reveal">
              <h3>
                <i className="fas fa-question-circle"></i>
                Can I cancel anytime?
              </h3>
              <p>
                Yes, you can cancel your subscription anytime with no questions asked. You'll have access to your plan 
                through the end of the current billing period.
              </p>
            </div>

            <div className="faq-card reveal">
              <h3>
                <i className="fas fa-question-circle"></i>
                Do you offer refunds?
              </h3>
              <p>
                We offer a 30-day money-back guarantee if you're not satisfied. Just contact our support team. 
                Business plans have custom refund policies.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="pricing-cta reveal">
        <div className="cta-content">
          <h2>Ready to Plan Your Next Adventure?</h2>
          <p>Join thousands of travelers who are already using Tripraft</p>
          <div className="cta-buttons">
            <button className="cta-button primary" onClick={() => handleSelectPlan('plus')}>
              <i className="fas fa-star"></i> Start with Plus
            </button>
            <button className="cta-button secondary" onClick={() => navigate('/contact')}>
              <i className="fas fa-headset"></i> Talk to Sales
            </button>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
};

export default Pricing;
