#! /usr/bin/env python3

import sys, os
from flask import Flask, render_template
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)

@app.route('/')
def index():
    app_name = os.getenv('APP_NAME', 'Work-ID')
    return render_template('index.html', app_name=app_name)

if __name__ == '__main__':
    ssl_cert = os.getenv('SSL_CERT')
    ssl_key = os.getenv('SSL_KEY')    
    ssl_context = None
    if ssl_cert and ssl_key:
        if os.path.exists(os.path.expanduser(ssl_cert)) and os.path.exists(os.path.expanduser(ssl_key)):
            ssl_context = (os.path.expanduser(ssl_cert), os.path.expanduser(ssl_key))
            print(f" * Starting with SSL using cert: {ssl_cert}")
        else:
            print(" * Warning: SSL certificate files specified but not found - starting without SSL")
            if not os.path.exists(os.path.expanduser(ssl_cert)):
                print(f"     Missing certificate file: {ssl_cert}")
            if not os.path.exists(os.path.expanduser(ssl_key)):
                print(f"     Missing key file: {ssl_key}")
    
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('FLASK_PORT', 5000)),
        debug=debug_mode,
        ssl_context=ssl_context
    )
