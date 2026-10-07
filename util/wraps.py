from flask import jsonify, request
from app import db

from models.gamer import Gamer

from functools import wraps

import extensions
import hashlib

def jsonToCrc(table: str, token: str):
    string = table
    if token != "undefined":
        string += token

    crc = hashlib.md5((string).encode()).hexdigest()
    return crc

def crc_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            id, token = request.headers["authorization"].split(":")
            crc = jsonToCrc(extensions.sortStringify(request.json), token)
            if crc != request.headers["Crc"]:
                return jsonify({}), 400
            
        except Exception as e:
            print(f"crc checking error: {e}")
            return jsonify({}), 400  

        return f(*args, **kwargs)
    
    return decorated

def auth_required(f):
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