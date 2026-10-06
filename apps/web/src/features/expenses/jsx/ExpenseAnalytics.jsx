// Purpose: Renders the Expense Analytics interface within apps\web\src\features\expenses\jsx.
/**
 * Expense Analytics Component
 * Advanced analytics dashboard for personal and group expenses
 * Similar to Splitwise's analytics features
 */

/**
 * Expense Analytics Component
 * Advanced analytics dashboard for personal and group expenses
 * Similar to Splitwise's analytics features
 */

import React, { useState, useMemo } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts';
import { TrendingUp, TrendingDown, DollarSign, Calendar, Users, BarChart2, Download, FileText } from 'lucide-react';
import { formatMoney } from '../../../utils/money';
import { formatDateLocal } from '../../../utils/timezoneUtils';
import '../css/ExpenseAnalytics.css';

// Color palette matching the theme
const COLORS = ['#667eea', '#764ba2', '#f093fb', '#f5576c', '#4facfe', '#00f2fe', '#43e97b', '#38f9d7', '#fa709a', '#fee140'];
const CATEGORY_COLORS = {
  'Food': '#667eea',
  'Transport': '#764ba2',
  'Entertainment': '#f093fb',
  'Shopping': '#f5576c',
  'Utilities': '#4facfe',
  'Health': '#00f2fe',
  'Travel': '#43e97b',
  'Other': '#38f9d7',
  'Accommodation': '#fa709a',
  'Activities': '#fee140'
};

const ExpenseAnalytics = ({ 
  mode, 
  expenses = [], 
  settlements = [],
  members = [],
  balances = [],
  groupName = '',
  currency = 'USD',
  onBack,
  onExportPDF
}) => {
  const [timeRange, setTimeRange] = useState('all');

  // Filter expenses by time range
  const filteredExpenses = useMemo(() => {
    if (timeRange === 'all') return expenses;
    
    const now = new Date();
    const ranges = {
      'week': 7,
      'month': 30,
      'quarter': 90,
      'year': 365
    };
    
    const daysAgo = ranges[timeRange] || 0;
    const cutoffDate = new Date(now.getTime() - (daysAgo * 24 * 60 * 60 * 1000));
    
    return expenses.filter(exp => {
      const expDate = new Date(exp.expense_date || exp.date || exp.created_at);
      return expDate >= cutoffDate;
    });
  }, [expenses, timeRange]);

  // Calculate summary statistics
  const stats = useMemo(() => {
    const total = filteredExpenses.reduce((sum, exp) => sum + (parseFloat(exp.amount) || 0), 0);
    const count = filteredExpenses.length;
    const avgPerTransaction = count > 0 ? total / count : 0;
    
    // Calculate daily average
    if (count === 0) return { total: 0, count: 0, avgPerTransaction: 0, dailyAvg: 0, monthlyAvg: 0 };
    
    const dates = filteredExpenses.map(exp => new Date(exp.expense_date || exp.date || exp.created_at));
    const minDate = new Date(Math.min(...dates));
    const maxDate = new Date(Math.max(...dates));
    const daysDiff = Math.max(1, Math.ceil((maxDate - minDate) / (1000 * 60 * 60 * 24)));
    
    const dailyAvg = total / daysDiff;
    const monthlyAvg = dailyAvg * 30;

    return { total, count, avgPerTransaction, dailyAvg, monthlyAvg };
  }, [filteredExpenses]);

  // Category breakdown
  const categoryData = useMemo(() => {
    const categories = {};
    filteredExpenses.forEach(exp => {
      const cat = exp.category || 'Other';
      categories[cat] = (categories[cat] || 0) + (parseFloat(exp.amount) || 0);
    });
    
    return Object.entries(categories)
      .map(([name, value]) => ({ 
        name, 
        value: parseFloat(value.toFixed(2)),
        color: CATEGORY_COLORS[name] || '#667eea'
      }))
      .sort((a, b) => b.value - a.value);
  }, [filteredExpenses]);

  // Monthly trend data
  const monthlyTrend = useMemo(() => {
    const months = {};
    filteredExpenses.forEach(exp => {
      const date = new Date(exp.expense_date || exp.date || exp.created_at);
      const monthKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
      months[monthKey] = (months[monthKey] || 0) + (parseFloat(exp.amount) || 0);
    });
    
    return Object.entries(months)
      .map(([month, amount]) => ({
        month: formatDateLocal(new Date(month + '-01'), { month: 'short', year: '2-digit' }),
        amount: parseFloat(amount.toFixed(2))
      }))
      .sort((a, b) => new Date(a.month) - new Date(b.month));
  }, [filteredExpenses]);

  // Daily spending for the selected period
  const dailySpending = useMemo(() => {
    const days = {};
    filteredExpenses.forEach(exp => {
      const date = new Date(exp.expense_date || exp.date || exp.created_at);
      const dayKey = date.toISOString().split('T')[0];
      days[dayKey] = (days[dayKey] || 0) + (parseFloat(exp.amount) || 0);
    });
    
    return Object.entries(days)
      .map(([date, amount]) => ({
        date: formatDateLocal(new Date(date), { month: 'short', day: 'numeric' }),
        amount: parseFloat(amount.toFixed(2))
      }))
      .sort((a, b) => new Date(a.date) - new Date(b.date))
      .slice(-30); // Last 30 days
  }, [filteredExpenses]);

  // Member spending (for group mode)
  const memberSpending = useMemo(() => {
    if (mode !== 'group') return [];
    
    const spending = {};
    filteredExpenses.forEach(exp => {
      const paidBy = exp.paid_by || exp.created_by;
      spending[paidBy] = (spending[paidBy] || 0) + (parseFloat(exp.amount) || 0);
    });
    
    return Object.entries(spending).map(([userId, amount]) => {
      const member = members.find(m => String(m.user_id) === String(userId) || String(m.id) === String(userId));
      return {
        name: member?.display_name || member?.user?.display_name || `User ${userId}`,
        amount: parseFloat(amount.toFixed(2)),
        userId
      };
    }).sort((a, b) => b.amount - a.amount);
  }, [filteredExpenses, members, mode]);

  // Week over week comparison
  const weekComparison = useMemo(() => {
    const now = new Date();
    const oneWeekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
    const twoWeeksAgo = new Date(now.getTime() - 14 * 24 * 60 * 60 * 1000);
    
    const thisWeek = expenses.filter(exp => {
      const date = new Date(exp.expense_date || exp.date || exp.created_at);
      return date >= oneWeekAgo && date <= now;
    }).reduce((sum, exp) => sum + (parseFloat(exp.amount) || 0), 0);
    
    const lastWeek = expenses.filter(exp => {
      const date = new Date(exp.expense_date || exp.date || exp.created_at);
      return date >= twoWeeksAgo && date < oneWeekAgo;
    }).reduce((sum, exp) => sum + (parseFloat(exp.amount) || 0), 0);
    
    const change = lastWeek > 0 ? ((thisWeek - lastWeek) / lastWeek * 100) : 0;
    return { thisWeek, lastWeek, change };
  }, [expenses]);

  // Month over month comparison
  const monthComparison = useMemo(() => {
    const now = new Date();
    const thisMonthStart = new Date(now.getFullYear(), now.getMonth(), 1);
    const lastMonthStart = new Date(now.getFullYear(), now.getMonth() - 1, 1);
    const lastMonthEnd = new Date(now.getFullYear(), now.getMonth(), 0);
    
    const thisMonth = expenses.filter(exp => {
      const date = new Date(exp.expense_date || exp.date || exp.created_at);
      return date >= thisMonthStart && date <= now;
    }).reduce((sum, exp) => sum + (parseFloat(exp.amount) || 0), 0);
    
    const lastMonth = expenses.filter(exp => {
      const date = new Date(exp.expense_date || exp.date || exp.created_at);
      return date >= lastMonthStart && date <= lastMonthEnd;
    }).reduce((sum, exp) => sum + (parseFloat(exp.amount) || 0), 0);
    
    const change = lastMonth > 0 ? ((thisMonth - lastMonth) / lastMonth * 100) : 0;
    return { thisMonth, lastMonth, change };
  }, [expenses]);

  // Top expenses
  const topExpenses = useMemo(() => {
    return [...filteredExpenses]
      .sort((a, b) => (parseFloat(b.amount) || 0) - (parseFloat(a.amount) || 0))
      .slice(0, 5);
  }, [filteredExpenses]);

  // Format currency
  const formatCurrency = (amount) => formatMoney(amount, currency);

  // Custom tooltip for charts
  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="exp-analytics-tooltip">
          <p className="exp-analytics-tooltip-label">{label}</p>
          <p className="exp-analytics-tooltip-value">{formatCurrency(payload[0].value)}</p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="exp-analytics">
      {/* Header */}
      <div className="exp-analytics-header">
        <div className="exp-analytics-header-left">
         
          <div className="exp-analytics-title">
            <h1>
              <BarChart2 size={28} />
              {mode === 'group' ? `${groupName} Analytics` : 'Personal Analytics'}
            </h1>
            <p>{filteredExpenses.length} transactions analyzed</p>
          </div>
        </div>
        <div className="exp-analytics-header-right">
          <select 
            className="exp-analytics-time-select"
            value={timeRange}
            onChange={(e) => setTimeRange(e.target.value)}
          >
            <option value="week">This Week</option>
            <option value="month">This Month</option>
            <option value="quarter">This Quarter</option>
            <option value="year">This Year</option>
            <option value="all">All Time</option>
          </select>
          <button 
            className="exp-analytics-export-btn"
            onClick={onExportPDF}
          >
            <Download size={18} />
            Export PDF
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="exp-analytics-summary">
        {/* Total Spent Card */}
        <div className="exp-analytics-card">
          <div className="exp-analytics-card-top">
            <span className="exp-analytics-card-label">TOTAL SPENT</span>
            <DollarSign size={20} className="exp-analytics-card-icon-simple" />
          </div>
          <div className="exp-analytics-card-value-large">{formatCurrency(stats.total)}</div>
          <div className="exp-analytics-card-metric">
            <span className={monthComparison.change >= 0 ? 'metric-positive' : 'metric-negative'}>
              {monthComparison.change >= 0 ? '↑' : '↓'} {Math.abs(monthComparison.change).toFixed(1)}%
            </span>
            <span className="metric-label">vs last month</span>
          </div>
        </div>
        
        {/* Monthly Average Card */}
        <div className="exp-analytics-card">
          <div className="exp-analytics-card-top">
            <span className="exp-analytics-card-label">MONTHLY AVG</span>
            <Calendar size={20} className="exp-analytics-card-icon-simple" />
          </div>
          <div className="exp-analytics-card-value-large">{formatCurrency(stats.monthlyAvg)}</div>
          <div className="exp-analytics-card-metric">
            <span className={monthComparison.change >= 0 ? 'metric-positive' : 'metric-negative'}>
              {monthComparison.change >= 0 ? '↑' : '↓'} {Math.abs(monthComparison.change).toFixed(1)}%
            </span>
            <span className="metric-label">vs last month</span>
          </div>
        </div>
        
        {/* Transactions Card */}
        <div className="exp-analytics-card">
          <div className="exp-analytics-card-top">
            <span className="exp-analytics-card-label">TRANSACTIONS</span>
            <FileText size={20} className="exp-analytics-card-icon-simple" />
          </div>
          <div className="exp-analytics-card-value-large">{stats.count}</div>
          <div className="exp-analytics-card-metric">
            <span className="metric-info">{filteredExpenses.length} in this period</span>
          </div>
        </div>
        
        {/* Spend Velocity Card */}
        <div className="exp-analytics-card">
          <div className="exp-analytics-card-top">
            <span className="exp-analytics-card-label">SPEND VELOCITY</span>
            <TrendingDown size={20} className="exp-analytics-card-icon-simple metric-negative" />
          </div>
          <div className="exp-analytics-card-value-large">{weekComparison.change >= 0 ? '+' : ''}{weekComparison.change.toFixed(1)}%</div>
          <div className="exp-analytics-card-metric">
            <span className={weekComparison.change > 0 ? 'metric-negative' : 'metric-positive'}>{weekComparison.change > 0 ? 'Spending increased' : weekComparison.change < 0 ? 'Spending decreased' : 'No change'}</span>
            <span className="metric-label">vs last week</span>
          </div>
        </div>
      </div>

      {/* Charts Section */}
      <div className="exp-analytics-charts">
        {/* Spending Trend */}
        <div className="exp-analytics-chart-container exp-analytics-chart-large">
          <h3>
            <TrendingUp size={20} />
            Spending Trend
          </h3>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={dailySpending}>
              <defs>
                <linearGradient id="colorAmount" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#667eea" stopOpacity={0.8}/>
                  <stop offset="95%" stopColor="#667eea" stopOpacity={0.1}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="date" stroke="#6b7280" fontSize={12} />
              <YAxis stroke="#6b7280" fontSize={12} tickFormatter={formatCurrency} />
              <Tooltip content={<CustomTooltip />} />
              <Area 
                type="monotone" 
                dataKey="amount" 
                stroke="#667eea" 
                fillOpacity={1} 
                fill="url(#colorAmount)" 
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>

       

        {/* Monthly Comparison */}
        <div className="exp-analytics-chart-container exp-analytics-chart-medium">
          <h3>
            <BarChart2 size={20} />
            Monthly Comparison
          </h3>
          {monthlyTrend.length > 0 ? (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={monthlyTrend}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis dataKey="month" stroke="#6b7280" fontSize={12} />
                <YAxis stroke="#6b7280" fontSize={12} tickFormatter={formatCurrency} />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="amount" fill="#667eea" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="exp-analytics-empty">No data available</div>
          )}
        </div>

       
      </div>

      {/* Category Legend */}
      <div className="exp-analytics-category-legend">
        <h3>Category Breakdown</h3>
        <div className="exp-analytics-category-grid">
          {categoryData.map((cat, index) => (
            <div key={cat.name} className="exp-analytics-category-item">
              <div 
                className="exp-analytics-category-color" 
                style={{ backgroundColor: cat.color }}
              />
              <div className="exp-analytics-category-info">
                <span className="exp-analytics-category-name">{cat.name}</span>
                <span className="exp-analytics-category-amount">{formatCurrency(cat.value)}</span>
              </div>
              <span className="exp-analytics-category-percent">
                {(stats.total > 0 ? (cat.value / stats.total) * 100 : 0).toFixed(1)}%
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Top Expenses */}
      <div className="exp-analytics-top-expenses">
        <h3>
          <TrendingUp size={20} />
          Top Expenses
        </h3>
        <div className="exp-analytics-top-list">
          {topExpenses.map((exp, index) => (
            <div key={exp.id || exp.expense_id || index} className="exp-analytics-top-item">
              <div className="exp-analytics-top-rank">#{index + 1}</div>
              <div className="exp-analytics-top-info">
                <span className="exp-analytics-top-desc">{exp.description}</span>
                <span className="exp-analytics-top-date">
                  {formatDateLocal(new Date(exp.expense_date || exp.date || exp.created_at), { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>
              <div className="exp-analytics-top-category">
                <span 
                  className="exp-analytics-category-badge"
                  style={{ backgroundColor: CATEGORY_COLORS[exp.category] || '#667eea' }}
                >
                  {exp.category || 'Other'}
                </span>
              </div>
              <div className="exp-analytics-top-amount">
                {formatCurrency(exp.amount)}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Balance Summary (Group Mode) */}
      {mode === 'group' && balances.length > 0 && (
        <div className="exp-analytics-balances">
          <h3>
            <Users size={20} />
            Current Balances
          </h3>
          <div className="exp-analytics-balance-grid">
            {balances.map((bal, index) => {
              const balance = parseFloat(bal.balance || bal.net_balance || 0);
              const isPositive = balance > 0;
              return (
                <div 
                  key={bal.user_id || index} 
                  className={`exp-analytics-balance-item ${isPositive ? 'positive' : 'negative'}`}
                >
                  <span className="exp-analytics-balance-name">
                    {bal.display_name || bal.user?.display_name || 'Member'}
                  </span>
                  <span className={`exp-analytics-balance-amount ${isPositive ? 'positive' : 'negative'}`}>
                    {isPositive ? '+' : ''}{formatCurrency(balance)}
                  </span>
                  <span className="exp-analytics-balance-status">
                    {isPositive ? 'is owed' : 'owes'}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};

export default ExpenseAnalytics;
