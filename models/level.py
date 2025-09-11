from app import db

from datetime import datetime
from sqlalchemy.ext.mutable import MutableList

import random

class Level(db.Model):
    levelId = db.Column(db.Integer, primary_key=True, default=1)
    id = db.Column(db.BigInteger, unique=True, nullable=False)
    creator = db.Column(db.BigInteger, nullable=False)
    createdAt = db.Column(db.BigInteger, default=0)
    map = db.Column(db.JSON, nullable=False, default=[])
    config = db.Column(db.JSON, nullable=False, default={})
    clearCount = db.Column(db.Integer, default=0)
    playCount = db.Column(db.Integer, default=0)
    rating = db.Column(db.Integer, default=0)
    ratingCount = db.Column(db.Integer, default=0)
    tag = db.Column(db.String(255), default="")
    theme = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    uuClearCount = db.Column(db.Integer, default=0)
    tier = db.Column(db.Integer, default=0)
    uuCount = db.Column(db.Integer, default=0)
    version = db.Column(db.Integer, default=1)

    def __init__(self, title, theme, map):
        levid = db.session.query(db.func.max(Level.levelId)).scalar() or 1 + 10000
        self.levelId = (levid + 1) if levid is not None else 10001
        self.title = title
        self.theme = theme
        self.map = map
        self.createdAt = round(datetime.timestamp(datetime.now()))
        self.id = random.randint(1000000000000000, 9999999999999999)
        
    def __repr__(self):
        return f'<Level {self.id}>'
