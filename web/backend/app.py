from flask import Flask, jsonify
from global_config import DEFAULT_API_PREFIX, APP_NAME
from web.backend.cache.redis_client import redis_client 
from web.backend.config import Config

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    redis_client.init_app(app)

    # --- Use the global constant ---
    @app.route(f'{DEFAULT_API_PREFIX}/health')
    def health():
        return jsonify({"status": "ok"})

    @app.route(f'{DEFAULT_API_PREFIX}/config')
    def get_config():
        return jsonify({
            'APP_NAME': APP_NAME,
            'API_PREFIX': DEFAULT_API_PREFIX,
        })

    try:
        from web.backend.auth import auth_bp
        # --- Register auth blueprint at /api/auth ---
        app.register_blueprint(auth_bp, url_prefix=f'{DEFAULT_API_PREFIX}/auth')
    except Exception as e:
        print(f"Error registering blueprint: {e}")
        pass

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)
