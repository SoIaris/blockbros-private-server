from app import db

from datetime import datetime
from sqlalchemy.ext.mutable import MutableList

import random

class Emblem(db.Model):
    createdAt = db.Column(db.BigInteger, default=0)
    creator = db.Column(db.BigInteger, default={})
    desc = db.Column(db.String(255), nullable=False, default="")
    id = db.Column(db.BigInteger, unique=True)
    map = db.Column(db.JSON, nullable=False, default=[])
    owners = db.Column(MutableList.as_mutable(db.PickleType), default=[])
    refId = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(255))

    def __init__(self, title, desc, map, creator):
        self.title = title
        self.desc = desc
        self.map = map
        self.creator = creator
        self.id = random.randint(1000000000000000, 9999999999999999)
        self.createdAt = round(datetime.timestamp(datetime.now()))
        
    def __repr__(self):
        return f'<Emblem {self.id}>'
