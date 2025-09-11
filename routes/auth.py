from flask import Blueprint, request, jsonify

from app import db

from models.gamer import Gamer
from models.comment import Comment
from models.emblem import Emblem

from datetime import datetime, timedelta
from extensions import sortStringify, jsonToCrc, master, loginRewardAmount
from app import limiter
import hashlib
import string
import random
import json as Json

auth = Blueprint("auth", __name__)

from app import limiter
limiter.limit("300 per minute")(auth)

@auth.route("/alt_login", methods=["POST"])
def alt_login():
    json = request.json
    try:
        _, token = request.headers["authorization"].split(":")
        crc = jsonToCrc(sortStringify(json), token)
        if crc != request.headers["Crc"]:
            return jsonify({}), 400
    except Exception as e:
        print(f"login error: {e}")
        return jsonify({}), 400  
    
    _, token = request.headers["authorization"].split(":")

    search = Gamer.query.filter_by(altPassword=json["password"], gamer_id=json["gamer_id"])
    gamer: Gamer = search.first()
    if not gamer:
        return jsonify({'reason': 'no_match'})
    
    if gamer and gamer.token == token:
        return jsonify({'reason': 'already_loggedin'}), 400
        
    gamer.token = ''.join(random.choices(string.ascii_lowercase + string.ascii_uppercase + string.digits, k=32))
    gamer.lastLoginAt = round(datetime.timestamp(datetime.now()))
    gamer.country = request.headers.get('X-Vercel-Ip-Country', 'US')
    gamer.followerCount = len(Json.loads(gamer.follows)["followers"])
    cts = round(datetime.timestamp(datetime.now()))
    loginBonus = 0

    if gamer.lastStreaklogin is None or gamer.lastStreaklogin == 0:
        gamer.lastStreaklogin = cts
    else:
        secondsPassed = cts - gamer.lastStreaklogin
        hoursPassed = secondsPassed / 3600
        print(hoursPassed)
        if hoursPassed >= 24 and hoursPassed <= 48:
            loginBonus = loginRewardAmount()
            gamer.gem += loginRewardAmount()
            gamer.lastStreaklogin = cts
        elif hoursPassed >= 48:
            gamer.lastStreaklogin = cts
            
    db.session.commit()

    query = db.session.query(Comment).order_by(Comment.createdAt.desc())
    comments = query.filter_by(group_key="feed").limit(10).all()

    items = []
    for comment in comments:
        gamerc: Gamer = Gamer.query.filter_by(id=comment.gamer_id).first()
        if gamerc:
            items.append({
                "args": comment.args,
                "commentId": comment.commentId,
                "createdAt": comment.createdAt,
                "gamer": {
                    "adminLevel": gamerc.adminLevel,
                    "avatar": gamerc.avatar,
                    "builderPt": gamerc.builderPt,
                    "campaigns": gamerc.campaigns,
                    "channel": gamerc.channel,
                    "clearCount": gamerc.clearCount,
                    "commentableAt": gamerc.commentableAt,
                    "country": gamerc.country,
                    "createdAt": gamerc.createdAt,
                    "emblemCount": gamerc.emblemCount,
                    "followerCount": gamerc.followerCount,
                    "gamerId": gamerc.gamer_id,
                    "gem": gamerc.gem,
                    "hasUnfinishedIAP": gamerc.hasUnfinishedIAP,
                    "id": gamerc.id,
                    "inventory": Json.loads(gamerc.inventory),
                    "lang": gamerc.lang,
                    **({"homeLevel": gamerc.homeLevel} if gamerc.homeLevel is not None else {}),
                    "lastLoginAt": gamerc.lastLoginAt,
                    "levelCount": gamerc.levelCount,
                    "maxVideoId": gamerc.maxVideoId,
                    "nameVersion": gamerc.nameVersion,
                    "nickname": gamerc.nickname,
                    "playerPt": gamerc.playerPt,
                    "researches": gamerc.researches,
                    "visibleAt": gamerc.visibleAt
                },
                "message": comment.message,
                "type": "plain"
            })

    nextCursor = hashlib.sha1(str(comments[-1].gamer_id).encode('utf-8')).hexdigest() if comments else None

    return jsonify({
        "success": True,
        "result": {            
            "loginBonus": loginBonus,
            "token": gamer.token,
            "user_id": gamer.id
        },        
        "updated": {
            'campaignInfo': {
                'comments': {}
            },
            'feeds': {
                'all_loaded': len(comments) < 10,
                'cursor': nextCursor,
                "index": len(comments),
                'items': items,
            },
            'gamer': {
                "adminLevel": gamer.adminLevel,
                "altPassword": gamer.altPassword,
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
                "password": gamer.password,
                "playerPt": gamer.playerPt,
                "researches": gamer.researches,
                "visibleAt": gamer.visibleAt
            },
            'follows': Json.loads(gamer.follows),
            'gifts': gamer.gifts,
            'notifications': sorted(gamer.notifications,key=lambda x: x["updated_at"], reverse=True),
        },
        "timestamp": round(datetime.timestamp(datetime.now()))
    }) 

@auth.route("/login", methods=["POST"])
def login():
    json = request.json
    try:
        _, token = request.headers["authorization"].split(":")
        crc = jsonToCrc(sortStringify(json), token)
        if crc != request.headers["Crc"]:
            return jsonify({}), 400
    except Exception as e:
        print(f"login error: {e}")
        return jsonify({}), 400  
    
    _, token = request.headers["authorization"].split(":")

    search = Gamer.query.filter_by(password=json["password"])
    gamer: Gamer = search.first()
    if not gamer:
        return jsonify({'reason': "password_mismatch"}), 400
    
    searchId = Gamer.query.filter_by(id=int(json["id"])).first()
    if not searchId:
        return jsonify({'reason': 'missing_gamer'}), 400
    
    if gamer and gamer.token == token:
        return jsonify({'reason': 'already_loggedin'}), 400

    gamer.token = ''.join(random.choices(string.ascii_lowercase + string.ascii_uppercase + string.digits, k=32))
    gamer.lastLoginAt = round(datetime.timestamp(datetime.now()))
    gamer.country = request.headers.get('X-Vercel-Ip-Country', 'US')
    gamer.followerCount = len(Json.loads(gamer.follows)["followers"])
    cts = round(datetime.timestamp(datetime.now()))
    loginBonus = 0
    print(cts)
    if gamer.lastStreaklogin is None or gamer.lastStreaklogin == 0:
        gamer.lastStreaklogin = cts
    else:
        secondsPassed = cts - gamer.lastStreaklogin
        hoursPassed = secondsPassed / 3600
        #print(hoursPassed)
        if hoursPassed >= 24 and hoursPassed <= 48:
            loginBonus = loginRewardAmount()
            gamer.gem += loginRewardAmount()
            gamer.lastStreaklogin = cts
        elif hoursPassed >= 48:
            gamer.lastStreaklogin = cts

    db.session.commit()

    query = db.session.query(Comment).order_by(Comment.createdAt.desc())
    comments = query.filter_by(group_key="feed").limit(10).all()

    items = []
    for comment in comments:
        gamerc: Gamer = Gamer.query.filter_by(id=comment.gamer_id).first()
        if gamerc:
            items.append({
                "args": comment.args,
                "commentId": comment.commentId,
                "createdAt": comment.createdAt,
                "gamer": {
                    "adminLevel": gamerc.adminLevel,
                    "avatar": gamerc.avatar,
                    "builderPt": gamerc.builderPt,
                    "campaigns": gamerc.campaigns,
                    "channel": gamerc.channel,
                    "clearCount": gamerc.clearCount,
                    "commentableAt": gamerc.commentableAt,
                    "country": gamerc.country,
                    "createdAt": gamerc.createdAt,
                    "emblemCount": gamerc.emblemCount,
                    "followerCount": gamerc.followerCount,
                    "gamerId": gamerc.gamer_id,
                    "gem": gamerc.gem,
                    "hasUnfinishedIAP": gamerc.hasUnfinishedIAP,
                    "id": gamerc.id,
                    "inventory": Json.loads(gamerc.inventory),
                    "lang": gamerc.lang,
                    **({"homeLevel": gamerc.homeLevel} if gamerc.homeLevel is not None else {}),
                    "lastLoginAt": gamerc.lastLoginAt,
                    "levelCount": gamerc.levelCount,
                    "maxVideoId": gamerc.maxVideoId,
                    "nameVersion": gamerc.nameVersion,
                    "nickname": gamerc.nickname,
                    "playerPt": gamerc.playerPt,
                    "researches": gamerc.researches,
                    "visibleAt": gamerc.visibleAt
                },
                "message": comment.message,
                "type": "plain"
            })

    nextCursor = hashlib.sha1(str(comments[-1].gamer_id).encode('utf-8')).hexdigest() if comments else None

    return jsonify({
        "success": True,
        "result": {
            "loginBonus": loginBonus,
            "token": gamer.token,
        },        
        "updated": {
            'campaignInfo': {
                'comments': {}
            },
            'feeds': {
                'all_loaded': len(comments) < 10,
                'cursor': nextCursor,
                "index": len(comments),
                'items': items,
            },
            'gamer': {
                "adminLevel": gamer.adminLevel,
                "altPassword": gamer.altPassword,
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
                "password": gamer.password,
                "playerPt": gamer.playerPt,
                "researches": gamer.researches,
                "visibleAt": gamer.visibleAt
            },
            'gifts': gamer.gifts,
            'follows': Json.loads(gamer.follows),
            'notifications': sorted(gamer.notifications,key=lambda x: x["updated_at"], reverse=True),
        },
        "timestamp": round(datetime.timestamp(datetime.now()))
    }) 

@auth.route("/register", methods=["POST"])
@limiter.limit("5/hour")
def register():
    json = request.json
    try:
        _, token = request.headers["authorization"].split(":")
        crc = jsonToCrc(sortStringify(json), token)
        if crc != request.headers["Crc"]:
            return jsonify({}), 400
    except Exception as e:
        print(f"register error: {e}")
        return jsonify({}), 400

    if request.json["key"] != master["config"]["register_key"]:
        return jsonify({
            'success': False, 
            'result': {},
            'updated': {}, 
            'timestamp': round(datetime.timestamp(datetime.now()))
        })

    newGamer = Gamer(str(Gamer.query.count() + 1).zfill(8), request.json["lang"], request.headers.get('X-Vercel-Ip-Country', 'US'))

    db.session.add(newGamer)
    db.session.commit()

    query = db.session.query(Comment).order_by(Comment.createdAt.desc())
    comments = query.filter_by(group_key="feed").limit(10).all()

    items = []
    for comment in comments:
        gamer: Gamer = Gamer.query.filter_by(id=comment.gamer_id).first()
        if gamer:     
            items.append({
                "args": comment.args,
                "commentId": comment.commentId,
                "createdAt": comment.createdAt,
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
                    "homeLevel": gamer.hasUnfinishedIAP,
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
                "message": comment.message,
                "type": "plain"
            })

    nextCursor = hashlib.sha1(str(comments[-1].gamer_id).encode('utf-8')).hexdigest() if comments else None

    return jsonify({
        "result": {
            "token": newGamer.token,
            "user_id": newGamer.id
        },
        "success": True,
        "timestamp": round(datetime.timestamp(datetime.now())),
        "updated": {
            # 'follows': newGamer.follows,
            'campaignInfo': {
                'comments': {}
            },
            'feeds': {
                'all_loaded': len(comments) < 10,
                'cursor': nextCursor,
                "index": len(comments),
                'items': items,
            },
            'gamer': {
                "adminLevel": newGamer.adminLevel,
                "altPassword": newGamer.altPassword,
                "avatar": newGamer.avatar,
                "builderPt": newGamer.builderPt,
                "campaigns": newGamer.campaigns,
                "channel": newGamer.channel,
                "clearCount": newGamer.clearCount,
                "commentableAt": newGamer.commentableAt,
                "country": newGamer.country,
                "createdAt": newGamer.createdAt,
                "emblemCount": newGamer.emblemCount,
                "followerCount": newGamer.followerCount,
                "gamerId": newGamer.gamer_id,
                "gem": newGamer.gem,
                "hasUnfinishedIAP": newGamer.hasUnfinishedIAP,
                "id": newGamer.id,
                "inventory": Json.loads(newGamer.inventory),
                "lang": newGamer.lang,
                **({"homeLevel": newGamer.homeLevel} if newGamer.homeLevel is not None else {}),
                "lastLoginAt": newGamer.lastLoginAt,
                "levelCount": newGamer.levelCount,
                "maxVideoId": newGamer.maxVideoId,
                "nameVersion": newGamer.nameVersion,
                "nickname": newGamer.nickname,
                "password": newGamer.password,
                "playerPt": newGamer.playerPt,
                "researches": newGamer.researches,
                "visibleAt": newGamer.visibleAt
            },
            'follows': Json.loads(newGamer.follows),

            #'gifts': newGamer.gifts,
            #'notifications': newGamer.notifications,
            #'token': newGamer.token
        }
    })