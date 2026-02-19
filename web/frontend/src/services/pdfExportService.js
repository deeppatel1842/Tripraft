/**
 * PDF Export Service for Expense Manager
 * Generates professional PDF reports for personal and group expenses with Tripraft branding
 */

import { jsPDF } from 'jspdf';
import autoTable from 'jspdf-autotable';

// Color theme matching Tripraft brand
const THEME = {
  primary: '#667eea',
  secondary: '#764ba2',
  success: '#059669',
  danger: '#dc2626',
  text: '#111827',
  textLight: '#6b7280',
  border: '#e5e7eb',
  tripraftPurple: '#667eea'
};

/**
 * Format currency
 */
const formatCurrency = (amount, currency = 'USD') => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: currency,
    minimumFractionDigits: 2
  }).format(amount);
};

/**
 * Format date
 */
const formatDate = (dateStr) => {
  if (!dateStr) return '-';
  return new Date(dateStr).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  });
};

/**
 * Helper to get member name from settlement
 */
const getMemberName = (userId, allMembers = [], settlement = {}) => {
  // Try settlement direct fields first
  if (settlement && settlement.from_user && settlement.from_user.display_name) {
    return settlement.from_user.display_name;
  }
  if (settlement && settlement.to_user && settlement.to_user.display_name) {
    return settlement.to_user.display_name;
  }
  
  // Try to find in members array
  if (allMembers && Array.isArray(allMembers)) {
    const member = allMembers.find(m => {
      const mId = m.user_id || m.id;
      return String(mId) === String(userId);
    });
    if (member) {
      return member.display_name || member.user?.display_name || member.email || 'Member';
    }
  }
  
  return `User ${userId}`;
};

/**
 * Generate PDF report for expenses
 */
export const generateExpensePDF = ({
  mode,
  groupName = 'Personal',
  expenses = [],
  settlements = [],
  members = [],
  balances = [],
  currency = 'USD',
  userName = 'User'
}) => {
  // Create PDF document
  const doc = new jsPDF({
    orientation: 'portrait',
    unit: 'mm',
    format: 'a4'
  });

  const pageWidth = doc.internal.pageSize.getWidth();
  const pageHeight = doc.internal.pageSize.getHeight();
  const margin = 15;
  let yPos = margin;
  let currentPage = 1;

  // Helper function to add beautiful header with branding
  const addHeader = (isFirstPage = true) => {
    // Background gradient effect (solid color)
    doc.setFillColor(102, 126, 234); // Tripraft purple
    doc.rect(0, 0, pageWidth, 50, 'F');
    
    // Tripraft branding
    doc.setTextColor(255, 255, 255);
    doc.setFontSize(28);
    doc.setFont('helvetica', 'bold');
    doc.text('TripRaft', margin, 18);
    
    // Tagline
    doc.setFontSize(10);
    doc.setFont('helvetica', 'normal');
    doc.text('Expense Management Made Simple', margin, 25);
    
    // Report details on right side
    if (isFirstPage) {
      doc.setFontSize(11);
      doc.setFont('helvetica', 'bold');
      doc.text('Expense Report', pageWidth - margin - 50, 18);
      
      doc.setFontSize(10);
      doc.setFont('helvetica', 'normal');
      doc.text(mode === 'group' ? groupName : 'Personal Expenses', pageWidth - margin - 50, 27);
      
      // Date
      doc.setFontSize(9);
      doc.text(`Generated: ${new Date().toLocaleDateString('en-US', { 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      })}`, pageWidth - margin - 50, 35);
    }
    
    yPos = 55;
  };

  // Helper function to add section title
  const addSectionTitle = (title) => {
    if (yPos > pageHeight - 40) {
      doc.addPage();
      addPageHeader();
      yPos = margin;
    }
    
    doc.setFillColor(248, 250, 252);
    doc.rect(margin - 2, yPos - 5, pageWidth - 2 * margin + 4, 10, 'F');
    
    doc.setTextColor(102, 126, 234);
    doc.setFontSize(13);
    doc.setFont('helvetica', 'bold');
    doc.text(title, margin, yPos);
    yPos += 12;
  };

  // Add page header for subsequent pages
  const addPageHeader = () => {
    currentPage++;
    doc.setFillColor(245, 245, 250);
    doc.rect(0, 0, pageWidth, 12, 'F');
    
    doc.setTextColor(102, 126, 234);
    doc.setFontSize(10);
    doc.setFont('helvetica', 'bold');
    doc.text('TripRaft • Expense Report', margin, 8);
  };

  // Add header
  addHeader(true);

  // Summary Section
  addSectionTitle('Financial Summary');
  
  const totalExpenses = expenses.reduce((sum, exp) => sum + (parseFloat(exp.amount) || 0), 0);
  const totalSettlements = settlements.reduce((sum, s) => sum + (parseFloat(s.amount) || 0), 0);
  
  const summaryData = [
    ['Total Expenses', formatCurrency(totalExpenses, currency)],
    ['Number of Transactions', expenses.length.toString()],
    ['Total Settlements', formatCurrency(totalSettlements, currency)],
  ];
  
  if (mode === 'group') {
    summaryData.push(['Group Members', members.length.toString()]);
  }

  autoTable(doc, {
    startY: yPos,
    head: [['Metric', 'Value']],
    body: summaryData,
    theme: 'striped',
    styles: {
      fontSize: 10,
      cellPadding: [7, 12],
      valign: 'middle',
    },
    headStyles: {
      fillColor: [102, 126, 234],
      textColor: [255, 255, 255],
      fontStyle: 'bold',
      cellPadding: [8, 12],
      fontSize: 11
    },
    columnStyles: {
      0: { fontStyle: 'bold', textColor: [102, 126, 234], halign: 'left', cellWidth: 70 },
      1: { fontStyle: 'bold', textColor: [17, 24, 39], halign: 'right' }
    },
    alternateRowStyles: {
      fillColor: [249, 250, 251]
    },
    margin: { left: margin, right: margin }
  });
  
  yPos = doc.lastAutoTable.finalY + 15;

  // Balances Section (Group Mode)
  if (mode === 'group' && balances.length > 0) {
    addSectionTitle('Current Balances');
    
    const balanceRows = balances.map(bal => {
      const balance = parseFloat(bal.balance || bal.net_balance || 0);
      return [
        bal.display_name || bal.user?.display_name || 'Member',
        balance >= 0 ? formatCurrency(balance, currency) : '-',
        balance < 0 ? formatCurrency(Math.abs(balance), currency) : '-',
        balance > 0.01 ? 'is owed' : (balance < -0.01 ? 'owes' : 'settled')
      ];
    });

    autoTable(doc, {
      startY: yPos,
      head: [['Member', 'Gets Back', 'Owes', 'Status']],
      body: balanceRows,
      theme: 'striped',
      styles: {
        fontSize: 10,
        cellPadding: [7, 10],
        valign: 'middle',
        lineColor: [229, 231, 235],
        lineWidth: 0.5
      },
      headStyles: {
        fillColor: [102, 126, 234],
        textColor: [255, 255, 255],
        fontStyle: 'bold',
        cellPadding: [8, 10],
        fontSize: 11,
        lineColor: [102, 126, 234],
        lineWidth: 1
      },
      columnStyles: {
        0: { halign: 'left' },
        1: { textColor: [5, 150, 105], halign: 'right', fontStyle: 'bold' },
        2: { textColor: [220, 38, 38], halign: 'right', fontStyle: 'bold' },
        3: { halign: 'center', textColor: [107, 114, 128], fontSize: 9 }
      },
      alternateRowStyles: {
        fillColor: [249, 250, 251]
      },
      margin: { left: margin, right: margin }
    });
    
    yPos = doc.lastAutoTable.finalY + 15;
  }

  // Category Breakdown
  addSectionTitle('Spending by Category');
  
  const categoryTotals = {};
  expenses.forEach(exp => {
    const cat = exp.category || 'Other';
    categoryTotals[cat] = (categoryTotals[cat] || 0) + (parseFloat(exp.amount) || 0);
  });
  
  const categoryRows = Object.entries(categoryTotals)
    .sort((a, b) => b[1] - a[1])
    .map(([cat, amount]) => [
      cat,
      formatCurrency(amount, currency),
      totalExpenses > 0 ? `${((amount / totalExpenses) * 100).toFixed(1)}%` : '0%'
    ]);

  autoTable(doc, {
    startY: yPos,
    head: [['Category', 'Amount', 'Percentage']],
    body: categoryRows,
    theme: 'striped',
    styles: {
      fontSize: 10,
      cellPadding: [7, 12],
      valign: 'middle',
      lineColor: [229, 231, 235],
      lineWidth: 0.5
    },
    headStyles: {
      fillColor: [102, 126, 234],
      textColor: [255, 255, 255],
      fontStyle: 'bold',
      cellPadding: [8, 12],
      fontSize: 11,
      lineWidth: 1
    },
    columnStyles: {
      0: { halign: 'left' },
      1: { halign: 'right', fontStyle: 'bold' },
      2: { halign: 'right', textColor: [102, 126, 234], fontStyle: 'bold' }
    },
    alternateRowStyles: {
      fillColor: [249, 250, 251]
    },
    margin: { left: margin, right: margin }
  });
  
  yPos = doc.lastAutoTable.finalY + 15;

  // Expense Details
  addSectionTitle('Transaction History');
  
  const expenseRows = expenses.map(exp => [
    formatDate(exp.expense_date || exp.date || exp.created_at),
    exp.description || '-',
    exp.category || 'Other',
    formatCurrency(exp.amount || 0, currency)
  ]);

  autoTable(doc, {
    startY: yPos,
    head: [['Date', 'Description', 'Category', 'Amount']],
    body: expenseRows,
    theme: 'striped',
    styles: {
      fontSize: 9,
      cellPadding: [6, 8],
      valign: 'middle',
      overflow: 'ellipsize',
      cellWidth: 'wrap',
      lineColor: [229, 231, 235],
      lineWidth: 0.5
    },
    headStyles: {
      fillColor: [102, 126, 234],
      textColor: [255, 255, 255],
      fontStyle: 'bold',
      cellPadding: [7, 8],
      fontSize: 10,
      lineWidth: 1
    },
    columnStyles: {
      0: { cellWidth: 25, halign: 'left' },
      1: { cellWidth: 'auto', halign: 'left' },
      2: { cellWidth: 30, halign: 'center' },
      3: { cellWidth: 30, halign: 'right', fontStyle: 'bold' }
    },
    alternateRowStyles: {
      fillColor: [249, 250, 251]
    },
    margin: { left: margin, right: margin }
  });

  // Settlement History (if any)
  if (settlements.length > 0) {
    yPos = doc.lastAutoTable.finalY + 15;
    
    if (yPos > pageHeight - 70) {
      doc.addPage();
      addPageHeader();
      yPos = margin;
    }
    
    addSectionTitle('Settlement History');
    
    const settlementRows = settlements.map(s => {
      // Get proper names from settlement object
      let fromName = 'Unknown';
      let toName = 'Unknown';
      
      // Check settlement object structure
      if (s.from_user && s.from_user.display_name) {
        fromName = s.from_user.display_name;
      } else if (s.payer_name && s.payer_name !== 'undefined') {
        fromName = s.payer_name;
      } else if (s.payer_id) {
        fromName = getMemberName(s.payer_id, members, s);
      }
      
      if (s.to_user && s.to_user.display_name) {
        toName = s.to_user.display_name;
      } else if (s.payee_name && s.payee_name !== 'undefined') {
        toName = s.payee_name;
      } else if (s.payee_id) {
        toName = getMemberName(s.payee_id, members, s);
      }
      
      return [
        formatDate(s.created_at || s.date || s.settlement_date),
        fromName,
        toName,
        formatCurrency(s.amount || 0, currency)
      ];
    });

    autoTable(doc, {
      startY: yPos,
      head: [['Date', 'From', 'To', 'Amount']],
      body: settlementRows,
      theme: 'striped',
      styles: {
        fontSize: 9,
        cellPadding: [7, 10],
        valign: 'middle',
        lineColor: [229, 231, 235],
        lineWidth: 0.5
      },
      headStyles: {
        fillColor: [118, 75, 162],
        textColor: [255, 255, 255],
        fontStyle: 'bold',
        cellPadding: [8, 10],
        fontSize: 10,
        lineWidth: 1
      },
      columnStyles: {
        0: { halign: 'left' },
        1: { halign: 'left' },
        2: { halign: 'left' },
        3: { halign: 'right', fontStyle: 'bold' }
      },
      alternateRowStyles: {
        fillColor: [249, 250, 251]
      },
      margin: { left: margin, right: margin }
    });
  }

  // Add footer to all pages
  const pageCount = doc.getNumberOfPages();
  for (let i = 1; i <= pageCount; i++) {
    doc.setPage(i);
    
    // Footer divider
    doc.setDrawColor(229, 231, 235);
    doc.setLineWidth(0.5);
    doc.line(margin, pageHeight - 15, pageWidth - margin, pageHeight - 15);
    
    // Footer text
    doc.setFontSize(8);
    doc.setTextColor(107, 114, 128);
    doc.text(
      'TripRaft • Expense Management',
      margin,
      pageHeight - 10
    );
    
    // Page number (right aligned)
    doc.text(
      `Page ${i} of ${pageCount}`,
      pageWidth - margin - 20,
      pageHeight - 10
    );
  }

  // Save the PDF
  const filename = mode === 'group' 
    ? `TripRaft_${groupName.replace(/[^a-z0-9]/gi, '_')}_${new Date().toISOString().split('T')[0]}.pdf`
    : `TripRaft_Personal_Expenses_${new Date().toISOString().split('T')[0]}.pdf`;
  
  doc.save(filename);
  
  return filename;
};


export default { generateExpensePDF };
