from flask import Blueprint, request, jsonify
from app import db, limiter

from models.gamer import Gamer
from models.video import Video

from datetime import datetime
from util import wraps

import json as Json

videoreward = Blueprint('/videoreward', __name__)
limiter.limit("300 per minute")(videoreward)

@videoreward.route("/claim", methods=["POST"])
@wraps.auth_required
@wraps.crc_required
def claim():
    json = request.json
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

    