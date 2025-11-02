from functools import wraps
from flask import Flask, request, jsonify
import jwt
from datetime import datetime, timedelta


SECRET_KEY = "your-jwt-secret-key"

def generate_token(username):
    payload = {
        "username": username,
        "exp": datetime.utcnow() + timedelta(hours=1)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def require_jwt(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization")
        if not token or not token.startswith("Bearer "):
            return jsonify({"error": "Token required"}), 401
        
        try:
            payload = jwt.decode(token.split(" ")[1], SECRET_KEY, algorithms=["HS256"])
            request.current_user = payload["username"]
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401
        
        return f(*args, **kwargs)
    return decorated