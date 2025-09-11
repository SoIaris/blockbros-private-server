from app import db
from datetime import datetime

class Ranking(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    creator = db.Column(db.BigInteger)
    levelId = db.Column(db.BigInteger, nullable=False)
    time = db.Column(db.Integer, nullable=False)
    cleared = db.Column(db.Boolean, default=False)
    createdAt = db.Column(db.BigInteger, default=0)

    def __init__(self, time, levelid, creator):
        self.createdAt = round(datetime.timestamp(datetime.now()))
        self.time = time
        self.levelId = levelid
        self.creator = creator

    def __repr__(self):
        return f'<Ranking {self.id}>'
