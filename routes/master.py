from flask import Blueprint, request, jsonify, Response
from app import limiter

from util import wraps
from datetime import datetime

import extensions
import gzip
import json as Json

master = Blueprint("master", __name__)
limiter.limit("300 per minute")(master)

# i think this is disabled in actual BlockBros i dont know so i had to go off of src.js
@master.route("/update", methods=["POST"])
@wraps.crc_required
def update():
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