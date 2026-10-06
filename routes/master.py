from flask import Blueprint, request, jsonify

import extensions
import json as Json
import gzip

from datetime import datetime
from flask import Response
from util import authentication as auth

master = Blueprint("master", __name__)

from app import limiter
limiter.limit("300 per minute")(master)

# i think this is disabled in actual BlockBros i dont know so i had to go off of src.js
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

    master = extensions.get_master()

    if int(request.headers.get("Master-Version")) == master["version"]:
        return jsonify({
            'success': True, 
            'result': {},
            "updated": {},
            "timestamp": round(datetime.timestamp(datetime.now()))
        })
    
    # flask-compress doesnt compress non 2xx error codes so we do it like a gangsta
    return Response(gzip.compress(Json.dumps({
        'master': master
    }).encode()), status=409, mimetype="application/json", headers={"Content-Encoding": "gzip"})