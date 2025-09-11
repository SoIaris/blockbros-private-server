from app import db

from datetime import datetime
from extensions import master
from sqlalchemy.ext.mutable import MutableList, MutableDict

import hashlib
import random
import string

def generateAltPassword():
    lowercase = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'k', 'l', 'm', 'n', 'p', 'q', 'r', 's', 't', 'u', 'w', 'x', 'z']
    uppercase = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'K', 'L', 'M', 'N', 'P', 'R', 'S', 'T', 'U', 'W', 'X', 'Z']
    numbers = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']
    return ''.join(random.choice(lowercase + uppercase + numbers) for _ in range(8))

class Gamer(db.Model):
    gamer_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id = db.Column(db.BigInteger, unique=True, nullable=False)
    nickname = db.Column(db.String(10), nullable=False, unique=True)
    altPassword = db.Column(db.String(255), nullable=False, unique=True)
    avatar = db.Column(db.Integer, default=1)
    adminLevel = db.Column(db.Integer, default=0)
    builderPt = db.Column(db.BigInteger, default=0)
    campaigns = db.Column(db.JSON, nullable=True, default={})
    channel = db.Column(db.String(255), default="")
    clearCount = db.Column(db.BigInteger, default=0)
    commentableAt = db.Column(db.BigInteger, default=0)
    country = db.Column(db.String(2), default="zz")
    createdAt = db.Column(db.BigInteger, default=0)
    emblemCount = db.Column(db.BigInteger, default=0)
    followerCount = db.Column(db.BigInteger, default=0)
    gem = db.Column(db.BigInteger, default=master["config"]["signup_gems"])
    homeLevel = db.Column(db.JSON, default=None)
    hasUnfinishedIAP = db.Column(db.Boolean, default=True)
    lang = db.Column(db.String(10), default="en")
    lastLoginAt = db.Column(db.BigInteger)
    levelCount = db.Column(db.BigInteger, default=0)
    maxVideoId = db.Column(db.BigInteger, default=0)
    nameVersion = db.Column(db.BigInteger, default=0)
    password = db.Column(db.String(255), nullable=False, unique=True)
    playerPt = db.Column(db.BigInteger, default=0)
    researches = db.Column(MutableList.as_mutable(db.PickleType), default=None)
    visibleAt = db.Column(db.BigInteger, default=0)
    lastStreaklogin = db.Column(db.BigInteger)

    follows = db.Column(db.String(1000000), default='{"blocked": [], "blocks": [], "followers": [], "follows": []}', nullable=False)
    inventory = db.Column(db.String(1000000), nullable=False, default='{"avatars": [1], "blocks": {"4": 100, "5": 20, "6": 20, "7": 5, "8": 1, "9": 3}, "themes": {"1": 1}}')
    favorites = db.Column(MutableList.as_mutable(db.PickleType), default=[])

    gifts = db.Column(MutableList.as_mutable(db.PickleType), default=[])
    notifications = db.Column(MutableList.as_mutable(db.PickleType), default=[])
    token = db.Column(db.String(255), nullable=True)

    def __init__(self, nickname, lang, country):
        self.lang = lang
        self.country = country
        self.nickname = nickname
        self.createdAt = round(datetime.timestamp(datetime.now()))
        self.id = random.randint(1000000000000000, 9999999999999999)
        self.lastLoginAt = round(datetime.timestamp(datetime.now()))
        self.altPassword = generateAltPassword() # ''.join(random.choices(string.ascii_lowercase + string.ascii_uppercase, k=8))
        self.token = ''.join(random.choices(string.ascii_lowercase + string.ascii_uppercase + string.digits, k=32))
        self.password = f"{hashlib.sha1(f'{''.join(random.choices(string.ascii_lowercase + string.ascii_letters + string.digits, k=40))}-{self.id + self.lastLoginAt}'.encode()).hexdigest()}$sha1${''.join(random.choices(string.ascii_letters + string.digits, k=22))}"

    def __repr__(self):
        return f'<Gamer {self.id}>'
