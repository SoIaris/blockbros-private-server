from flask import Blueprint, request, jsonify
from app import db, limiter, config

from models.gamer import Gamer
from models.level import Level
from models.comment import Comment
from models.ranking import Ranking
from models.video import Video
from models.rating import Rating
from models.play import Play
from sqlalchemy import func, or_, and_, case, false

from util import wraps
from util import cursor as cursor_key
from datetime import datetime

import util.filter as filter
import extensions
import json as Json
import hashlib
import time
import re

level = Blueprint("level", __name__)
limiter.limit("300 per minute")(level)

def LevelPostLimit():
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
    
@level.route("/clear", methods=["POST"])
@wraps.auth_required
@wraps.crc_required
def clear():
    json = request.json
    id, token = request.headers["authorization"].split(":")
    gamer: Gamer = Gamer.query.filter_by(id=id, token=token).first()

    levelId = json.get("level_id")
    time = json.get("time")
    videoLoaded = json.get("video_loaded")

    levelSearch: Level = Level.query.filter_by(id=levelId).with_for_update().first()
    if not levelSearch:
        return jsonify({
            "reason": "invalid_level"
        }), 400

    firstClear = False
    ownRecord = False

    ranking: Ranking = Ranking.query.filter_by(
        creator=gamer.id, levelId=levelSearch.id, cleared=False
    ).order_by(Ranking.time.asc(), Ranking.id.asc()).first()
    previousClear = Ranking.query.filter_by(
        creator=gamer.id, levelId=levelSearch.id, cleared=True
    ).first() is not None
    difficulty = extensions.calculateDifficulty(levelSearch.uuCount, levelSearch.uuClearCount)

    if ranking:
        if time < ranking.time:
            ranking.time = time
            ownRecord = True
    else:
        ranking = Ranking(time, levelSearch.id, gamer.id)
        db.session.add(ranking)
        if not previousClear:
            firstClear = True
            gamer.playerPt += difficulty
            levelSearch.uuClearCount += 1

    clearReward = {}
    videoStr = ""
    if firstClear:
        clearReward = extensions.getDifficultyReward(difficulty)
        inventory = Json.loads(gamer.inventory)
        blocks = inventory.setdefault("blocks", {})
        if clearReward["type"] == "block":
            key = str(clearReward["id"])
            blocks[key] = blocks.get(key, 0) + clearReward["quantity"]
        elif clearReward["type"] == "gem":
            videomodel: Video = Video(gamer.id, clearReward["quantity"])
            db.session.add(videomodel)
            db.session.flush()
            videoStr = f"{videomodel.id}:{videomodel.token}"

        gamer.inventory = Json.dumps(inventory)

    db.session.flush()

    betterPlayers = db.session.query(
        func.count(func.distinct(Ranking.creator))
    ).filter(
        Ranking.levelId == levelSearch.id,
        Ranking.cleared == False,
        Ranking.creator != gamer.id,
        or_(
            Ranking.time < ranking.time,
            and_(Ranking.time == ranking.time, Ranking.id < ranking.id)
        )
    ).scalar() or 0
    rank = betterPlayers + 1

    db.session.commit()

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
@wraps.auth_required
@wraps.crc_required
def get():
    json = request.json
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
@wraps.auth_required
@wraps.crc_required
def update():
    json = request.json
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
@wraps.auth_required
@wraps.crc_required
def delete():
    json = request.json
    id, token = request.headers["authorization"].split(":")
    gamer: Gamer = Gamer.query.filter_by(id=id, token=token).first()

    levelId = json.get("level_id")

    levelSearch: Level = Level.query.filter_by(id=levelId).first()
    if not levelSearch:
        return jsonify({
            "reason": "invalid_level"
        }), 400
    
    if levelSearch.creator != gamer.id or gamer.adminLevel < 1:
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

    master = extensions.get_master()
    removed = sum(
        reward["builderpt"] for reward in master["builderreward"]
        if reward["tier"] <= levelSearch.tier
    )
   
    gamer.builderPt = max(0, gamer.builderPt - removed)
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
@wraps.auth_required
@wraps.crc_required
def list():
    body = request.json
    gamerId, token = request.headers["authorization"].split(":")
    gamer: Gamer = Gamer.query.filter_by(id=gamerId, token=token).first()
    listType = body.get("type", "new")
    index = body.get("index", 0)
    cursor = body.get("cursor")
    pageSize = 10
    dayAgo = int(time.time()) - 86400
 
    query = db.session.query(Level)
    sortColumn = None
 
    if listType == "new":
        sortColumn = Level.createdAt
 
    if listType == "tag":
        sortColumn = Level.createdAt
        query = query.filter(Level.tag == body.get("tag"))
 
    if listType == "own" or listType == "activity":
        sortColumn = Level.createdAt
        query = query.filter(Level.creator == body.get("gamer_id"))
 
    if listType == "fav":
        sortColumn = Level.createdAt
        favoriteGamer = Gamer.query.filter_by(id=body.get("gamer_id")).first()
        if favoriteGamer and favoriteGamer.favorites:
            query = query.filter(Level.id.in_(favoriteGamer.favorites))
        else:
            query = query.filter(false())
 
    #if listType == "activity":
    #    ...
 
    if listType == "top":
        startOfDay = int(time.time()) - (int(time.time()) % 86400)
        dayRatings = db.session.query(
            Rating.levelid.label("ratedLevelId"),
            func.sum(Rating.rating).label("total"),
        ).filter(Rating.createdAt >= startOfDay).group_by(Rating.levelid).subquery()
        sortColumn = dayRatings.c.total
        query = query.join(dayRatings, Level.id == dayRatings.c.ratedLevelId)
 
    if listType == "recent":
        playTimes = db.session.query(
            Play.levelid.label("playedLevelId"),
            func.max(Play.createdAt).label("latest"),
        ).filter(Play.gamer == gamer.id).group_by(Play.levelid).subquery()
        sortColumn = playTimes.c.latest
        query = query.join(playTimes, Level.id == playTimes.c.playedLevelId)
 
    if sortColumn is None:
        return jsonify({
            "success": False,
            "result": {},
            "updated": {},
            "timestamp": round(datetime.timestamp(datetime.now()))
        })
 
    query = query.add_columns(sortColumn.label("sortValue")).order_by(sortColumn.desc(), Level.id.desc())
 
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
            and_(sortColumn == decodedCursor["value"], Level.id < decodedCursor["id"])
        ))
 
    rows = query.limit(pageSize + 1).all()
    hasMore = len(rows) > pageSize
    rows = rows[:pageSize]
    levels = [row[0] for row in rows]
    nextCursor = None
 
    if hasMore:
        nextCursor = cursor_key.makeCursor({
            "value": int(rows[-1][1]),
            "id": rows[-1][0].id
        }, config.CURSOR_SECRET)
 
    levelIds = [levelData.id for levelData in levels]
    creatorIds = {levelData.creator for levelData in levels}
 
    creators = {}
    rankings = {}
    ratingSums = {}
    myRatings = {}
    commentCounts = {}
 
    if levels:
        creators = {
            creator.id: creator
            for creator in Gamer.query.filter(Gamer.id.in_(creatorIds)).all()
        }
 
        rankings = {
            ranking.levelId: ranking
            for ranking in Ranking.query.filter(
                Ranking.levelId.in_(levelIds),
                Ranking.creator == gamer.id,
                Ranking.cleared == False
            ).all()
        }
 
        ratingRows = db.session.query(
            Rating.levelid,
            func.coalesce(func.sum(case((Rating.createdAt >= dayAgo, Rating.rating), else_=0)), 0),
            func.coalesce(func.sum(case((Rating.createdAt < dayAgo, Rating.rating), else_=0)), 0),
            func.coalesce(func.sum(Rating.rating), 0),
        ).filter(
            Rating.levelid.in_(levelIds),
            Rating.rating > 0
        ).group_by(Rating.levelid).all()
        ratingSums = {row[0]: (row[1], row[2], row[3]) for row in ratingRows}
 
        myRatings = {
            myRating.levelid: myRating
            for myRating in Rating.query.filter(
                Rating.gamer == gamer.id,
                Rating.levelid.in_(levelIds)
            ).all()
        }
 
        commentCounts = dict(
            db.session.query(Comment.group_key, func.count(Comment.commentId))
            .filter(Comment.group_key.in_([f"level_{levelId}" for levelId in levelIds]))
            .group_by(Comment.group_key)
            .all()
        )
 
    favorites = gamer.favorites or ""
    inventories = {}
    items = []
 
    for levelData in levels:
        creator = creators.get(levelData.creator)
        if not creator:
            continue
 
        ranking = rankings.get(levelData.id)
        myRating = myRatings.get(levelData.id)
        ratingToday, ratingYesterday, ratingTotal = ratingSums.get(levelData.id, (0, 0, 0))
 
        if creator.id not in inventories:
            inventories[creator.id] = Json.loads(creator.inventory)
 
        items.append({
            "clearCount": levelData.clearCount,
            "clearVersion": 0,
            "commentCount": commentCounts.get(f"level_{levelData.id}", 0),
            "commentedAt": 0,
            "config": levelData.config,
            "createdAt": levelData.createdAt,
            "difficulty": extensions.calculateDifficulty(levelData.uuCount, levelData.uuClearCount),
            "draft": 0,
            "fav": str(levelData.id) in favorites,
            "gamer": {
                "adminLevel": creator.adminLevel,
                "avatar": creator.avatar,
                "builderPt": creator.builderPt,
                "channel": creator.channel,
                "commentableAt": creator.commentableAt,
                "country": creator.country,
                "createdAt": creator.createdAt,
                "emblemCount": creator.emblemCount,
                "followerCount": creator.followerCount,
                "gamerId": creator.gamer_id,
                **({"homeLevel": creator.homeLevel} if creator.homeLevel is not None else {}),
                "id": creator.id,
                "inventory": inventories[creator.id],
                "lastLoginAt": creator.lastLoginAt,
                "levelCount": creator.levelCount,
                "nickname": creator.nickname,
                "playerPt": creator.playerPt,
                "userId": str(creator.gamer_id),
                "visibleAt": creator.visibleAt
            },
            "givenRating": -1,
            "id": levelData.id,
            "levelId": levelData.levelId,
            "map": levelData.map,
            "playCount": levelData.playCount,
            "rating": ratingTotal,
            "ratingCount": myRating.rating if myRating else 0,
            "tag": levelData.tag,
            "theme": levelData.theme,
            "tier": levelData.tier or 1,
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
            "all_loaded": not hasMore,
            **({"cursor": nextCursor} if nextCursor is not None else {}),
            "index": index + len(items),
            "items": items,
        },
        "updated": {},
        "timestamp": round(datetime.timestamp(datetime.now()))
    })

@level.route("/quickGet", methods=["POST"])
@wraps.auth_required
@wraps.crc_required
def quickget():
    json = request.json
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
@wraps.auth_required
@wraps.crc_required
def ranklist():
    body = request.json
    index = body.get("index", 0)
    levelId = body.get("level_id")
    cursor = body.get("cursor")
    pageSize = 20
 
    query = Ranking.query.filter_by(levelId=levelId, cleared=False).order_by(Ranking.time.asc(), Ranking.id.asc())
 
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
            Ranking.time > decodedCursor["time"],
            and_(Ranking.time == decodedCursor["time"], Ranking.id > decodedCursor["id"])
        ))
 
    ranks = query.limit(pageSize + 1).all()
    hasMore = len(ranks) > pageSize
    ranks = ranks[:pageSize]
    nextCursor = None
 
    if hasMore:
        nextCursor = cursor_key.makeCursor({
            "time": ranks[-1].time,
            "id": ranks[-1].id
        }, config.CURSOR_SECRET)
 
    gamers = {}
    if ranks:
        creatorIds = {rank.creator for rank in ranks}
        gamers = {gamer.id: gamer for gamer in Gamer.query.filter(Gamer.id.in_(creatorIds)).all()}
 
    inventories = {}
    items = []
 
    for rank in ranks:
        gamer = gamers.get(rank.creator)
 
        if not gamer:
            items.append({
                "gamer": extensions.deleted_user,
                "levelId": rank.levelId,
                "time": rank.time
            })
            continue
 
        if gamer.id not in inventories:
            inventories[gamer.id] = Json.loads(gamer.inventory)
 
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
                "inventory": inventories[gamer.id],
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

@level.route("/post", methods=["POST"])
@limiter.limit("5/day", exempt_when=lambda: LevelPostLimit())
@wraps.auth_required
@wraps.crc_required
def post():
    json = request.json
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