from flask import Blueprint, jsonify, request
from app import db, limiter, config

from sqlalchemy import func, and_, or_
from models.comment import Comment
from models.gamer import Gamer
from models.emblem import Emblem
from models.level import Level

from datetime import datetime
from util import wraps, filter
from util import cursor as cursor_key

import json as Json
import re

comment = Blueprint("comment", __name__)
limiter.limit("300 per minute")(comment)

@comment.route("/delete", methods=["POST"])
@wraps.auth_required
@wraps.crc_required
def delete():
    json = request.json
    id, token = request.headers["authorization"].split(":")

    comment: Comment = Comment.query.filter_by(commentId=json["comment_id"]).first()
    if not comment:
        return jsonify({
            "success": False,
            "result": {},
            "updated": {},
            "timestamp": round(datetime.timestamp(datetime.now()))
        })
    
    gamer: Gamer = Gamer.query.filter_by(id=id, token=token).first()
    
    if comment.gamer_id != gamer.id and gamer.adminLevel <= 1:
        return jsonify({
            "success": False,
            "result": {},
            "updated": {},
            "timestamp": round(datetime.timestamp(datetime.now()))
        })
    
    db.session.delete(comment)
    db.session.commit()

    return jsonify({
        "success": True,
        "result": {
            "commentId": comment.commentId
        },
        "updated": {},
        "timestamp": round(datetime.timestamp(datetime.now()))
    })
        
@comment.route("/post", methods=["POST"])
@wraps.auth_required
@wraps.crc_required
def post():
    json = request.json
    id, token = request.headers["authorization"].split(":")

    gamer: Gamer = Gamer.query.filter_by(id=id, token=token).first()
    if not gamer:
        return jsonify({
            "success": False,
            "result": {},
            "updated": {},
            "timestamp": round(datetime.timestamp(datetime.now()))
        })
    
    if json["group_key"] == "feed_vip" and gamer.adminLevel < 1:
        return jsonify({
            'reason': 'validation_exception'
        }), 400
 
    timeDifference = gamer.commentableAt - datetime.now().timestamp()
    if timeDifference > 0:
        return jsonify({
            "reason": "comment_prevention",
            "result": {
              "sec": str(round(timeDifference, 1))
            }
        }), 500
    
    groupKey = json.get("group_key")
    if re.fullmatch(r'level_(\d+)', str(groupKey)):
        levelid = re.fullmatch(r'level_(\d+)', str(groupKey)).group(1)
        level: Level = Level.query.filter_by(id=int(levelid)).first()
        if level:
            levelCreator: Gamer = Gamer.query.filter_by(id=level.creator).first()

            # notification stuff
            if levelCreator.id != gamer.id:
                if re.search(r'@(\w+)', json.get("comment")): # @GAMER
                    user = re.search(r'@(\w+)', json.get("comment")).group(1)
                    gamerSearch: Gamer = Gamer.query.filter(func.lower(Gamer.nickname) == func.lower(user)).first()

                    if gamerSearch:
                        existingNotification = next(
                            (n for n in gamerSearch.notifications if n["id"] == f"mention{level.id}"),
                            None
                        )
                        if existingNotification:
                            existingNotification['updated_at'] = round(datetime.timestamp(datetime.now()))
                        else:
                            gamerSearch.notifications.append({
                                "args": {
                                  "level_id": level.id,
                                  "level_title": level.title,
                                  "senders": [
                                    {
                                        "id": gamer.id,
                                        "nickname": gamer.nickname,
                                        "time": round(datetime.timestamp(datetime.now()))
                                    }
                                  ]
                                },
                                "id": f"mention{level.id}",
                                "type": "mention",
                                "updated_at": round(datetime.timestamp(datetime.now()))
                            })
                else: # comment notification
                    existingcommentNotification = next(
                        (n for n in levelCreator.notifications if n["id"] == f"comment{level.id}"),
                        None
                    )
                    if existingcommentNotification:
                        existingcommentNotification["args"]["senders"].append({
                          "id": gamer.id,
                          "nickname": gamer.nickname,
                          "time": round(datetime.timestamp(datetime.now()))
                        })
                        existingcommentNotification['updated_at'] = round(datetime.timestamp(datetime.now()))
                    else:
                        levelCreator.notifications.append(
                            {
                              "args": {
                                "level_id": level.id,
                                "level_title": level.title,
                                "senders": [
                                  {
                                    "id": gamer.id,
                                    "nickname": gamer.nickname,
                                    "time": round(datetime.timestamp(datetime.now()))
                                  },
                                ]
                              },
                              "id": f"comment{level.id}",
                              "type": "comment",
                              "updated_at": round(datetime.timestamp(datetime.now()))
                        })
            
    newComment = Comment(groupKey, str(json["comment"]), "plain", json["options"], gamer.id)

    gamer.commentableAt = datetime.now().timestamp() + 10
    newComment.message = filter.filterText(str(newComment.message))

    if newComment.message.endswith(":youtube"):
        newComment.args["youtube"] = gamer.channel
        newComment.message = newComment.message.replace(":youtube", "")
        newComment.type = "youtube"
    elif re.search(r'\$(\d+)$', newComment.message):
        print(re.search(r'\$(\d+)$', newComment.message).group(1))
        emblem: Emblem = Emblem.query.filter_by(refId=re.search(r'\$(\d+)$', newComment.message).group(1)).first()
        if emblem:
            newComment.args["refId"] = emblem.refId
            newComment.type = "emblem"
        newComment.message = newComment.message.replace(f"${emblem.refId}", "")
    elif re.search(r'\#(\d+)$', newComment.message):
        id = int(re.search(r'\#(\d+)$', newComment.message).group(1))
        level: Level = Level.query.filter_by(levelId=id+10_000).first()
        if level:
            newComment.args["levelId"] = level.levelId
            newComment.type = "level"
        newComment.message = newComment.message.replace(f"#{id}", "")
    elif re.search(r'#(\w+)', newComment.message):
        tag = re.search(r'#(\w+)', newComment.message).group(1)
        newComment.args["tag"] = tag
        newComment.type = "hashtag"
        newComment.message = newComment.message.replace(f"#{tag}", "")
    elif newComment.message.endswith("#star"):
        newComment.message = newComment.message.replace("#star", "")
        newComment.type = "review"

    db.session.add(newComment)
    db.session.commit()

    return jsonify({
      "success": True,
      "updated": {},
      "result": {
        "comment": {
            "args": newComment.args,
            "commentId": newComment.commentId,
            "createdAt": newComment.createdAt,
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
            "message": newComment.message,
            "type": newComment.type
        }
      },
      "timestamp": round(datetime.timestamp(datetime.now())),
    })

@comment.route("/list", methods=["POST"])
@wraps.auth_required
@wraps.crc_required
def list():
    body = request.json
    gamerId, token = request.headers["authorization"].split(":")
    gamer: Gamer = Gamer.query.filter_by(id=gamerId, token=token).first()
    groupKey = body["group_key"]
    cursor = body.get("cursor")
    index = body.get("index", 0)
    pageSize = 10
 
    if groupKey == "feed_vip" and gamer.adminLevel < 1:
        return jsonify({
            "success": False,
            "result": {},
            "updated": {},
            "timestamp": round(datetime.timestamp(datetime.now()))
        })
 
    query = Comment.query.filter_by(group_key=groupKey).order_by(Comment.createdAt.desc(), Comment.commentId.desc())
 
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
            Comment.createdAt < decodedCursor["createdAt"],
            and_(Comment.createdAt == decodedCursor["createdAt"], Comment.commentId < decodedCursor["id"])
        ))
 
    comments = query.limit(pageSize + 1).all()
    hasMore = len(comments) > pageSize
    comments = comments[:pageSize]
    nextCursor = None
 
    if hasMore:
        nextCursor = cursor_key.makeCursor({
            "createdAt": comments[-1].createdAt,
            "id": comments[-1].commentId
        }, config.CURSOR_SECRET)
 
    authors = {}
    if comments:
        authorIds = {comment.gamer_id for comment in comments}
        authors = {author.id: author for author in Gamer.query.filter(Gamer.id.in_(authorIds)).all()}
 
    inventories = {}
    items = []
 
    for comment in comments:
        author = authors.get(comment.gamer_id)
        if not author:
            continue
 
        if author.id not in inventories:
            inventories[author.id] = Json.loads(author.inventory)
 
        items.append({
            "args": comment.args,
            "commentId": comment.commentId,
            "createdAt": comment.createdAt,
            "gamer": {
                "adminLevel": author.adminLevel,
                "avatar": author.avatar,
                "builderPt": author.builderPt,
                "campaigns": author.campaigns,
                "channel": author.channel,
                "clearCount": author.clearCount,
                "commentableAt": author.commentableAt,
                "country": author.country,
                "createdAt": author.createdAt,
                "emblemCount": author.emblemCount,
                "followerCount": author.followerCount,
                "gamerId": author.gamer_id,
                "gem": author.gem,
                "hasUnfinishedIAP": author.hasUnfinishedIAP,
                "id": author.id,
                "inventory": inventories[author.id],
                "lang": author.lang,
                **({"homeLevel": author.homeLevel} if author.homeLevel is not None else {}),
                "lastLoginAt": author.lastLoginAt,
                "levelCount": author.levelCount,
                "maxVideoId": author.maxVideoId,
                "nameVersion": author.nameVersion,
                "nickname": author.nickname,
                "playerPt": author.playerPt,
                "researches": author.researches,
                "visibleAt": author.visibleAt
            },
            "message": comment.message,
            "type": comment.type
        })
 
    return jsonify({
        "result": {
            "all_loaded": not hasMore,
            **({"cursor": nextCursor} if nextCursor is not None else {}),
            "index": index + len(comments),
            "items": items,
        },
        "success": True,
        "updated": {},
        "timestamp": round(datetime.timestamp(datetime.now()))
    })