from flask import Blueprint, jsonify, request
from sqlalchemy import func

from app import db
from models.comment import Comment
from models.gamer import Gamer
from models.emblem import Emblem
from models.level import Level

from datetime import datetime

import util.authentication as auth
import util.filter as filter
import json as Json
import extensions
import re

comment = Blueprint("comment", __name__)

from app import limiter
limiter.limit("300 per minute")(comment)

@comment.route("/delete", methods=["POST"])
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
    
    id, _ = request.headers["authorization"].split(":")
    gamer: Gamer 

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
@auth.check_auth
def post():
    json = request.json

    try:
        _, token = request.headers["authorization"].split(":")
        crc = extensions.jsonToCrc(extensions.sortStringify(json), token)
        print(request.headers["Crc"], crc)
        if crc != request.headers["Crc"]:
            return jsonify({}), 400
    except Exception as e:
        print(f"login error: {e}")
        return jsonify({}), 400 

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
        if not level:
            return jsonify({}), 500
        
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
    sgamer: Gamer = Gamer.query.filter_by(id=id, token=token).first()
    cursor = json.get("cursor")
    index = json.get("index")
    
    if json["group_key"] == "feed_vip" and sgamer.adminLevel < 1:
        return jsonify({
            "success": False,
            "result": {},
            "updated": {},
            "timestamp": round(datetime.timestamp(datetime.now()))
        })

    baseQuery = Comment.query.filter_by(group_key=json["group_key"]).order_by(Comment.createdAt.desc())
    
    if cursor:
        try:
            position = db.session.query(func.count(Comment.commentId)).filter(
                Comment.group_key == json["group_key"],
                Comment.createdAt >= db.session.query(Comment.createdAt).filter(Comment.commentId == int(cursor)).scalar_subquery()
            ).scalar()
            
            pagination = baseQuery.paginate(page=(position // 10) + 1, per_page=10, error_out=False)
        except ValueError:
            return jsonify({"error": "Invalid cursor"}), 400
    else:
        pagination = baseQuery.paginate(page=1, per_page=10, error_out=False)

    comments = pagination.items
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
                "type": comment.type
            })

    return jsonify({
        "result": {
            'all_loaded': not pagination.has_next,
            **({'cursor': str(comments[-1].commentId)} if pagination.has_next else {}),
            "index": index + len(comments),
            'items': items,
        },
        "success": True,
        "updated": {},
        "timestamp": round(datetime.timestamp(datetime.now()))
    })