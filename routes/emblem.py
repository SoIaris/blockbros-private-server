from flask import Blueprint, request, jsonify

from app import db

import extensions
import hashlib
import json as Json

from models.emblem import Emblem
from models.gamer import Gamer
from extensions import master

from datetime import datetime
import util.authentication as auth
import util.filter as filter

emblem = Blueprint("emblem", __name__)

from app import limiter
limiter.limit("300 per minute")(emblem)

@emblem.route("/update", methods=["POST"])
@auth.check_auth
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
@auth.check_auth
def delete():
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
    
    cursor = json.get("cursor")
    gamerId = json.get("gamer_id")
    index = json.get("index")

    query = db.session.query(Emblem)
    
    if cursor:
        id = int(hashlib.sha1(bytes(cursor, 'utf-8')).hexdigest(), 16)
        query = query.filter(Emblem.id < id)

    emblems = query.limit(10).all()
    ownsemblems = [emblem for emblem in emblems if gamerId in emblem.owners]

    items = []
    for emblem in ownsemblems:
        creator: Gamer = Gamer.query.filter_by(id=emblem.creator).first()
        if not creator:
            return jsonify({
                "success": False,
                "result": {},
                "updated": {},
                "timestamp": round(datetime.timestamp(datetime.now()))
            })
    
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

    nextCursor = hashlib.sha1(str(emblems[-1].id).encode('utf-8')).hexdigest() if emblems else None

    return jsonify({
        "result": {
            'all_loaded': len(emblems) < 10,
            'cursor': nextCursor,
            "index": len(emblems),
            'items': items,
        },
        "success": True,
        "updated": {},
        "timestamp": round(datetime.timestamp(datetime.now()))
    })

@emblem.route("/gift", methods=["POST"])
@auth.check_auth
def gift():
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
@auth.check_auth
def post_emblem():
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
@auth.check_auth
def post():
    json = request.json

    try:
        _, token = request.headers["authorization"].split(":")
        crc = extensions.jsonToCrc(extensions.sortStringify(json), token)
        if crc != request.headers["Crc"]:
            return jsonify({}), 400
    except Exception as e:
        print(f"login error: {e}")
        return jsonify({}), 400 

    cursor = json.get("cursor")
    index = json.get("index")
    id, token = request.headers["authorization"].split(":")

    query = db.session.query(Emblem).order_by(Emblem.createdAt.desc())
    gamer: Gamer = Gamer.query.filter_by(id=id).first()

    if cursor:
        emblemid = int(hashlib.sha1(bytes(cursor, 'utf-8')).hexdigest(), 16)
        query = query.filter(Emblem.id < emblemid)

    emblems = query.filter_by(creator=gamer.id).limit(10).all()

    items = []
    for emblem in emblems:
        emblem: Emblem = Emblem.query.filter_by(id=emblem.id).first()
        if not emblem:
            return jsonify({
                "success": False,
                "result": {},
                "updated": {},
                "timestamp": round(datetime.timestamp(datetime.now()))
            })
        
        items.append({
            'desc': emblem.desc, 
            'id': emblem.id, 
            'map': emblem.map, 
            'owners': emblem.owners,
            'refId': emblem.refId,
            'title': emblem.title
        })

    nextCursor = hashlib.sha1(str(emblems[-1].id).encode('utf-8')).hexdigest() if emblems else None

    return jsonify({
        "result": {
            'all_loaded': len(emblems) < 10,
            'cursor': nextCursor,
            "index": len(emblems),
            'items': items,
        },
        "success": True,
        "updated": {},
        "timestamp": round(datetime.timestamp(datetime.now()))
    })
