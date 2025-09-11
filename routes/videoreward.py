from flask import Blueprint, request, jsonify
from app import db

from datetime import datetime
from models.gamer import Gamer
from models.video import Video

import json as Json
import extensions
from util import authentication as auth

videoreward = Blueprint('/videoreward', __name__)

from app import limiter
limiter.limit("300 per minute")(videoreward)

@videoreward.route("/claim", methods=["POST"])
@auth.check_auth
def claim():
    json = request.json

    try:
        _, token = request.headers["authorization"].split(":")
        crc = extensions.jsonToCrc(extensions.sortStringify(json), token)
        if crc != request.headers["Crc"]:
            return jsonify({}), 400
    except Exception as e:
        print(f"login error: {e}")
        return jsonify({}), 400 
    
    id, token = request.headers["authorization"].split(":")
    gamer: Gamer = Gamer.query.filter_by(id=id).first()

    video = json.get("video")
    _id, _token = video.split(":")

    video: Video = Video.query.filter_by(id=_id, token=_token).first()
    if not video:
        return jsonify({
            "reason": "validation_exception"
        }), 400
    
    if video.creator != gamer.id:
        return jsonify({
            "reason": "validation_exception"
        }), 400
    
    db.session.delete(video)
    gamer.gem += video.gem
    
    db.session.commit()
    
    return jsonify({
        "success": True,
        "result": {},
        "updated": {
            "gamer": {
                "adminLevel": gamer.adminLevel,
                "avatar": gamer.avatar,
                "builderPt": gamer.builderPt,
                "campaigns": gamer.campaigns,
                "channel": gamer.channel,
                "clearCount": gamer.clearCount,
                "commentableAt": gamer.commentableAt,
                "country": gamer.country,
                "createdAt": gamer.createdAt,
                "emblemCount": gamer.emblemCount,
                "followerCount": gamer.followerCount,
                "gamerId": gamer.gamer_id,
                "gem": gamer.gem,
                "hasUnfinishedIAP": gamer.hasUnfinishedIAP,
                "id": gamer.id,
                "inventory": Json.loads(gamer.inventory),
                "lang": gamer.lang,
                **({"homeLevel": gamer.homeLevel} if gamer.homeLevel is not None else {}),
                "lastLoginAt": gamer.lastLoginAt,
                "levelCount": gamer.levelCount,
                "maxVideoId": gamer.maxVideoId,
                "nameVersion": gamer.nameVersion,
                "nickname": gamer.nickname,
                "playerPt": gamer.playerPt,
                "researches": gamer.researches,
                "visibleAt": gamer.visibleAt
            }
        },
        "timestamp": round(datetime.timestamp(datetime.now())) 
    })

    