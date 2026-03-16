from functools import wraps
from flask import session, jsonify, redirect, request
from .models import SuperadminUsuario

def require_superadmin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('superadmin_id'):
            if request.path.startswith('/api/'):
                return jsonify({'error': 'unauthorized'}), 401
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated
