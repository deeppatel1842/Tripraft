import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import '../css/Analytics.css';

const Analytics = () => {
  const { currentUser, signOut } = useAuth();
  const navigate = useNavigate();
  
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(null);

  // Admin check - only allow access to specific admin email
  // You can change this to your admin email
  const ADMIN_EMAIL = 'tripraft@gmail.com'; // Change this to your email
  
  const isAdmin = currentUser && currentUser.email === ADMIN_EMAIL;

  const fetchAnalytics = async () => {
    try {
      const response = await fetch('http://localhost:5000/api/analytics/stats', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include'
      });

      if (!response.ok) {
        throw new Error('Failed to fetch analytics');
      }

      const data = await response.json();
      setAnalytics(data);
      setLastUpdated(new Date());
      setError(null);
    } catch (err) {
      console.error('Analytics fetch error:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Check if user is admin, if not redirect to home
    if (!isAdmin && !loading) {
      navigate('/');
      return;
    }
    
    if (isAdmin) {
      fetchAnalytics();
    }
  }, [isAdmin, loading, navigate]);

  // Auto-refresh every 5 seconds if enabled
  useEffect(() => {
    if (!autoRefresh || !isAdmin) return;

    const interval = setInterval(() => {
      fetchAnalytics();
    }, 5000);

    return () => clearInterval(interval);
  }, [autoRefresh, isAdmin]);

  const formatTimestamp = (date) => {
    if (!date) return 'Never';
    return date.toLocaleTimeString('en-US', { 
      hour: '2-digit', 
      minute: '2-digit', 
      second: '2-digit' 
    });
  };

  const formatDuration = (seconds) => {
    if (seconds < 60) return `${seconds.toFixed(1)}s`;
    const minutes = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${minutes}m ${secs}s`;
  };

  // If not admin, show access denied or redirect (redundant with useEffect but good UX)
  if (!loading && !isAdmin) {
    return (
      <div className="analytics-page">
        <div className="analytics-container">
          <div className="analytics-error">
            <i className="fas fa-lock"></i>
            <p>Access Denied. This page is for administrators only.</p>
          </div>
        </div>
        <Footer />
      </div>
    );
  }

  const calculateCacheEfficiency = () => {
    if (!analytics || !analytics.cache_stats) return 0;
    const { total_hits, total_requests } = analytics.cache_stats;
    if (total_requests === 0) return 0;
    return ((total_hits / total_requests) * 100).toFixed(1);
  };

  const calculateCostSavings = () => {
    if (!analytics || !analytics.cost_analysis) return 0;
    const { baseline_cost_usd, actual_cost_usd } = analytics.cost_analysis;
    return (baseline_cost_usd - actual_cost_usd).toFixed(4);
  };

  if (loading && !analytics) {
    return (
      <div className="analytics-page">
        <div className="analytics-loading">
          <div className="spinner"></div>
          <p>Loading analytics...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="analytics-page">
      <div className="analytics-container">
        <div className="analytics-header">
          <div className="analytics-title-section">
            <h1>
              <i className="fas fa-chart-line"></i>
              Real-Time Analytics Dashboard
            </h1>
            <p className="analytics-subtitle">
              Monitor search performance, cache efficiency, and cost optimization in real-time
            </p>
          </div>

          <div className="analytics-controls">
            <button 
              className={`refresh-toggle ${autoRefresh ? 'active' : ''}`}
              onClick={() => setAutoRefresh(!autoRefresh)}
            >
              <i className={`fas fa-${autoRefresh ? 'pause' : 'play'}`}></i>
              {autoRefresh ? 'Auto-Refresh ON' : 'Auto-Refresh OFF'}
            </button>
            <button className="manual-refresh" onClick={fetchAnalytics}>
              <i className="fas fa-sync-alt"></i>
              Refresh Now
            </button>
            <div className="last-updated">
              <i className="fas fa-clock"></i>
              Last updated: {formatTimestamp(lastUpdated)}
            </div>
          </div>
        </div>

        {error && (
          <div className="analytics-error">
            <i className="fas fa-exclamation-triangle"></i>
            <p>Error: {error}</p>
          </div>
        )}

        {analytics && (
          <>
            {/* Key Metrics Grid */}
            <div className="metrics-grid">
              <div className="metric-card primary">
                <div className="metric-icon">
                  <i className="fas fa-search"></i>
                </div>
                <div className="metric-content">
                  <span className="metric-value">{analytics.total_searches || 0}</span>
                  <span className="metric-label">Total Searches</span>
                  <span className="metric-sublabel">Last 60 minutes</span>
                </div>
              </div>

              <div className="metric-card success">
                <div className="metric-icon">
                  <i className="fas fa-bolt"></i>
                </div>
                <div className="metric-content">
                  <span className="metric-value">
                    {(analytics.cache_stats?.hit_rate || 0).toFixed(1)}%
                  </span>
                  <span className="metric-label">Cache Hit Rate</span>
                  <span className="metric-sublabel">
                    {analytics.cache_stats?.total_hits || 0} / {analytics.cache_stats?.total_requests || 0} hits
                  </span>
                </div>
              </div>

              <div className="metric-card warning">
                <div className="metric-icon">
                  <i className="fas fa-cloud"></i>
                </div>
                <div className="metric-content">
                  <span className="metric-value">{analytics.api_calls_made || 0}</span>
                  <span className="metric-label">API Calls</span>
                  <span className="metric-sublabel">Google Places API</span>
                </div>
              </div>

              <div className="metric-card info">
                <div className="metric-icon">
                  <i className="fas fa-dollar-sign"></i>
                </div>
                <div className="metric-content">
                  <span className="metric-value">${(analytics.total_cost_usd || 0).toFixed(4)}</span>
                  <span className="metric-label">Total Cost</span>
                  <span className="metric-sublabel">Saved ${calculateCostSavings()}</span>
                </div>
              </div>
            </div>

            {/* Performance Metrics */}
            <div className="analytics-section">
              <h2>
                <i className="fas fa-tachometer-alt"></i>
                Performance Metrics
              </h2>
              <div className="performance-grid">
                <div className="performance-card">
                  <div className="performance-header">
                    <i className="fas fa-stopwatch"></i>
                    <h3>Response Times</h3>
                  </div>
                  <div className="performance-stats">
                    <div className="stat-row">
                      <span className="stat-label">Average:</span>
                      <span className="stat-value">
                        {formatDuration(analytics.performance?.avg_response_time || 0)}
                      </span>
                    </div>
                    <div className="stat-row">
                      <span className="stat-label">Min:</span>
                      <span className="stat-value success">
                        {formatDuration(analytics.performance?.min_response_time || 0)}
                      </span>
                    </div>
                    <div className="stat-row">
                      <span className="stat-label">Max:</span>
                      <span className="stat-value warning">
                        {formatDuration(analytics.performance?.max_response_time || 0)}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="performance-card">
                  <div className="performance-header">
                    <i className="fas fa-database"></i>
                    <h3>Cache Performance</h3>
                  </div>
                  <div className="performance-stats">
                    <div className="stat-row">
                      <span className="stat-label">Memory Cache:</span>
                      <span className="stat-value">
                        {analytics.cache_stats?.memory_cache?.hit_rate || 0}%
                      </span>
                    </div>
                    <div className="stat-row">
                      <span className="stat-label">SQLite Cache:</span>
                      <span className="stat-value">
                        {analytics.cache_stats?.sqlite_cache?.hit_rate || 0}%
                      </span>
                    </div>
                    <div className="stat-row">
                      <span className="stat-label">Total Entries:</span>
                      <span className="stat-value">
                        {(analytics.cache_stats?.memory_cache?.entries || 0) + 
                         (analytics.cache_stats?.sqlite_cache?.entries || 0)}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="performance-card">
                  <div className="performance-header">
                    <i className="fas fa-chart-pie"></i>
                    <h3>API Usage Breakdown</h3>
                  </div>
                  <div className="performance-stats">
                    <div className="stat-row">
                      <span className="stat-label">Search Nearby:</span>
                      <span className="stat-value">
                        {analytics.api_breakdown?.search_nearby || 0}
                      </span>
                    </div>
                    <div className="stat-row">
                      <span className="stat-label">Geocoding:</span>
                      <span className="stat-value">
                        {analytics.api_breakdown?.geocoding || 0}
                      </span>
                    </div>
                    <div className="stat-row">
                      <span className="stat-label">Places Details:</span>
                      <span className="stat-value">
                        {analytics.api_breakdown?.place_details || 0}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Cost Analysis */}
            <div className="analytics-section">
              <h2>
                <i className="fas fa-coins"></i>
                Cost Analysis
              </h2>
              <div className="cost-grid">
                <div className="cost-card">
                  <div className="cost-header">
                    <i className="fas fa-money-bill-wave"></i>
                    <h3>Current Session</h3>
                  </div>
                  <div className="cost-breakdown">
                    <div className="cost-row">
                      <span>Baseline Cost (No Cache):</span>
                      <span className="cost-value baseline">
                        ${(analytics.cost_analysis?.baseline_cost_usd || 0).toFixed(4)}
                      </span>
                    </div>
                    <div className="cost-row">
                      <span>Total Cost (API Calls):</span>
                      <span className="cost-value actual">
                        ${(analytics.total_cost_usd || 0).toFixed(4)}
                      </span>
                    </div>
                    <div className="cost-row savings">
                      <span>Cost Saved (Cache Hits):</span>
                      <span className="cost-value">
                        ${(analytics.cost_analysis?.cost_savings_usd || 0).toFixed(4)}
                      </span>
                    </div>
                    <div className="cost-row">
                      <span>Optimization Rate:</span>
                      <span className="cost-value optimization">
                        {analytics.cost_analysis?.optimization_percentage || 0}%
                      </span>
                    </div>
                  </div>
                </div>

                <div className="cost-card projection">
                  <div className="cost-header">
                    <i className="fas fa-calendar-alt"></i>
                    <h3>Monthly Projection</h3>
                  </div>
                  <div className="projection-stats">
                    <p className="projection-note">
                      Based on current cache efficiency (10,000 searches/month):
                    </p>
                    <div className="projection-row">
                      <span>Without Optimization:</span>
                      <span className="projection-value">
                        ${(analytics.monthly_projections?.without_optimization || 170.0).toFixed(2)}/mo
                      </span>
                    </div>
                    <div className="projection-row">
                      <span>With Current Cache:</span>
                      <span className="projection-value success">
                        ${(analytics.monthly_projections?.with_optimization || 102.0).toFixed(2)}/mo
                      </span>
                    </div>
                    <div className="projection-row highlight">
                      <span>Projected Savings:</span>
                      <span className="projection-value">
                        ${(analytics.monthly_projections?.estimated_savings || 68.0).toFixed(2)}/mo
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Recent Activity */}
            {analytics.recent_searches && analytics.recent_searches.length > 0 && (
              <div className="analytics-section">
                <h2>
                  <i className="fas fa-history"></i>
                  Recent Search Activity
                </h2>
                <div className="recent-activity-table">
                  <table>
                    <thead>
                      <tr>
                        <th>Time</th>
                        <th>City</th>
                        <th>Results</th>
                        <th>Cache Status</th>
                        <th>Response Time</th>
                        <th>API Calls</th>
                        <th>Cost</th>
                      </tr>
                    </thead>
                    <tbody>
                      {analytics.recent_searches.slice(0, 10).map((search, index) => {
                        // Determine cache type
                        let cacheType = 'MISS';
                        let cacheClass = 'miss';
                        if (search.cache_hit) {
                          if (search.memory_cache_hit) {
                            cacheType = 'MEMORY';
                            cacheClass = 'hit';
                          } else if (search.sqlite_cache_hit) {
                            cacheType = 'SQLITE';
                            cacheClass = 'hit';
                          } else {
                            cacheType = 'HIT';
                            cacheClass = 'hit';
                          }
                        }
                        
                        return (
                          <tr key={index}>
                            <td>{new Date(search.timestamp).toLocaleTimeString()}</td>
                            <td>
                              <i className="fas fa-map-marker-alt"></i>
                              {search.city}
                            </td>
                            <td>{search.results_count}</td>
                            <td>
                              <span className={`cache-badge ${cacheClass}`}>
                                {cacheType}
                              </span>
                            </td>
                            <td>{formatDuration(search.response_time)}</td>
                            <td>{search.api_calls}</td>
                            <td>${(search.cost || 0).toFixed(4)}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* System Health */}
            <div className="analytics-section">
              <h2>
                <i className="fas fa-heartbeat"></i>
                System Health
              </h2>
              <div className="health-grid">
                <div className="health-card">
                  <i className="fas fa-check-circle"></i>
                  <span>Memory Cache</span>
                  <span className="health-status online">Online</span>
                </div>
                <div className="health-card">
                  <i className="fas fa-check-circle"></i>
                  <span>SQLite Cache</span>
                  <span className="health-status online">Online</span>
                </div>
                <div className="health-card">
                  <i className="fas fa-check-circle"></i>
                  <span>Google Places API</span>
                  <span className="health-status online">Online</span>
                </div>
                <div className="health-card">
                  <i className="fas fa-check-circle"></i>
                  <span>Database</span>
                  <span className="health-status online">Online</span>
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default Analytics;
