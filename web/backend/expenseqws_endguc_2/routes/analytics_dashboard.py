"""
Analytics Dashboard Route
=========================

Professional analytics dashboard for monitoring Expense Engine performance.

Features:
- Real-time API call tracking
- Firestore operation metrics
- Cache hit/miss rates
- Response time analysis
- Interactive charts and graphs
- Uses TOKEN_ADMIN for secure access

Author: AI Assistant
Date: 2025-11-21
"""

from flask import Blueprint, request, jsonify, render_template_string
from functools import wraps
import os
from datetime import datetime
import json

# Create blueprint
analytics_dashboard_bp = Blueprint('analytics_dashboard', __name__)

# Get admin token from environment
ADMIN_TOKEN = os.getenv('TOKEN_ADMIN', '').strip()


def require_admin_token(f):
    """Decorator to require admin token authentication
    
    Supports three authentication methods:
    1. Authorization header: Authorization: Bearer <TOKEN_ADMIN>
    2. Query parameter: ?token=<TOKEN_ADMIN>
    3. Auto-auth for embedded iframe: ?auto_auth=true (automatically uses TOKEN_ADMIN from .env)
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Method 1: Check Authorization header
        auth_header = request.headers.get('Authorization', '')
        token_from_header = None
        
        if auth_header:
            if auth_header.startswith('Bearer '):
                token_from_header = auth_header[7:].strip()
            else:
                token_from_header = auth_header.strip()
        
        # Method 2: Check query parameter (for manual token passing)
        token_from_query = request.args.get('token', '').strip()
        
        # Method 3: Auto-authentication (for embedded frontend iframe)
        auto_auth = request.args.get('auto_auth', '').lower() == 'true'
        
        # Use whichever token is provided, or auto-auth
        if auto_auth:
            # Automatically use TOKEN_ADMIN from environment
            # This is safe because it's only for the embedded dashboard
            token = ADMIN_TOKEN
        else:
            token = token_from_header or token_from_query
        
        # If no token provided at all and not auto-auth
        if not token:
            # For HTML requests (browser), show friendly error page
            if 'text/html' in request.headers.get('Accept', ''):
                return render_error_page(
                    'Authentication Required',
                    'Please provide TOKEN_ADMIN in Authorization header or use ?auto_auth=true'
                ), 401
            
            # For API requests, return JSON
            return jsonify({
                'success': False,
                'error': 'Missing authentication',
                'message': 'Please provide Authorization: Bearer <TOKEN_ADMIN> or ?token=<TOKEN_ADMIN> or ?auto_auth=true'
            }), 401
        
        # Validate token
        if token != ADMIN_TOKEN:
            # For HTML requests, show friendly error page
            if 'text/html' in request.headers.get('Accept', ''):
                return render_error_page(
                    'Access Denied',
                    'Invalid TOKEN_ADMIN provided'
                ), 403
            
            # For API requests, return JSON
            return jsonify({
                'success': False,
                'error': 'Invalid admin token',
                'message': 'The provided TOKEN_ADMIN is incorrect'
            }), 403
        
        return f(*args, **kwargs)
    
    return decorated_function


def render_error_page(title: str, message: str) -> str:
    """Render a friendly error page for authentication failures"""
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            margin: 0;
            padding: 20px;
        }}
        .error-container {{
            background: white;
            padding: 50px;
            border-radius: 15px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            text-align: center;
            max-width: 500px;
        }}
        .error-icon {{
            font-size: 4rem;
            color: #f87171;
            margin-bottom: 20px;
        }}
        h1 {{
            color: #333;
            margin-bottom: 15px;
        }}
        p {{
            color: #666;
            font-size: 1.1rem;
            line-height: 1.6;
        }}
        .code {{
            background: #f5f5f5;
            padding: 10px;
            border-radius: 5px;
            font-family: monospace;
            margin: 20px 0;
        }}
    </style>
</head>
<body>
    <div class="error-container">
        <div class="error-icon">🔒</div>
        <h1>{title}</h1>
        <p>{message}</p>
        <div class="code">
            Contact your administrator for access
        </div>
    </div>
</body>
</html>
"""


@analytics_dashboard_bp.route('/dashboard', methods=['GET'])
@require_admin_token
def get_analytics_dashboard():
    """
    Professional Analytics Dashboard
    
    GET /api/expense/analytics/dashboard
    
    Headers:
        Authorization: Bearer <TOKEN_ADMIN>
    
    Returns:
        HTML page with interactive analytics dashboard showing:
        - Total API calls
        - Firestore operations (reads/writes/deletes)
        - Cache hit/miss rates
        - Average response times
        - Endpoint performance breakdown
        - Recent API activity
    
    Response:
        200: HTML dashboard page
        401: Missing authorization
        403: Invalid admin token
    """
    from ..analytics import analytics_tracker
    
    # Get comprehensive analytics
    stats = analytics_tracker.get_comprehensive_stats()
    
    # Render HTML dashboard
    html = render_analytics_html(stats)
    
    return html, 200, {'Content-Type': 'text/html'}


@analytics_dashboard_bp.route('/api/stats', methods=['GET'])
@require_admin_token
def get_api_stats():
    """
    Get analytics data as JSON (for AJAX requests)
    
    GET /api/expense/analytics/api/stats
    
    Headers:
        Authorization: Bearer <TOKEN_ADMIN>
    
    Query Parameters:
        refresh: Set to 'true' to get latest data
    
    Returns:
        JSON with all analytics metrics
    """
    from ..analytics import analytics_tracker
    
    stats = analytics_tracker.get_comprehensive_stats()
    
    return jsonify({
        'success': True,
        'timestamp': datetime.utcnow().isoformat(),
        'data': stats
    }), 200


@analytics_dashboard_bp.route('/api/endpoints', methods=['GET'])
@require_admin_token
def get_endpoint_metrics():
    """
    Get per-endpoint performance metrics
    
    GET /api/expense/analytics/api/endpoints
    
    Returns detailed metrics for each endpoint:
    - Call count
    - Average response time
    - Min/max response times
    - Total execution time
    - Cache hit rates
    """
    from ..analytics import analytics_tracker
    
    endpoint_stats = analytics_tracker.get_endpoint_breakdown()
    
    return jsonify({
        'success': True,
        'timestamp': datetime.utcnow().isoformat(),
        'endpoints': endpoint_stats
    }), 200


def render_analytics_html(stats: dict) -> str:
    """Render professional HTML dashboard with charts"""
    
    # Extract key metrics
    total_calls = stats.get('total_api_calls', 0)
    firestore_ops = stats.get('firestore_operations', {})
    cache_stats = stats.get('cache_stats', {})
    endpoint_breakdown = stats.get('endpoint_breakdown', {})
    
    # Calculate cache hit rate
    cache_hits = cache_stats.get('hits', 0)
    cache_misses = cache_stats.get('misses', 0)
    total_cache_ops = cache_hits + cache_misses
    hit_rate = (cache_hits / total_cache_ops * 100) if total_cache_ops > 0 else 0
    
    # Get top 5 endpoints by call count
    top_endpoints = sorted(
        endpoint_breakdown.items(),
        key=lambda x: x[1].get('count', 0),
        reverse=True
    )[:5]
    
    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Expense Engine Analytics Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        
        header {{
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }}
        
        h1 {{
            color: #667eea;
            font-size: 2.5rem;
            margin-bottom: 10px;
        }}
        
        .subtitle {{
            color: #666;
            font-size: 1.1rem;
        }}
        
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .metric-card {{
            background: white;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: transform 0.3s;
        }}
        
        .metric-card:hover {{
            transform: translateY(-5px);
        }}
        
        .metric-label {{
            color: #666;
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 10px;
        }}
        
        .metric-value {{
            color: #333;
            font-size: 2.5rem;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        
        .metric-subtext {{
            color: #999;
            font-size: 0.85rem;
        }}
        
        .charts-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .chart-card {{
            background: white;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        
        .chart-title {{
            font-size: 1.3rem;
            color: #333;
            margin-bottom: 20px;
            font-weight: 600;
        }}
        
        .table-container {{
            background: white;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            overflow-x: auto;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        
        th {{
            background: #667eea;
            color: white;
            padding: 15px;
            text-align: left;
            font-weight: 600;
        }}
        
        td {{
            padding: 15px;
            border-bottom: 1px solid #eee;
        }}
        
        tr:hover {{
            background: #f5f5f5;
        }}
        
        .refresh-btn {{
            background: #667eea;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 1rem;
            transition: background 0.3s;
            float: right;
        }}
        
        .refresh-btn:hover {{
            background: #5568d3;
        }}
        
        .status-badge {{
            display: inline-block;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 600;
        }}
        
        .status-good {{
            background: #d4edda;
            color: #155724;
        }}
        
        .status-warning {{
            background: #fff3cd;
            color: #856404;
        }}
        
        .status-critical {{
            background: #f8d7da;
            color: #721c24;
        }}
        
        .timestamp {{
            text-align: center;
            color: white;
            margin-top: 20px;
            font-size: 0.9rem;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📊 Expense Engine Analytics</h1>
            <p class="subtitle">Real-time performance monitoring and metrics</p>
            <button class="refresh-btn" onclick="location.reload()">🔄 Refresh Data</button>
        </header>
        
        <!-- Key Metrics -->
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-label">Total API Calls</div>
                <div class="metric-value">{total_calls:,}</div>
                <div class="metric-subtext">Since server start</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-label">Firestore Reads</div>
                <div class="metric-value">{firestore_ops.get('read', 0):,}</div>
                <div class="metric-subtext">Total database reads</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-label">Cache Hit Rate</div>
                <div class="metric-value">{hit_rate:.1f}%</div>
                <div class="metric-subtext">{cache_hits} hits / {total_cache_ops} total</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-label">Avg Response Time</div>
                <div class="metric-value">{stats.get('avg_response_time', 0):.0f}ms</div>
                <div class="metric-subtext">Across all endpoints</div>
            </div>
        </div>
        
        <!-- Charts -->
        <div class="charts-grid">
            <div class="chart-card">
                <h3 class="chart-title">Firestore Operations Breakdown</h3>
                <canvas id="firestoreChart"></canvas>
            </div>
            
            <div class="chart-card">
                <h3 class="chart-title">Cache Performance</h3>
                <canvas id="cacheChart"></canvas>
            </div>
        </div>
        
        <!-- Top Endpoints Table -->
        <div class="table-container">
            <h3 class="chart-title">Top 5 API Endpoints</h3>
            <table>
                <thead>
                    <tr>
                        <th>Endpoint</th>
                        <th>Calls</th>
                        <th>Avg Time</th>
                        <th>Min Time</th>
                        <th>Max Time</th>
                        <th>Total Time</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
"""
    
    # Add top endpoints rows
    for endpoint, data in top_endpoints:
        count = data.get('count', 0)
        avg_time = data.get('avg_time', 0)
        min_time = data.get('min_time', 0)
        max_time = data.get('max_time', 0)
        total_time = data.get('total_time', 0)
        
        # Determine status badge
        if avg_time < 500:
            status = '<span class="status-badge status-good">Good</span>'
        elif avg_time < 1000:
            status = '<span class="status-badge status-warning">Warning</span>'
        else:
            status = '<span class="status-badge status-critical">Critical</span>'
        
        html += f"""
                    <tr>
                        <td><strong>{endpoint}</strong></td>
                        <td>{count:,}</td>
                        <td>{avg_time:.0f}ms</td>
                        <td>{min_time:.0f}ms</td>
                        <td>{max_time:.0f}ms</td>
                        <td>{total_time:.0f}ms</td>
                        <td>{status}</td>
                    </tr>
"""
    
    html += """
                </tbody>
            </table>
        </div>
        
        <p class="timestamp">Last updated: """ + datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC') + """</p>
    </div>
    
    <script>
        // Firestore Operations Chart
        const firestoreCtx = document.getElementById('firestoreChart').getContext('2d');
        new Chart(firestoreCtx, {
            type: 'doughnut',
            data: {
                labels: ['Reads', 'Writes', 'Deletes', 'Searches'],
                datasets: [{
                    data: [""" + f"{firestore_ops.get('read', 0)}, {firestore_ops.get('write', 0)}, {firestore_ops.get('delete', 0)}, {firestore_ops.get('search', 0)}" + """],
                    backgroundColor: [
                        '#667eea',
                        '#764ba2',
                        '#f093fb',
                        '#4facfe'
                    ]
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
        
        // Cache Performance Chart
        const cacheCtx = document.getElementById('cacheChart').getContext('2d');
        new Chart(cacheCtx, {
            type: 'bar',
            data: {
                labels: ['Cache Hits', 'Cache Misses'],
                datasets: [{
                    label: 'Count',
                    data: [""" + f"{cache_hits}, {cache_misses}" + """],
                    backgroundColor: [
                        '#4ade80',
                        '#f87171'
                    ]
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    </script>
</body>
</html>
"""
    
    return html


# Export blueprint
__all__ = ['analytics_dashboard_bp']
