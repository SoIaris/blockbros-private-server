from app import db

from datetime import datetime

import random

class Comment(db.Model):
    commentId = db.Column(db.BigInteger, primary_key=True, unique=True)
    args = db.Column(db.JSON, default={})
    createdAt = db.Column(db.BigInteger, nullable=False, default=0)
    gamer_id = db.Column(db.BigInteger, nullable=False)
    message = db.Column(db.String(255), nullable=False)
    type = db.Column(db.String(10), default="plain")
    group_key = db.Column(db.String(255), default="feed")

    def __init__(self, group_key, message, type, args, gamer_id):
        self.message = message
        self.type = type
        self.args = args
        self.group_key = group_key
        self.commentId = random.randint(1000000000000000, 9999999999999999)
        self.gamer_id = gamer_id
        self.createdAt = round(datetime.timestamp(datetime.now()))
        
    def __repr__(self):
        return f'<Comment {self.commentId}>'
