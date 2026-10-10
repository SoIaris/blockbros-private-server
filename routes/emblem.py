from flask import Blueprint, request, jsonify
from app import db, limiter, config

from models.emblem import Emblem
from models.gamer import Gamer

from datetime import datetime
from util import wraps, filter
from util import cursor as cursor_key

import json as Json
import extensions
import hashlib

emblem = Blueprint("emblem", __name__)

limiter.limit("300 per minute")(emblem)

@emblem.route("/update", methods=["POST"])
@wraps.auth_required
@wraps.crc_required
def update():
    json = request.json
    id, token = request.headers["authorization"].split(":")
    gamer: Gamer = Gamer.query.filter_by(id=id, token=token).first()

    emblem_id = json.get("emblemId")
    map = json.get("map")

    if len(map) != 81:
        return jsonify({}), 500
    
    emblem: Emblem = Emblem.query.filter_by(id=emblem_id).first()
    if not emblem:
        return jsonify({
            "success": False,
            "result": {},
            "updated": {},
            "timestamp": round(datetime.timestamp(datetime.now()))
        })
    
    if emblem.creator != gamer.id:
        return jsonify({
            "success": False,
            "result": {},
            "updated": {},
            "timestamp": round(datetime.timestamp(datetime.now()))
        })
    
    inventory = Json.loads(gamer.inventory)

    count = {}
    for block in map:
        decodedBlock = extensions.decodeBlock(block)
        if decodedBlock["blockType"] != 0:
            count[decodedBlock["blockType"]] = count.get(decodedBlock["blockType"], 0) + 1

    enough = True
    for id, amount in count.items():
        # print(inventory.get(str(id)))
        if not id or str(id) not in inventory["blocks"] or inventory["blocks"][str(id)] < amount:
            enough = False

    if not enough:
        return 500

    for id, amount in count.items():
        if str(id) in inventory["blocks"]:
            inventory["blocks"][str(id)] -= amount
            if inventory["blocks"][str(id)] < 0:
                del inventory["blocks"][str(id)]

    gamer.inventory = Json.dumps(inventory)
    
    emblem.desc = json.get("desc")
    emblem.map = map
    emblem.title = json.get("title")

    db.session.commit()
    return jsonify({
        "success": True,
        "result": {
            "createdAt": emblem.createdAt,
            "desc": emblem.desc,
            "id": emblem.id,
            "map": emblem.map,
            "owners": emblem.owners,
            "refId": emblem.refId,
            "title": emblem.title
        },
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

@emblem.route("/delete", methods=["POST"])
@wraps.auth_required
@wraps.crc_required
def delete():
    json = request.json
    id, token = request.headers["authorization"].split(":")
    gamer: Gamer = Gamer.query.filter_by(id=id, token=token).first()

    emblem_id = json.get("emblem_id")

    emblem: Emblem = Emblem.query.filter_by(id=emblem_id).first()
    if not emblem:
        return jsonify({
            "success": False,
            "result": {},
            "updated": {},
            "timestamp": round(datetime.timestamp(datetime.now()))
        })
    
    if emblem.creator != gamer.id:
        return jsonify({
            "success": False,
            "result": {},
            "updated": {},
            "timestamp": round(datetime.timestamp(datetime.now()))
        })
    
    map = emblem.map
    inventory = Json.loads(gamer.inventory)

    count = {}
    for block in map:
        decodedBlock = extensions.decodeBlock(block)
        if decodedBlock["blockType"] != 0:
            count[decodedBlock["blockType"]] = count.get(decodedBlock["blockType"], 0) + 1

    for id, amount in count.items():
        if str(id) in inventory["blocks"]:
            inventory["blocks"][str(id)] += amount

    gamer.inventory = Json.dumps(inventory)

    db.session.delete(emblem)
    db.session.commit()

    return jsonify({
        "success": True,
        "result": {
            "id": emblem.id
        },
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

@emblem.route("/givenList", methods=["POST"])
@wraps.auth_required
@wraps.crc_required
def list():
    body = request.json
    cursor = body.get("cursor")
    gamerId = body.get("gamer_id")
    index = body.get("index") or 0
    pageSize = 10

    lastId = None
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
        
        lastId = decodedCursor["id"]

    owned = []
    while len(owned) <= pageSize:
        query = db.session.query(Emblem).order_by(Emblem.id.desc())
        if lastId is not None:
            query = query.filter(Emblem.id < lastId)

        batch = query.limit(100).all()
        if not batch:
            break

        for emblem in batch:
            lastId = emblem.id
            if gamerId in emblem.owners:
                owned.append(emblem)
                if len(owned) > pageSize:
                    break

        if len(batch) < 100:
            break

    hasMore = len(owned) > pageSize
    page = owned[:pageSize]
    nextCursor = None

    if hasMore:
        nextCursor = cursor_key.makeCursor({
            "id": page[-1].id
        }, config.CURSOR_SECRET)

    creators = {}
    items = []
    for emblem in page:
        if emblem.creator not in creators:
            creators[emblem.creator] = Gamer.query.filter_by(id=emblem.creator).first()

        creator: Gamer = creators[emblem.creator]
        if not creator:
            continue

        items.append({
            "createdAt": emblem.createdAt,
            "creator": {
                "adminLevel": creator.adminLevel,
                "avatar": creator.avatar,
                "builderPt": creator.builderPt,
                "campaigns": creator.campaigns,
                "channel": creator.channel,
                "clearCount": creator.clearCount,
                "commentableAt": creator.commentableAt,
                "country": creator.country,
                "createdAt": creator.createdAt,
                "emblemCount": creator.emblemCount,
                "followerCount": creator.followerCount,
                "gamerId": creator.gamer_id,
                "gem": creator.gem,
                "hasUnfinishedIAP": creator.hasUnfinishedIAP,
                "id": creator.id,
                "inventory": creator.inventory,
                "lang": creator.lang,
                **({"homeLevel": creator.homeLevel} if creator.homeLevel is not None else {}),
                "lastLoginAt": creator.lastLoginAt,
                "levelCount": creator.levelCount,
                "maxVideoId": creator.maxVideoId,
                "nameVersion": creator.nameVersion,
                "nickname": creator.nickname,
                "playerPt": creator.playerPt,
                "researches": creator.researches,
                "visibleAt": creator.visibleAt
            },
            "desc": emblem.desc,
            "id": emblem.id,
            "map": emblem.map,
            "owners": emblem.owners,
            "refId": emblem.refId,
            "title": emblem.title
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

@emblem.route("/gift", methods=["POST"])
@wraps.auth_required
@wraps.crc_required
def gift():
    json = request.json
    id, token = request.headers["authorization"].split(":")
    gamer: Gamer = Gamer.query.filter_by(id=id).first()
    master = extensions.get_master()

    findGamer: Gamer = Gamer.query.filter_by(id=json["target_gamer_id"]).first()
    if not findGamer:
        return jsonify({
            'reason': 'validation_exception'
        }), 400

    findEmblem: Emblem = Emblem.query.filter_by(id=json["emblem_id"]).first()
    if not findEmblem:
        return jsonify({
            'reason': 'validation_exception'
        }), 400
    
    if findEmblem.creator != gamer.id:
        return jsonify({
            'reason': 'validation_exception'
        }), 400
    
    if not gamer.gem >= master["config"]["emblem_gem"]:
        return jsonify({
            "success": False,
            "result": {},
            "updated": {},
            "timestamp": round(datetime.timestamp(datetime.now()))
        })
    
    gamer.gem -= master["config"]["emblem_gem"]

    findGamer.gifts.append({       
        "builderPt": 0,
        "desc": "",
        "params": {
            "sender_name": gamer.nickname,
            "map": findEmblem.map,
            "sender_id": gamer.id,
            "time": round(datetime.timestamp(datetime.now()))
        },
        "productId": findEmblem.id,
        "productType": "emblem",
        "quantity": 1,
        "senderId": gamer.id,
        "title": findEmblem.title
    })
    
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

@emblem.route("/post", methods=["POST"])
@wraps.auth_required
@wraps.crc_required
def post_emblem():
    json = request.json
    id, token = request.headers["authorization"].split(":")
    gamer: Gamer = Gamer.query.filter_by(id=id).first()

    emblem = Emblem(filter.filterText(json.get("title")), filter.filterText(json.get("title")), json["map"], gamer.id)
    
    map = json.get("map")
    inventory = Json.loads(gamer.inventory)

    if len(map) != 81:
        return 500
    
    count = {}
    for block in map:
        decodedBlock = extensions.decodeBlock(block)
        if decodedBlock["blockType"] != 0:
            count[decodedBlock["blockType"]] = count.get(decodedBlock["blockType"], 0) + 1

    enough = True
    for id, amount in count.items():
        if not id or str(id) not in inventory["blocks"] or inventory["blocks"][str(id)] < amount:
            enough = False

    if not enough:
        return jsonify({}), 500

    for id, amount in count.items():
        if str(id) in inventory["blocks"]:
            inventory["blocks"][str(id)] -= amount
            if inventory["blocks"][str(id)] < 0:
                del inventory["blocks"][str(id)]

    gamer.inventory = Json.dumps(inventory)

    db.session.add(emblem)
    db.session.commit()
    
    return jsonify({
        "success": True,
        "result": {
            "createdAt": emblem.createdAt,
            "creator": {
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
            "desc": emblem.desc,
            "id": emblem.id,
            "map": emblem.map,
            "recievedAt": 0,
            "refId": emblem.refId,
            "title": emblem.title,
        },
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

@emblem.route("/get", methods=["POST"])
@wraps.auth_required
@wraps.crc_required
def get():
    json = request.json
    emblem: Emblem = Emblem.query.filter_by(refId=json["refId"]).first()

    if not emblem:
        return jsonify({
            "success": False,
            "result": {},
            "updated": {},
            "timestamp": round(datetime.timestamp(datetime.now()))
        })
    
    creator: Gamer = Gamer.query.filter_by(id=emblem.creator).first()

    return jsonify({
        "success": True,
        "result": {
            "emblem": {
                "createdAt": emblem.createdAt,
                "creator": {
                    "adminLevel": creator.adminLevel,
                    "avatar": creator.avatar,
                    "builderPt": creator.builderPt,
                    "campaigns": creator.campaigns,
                    "channel": creator.channel,
                    "clearCount": creator.clearCount,
                    "commentableAt": creator.commentableAt,
                    "country": creator.country,
                    "createdAt": creator.createdAt,
                    "emblemCount": creator.emblemCount,
                    "followerCount": creator.followerCount,
                    "gamerId": creator.gamer_id,
                    "gem": creator.gem,
                    "hasUnfinishedIAP": creator.hasUnfinishedIAP,
                    "id": creator.id,
                    "inventory": creator.inventory,
                    "lang": creator.lang,
                    "lastLoginAt": creator.lastLoginAt,
                    "levelCount": creator.levelCount,
                    "maxVideoId": creator.maxVideoId,
                    "nameVersion": creator.nameVersion,
                    "nickname": creator.nickname,
                    "playerPt": creator.playerPt,
                    "researches": creator.researches,
                    "visibleAt": creator.visibleAt
                },
                "desc": emblem.desc,
                "id": emblem.id,
                "map": emblem.map,
                "owners": emblem.owners,
                "refId": emblem.refId,
                "title": emblem.title
            },
            "gamer": {
                "adminLevel": creator.adminLevel,
                "avatar": creator.avatar,
                "builderPt": creator.builderPt,
                "campaigns": creator.campaigns,
                "channel": creator.channel,
                "clearCount": creator.clearCount,
                "commentableAt": creator.commentableAt,
                "country": creator.country,
                "createdAt": creator.createdAt,
                "emblemCount": creator.emblemCount,
                "followerCount": creator.followerCount,
                "gamerId": creator.gamer_id,
                "gem": creator.gem,
                "hasUnfinishedIAP": creator.hasUnfinishedIAP,
                "id": creator.id,
                "inventory": creator.inventory,
                "lang": creator.lang,
                **({"homeLevel": creator.homeLevel} if creator.homeLevel is not None else {}),
                "lastLoginAt": creator.lastLoginAt,
                "levelCount": creator.levelCount,
                "maxVideoId": creator.maxVideoId,
                "nameVersion": creator.nameVersion,
                "nickname": creator.nickname,
                "playerPt": creator.playerPt,
                "researches": creator.researches,
                "visibleAt": creator.visibleAt
            }
        },
        "updated": {},
        "timestamp": round(datetime.timestamp(datetime.now()))
    })

@emblem.route("/ownList", methods=["POST"])
@wraps.auth_required
@wraps.crc_required
def post():
    json = request.json
    id, token = request.headers["authorization"].split(":")

    cursor = json.get("cursor")
    index = json.get("index")
    pageSize = 10

    query = db.session.query(Emblem).filter_by(creator=id).order_by(Emblem.createdAt.desc())
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
        
        query = query.filter(Emblem.id < decodedCursor["id"])
    
    rows = query.limit(pageSize + 1).all()
    hasMore = len(rows) > pageSize
    emblems = rows[:pageSize]
    nextCursor = None
    if hasMore:
        nextCursor = cursor_key.makeCursor({
            "id": emblems[-1].id
        }, config.CURSOR_SECRET)
        
    items = []

    for emblem in emblems:
        items.append({
            'desc': emblem.desc, 
            'id': emblem.id, 
            'map': emblem.map, 
            'owners': emblem.owners,
            'refId': emblem.refId,
            'title': emblem.title
        })

    return jsonify({
        "result": {
            'all_loaded': not hasMore,
            **({"cursor": nextCursor} if nextCursor is not None else {}),
            'index': len(items) + index,
            'items': items,
        },
        "success": True,
        "updated": {},
        "timestamp": round(datetime.timestamp(datetime.now()))
    })
