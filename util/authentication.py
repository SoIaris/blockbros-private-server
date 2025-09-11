from flask import jsonify, request

from functools import wraps
from models.gamer import Gamer
from app import db

def check_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            id, token = request.headers["Authorization"].split(":")
            gamer: Gamer = Gamer.query.filter_by(id=id).first()

            if not gamer:
                return jsonify({"reason": "missing_gamer"}), 400

            if gamer.token != token:
                return jsonify({"reason": "token_mismatch"}), 400

        except Exception as e:
            print(e)
            return 500
        
        return f(*args, **kwargs)
    
    return decorated