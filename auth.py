from functools import wraps
from flask import session, redirect


def login_requerido(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user' not in session:
            return redirect('/login')
        return f(*args, **kwargs)
    return wrapper


def rol_requerido(roles):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if 'user' not in session:
                return redirect('/login')
            if session.get('rol') not in roles:
                return "Acceso restringido", 403
            return f(*args, **kwargs)
        return wrapper
    return decorator