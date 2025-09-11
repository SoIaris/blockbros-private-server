from app import db
import random
import string

class Video(db.Model):
    id = db.Column(db.BigInteger, nullable=False, primary_key=True)
    token = db.Column(db.String(255), nullable=False)
    gem = db.Column(db.Integer, nullable=False)
    creator = db.Column(db.BigInteger, nullable=False)

    def __init__(self, creator, gem):
        self.id = random.randint(1000000000000000, 9999999999999999)
        self.token = ''.join(random.choices(string.ascii_lowercase + string.ascii_uppercase + string.digits, k=32))
        self.creator = creator
        self.gem = gem

    def __repr__(self):
        return f"<Video {self.id}>"