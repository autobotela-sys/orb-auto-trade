"""
Main entry point for Railway deployment
Railway uses gunicorn with main:app by default
"""
from app import app

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
