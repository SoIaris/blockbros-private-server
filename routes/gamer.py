from flask import Blueprint, request, jsonify
from app import db, limiter, config

from sqlalchemy import func, or_, and_, false
from models.gamer import Gamer
from models.emblem import Emblem
from models.comment import Comment

from datetime import datetime
from util import wraps
from util import cursor as cursor_key

import extensions
import hashlib
import json as Json

gamerr = Blueprint("gamer", __name__)
limiter.limit("300 per minute")(gamerr)

@gamerr.route("/follow/put", methods=["POST"])
@wraps.auth_required
@wraps.crc_required
def follow():
    json = request.json
    id, token = request.headers["authorization"].split(":")

    gamer: Gamer = Gamer.query.filter_by(id=id, token=token).first()

    action = json.get("action")
    gamer_id = json.get("gamer_id")

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
@wraps.auth_required
@wraps.crc_required
def list():
    body = request.json
    gamerId, token = request.headers["authorization"].split(":")
    gamer: Gamer = Gamer.query.filter_by(id=gamerId, token=token).first()
    listType = body.get("type")
    index = body.get("index")
    cursor = body.get("cursor")
    pageSize = 10
 
    query = db.session.query(Gamer)
    sortColumn = None
 
    if listType == "topPlayer":
        sortColumn = Gamer.playerPt
 
    if listType == "topBuilder":
        sortColumn = Gamer.builderPt
 
    if listType == "active":
        sortColumn = Gamer.lastLoginAt
 
    if listType == "follows":
        sortColumn = Gamer.id
        followedIds = Json.loads(gamer.follows)["follows"]
        query = query.filter(Gamer.id.in_(followedIds)) if followedIds else query.filter(false())
 
    if listType == "followers":
        sortColumn = Gamer.id
        followerIds = Json.loads(gamer.follows)["followers"]
        query = query.filter(Gamer.id.in_(followerIds)) if followerIds else query.filter(false())
 
    if sortColumn is None:
        return jsonify({
            "success": False,
            "result": {},
            "updated": {},
            "timestamp": round(datetime.timestamp(datetime.now()))
        })
 
    query = query.add_columns(sortColumn.label("sortValue")).order_by(sortColumn.desc(), Gamer.id.desc())
 
    if cursor:
        try:
            decodedCursor = cursor_key.readCursor(cursor, config.CURSOR_SECRET)
        except ValueError:
            return jsonify({
                "success": False,
                "result": {},
                "updated": {},
                "timestamp": round(datetime.timestamp(datetime.now()))
            })
        
        query = query.filter(or_(
            sortColumn < decodedCursor["value"],
            and_(sortColumn == decodedCursor["value"], Gamer.id < decodedCursor["id"])
        ))
 
    rows = query.limit(pageSize + 1).all()
    hasMore = len(rows) > pageSize
    rows = rows[:pageSize]
    players = [row[0] for row in rows]
    nextCursor = None
 
    if hasMore:
        nextCursor = cursor_key.makeCursor({
            "value": int(rows[-1][1]),
            "id": rows[-1][0].id
        }, config.CURSOR_SECRET)
 
    items = []
    for player in players:
        items.append({
            "adminLevel": player.adminLevel,
            "avatar": player.avatar,
            "builderPt": player.builderPt,
            "campaigns": player.campaigns,
            "channel": player.channel,
            "clearCount": player.clearCount,
            "commentableAt": player.commentableAt,
            "country": player.country,
            "createdAt": player.createdAt,
            "emblemCount": player.emblemCount,
            "followerCount": player.followerCount,
            "gamerId": player.gamer_id,
            "gem": player.gem,
            "hasUnfinishedIAP": player.hasUnfinishedIAP,
            "id": player.id,
            "inventory": Json.loads(player.inventory),
            "lang": player.lang,
            **({"homeLevel": player.homeLevel} if player.homeLevel is not None else {}),
            "lastLoginAt": player.lastLoginAt,
            "levelCount": player.levelCount,
            "maxVideoId": player.maxVideoId,
            "nameVersion": player.nameVersion,
            "nickname": player.nickname,
            "playerPt": player.playerPt,
            "researches": player.researches,
            "visibleAt": player.visibleAt
        })
 
    return jsonify({
        "success": True,
        "result": {
            "all_loaded": not hasMore,
            **({"cursor": nextCursor} if nextCursor is not None else {}),
            "index": index + len(items),
            "items": items,
        },
        "updated": {},
        "timestamp": round(datetime.timestamp(datetime.now()))
    })

@gamerr.route("/claimGift", methods=["POST"])
@wraps.auth_required
@wraps.crc_required
def claimgift():
    json = request.json
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
@wraps.auth_required
@wraps.crc_required
def channelset():
    json = request.json
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
@wraps.auth_required
@wraps.crc_required
def email():
    json = request.json
    
    return jsonify({
        "success": True,
        "result": {},
        "updated": {},
        "timestamp": round(datetime.timestamp(datetime.now()))
    })

@gamerr.route("/ban", methods=["POST"])
@wraps.auth_required
@wraps.crc_required
def ban():
    json = request.json
    id, token = request.headers["authorization"].split(":")
    gamer: Gamer = Gamer.query.filter_by(id=id, token=token).first()
    if gamer.adminLevel < 2:
        return jsonify({
            "reason": "validation_exception"
        }), 400

    gamer_id = json.get("gamer_id")
    enabled = json.get("enabled")

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
@wraps.auth_required
@wraps.crc_required
def sync():
    json = request.json
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
@wraps.auth_required
@wraps.crc_required
def get():
    json = request.json
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
@wraps.auth_required
@wraps.crc_required
def search():
    json = request.json
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
@wraps.auth_required
@wraps.crc_required
def warn():
    json = request.json
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
@wraps.auth_required
@wraps.crc_required
def checknickname():
    json = request.json
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
@wraps.auth_required
@wraps.crc_required
def admingift():
    json = request.json
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
@wraps.auth_required
@wraps.crc_required
def put():
    json = request.json
    id, token = request.headers["authorization"].split(":")

    gamer: Gamer = Gamer.query.filter_by(id=id, token=token).first()

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

    master = extensions.get_master()
    
    if gamer.nameVersion != 0 and gamer.gem >= master["config"]["change_name_cost"]:
        gamer.gem -= master["config"]["change_name_cost"]
    elif gamer.gem <= master["config"]["change_name_cost"] and gamer.nameVersion != 0:
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