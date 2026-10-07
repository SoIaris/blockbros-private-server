from flask import Blueprint, request, jsonify
from app import db, limiter

from models.gamer import Gamer

from datetime import datetime
from util import wraps

import extensions
import json as Json

shop = Blueprint("shop", __name__)
limiter.limit("300 per minute")(shop)

@shop.route("/item/buy", methods=["POST"])
@wraps.auth_required
@wraps.crc_required
def buy():
    json = request.json
    id, token = request.headers["authorization"].split(":")
    gamer: Gamer = Gamer.query.filter_by(id=id).first()

    id = json.get("id")
    type = json.get("type")
    item = extensions.GetShopItem(type, id)
    if item and item["enabled"] == 1:
        if gamer.gem < item["price"]:
            return jsonify({
                'reason': 'validation_exception'
            }), 400

        if item["category"] != "research":
            inventory = Json.loads(gamer.inventory)
            id = str(item['id'])
            type = f'{item["category"]}s'
            if not id in inventory[type]:
                inventory[type][id] = item["quantity"]
            else:
                inventory[type][id] += item["quantity"]
            gamer.inventory = Json.dumps(inventory)
        elif item["category"] == "research":
            if gamer.researches is None:
                gamer.researches = []
            gamer.researches.append(id)
            
        gamer.gem = gamer.gem - item["price"]
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
    
@shop.route("/transaction/finish", methods=["POST"])
@wraps.auth_required
@wraps.crc_required
def transactionfinish():
    json = request.json
    id, token = request.headers["authorization"].split(":")
    gamer: Gamer = Gamer.query.filter_by(id=id).first()

    gem_id = json.get("gem_id")
    receipt_data = json.get("receipt_data")
    print(gem_id, receipt_data)

    gamer.hasUnfinishedIAP = False

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

@shop.route("/transaction/start", methods=["POST"])
@wraps.auth_required
@wraps.crc_required
def transactionstart():
    json = request.json
    id, token = request.headers["authorization"].split(":")
    gamer: Gamer = Gamer.query.filter_by(id=id).first()
    gamer.hasUnfinishedIAP = True

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
    
@shop.route("/gacha/character/spin", methods=["POST"])
@wraps.auth_required
@wraps.crc_required
def spin():
    json = request.json
    id, token = request.headers["authorization"].split(":")
    gamer: Gamer = Gamer.query.filter_by(id=id).first()
    
    type = json.get("type")
    master = extensions.get_master()
    
    if type == 0:
        if not gamer.gem >= master["config"]["character_gacha_price"]:
            return jsonify({
                'reason': 'validation_exception'
            }), 400
        
        inventory = Json.loads(gamer.inventory)
        characterId = extensions.randomAvatar()
        gamer.gem -= master["config"]["character_gacha_price"]

        inventory["avatars"].append(characterId["id"])

        gamer.inventory = Json.dumps(inventory)
        db.session.commit()

        return jsonify({
            "success": True,
            "result": {
                "avatarId": characterId["id"]
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
    else:
        return jsonify({
            'reason': 'validation_exception'
        }), 400