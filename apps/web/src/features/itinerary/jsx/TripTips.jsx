// Purpose: Renders the Trip Tips interface within apps\web\src\features\itinerary\jsx.
import React from 'react';

const TripTips = () => {
  const tipsCategories = [
    {
      title: 'Bookings & Documents',
      tips: [
        'Book Transportation & Lodging: Secure your flights, trains, rental cars, and accommodations well in advance.',
        'Check Passports & Visas: Ensure your passport is valid for at least six months beyond your travel dates and check the visa requirements for your destination.',
        'Copy Important Documents: Make digital and physical copies of your passport, visas, driver\'s license, and hotel confirmations.',
        'Plan Key Activities: Book any must-see tours or popular attractions in advance to avoid disappointment.'
      ]
    },
    {
      title: 'Home & Health',
      tips: [
        'Arrange Home Care: Organize a sitter for pets, care for plants, and arrange for mail to be held.',
        'Consult Your Doctor: Check for required vaccinations and get any necessary prescription medications to last your entire trip.',
        'Get Travel Insurance: Purchase comprehensive travel insurance that covers medical emergencies, trip cancellations, and lost luggage.'
      ]
    },
    {
      title: 'Money & Communication',
      tips: [
        'Notify Your Bank: Inform your bank and credit card companies of your travel plans to prevent your cards from being blocked.',
        'Prepare Multiple Payment Methods: Carry a mix of local currency, a debit card, and at least two different credit cards.',
        'Set Up Your Phone: Arrange for an international data plan, purchase a local SIM card, or download an eSIM to stay connected affordably.'
      ]
    },
    {
      title: 'Packing & Preparation',
      tips: [
        'Pack Smart: Choose versatile clothing that can be layered and pack comfortable walking shoes.',
        'Get Power Adapters: Research the plug type for your destination and pack the correct universal adapter or converter.',
        'Download Offline Resources: Save offline maps, translation apps, and entertainment for your journey.',
        'Charge Everything: Fully charge all your electronics, including your phone, power banks, and camera, the night before you leave.'
      ]
    }
  ];

  return (
    <div className="trip-tips-container">
      <h2 className="trip-tips-title">Trip Tips</h2>
      <div className="tips-grid">
        {tipsCategories.map((category, index) => (
          <div key={index} className="tip-category">
            <h3 className="tip-category-title">{category.title}</h3>
            <ul className="tip-list">
              {category.tips.map((tip, tipIndex) => (
                <li key={tipIndex} className="tip-item">
                  <span className="tip-bullet">•</span>
                  <span className="tip-text">{tip}</span>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
};

export default TripTips;
