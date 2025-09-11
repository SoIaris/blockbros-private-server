from app import db
from datetime import datetime
import random

class Rating(db.Model):
    id = db.Column(db.BigInteger, nullable=False, primary_key=True)
    gamer = db.Column(db.BigInteger, nullable=False)
    levelid = db.Column(db.BigInteger, nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    createdAt = db.Column(db.BigInteger, default=0)

    def __init__(self, gamer, levelid, rating):
        self.gamer = gamer
        self.levelid = levelid
        self.rating = rating
        self.id = random.randint(1000000000000000, 9999999999999999)
        self.createdAt = round(datetime.timestamp(datetime.now()))
        
    def __repr__(self):
        return f'<Rating {self.id}>'
