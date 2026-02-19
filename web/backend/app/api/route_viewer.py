"""
API Route Viewer
Provides a styled HTML / JSON endpoint listing all registered API routes.
"""
from flask import Blueprint, current_app, jsonify, request

route_viewer_bp = Blueprint('route_viewer', __name__)


BLUEPRINT_EMOJI = {
    'expense': '\U0001f4b0',
    'group_planner': '\U0001f4c5',
    'countries': '\U0001f30d',
    'states': '\U0001f5fa\ufe0f',
    'cities': '\U0001f3d9\ufe0f',
    'places': '\U0001f4cd',
    'health': '\u2764\ufe0f',
    'main': '\U0001f3e0',
}

BLUEPRINT_COLORS = {
    'expense': '#e74c3c',
    'group_planner': '#9b59b6',
    'countries': '#3498db',
    'states': '#1abc9c',
    'cities': '#f39c12',
    'places': '#16a085',
    'health': '#27ae60',
}


def _collect_routes():
    """Gather all non-internal routes from the running application."""
    routes = []
    for rule in current_app.url_map.iter_rules():
        if rule.endpoint == 'static' or rule.endpoint.startswith('_'):
            continue

        try:
            view_func = current_app.view_functions.get(rule.endpoint)
            docstring = (view_func.__doc__ or 'No description').strip() if view_func else 'No description'
        except (AttributeError, TypeError):
            docstring = 'No description'

        blueprint = rule.endpoint.split('.')[0] if '.' in rule.endpoint else 'main'

        routes.append({
            'endpoint': rule.endpoint,
            'path': str(rule),
            'methods': sorted(m for m in (rule.methods or []) if m not in ('HEAD', 'OPTIONS')),
            'description': docstring,
            'blueprint': blueprint,
        })

    routes.sort(key=lambda r: r['path'])
    return routes


def _group_by_blueprint(routes):
    grouped = {}
    for route in routes:
        grouped.setdefault(route['blueprint'], []).append(route)
    return grouped


def _render_html(routes, grouped):
    """Build the HTML view of routes."""
    # CSS
    css = """
    body { font-family: 'Segoe UI', Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
    .container { max-width: 1400px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
    h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }
    h2 { color: #34495e; margin-top: 30px; border-left: 4px solid #3498db; padding-left: 10px; }
    .route { background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 5px; border-left: 4px solid #95a5a6; }
    .route:hover { background: #e9ecef; }
    .path { font-family: 'Courier New', monospace; font-weight: bold; color: #2c3e50; font-size: 14px; }
    .methods { display: inline-block; margin-left: 10px; }
    .method { display: inline-block; padding: 3px 8px; margin: 0 3px; border-radius: 3px; font-size: 11px; font-weight: bold; }
    .GET { background: #28a745; color: white; }
    .POST { background: #007bff; color: white; }
    .PUT { background: #ffc107; color: #000; }
    .PATCH { background: #17a2b8; color: white; }
    .DELETE { background: #dc3545; color: white; }
    .description { color: #6c757d; margin-top: 8px; font-size: 13px; line-height: 1.5; }
    .endpoint { color: #7f8c8d; font-size: 11px; font-family: monospace; }
    .stats { background: #e3f2fd; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
    .stat { display: inline-block; margin-right: 20px; }
    .stat-label { color: #666; font-size: 12px; }
    .stat-value { font-weight: bold; font-size: 18px; color: #1976d2; }
    """

    # Per-blueprint colour classes
    for bp, color in BLUEPRINT_COLORS.items():
        css += f"\n    .blueprint-{bp} {{ border-left-color: {color}; }}"

    # Header
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>TripRaft API Routes</title>
    <style>{css}
    </style>
</head>
<body>
    <div class="container">
        <h1>TripRaft API Routes</h1>
        <div class="stats">
            <div class="stat">
                <div class="stat-label">Total Endpoints</div>
                <div class="stat-value">{len(routes)}</div>
            </div>
            <div class="stat">
                <div class="stat-label">Blueprints</div>
                <div class="stat-value">{len(grouped)}</div>
            </div>
        </div>
"""

    for blueprint, bp_routes in sorted(grouped.items()):
        emoji = BLUEPRINT_EMOJI.get(blueprint, '\U0001f4e6')
        title = blueprint.replace('_', ' ').title()
        html += f'        <h2>{emoji} {title} ({len(bp_routes)} routes)</h2>\n'

        for route in bp_routes:
            methods_html = ''.join(f'<span class="method {m}">{m}</span>' for m in route['methods'])
            html += f"""        <div class="route blueprint-{blueprint}">
            <div class="path">{route['path']}</div>
            <div class="methods">{methods_html}</div>
            <div class="description">{route['description']}</div>
            <div class="endpoint">Endpoint: {route['endpoint']}</div>
        </div>
"""

    html += """    </div>
</body>
</html>
"""
    return html


@route_viewer_bp.route('/api/routes', methods=['GET'])
def list_routes():
    """List all API routes with methods and descriptions"""
    routes = _collect_routes()
    grouped = _group_by_blueprint(routes)

    if 'text/html' in request.headers.get('Accept', ''):
        return _render_html(routes, grouped)

    return jsonify({
        'total_routes': len(routes),
        'blueprints': list(grouped.keys()),
        'routes': grouped,
    }), 200
