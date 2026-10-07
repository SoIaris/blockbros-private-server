from flask import Flask, jsonify, request, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_compress import Compress
from sqlalchemy import func

from dotenv import load_dotenv

db = SQLAlchemy()
migrate = Migrate()
limiter = Limiter(key_func=get_remote_address) 
load_dotenv()

from models.gamer import Gamer
from models.comment import Comment
from models.ranking import Ranking
from models.rating import Rating
from models.emblem import Emblem
from models.level import Level
from models.play import Play

import extensions
import requests
import os

class config:
    SQLALCHEMY_DATABASE_URI = os.getenv("POSTGRES_URL") # PostgresSQL
    VPNAPI_KEY = os.getenv("VPNAPI_KEY") # https://vpnapi.io/
    CURSOR_SECRET = os.getenv("CURSOR_SECRET")

    COMPRESS_MIN_SIZE = 0
    COMPRESS_ALGORITHM = ["gzip"]

def create_app():
    app = Flask(__name__, template_folder="routes")
    app.config.from_object(config)
    
    CORS(app)
    Compress(app)

    db.init_app(app)
    migrate.init_app(app, db)
    limiter.init_app(app)

    # blueprints
    from routes.auth import auth
    from routes.gamer import gamerr
    from routes.master import master
    from routes.comment import comment
    from routes.videoreward import videoreward
    from routes.emblem import emblem
    from routes.level import level
    from routes.shop import shop

    app.register_blueprint(auth, url_prefix="/auth")
    app.register_blueprint(gamerr, url_prefix="/gamer")
    app.register_blueprint(master, url_prefix="/master")
    app.register_blueprint(comment, url_prefix="/comment")
    app.register_blueprint(videoreward, url_prefix="/videoreward")
    app.register_blueprint(emblem, url_prefix="/emblem")
    app.register_blueprint(level, url_prefix="/level")
    app.register_blueprint(shop, url_prefix="/shop")

    # routes
    @app.route("/ping", methods=["POST", "GET"])
    def ping():    
        if not request.is_json:
            return jsonify({"success": True, "message": "pong", "header": dict(request.headers), "body": ""})

        body = request.get_json() or {}

        return jsonify({"success": True, "message": "pong", "header": dict(request.headers), "body": str(extensions.sortStringify(body))})

    @app.route("/")
    def home():
        return render_template("home/index.html")
    
    # handlers
    @app.after_request
    def afterreq(r):
        try:
            if request.headers.get("Content-Type") in ("application/json;charset=UTF-8", "application/json"):      
                    json = request.json
                    id, token = request.headers["authorization"].split(":")
                    gamer: Gamer = Gamer.query.filter_by(id=id, token=token).first()
                    if gamer and json.get("batch") and json.get("batch") != None:
                        batch = json["batch"]
                        #if batch.get("campaign"): # campaign logic that i prolly can't use
                        #    campaigns = batch.get("campaign")
                        #    for campaign in campaigns:
                        #        time = campaign["time"]
                        #        ranking: Ranking = Ranking.query.filter_by(creator=gamer.id, campaignId=campaign["campaign_id"], cleared=False).order_by(Ranking.time.asc()).first()
                        #        previousClear = Ranking.query.filter_by(creator=gamer.id, campaignId=campaign["campaign_id"],cleared=True).first() is not None
                        #        firstClear = False
                        #        if time < ranking.time:
                        #            ranking.time = time
                        #            ownRecord = True
                        #        else:
                        #            ranking = Ranking(time, None, gamer.id, campaignId=campaign["campaign_id"])
                        #            if not previousClear:
                        #                firstClear = True

                        #            db.session.add(ranking)

                        #        if firstClear:
                        #            print("clear")

                        if batch.get("gamer"):
                            gamerb = batch.get("gamer")
                            if gamerb.get("avatar"):
                                gamer.avatar = batch["gamer"]["avatar"]
                            if gamerb.get("homeLevel"):
                                levelid = gamerb.get("homeLevel").get("levelId")
                                level: Level = Level.query.filter_by(id=levelid).first()
                                if level:
                                    gamer.homeLevel = {
                                        'levelId': level.id,
                                        'map': level.map,
                                        'theme': level.theme
                                    }
                                    db.session.commit()

                        if batch.get("level"):
                            for id, data in batch.get("level").items():
                                level: Level = Level.query.filter_by(id=id).first()
                                if level:
                                    print(data)
                                    if data.get("play"):
                                        level.playCount += data.get("play")
                                        if not Play.query.filter_by(gamer=gamer.id, levelid=level.id).first():
                                            play = Play(gamer.id, level.id)
                                            level.uuCount += 1
                                            db.session.add(play)
                                    if data.get("clear"):
                                        level.clearCount += data.get("clear")
                                    if 'fav' in data:
                                        if data.get("fav") == True and str(level.id) not in gamer.favorites:
                                            gamer.favorites.append(str(level.id))
                                        elif data.get("fav") == False and str(level.id) in gamer.favorites:
                                            gamer.favorites.remove(str(level.id))

                                    if data.get("rating"):
                                        rating: Rating = Rating.query.filter_by(gamer=gamer.id, levelid=level.id).first()
                                        ratingTotal: Rating = db.session.query(func.sum(Rating.rating)).filter(Rating.levelid == level.id,Rating.rating > 0).scalar() or 0

                                        if not rating:
                                            if data.get("rating") == 1 or data.get("rating") == 2 or data.get("rating") == 3:
                                                ratingn = Rating(gamer.id, level.id, data.get("rating"))
                                                creator: Gamer = Gamer.query.filter_by(id=level.creator).first()
                                                if creator:
                                                    if ratingTotal + data.get("rating") >= 10 and level.tier == 0:
                                                        level.tier = 1
                                                        creator.gifts.append({
                                                            "builderPt": 5,
                                                            "desc": "ui_builder_gift_desc",
                                                            "params": {
                                                              "tier": level.tier,
                                                              "level_id": level.levelId,
                                                              "level_title": level.title,
                                                              "rating": ratingTotal
                                                            },
                                                            "productId": 0,
                                                            "productType": "none",
                                                            "quantity": 0,
                                                            "senderId": 0,
                                                            "title": "ui_builder_gift_title"
                                                        })
                                                    elif ratingTotal + data.get("rating") >= 100 and level.tier == 1:
                                                        level.tier = 2
                                                        creator.gifts.append({
                                                            "builderPt": 50,
                                                            "desc": "ui_builder_gift_desc",
                                                            "params": {
                                                              "tier": level.tier,
                                                              "level_id": level.levelId,
                                                              "level_title": level.title,
                                                              "rating": ratingTotal
                                                            },
                                                            "productId": 0,
                                                            "productType": "none",
                                                            "quantity": 0,
                                                            "senderId": 0,
                                                            "title": "ui_builder_gift_title"
                                                        })
                                                    elif ratingTotal + data.get("rating") >= 1000 and level.tier == 2:
                                                        level.tier = 3
                                                        creator.gifts.append({
                                                            "builderPt": 250,
                                                            "desc": "ui_builder_gift_desc",
                                                            "params": {
                                                              "tier": level.tier,
                                                              "level_id": level.levelId,
                                                              "level_title": level.title,
                                                              "rating": ratingTotal
                                                            },
                                                            "productId": 0,
                                                            "productType": "none",
                                                            "quantity": 0,
                                                            "senderId": 0,
                                                            "title": "ui_builder_gift_title"
                                                        })

                                                db.session.add(ratingn)
                        db.session.commit()

        except Exception as e:
            print(f"Batch error: {e}")
            db.session.rollback()
        return r

    @app.before_request
    def before_request_func(): # shit way of detecting proxy but it works
        try:
            ip = request.remote_addr or request.headers.get("x-real-ip")
            res = requests.get(f"https://vpnapi.io/api/{ip}?key={app.config['VPNAPI_KEY']}")
            data = res.json()
            if 'security' in data:
                security = data['security']
                if security["proxy"] == True:
                    return jsonify({}), 403
        except Exception as e:
            pass
        
    @app.errorhandler(404)
    def handle_404(error):
        return jsonify({
            "error": "code=404, message=Not Found",
            "message": "Not Found"
        }), 404

    @app.errorhandler(429)
    def handle_429(error):
        return jsonify({
            'error': 'code=429, message=rate limit exceeded', 
            'message': 'rate limit exceeded'
        }), 429
        
    @app.errorhandler(403)
    def handle_403(error):
        return jsonify({
            "error": "code=403, message=Forbidden",
            "message": "Forbidden"
        }), 403
    
    @app.errorhandler(405)
    def handle_405(error):
        return jsonify({
            "error": "code=405, message=Forbidden",
            "message": "Forbidden"
            }), 405

    master = extensions.get_master()
    print(f'version {master["config"]['assetversion']}.{master["version"]}')
    return app

app = create_app()
