from flask import Blueprint, request, jsonify
from sqlalchemy import func

from models.gamer import Gamer
from models.emblem import Emblem
from models.comment import Comment

from datetime import datetime
from app import db
import hashlib
import json as Json

import extensions as extensions
from util import authentication as auth
from app import limiter

gamerr = Blueprint("gamer", __name__)
limiter.limit("300 per minute")(gamerr)

@gamerr.route("/follow/put", methods=["POST"])
@auth.check_auth
def follow():
    json_data = request.json
    try:
        _, token = request.headers["authorization"].split(":")
        crc = extensions.jsonToCrc(extensions.sortStringify(json_data), token)
        if crc != request.headers["Crc"]:
            return jsonify({}), 400
    except Exception as e:
        print(f"login error: {e}")
        return jsonify({}), 400 
    
    id, token = request.headers["authorization"].split(":")

    gamer: Gamer = Gamer.query.filter_by(id=id, token=token).first()

    action = json_data.get("action")
    gamer_id = json_data.get("gamer_id")

    targetGamer: Gamer = Gamer.query.filter_by(id=gamer_id).first()
    if not targetGamer:
        return jsonify({
            'reason': 'validation_exception'
        }), 400
    
    follows = Json.loads(gamer.follows)
    targetfollows = Json.loads(targetGamer.follows)

    if action == "follow" and targetGamer.id not in follows["follows"] and gamer.id not in targetfollows["follows"]:
        follows["follows"].append(targetGamer.id)
        targetfollows["followers"].append(gamer.id)
    elif action == "unfollow":
        follows["follows"].remove(targetGamer.id)
        targetfollows["followers"].remove(gamer.id)
    elif action == "block" and targetGamer.id not in follows["blocked"]:
        follows["blocked"].append(targetGamer.id)
        targetfollows["blocks"].append(gamer.id)
    elif action == "unblock":
        follows["blocked"].remove(targetGamer.id)
        targetfollows["blocks"].remove(gamer.id)

    gamer.follows = Json.dumps(follows)
    targetGamer.follows = Json.dumps(targetfollows)
    db.session.commit()

    return jsonify({
        "success": True,
        "result": {},
        "updated": {
            'follows': follows
        },
        "timestamp": round(datetime.timestamp(datetime.now()))
    })

@gamerr.route("/list", methods=["POST"])
@auth.check_auth
def list():
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

    gamer: Gamer = Gamer.query.filter_by(id=id, token=token).first()
    
    index = json.get("index")
    type = json.get('type')
    cursor = json.get("cursor")

    base_query = db.session.query(Gamer)

    if type == "topPlayer":
        base_query = base_query.order_by(Gamer.playerPt.desc())
    elif type == "topBuilder":
        base_query = base_query.order_by(Gamer.builderPt.desc())
    elif type == "active":
        base_query = base_query.order_by(Gamer.lastLoginAt.desc())
    elif type == "follows":
        follows = Json.loads(gamer.follows)
        base_query = base_query.filter(Gamer.id.in_(follows["follows"]))
    elif type == "followers":
        follows = Json.loads(gamer.follows)
        base_query = base_query.filter(Gamer.id.in_(follows["followers"]))

    if cursor:
        position = db.session.query(func.count(Gamer.id)).scalar()
        pagination = base_query.paginate(page=(position // 10) + 1, per_page=10, error_out=False)
    else:
        pagination = base_query.paginate(page=1, per_page=10, error_out=False)

    gamers = pagination.items

    items = []
    for gamer in gamers:
        items.append({
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
        })

    return jsonify({
        "success": True,
        "result": {
            'all_loaded': not pagination.has_next,
            **({'cursor': str(gamers[-1].id)} if pagination.has_next else {}),
            "index": index + len(gamers),
            'items': items,
        },
        "updated": {},
        "timestamp": round(datetime.timestamp(datetime.now()))
    })

@gamerr.route("/claimGift", methods=["POST"])
@auth.check_auth
def claimgift():
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

    gamer: Gamer = Gamer.query.filter_by(id=id, token=token).first()

    gifts = gamer.gifts
    index = json.get("index")
    print(index, gifts)

    if not gifts[index]:
        return jsonify({
            "success": False,
            "result": {},
            "updated": {},
            "timestamp": round(datetime.timestamp(datetime.now()))
        })
    
        
    # {'builderPt': 0, 'desc': 'reward_desc_happynewyear', 'params': {}, 'productId': 0, 'productType': 'gem', 'quantity': 500, 'senderId': 0, 'title': 'reward_title_happynewyear'}, 
    print(gifts[index])

    if gifts[index]["productType"] == "emblem":
        emblem: Emblem = Emblem.query.filter_by(id=gifts[index]["productId"]).first()
        if not emblem:
            return jsonify({
                "success": False,
                "result": {},
                "updated": {},
                "timestamp": round(datetime.timestamp(datetime.now()))
            })

        if gamer.id in emblem.owners:
            return jsonify({
                "success": False,
                "result": {
                    'reason': 'already_has_emblem'
                },
                "updated": {},
                "timestamp": round(datetime.timestamp(datetime.now()))
            })
    
        emblem.owners.append(gamer.id)

        ownsemblems = [emblem for emblem in db.session.query(Emblem).all() if gamer.id in emblem.owners]
        gamer.emblemCount = len(ownsemblems)
    elif gifts[index]["productType"] == "gem":
        gamer.gem += gifts[index]["quantity"]

    if gifts[index]["builderPt"] != 0:
        gamer.builderPt += gifts[index]["builderPt"]

    gifts.pop(index)
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
            },
            "gifts": gamer.gifts
        },
        "timestamp": round(datetime.timestamp(datetime.now()))
    })

@gamerr.route("/channel/set", methods=["POST"])
@auth.check_auth
def channelset():
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

    search = Gamer.query.filter_by(id=id, token=token)
    gamer: Gamer = search.first()
    if not gamer:
        return jsonify({
            "success": False,
            "result": {},
            "updated": {},
            "timestamp": round(datetime.timestamp(datetime.now()))
        })
    
    gamer.channel = json["url"]
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

@gamerr.route("/email", methods=["POST"])
@auth.check_auth
def email():
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
        "success": True,
        "result": {},
        "updated": {},
        "timestamp": round(datetime.timestamp(datetime.now()))
    })

@gamerr.route("/ban", methods=["POST"])
@auth.check_auth
def ban():
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
    gamer: Gamer = Gamer.query.filter_by(id=id, token=token).first()
    if gamer.adminLevel < 2:
        return jsonify({
            "reason": "validation_exception"
        }), 400

    gamer_id = json.get("gamer_id")
    enabled = json.get("enabled")
    print(enabled)

    searchGamer: Gamer = Gamer.query.filter_by(gamer_id=gamer_id).first()
    if not searchGamer:
        return jsonify({
            "success": False,
            "result": {},
            "updated": {},
            "timestamp": round(datetime.timestamp(datetime.now()))
        })
    
    if enabled == 0:
        searchGamer.visibleAt = 0
    else:
        searchGamer.visibleAt = 4102444800

    db.session.commit()
    
    return jsonify({
        "success": True,
        "result": {
            "adminLevel": searchGamer.adminLevel,
            "avatar": searchGamer.avatar,
            "builderPt": searchGamer.builderPt,
            "campaigns": searchGamer.campaigns,
            "channel": searchGamer.channel,
            "clearCount": searchGamer.clearCount,
            "commentableAt": searchGamer.commentableAt,
            "country": searchGamer.country,
            "createdAt": searchGamer.createdAt,
            "emblemCount": searchGamer.emblemCount,
            "followerCount": searchGamer.followerCount,
            "gamerId": searchGamer.gamer_id,
            "gem": searchGamer.gem,
            "hasUnfinishedIAP": searchGamer.hasUnfinishedIAP,
            "id": searchGamer.id,
            "inventory": Json.loads(searchGamer.inventory),
            "lang": searchGamer.lang,
            **({"homeLevel": gamer.homeLevel} if gamer.homeLevel is not None else {}),
            "lastLoginAt": searchGamer.lastLoginAt,
            "levelCount": searchGamer.levelCount,
            "maxVideoId": searchGamer.maxVideoId,
            "nameVersion": searchGamer.nameVersion,
            "nickname": searchGamer.nickname,
            "playerPt": searchGamer.playerPt,
            "researches": searchGamer.researches,
            "visibleAt": searchGamer.visibleAt
        },
        "updated": {},
        "timestamp": round(datetime.timestamp(datetime.now()))
    })

@gamerr.route("/sync", methods=["POST"])
@auth.check_auth
def sync():
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
    gamer: Gamer = Gamer.query.filter_by(id=id, token=token).first()

    batch = json.get("batch")

    query = db.session.query(Comment).order_by(Comment.createdAt.desc())
    comments = query.filter_by(group_key="feed").limit(10).all()

    items = []
    for comment in comments:
        gamerc: Gamer = Gamer.query.filter_by(id=comment.gamer_id).first()
        if not gamerc:
            return jsonify({
                "success": False,
                "result": {},
                "updated": {},
                "timestamp": round(datetime.timestamp(datetime.now()))
            })
        
        items.append({
            "args": comment.args,
            "commentId": comment.commentId,
            "createdAt": comment.createdAt,
            "gamer": {
                "adminLevel": gamer.adminLevel,
                "avatar": gamer.avatar,
                "builderPt": gamer.builderPt,
                "channel": gamer.channel,
                "commentableAt": gamer.commentableAt,
                "country": gamer.country,
                "createdAt": gamer.createdAt,
                "emblemCount": gamer.emblemCount,
                "followerCount": gamer.followerCount,
                "gamerId": gamer.gamer_id,
                **({"homeLevel": gamer.homeLevel} if gamer.homeLevel is not None else {}),
                "id": gamer.id,
                "inventory": Json.loads(gamer.inventory),
                "lastLoginAt": gamer.lastLoginAt,
                "levelCount": gamer.levelCount,
                "nickname": gamer.nickname,
                "playerPt": gamer.playerPt,
                "userId": str(gamer.gamer_id),
                "visibleAt": gamer.visibleAt
            },
            "message": comment.message,
            "type": "plain"
        })

    nextCursor = hashlib.sha1(str(comments[-1].gamer_id).encode('utf-8')).hexdigest() if comments else None

    return jsonify({
        "success": True,
        "result": {},
        "updated": {
            "feeds": {
                'all_loaded': len(comments) < 10,
                'cursor': nextCursor,
                "index": len(comments),
                'items': items,
            },
            "follows": Json.loads(gamer.follows),
            "gifts": gamer.gifts,
            'notifications': sorted(gamer.notifications,key=lambda x: x["updated_at"], reverse=True),
        },
        "timestamp": round(datetime.timestamp(datetime.now()))
    })

@gamerr.route("/get", methods=["POST"])
@auth.check_auth
def get():
    json = request.json

    try:
        _, token = request.headers["authorization"].split(":")
        crc = extensions.jsonToCrc(extensions.sortStringify(json), token)
        if crc != request.headers["Crc"]:
            return jsonify({}), 400
    except Exception as e:
        print(f"login error: {e}")
        return jsonify({}), 400 
    
    gamer: Gamer = Gamer.query.filter_by(gamer_id=json["gamer_id"]).first()
    if not gamer:
        return jsonify({
            "success": False,
            "result": {},
            "updated": {},
            "timestamp": round(datetime.timestamp(datetime.now()))
        })
    
    return jsonify({
        "success": True,
        "result": {
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
        },
        "updated": {},
        "timestamp": round(datetime.timestamp(datetime.now()))
    })

@gamerr.route("/search", methods=["POST"])
@auth.check_auth
def search():
    json = request.json

    try:
        _, token = request.headers["authorization"].split(":")
        crc = extensions.jsonToCrc(extensions.sortStringify(json), token)
        if crc != request.headers["Crc"]:
            return jsonify({}), 400
    except Exception as e:
        print(f"login error: {e}")
        return jsonify({}), 400 
    
    gamer: Gamer = Gamer.query.filter(func.lower(Gamer.nickname) == func.lower(json["nickname"])).first()
    if not gamer:
        return jsonify({
            "result": {},
            "success": False,
            "updated": {},
            "timestamp": round(datetime.timestamp(datetime.now()))
        })

    return jsonify({
        "result": {
            'all_loaded': True,
            "index": 1,
            'items': [
                {
                    "adminLevel": gamer.adminLevel,
                    "avatar": gamer.avatar,
                    "builderPt": gamer.builderPt,
                    "channel": gamer.channel,
                    "commentableAt": gamer.commentableAt,
                    "country": gamer.country,
                    "createdAt": gamer.createdAt,
                    "emblemCount": gamer.emblemCount,
                    "followerCount": gamer.followerCount,
                    "gamerId": gamer.gamer_id,
                    "id": gamer.id,
                    "inventory": Json.loads(gamer.inventory),
                    **({"homeLevel": gamer.homeLevel} if gamer.homeLevel is not None else {}),
                    "lastLoginAt": gamer.lastLoginAt,
                    "levelCount": gamer.levelCount,
                    "nickname": gamer.nickname,
                    "playerPt": gamer.playerPt,
                    "userId": str(gamer.gamer_id),
                    "visibleAt": gamer.visibleAt
                }
            ],
        },
        "success": True,
        "timestamp": round(datetime.timestamp(datetime.now())),
        "updated": {}
    })

@gamerr.route("/warn", methods=["POST"])
@auth.check_auth
def warn():
    json = request.json

    try:
        _, token = request.headers["authorization"].split(":")
        crc = extensions.jsonToCrc(extensions.sortStringify(json), token)
        if crc != request.headers["Crc"]:
            return jsonify({}), 400
    except Exception as e:
        print(f"login error: {e}")
        return jsonify({}), 400 
    
    gamerid = json.get("gamer_id")

    id, token = request.headers["authorization"].split(":")
    selfGamer: Gamer = Gamer.query.filter_by(id=id).first()
    if selfGamer.adminLevel < 1:
        return jsonify({
            "success": False,
            "result": {},
            "updated": {},
            "timestamp": round(datetime.timestamp(datetime.now()))
        })
    
    searchGamer: Gamer = Gamer.query.filter_by(gamer_id=gamerid).first()
    if not searchGamer:
        return jsonify({
            "success": False,
            "result": {},
            "updated": {},
            "timestamp": round(datetime.timestamp(datetime.now()))
        })
    
    searchGamer.commentableAt = datetime.now().timestamp() + json["duration"]
    print(searchGamer.commentableAt)
    db.session.commit()

    return jsonify({
        "success": True,
        "result": {
            "adminLevel": searchGamer.adminLevel,
            "avatar": searchGamer.avatar,
            "builderPt": searchGamer.builderPt,
            "campaigns": searchGamer.campaigns,
            "channel": searchGamer.channel,
            "clearCount": searchGamer.clearCount,
            "commentableAt": searchGamer.commentableAt,
            "country": searchGamer.country,
            "createdAt": searchGamer.createdAt,
            "emblemCount": searchGamer.emblemCount,
            "followerCount": searchGamer.followerCount,
            "gamerId": searchGamer.gamer_id,
            "gem": searchGamer.gem,
            "hasUnfinishedIAP": searchGamer.hasUnfinishedIAP,
            "id": searchGamer.id,
            "inventory": Json.loads(searchGamer.inventory),
            "lang": searchGamer.lang,
            **({"homeLevel": searchGamer.homeLevel} if searchGamer.homeLevel is not None else {}),
            "lastLoginAt": searchGamer.lastLoginAt,
            "levelCount": searchGamer.levelCount,
            "maxVideoId": searchGamer.maxVideoId,
            "nameVersion": searchGamer.nameVersion,
            "nickname": searchGamer.nickname,
            "playerPt": searchGamer.playerPt,
            "researches": searchGamer.researches,
            "visibleAt": searchGamer.visibleAt
        },
        "updated": {},
        "timestamp": round(datetime.timestamp(datetime.now()))
    })

@gamerr.route("/nickname/check", methods=["POST"])
@auth.check_auth
def checknickname():
    json = request.json

    try:
        _, token = request.headers["authorization"].split(":")
        crc = extensions.jsonToCrc(extensions.sortStringify(json), token)
        if crc != request.headers["Crc"]:
            return jsonify({}), 400
    except Exception as e:
        print(f"login error: {e}")
        return jsonify({}), 400 
         
    checkNickname = Gamer.query.filter(func.lower(Gamer.nickname) == func.lower(json["nickname"])).first()
    if checkNickname:
        return jsonify({
            "success": False,
            "result": {},
            "updated": {},
            "timestamp": round(datetime.timestamp(datetime.now()))
        })
    
    return jsonify({
        "success": True,
        "result": {},
        "updated": {},
        "timestamp": round(datetime.timestamp(datetime.now()))
    })

@gamerr.route("/adminGift", methods=["POST"])
@auth.check_auth
def admingift():
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
    gamer: Gamer = Gamer.query.filter_by(id=id, token=token).first()

    if gamer.adminLevel != 2:
        return jsonify({
            "reason": "validation_exception"
        }), 400

    gamerid = json.get("gamer_id")
    message = json.get("message")
    quantity = json.get("quantity")

    searchGamer: Gamer = Gamer.query.filter_by(gamer_id=gamerid).first()
    if not searchGamer:
        return jsonify({
            "success": False,
            "result": {},
            "updated": {},
            "timestamp": round(datetime.timestamp(datetime.now()))
        })
    
    searchGamer.gifts.append({
        "builderPt": 0,
        "desc": message,
        "params": {},
        "productId": 0,
        "productType": "gem",
        "quantity": quantity,
        "senderId": gamer.id,
        "title": "Reward Gem for you!"
    })
    db.session.commit()

    return jsonify({
        "success": True,
        "result": {},
        "updated": {
            "admin": {
                "giftgems": quantity
            }
        },
        "timestamp": round(datetime.timestamp(datetime.now()))
    })
        
@gamerr.route("/put", methods=["POST"])
@auth.check_auth
def put():
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

    search = Gamer.query.filter_by(id=id, token=token)
    gamer: Gamer = search.first()
    if not gamer:
        return jsonify({
            "success": True,
            "result": {},
            "updated": {},
            "timestamp": round(datetime.timestamp(datetime.now()))
        })
    
    if len(json["nickname"]) > 10:
        return jsonify({
            'reason': 'sanitize_exception'
        }), 400
    
    checkNickname = Gamer.query.filter(func.lower(Gamer.nickname) == func.lower(json["nickname"])).first()
    if checkNickname:
        return jsonify({
            "success": False,
            "result": {},
            "updated": {},
            "timestamp": round(datetime.timestamp(datetime.now()))
        })

    if len(request.json["nickname"]) <= 2 or len(request.json["nickname"]) >= 10:
        return jsonify({
            "success": False,
            "result": {},
            "updated": {},
            "timestamp": round(datetime.timestamp(datetime.now()))
        })
    
    if gamer.nameVersion != 0 and gamer.gem >= extensions.master["config"]["change_name_cost"]:
        gamer.gem -= extensions.master["config"]["change_name_cost"]
    elif gamer.gem <= extensions.master["config"]["change_name_cost"] and gamer.nameVersion != 0:
        return jsonify({
            "success": False,
            "result": {},
            "updated": {},
            "timestamp": round(datetime.timestamp(datetime.now()))
        })

    gamer.nameVersion = gamer.nameVersion + 1
    gamer.nickname = request.json["nickname"]
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