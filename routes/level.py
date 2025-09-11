from flask import Blueprint, request, jsonify, render_template
from app import db

from models.gamer import Gamer
from models.level import Level
from models.comment import Comment
from models.ranking import Ranking
from models.video import Video
from models.rating import Rating
from models.play import Play

from app import limiter
from datetime import datetime
from sqlalchemy import func
import time
from util import authentication as auth
import util.filter as filter

level = Blueprint("level", __name__)

from app import limiter
limiter.limit("300 per minute")(level)

import extensions
import json as Json
import hashlib
import re

@level.route("/clear", methods=["POST"])
@auth.check_auth
def clear():
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

    levelId = json.get("level_id")
    time = json.get('time')
    videoLoaded = json.get("video_loaded")

    levelSearch: Level = Level.query.filter_by(id=levelId).first()
    if not levelSearch:
        return jsonify({
            "reason": "invalid_level"
        }), 400
    
    firstClear = False
    ownRecord = False

    ranking: Ranking = Ranking.query.filter_by(creator=gamer.id, levelId=levelSearch.id, cleared=False).order_by(Ranking.time.asc()).first()
    difficulty = extensions.calculateDifficulty(levelSearch.uuCount, levelSearch.uuClearCount)
    previousClear = Ranking.query.filter_by(creator=gamer.id, levelId=levelSearch.id,cleared=True).first() is not None
    print(previousClear)
    if ranking:
        if time < ranking.time:
            ranking.time = time
            ownRecord = True
    else:
        ranking = Ranking(time, levelSearch.id, gamer.id)
        if not previousClear:
            firstClear = True
            gamer.playerPt += difficulty
            levelSearch.uuClearCount += 1
        db.session.add(ranking)

    clearReward = {}
    videoStr = ""
    if firstClear:
        clearReward = extensions.getDifficultyReward(difficulty)
        inventory = Json.loads(gamer.inventory)
        blocks = inventory["blocks"]
        print(blocks)
        if clearReward["type"] == "block":
            if not str(clearReward['id']) in blocks:
                blocks[str(clearReward['id'])] = clearReward["quantity"]
            else:
                blocks[str(clearReward['id'])] += clearReward["quantity"]
        elif clearReward["type"] == "gem":
            videomodel: Video = Video(gamer.id, clearReward["quantity"])
            videoStr = f"{videomodel.id}:{videomodel.token}"
            db.session.add(videomodel)

        gamer.inventory = Json.dumps(inventory)

    subquery = db.session.query(
        Ranking.creator,
        func.min(Ranking.time).label('best_time')
    ).filter(
        Ranking.levelId == levelSearch.id,
        Ranking.cleared == False
    ).group_by(
        Ranking.creator
    ).subquery()

    better_players = db.session.query(
        func.count(subquery.c.creator)
    ).filter(
        subquery.c.best_time < ranking.time
    ).scalar()
    db.session.commit()
    rank = better_players + 1 if ranking else None
    print(clearReward)
    return jsonify({
       "success": True,
       "result": {
            "clearReward": clearReward if clearReward and clearReward["type"] != "gem" else {},
            "completed": True,
            "firstClear": firstClear,
            "ownRecord": ownRecord,
            "playerPt": difficulty if firstClear else 0,
            "rank": rank,
            "time": time,
            "video": videoStr,
            "videoGem": clearReward["quantity"] if videoStr else 0
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
            },
       },
       "timestamp": round(datetime.timestamp(datetime.now()))
    })

@level.route("/get", methods=["POST"])
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
    
    levelId = json.get("level_id")
    levelSearch: Level = Level.query.filter_by(levelId=levelId).first()
    if len(str(levelId)) == 16:
        levelSearch: Level = Level.query.filter_by(id=levelId).first()

    if not levelSearch:
        return jsonify({
            "success": False,
            "result": {},
            "updated": {},
            "timestamp": round(datetime.timestamp(datetime.now()))
        })
    
    gamer: Gamer = Gamer.query.filter_by(id=levelSearch.creator).first()
    dayAgo = int(time.time()) - 86400
    ratingToday: Rating = db.session.query(func.sum(Rating.rating)).filter(Rating.levelid == levelSearch.id,Rating.rating > 0, Rating.createdAt >= dayAgo).scalar() or 0
    ratingYesterday: Rating = db.session.query(func.sum(Rating.rating)).filter(Rating.levelid == levelSearch.id,Rating.rating > 0, Rating.createdAt < dayAgo).scalar() or 0
    ratingTotal: Rating = db.session.query(func.sum(Rating.rating)).filter(Rating.levelid == levelSearch.id,Rating.rating > 0).scalar() or 0
    rating: Rating = Rating.query.filter_by(gamer=gamer.id,levelid=levelSearch.id).first()
    ranking: Ranking = Ranking.query.filter_by(creator=gamer.id,levelId=levelSearch.id).first()

    items = []
    items.append({
        "clearCount": levelSearch.clearCount,
        "clearVersion": 0,
        "commentCount": Comment.query.filter_by(group_key=f"level_{levelSearch.id}").count(),
        "commentedAt": 0,
        "config": levelSearch.config,
        "createdAt": levelSearch.createdAt,
        "difficulty": extensions.calculateDifficulty(levelSearch.uuCount, levelSearch.uuClearCount),
        "draft": 0,
        "fav": True if gamer.favorites and str(levelSearch.id) in gamer.favorites else False,
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
        "givenRating": -1,
        "id": levelSearch.id,
        "levelId": levelSearch.levelId,
        "map": levelSearch.map,
        "playCount": levelSearch.playCount,
        "rating": ratingTotal,
        "ratingCount": rating,
        "tag": levelSearch.tag,
        "theme": levelSearch.theme,
        "tier": levelSearch.tier if levelSearch.tier else 1,
        "time": ranking.time if ranking.time else 0,
        "title": levelSearch.title,
        "todayRating": ratingToday,
        "uuClearCount": levelSearch.uuClearCount,
        "uuCount": levelSearch.uuCount,
        "version": levelSearch.version,
        "yesterdayRating": ratingYesterday
    })

    return jsonify({
        'success': True, 
        'result': {
            'all_loaded': True, 
            'index': len(items), 
            'items': items
        },
        "updated": {},
        "timestamp": round(datetime.timestamp(datetime.now()))
    })

@level.route("/update", methods=["POST"])
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

    levelId = json.get("level_id")

    levelSearch: Level = Level.query.filter_by(id=levelId).first()
    if not levelSearch:
        return jsonify({}), 500
    
    if levelSearch.creator != gamer.id:
        return jsonify({}), 500
    
    map = json.get("map")
    title = json.get("title")
    theme = json.get("theme")    
    config = json.get("config")
    clearranking = json.get("clear_ranking")

    inventory = Json.loads(gamer.inventory)

    if len(map) != 400:
        return jsonify({}), 500
    
    count = {}
    for i, block in enumerate(map, 1):  
        if block == 16:
            if map[i-2] == 32:
                return jsonify({}), 500

        decodedBlock = extensions.decodeBlock(block)
        if decodedBlock["blockType"] != 0 and decodedBlock["blockType"] != 1 and decodedBlock["blockType"] != 2:
            count[decodedBlock["blockType"]] = count.get(decodedBlock["blockType"], 0) + 1

    for id, amount in count.items():
        if not id or str(id) not in inventory["blocks"] or int(inventory["blocks"].get(str(id), 0)) < amount:
            return jsonify({
                "success": False,
                "result": {
                    "reason": "not_enough_block",
                    "blockId": id,
                    "quantity": amount
                }
            }), 400

    for id, amount in count.items():
        if str(id) in inventory["blocks"]:
            inventory["blocks"][str(id)] -= amount
            if inventory["blocks"][str(id)] < 0:
                del inventory["blocks"][str(id)]

    levelSearch.map = map
    levelSearch.title = filter.filterText(json.get("title"))
    levelSearch.theme = theme
    levelSearch.config = config
    ranking: Ranking = Ranking.query.filter_by(creator=gamer.id,levelId=levelId).first()

    tagMatch = re.search(r'#(\w+)', levelSearch.title)
    if tagMatch:
        levelSearch.title = levelSearch.title.replace(f"#{tagMatch.group(1)}", "").strip()
        levelSearch.tag = tagMatch.group(1)

    if clearranking == 1:
        ranks: Ranking = Ranking.query.filter_by(levelId=levelId).all()
        for rank in ranks:
            rank.cleared = True
        
    db.session.commit()
    return jsonify({
        "success": True,
        "result": {
            "clearCount": levelSearch.clearCount,
            "clearVersion": 0,
            "commentCount": Comment.query.filter_by(group_key=f"level_{levelSearch.id}").count(),
            "commentedAt": 0,
            "config": levelSearch.config,
            "createdAt": levelSearch.createdAt,
            "difficulty": extensions.calculateDifficulty(levelSearch.uuCount, levelSearch.uuClearCount),
            "draft": 0,
            "fav": True if gamer.favorites and str(levelSearch.id) in gamer.favorites else False,
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
            "givenRating": -1,
            "id": levelSearch.id,
            "levelId": levelSearch.levelId,
            "map": levelSearch.map,
            "playCount": levelSearch.playCount,
            "rating": levelSearch.rating,
            "ratingCount": levelSearch.ratingCount,
            "tag": levelSearch.tag,
            "theme": levelSearch.theme,
            "tier": levelSearch.tier if levelSearch.tier else 1,
            "time": ranking.time if ranking.time else 0,
            "title": levelSearch.title,
            "todayRating": 0,
            "uuClearCount": levelSearch.uuClearCount,
            "uuCount": levelSearch.uuCount,
            "version": levelSearch.version,
            "yesterdayRating": 0
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
    
@level.route("/delete", methods=["POST"])
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

    levelId = json.get("level_id")

    levelSearch: Level = Level.query.filter_by(id=levelId).first()
    if not levelSearch:
        return jsonify({
            "reason": "invalid_level"
        }), 400
    
    if levelSearch.creator != gamer.id:
        return jsonify({
            "reason": "forbidden"
        }), 400

    if gamer.gem < 1:
        return jsonify({
            "reason": "not_enough_gem"
        }), 400
    
    inventory = Json.loads(gamer.inventory)

    count = {}
    for block in levelSearch.map:
        decodedBlock = extensions.decodeBlock(block)
        if decodedBlock["blockType"] != 0:
            count[decodedBlock["blockType"]] = count.get(decodedBlock["blockType"], 0) + 1

    for id, amount in count.items():
        if str(id) in inventory["blocks"]:
            inventory["blocks"][str(id)] += amount

    gamer.inventory = Json.dumps(inventory)

    gamer.gem = gamer.gem - 1
    db.session.delete(levelSearch)
    db.session.commit()

    return jsonify({
        "success": True,
        "result": {
            "level_id": levelSearch.id
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
    

@level.route("/list", methods=["POST"])
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
    type = json.get('type')
    index = json.get('index')
    cursor = json.get("cursor")

    base_query = db.session.query(Level)

    if type == "new" :
        base_query = base_query.order_by(Level.createdAt.desc())
    elif type == "activity":
        base_query = base_query.order_by(Level.createdAt.desc())
    elif type == "tag":
        base_query = base_query.filter_by(tag=json.get("tag")).order_by(Level.createdAt.desc())
    elif type == "own":
        base_query = base_query.filter_by(creator=json.get("gamer_id")).order_by(Level.createdAt.desc())
    elif type == "top":
        subquery = db.session.query(Rating.levelid,func.sum(Rating.rating).label('total_rating')).filter(Rating.createdAt >= int(time.time()) - (int(time.time()) % 86400)).group_by(Rating.levelid).subquery()
        base_query = base_query.join(subquery,Level.id == subquery.c.levelid).order_by(subquery.c.total_rating.desc())
    elif type == "recent":
        subquery = db.session.query(Play.levelid, func.max(Play.createdAt).label("latest")).filter(Play.gamer==gamer.id).group_by(Play.levelid).subquery()
        base_query = base_query.join(subquery,Level.id == subquery.c.levelid).order_by(subquery.c.latest.desc())
    elif type == "fav":
        gamer = db.session.query(Gamer).filter_by(id=json.get("gamer_id")).first()
        if gamer and gamer.favorites:
            base_query = base_query.filter(Level.id.in_(gamer.favorites)).order_by(Level.createdAt.desc())
        else:
            base_query = base_query.filter(False)
    elif type == "activity":
        ids = [id for id in gamer.follows['follows']]
        if len(ids) == 0:
            base_query = base_query.filter(False)
        else:
            base_query = base_query.filter(Level.creator.in_(ids)).order_by(Level.createdAt.desc())

    if cursor:
        position = db.session.query(func.count(Level.id)).filter(
            Level.createdAt >= db.session.query(Level.createdAt).filter(Level.id == int(cursor)).scalar_subquery()
        ).scalar()
        
        pagination = base_query.paginate(page=(position // 10) + 1, per_page=10, error_out=False)
    else:
        pagination = base_query.paginate(page=1, per_page=10, error_out=False)

    levels = pagination.items
    items = []
    for levelData in levels:
        gamerc: Gamer = Gamer.query.filter_by(id=levelData.creator).first()
        if gamerc:
            ranking: Ranking = Ranking.query.filter_by(levelId=levelData.id, creator=gamer.id, cleared=False).first()
            dayAgo = int(time.time()) - 86400
            ratingToday: Rating = db.session.query(func.sum(Rating.rating)).filter(Rating.levelid == levelData.id,Rating.rating > 0, Rating.createdAt >= dayAgo).scalar() or 0
            ratingYesterday: Rating = db.session.query(func.sum(Rating.rating)).filter(Rating.levelid == levelData.id,Rating.rating > 0, Rating.createdAt < dayAgo).scalar() or 0
            ratingTotal: Rating = db.session.query(func.sum(Rating.rating)).filter(Rating.levelid == levelData.id,Rating.rating > 0).scalar() or 0
            rating: Rating = Rating.query.filter_by(gamer=gamer.id,levelid=levelData.id).first()
            items.append({
                "clearCount": levelData.clearCount,
                "clearVersion": 0,
                "commentCount": Comment.query.filter_by(group_key=f"level_{levelData.id}").count(),
                "commentedAt": 0,
                "config": levelData.config,
                "createdAt": levelData.createdAt,
                "difficulty": extensions.calculateDifficulty(levelData.uuCount, levelData.uuClearCount),
                "draft": 0,
                "fav": True if gamer.favorites and str(levelData.id) in gamer.favorites else False,
                "gamer": {
                    "adminLevel": gamerc.adminLevel,
                    "avatar": gamerc.avatar,
                    "builderPt": gamerc.builderPt,
                    "channel": gamerc.channel,
                    "commentableAt": gamerc.commentableAt,
                    "country": gamerc.country,
                    "createdAt": gamerc.createdAt,
                    "emblemCount": gamerc.emblemCount,
                    "followerCount": gamerc.followerCount,
                    "gamerId": gamerc.gamer_id,
                    **({"homeLevel": gamerc.homeLevel} if gamerc.homeLevel is not None else {}),
                    "id": gamerc.id,
                    "inventory": Json.loads(gamerc.inventory),
                    "lastLoginAt": gamerc.lastLoginAt,
                    "levelCount": gamerc.levelCount,
                    "nickname": gamerc.nickname,
                    "playerPt": gamerc.playerPt,
                    "userId": str(gamerc.gamer_id),
                    "visibleAt": gamerc.visibleAt
                },
                "givenRating": -1,
                "id": levelData.id,
                "levelId": levelData.levelId,
                "map": levelData.map,
                "playCount": levelData.playCount,
                "rating": ratingTotal,
                "ratingCount": rating.rating if rating else 0,
                "tag": levelData.tag,
                "theme": levelData.theme,
                "tier": levelData.tier if levelData.tier else 1,
                "time": ranking.time if ranking else 0,
                "title": levelData.title,
                "todayRating": ratingToday,
                "uuClearCount": levelData.uuClearCount,
                "uuCount": levelData.uuCount,
                "version": levelData.version,
                "yesterdayRating": ratingYesterday
            })
            
    return jsonify({
        "success": True,
        "result": {
            'all_loaded': not pagination.has_next,
            **({'cursor': str(levels[-1].id)} if pagination.has_next else {}),
            "index": index + len(levels),
            'items': items,
        },
        "updated": {},
        "timestamp": round(datetime.timestamp(datetime.now()))
    })

@level.route("/quickGet", methods=["POST"])
@auth.check_auth
def quickget():
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
    ggamer: Gamer = Gamer.query.filter_by(id=id).first()

    items = []
    randomlevel: Level = Level.query.order_by(func.random()).first()
    if randomlevel:
        gamer: Gamer = Gamer.query.filter_by(id=randomlevel.creator).first()
        dayAgo = int(time.time()) - 86400
        ratingToday: Rating = db.session.query(func.sum(Rating.rating)).filter(Rating.levelid == randomlevel.id,Rating.rating > 0, Rating.createdAt >= dayAgo).scalar() or 0
        ratingYesterday: Rating = db.session.query(func.sum(Rating.rating)).filter(Rating.levelid == randomlevel.id,Rating.rating > 0, Rating.createdAt < dayAgo).scalar() or 0
        ratingTotal: Rating = db.session.query(func.sum(Rating.rating)).filter(Rating.levelid == randomlevel.id,Rating.rating > 0).scalar() or 0
        rating: Rating = Rating.query.filter_by(gamer=gamer.id,levelid=randomlevel.id).first()
        ranking: Ranking = Ranking.query.filter_by(creator=gamer.id,levelId=randomlevel.id).first()

        items.append({
            "clearCount": randomlevel.clearCount,
            "clearVersion": 0,
            "commentCount": Comment.query.filter_by(group_key=f"level_{randomlevel.id}").count(),
            "commentedAt": 0,
            "config": randomlevel.config,
            "createdAt": randomlevel.createdAt,
            "difficulty": extensions.calculateDifficulty(randomlevel.uuCount, randomlevel.uuClearCount),
            "draft": 0,
            "fav": True if ggamer.favorites and str(randomlevel.id) in ggamer.favorites else False,
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
            "givenRating": -1,
            "id": randomlevel.id,
            "levelId": randomlevel.levelId,
            "map": randomlevel.map,
            "playCount": randomlevel.playCount,
            "rating": ratingTotal,
            "ratingCount": rating,
            "tag": randomlevel.tag,
            "theme": randomlevel.theme,
            "tier": randomlevel.tier if randomlevel.tier else 1,
            "time": ranking.time if ranking.time else 0,
            "title": randomlevel.title,
            "todayRating": ratingToday,
            "uuClearCount": randomlevel.uuClearCount,
            "uuCount": randomlevel.uuCount,
            "version": randomlevel.version,
            "yesterdayRating": ratingYesterday
        })
    
    return jsonify({
        'success': True, 
        'result': {
            'all_loaded': True, 
            'index': len(items), 
            'items': items
        },
        "updated": {},
        "timestamp": round(datetime.timestamp(datetime.now()))
    })

@level.route("/ranking/list", methods=["POST"])
@auth.check_auth
def ranklist():
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
    
    index = json.get("index")
    levelid = json.get('level_id')
    cursor = json.get("cursor")

    query = db.session.query(Ranking).filter_by(levelId=levelid, cleared=False).order_by(Ranking.time.asc())

    if cursor:
        cursor_id = int(hashlib.sha1(bytes(cursor, 'utf-8')).hexdigest(), 16)
        query = query.filter(Ranking.id < cursor_id)

    ranks = query.limit(20).all()

    items = []
    for rank in ranks:
        gamer: Gamer = Gamer.query.filter_by(id=rank.creator).first()
        if not gamer:
            items.append({
                "gamer": extensions.deleted_user,
                "levelId": rank.levelId,
                "time": rank.time
            })
        else:
            items.append({
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
                "levelId": rank.levelId,
                "time": rank.time
            })

    nextCursor = hashlib.sha1(str(ranks[-1].id).encode('utf-8')).hexdigest() if ranks else None

    return jsonify({
        "success": True,
        "result": {
            'all_loaded': len(ranks) < 20,
            'cursor': nextCursor,
            "index": len(ranks),
            'items': items,
        },
        "updated": {},
        "timestamp": round(datetime.timestamp(datetime.now()))
    })

def over5bp():
    try:
        authorization = request.headers.get("authorization")
        if not authorization:
            return False
            
        id, token = authorization.split(":")
        
        gamer: Gamer = Gamer.query.filter_by(id=id).first()
        if not gamer:
            return False
            
        return gamer.playerPt > 5000
        
    except Exception as e:
        return False

@level.route("/post", methods=["POST"])
@limiter.limit("5/day", exempt_when=lambda: over5bp())
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

    id, token = request.headers["authorization"].split(":")
    gamer: Gamer = Gamer.query.filter_by(id=id).first()

    map = json.get("map")
    inventory = Json.loads(gamer.inventory)

    if len(map) != 400:
        return jsonify({}), 500
    
    count = {}
    for i, block in enumerate(map, 1):        
        if block == 16:
            if map[i-2] == 32:
                return jsonify({}), 500
    
        decodedBlock = extensions.decodeBlock(block)
        if decodedBlock["blockType"] != 0 and decodedBlock["blockType"] != 1 and decodedBlock["blockType"] != 2:
            count[decodedBlock["blockType"]] = count.get(decodedBlock["blockType"], 0) + 1

    for id, amount in count.items():
        if not id or str(id) not in inventory["blocks"] or int(inventory["blocks"].get(str(id), 0)) < amount:
            return jsonify({
                "success": False,
                "result": {
                    "reason": "not_enough_block",
                    "blockId": id,
                    "quantity": amount
                }
            }), 400

    for id, amount in count.items():
        if str(id) in inventory["blocks"]:
            inventory["blocks"][str(id)] -= amount
            if inventory["blocks"][str(id)] < 0:
                del inventory["blocks"][str(id)]

    levelData = Level(filter.filterText(json.get("title")), json.get("theme"), map)
    RankingData = Ranking(json.get("time"), levelData.id, gamer.id)
    levelData.creator = gamer.id
    levelData.config = json.get("config")
    levelData.uuClearCount = 1
    levelData.uuCount = 1
    levelData.clearCount = 1
    levelData.playCount = 1

    tagMatch = re.search(r'#(\w+)', levelData.title)
    if tagMatch:
        levelData.title = levelData.title.replace(f"#{tagMatch.group(1)}", "").strip()
        levelData.tag = tagMatch.group(1)
        
    db.session.add(levelData)
    db.session.add(RankingData)

    gamer.levelCount = Level.query.filter_by(creator=gamer.id).count()
    gamer.inventory = Json.dumps(inventory)
    db.session.commit()

    return jsonify({
        "success": True,
        "result": {
            "clearCount": levelData.clearCount,
            "clearVersion": 0,
            "commentCount": Comment.query.filter_by(group_key=f"level_{levelData.id}").count(),
            "commentedAt": 0,
            "config": levelData.config,
            "createdAt": levelData.createdAt,
            "difficulty": extensions.calculateDifficulty(levelData.uuCount, levelData.uuClearCount),
            "draft": 0,
            "fav": True if gamer.favorites and str(levelData.id) in gamer.favorites else False,
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
            "givenRating": -1,
            "id": levelData.id,
            "levelId": levelData.levelId,
            "map": levelData.map,
            "playCount": levelData.playCount,
            "rating": levelData.rating,
            "ratingCount": levelData.ratingCount,
            "tag": levelData.tag,
            "theme": levelData.theme,
            "tier": levelData.tier if levelData.tier else 1,
            "time": RankingData.time,
            "title": levelData.title,
            "todayRating": 0,
            "uuClearCount": levelData.uuClearCount,
            "uuCount": levelData.uuCount,
            "version": levelData.version,
            "yesterdayRating": 0
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