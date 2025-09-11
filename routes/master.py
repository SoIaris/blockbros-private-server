from flask import Blueprint, request, jsonify

from datetime import datetime
import extensions
import json
from util import authentication as auth

master = Blueprint("master", __name__)

from app import limiter
limiter.limit("300 per minute")(master)

@master.route("/update", methods=["POST"])
def update():
    json = request.json
    try:
        _, token = request.headers["authorization"].split(":")
        crc = extensions.jsonToCrc(extensions.sortStringify(json), token)
        if crc != request.headers["Crc"]:
            return jsonify({}), 400
    except Exception as e:
        print(f"login error: {e}")
        return jsonify({}), 400 

    return jsonify({
        'success': True, 
        'result': {}, 
        'updated': {}, 
        'timestamp': round(datetime.timestamp(datetime.now()))
    })