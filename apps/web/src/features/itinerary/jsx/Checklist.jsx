// Purpose: Renders the Checklist interface within apps\web\src\features\itinerary\jsx.
import React, { useState } from 'react';

const Checklist = () => {
  const checklistItems = [
    {
      category: 'Essentials (Carry-On Bag)',
      items: [
        'Passport / Visa / ID',
        'Wallet (Credit cards, debit cards, and some local currency)',
        'All booking confirmations (flights, hotels, cars)',
        'Prescription medications (in original bottles if possible)',
        'A change of clothes (in case of lost luggage)',
        'Basic toiletries (toothbrush, travel-sized toothpaste, deodorant)',
      ]
    },
    {
      category: 'Health & First-Aid',
      items: [
        'Small first-aid kit (band-aids, antiseptic wipes, pain relievers)'
      ]
    },
    {
      category: 'Electronics & Miscellaneous',
      items: [
        'Phone charger and cables',
        'Travel power adapter / converter',
        'Sunglasses'
      ]
    }
  ];

  const [checkedItems, setCheckedItems] = useState({});

  const toggleItem = (categoryIndex, itemIndex) => {
    const key = `${categoryIndex}-${itemIndex}`;
    setCheckedItems(prev => ({
      ...prev,
      [key]: !prev[key]
    }));
  };

  return (
    <div className="checklist-container">
      <h2 className="checklist-title">Travel Checklist</h2>
      <div className="checklist-content">
        {checklistItems.map((category, categoryIndex) => (
          <div key={categoryIndex} className="checklist-category">
            <h3 className="checklist-category-title">{category.category}</h3>
            <ul className="checklist-items">
              {category.items.map((item, itemIndex) => {
                const key = `${categoryIndex}-${itemIndex}`;
                const isChecked = checkedItems[key] || false;
                
                return (
                  <li 
                    key={itemIndex} 
                    className={`checklist-item ${isChecked ? 'checked' : ''}`}
                    onClick={() => toggleItem(categoryIndex, itemIndex)}
                  >
                    <div className="checkbox-wrapper">
                      <div className={`checkbox ${isChecked ? 'checked' : ''}`}>
                        {isChecked && (
                          <svg width="12" height="10" viewBox="0 0 12 10" fill="none">
                            <path d="M1 5L4.5 8.5L11 1" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                          </svg>
                        )}
                      </div>
                    </div>
                    <span className="checklist-item-text">{item}</span>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Checklist;
