import json
import random

from datetime import datetime
from app import db

deleted_user = {
    "adminLevel": 0,
    "avatar": 0,
    "builderPt": 0,
    "channel": "",
    "commentableAt": 0,
    "country": "ZZ",
    "createdAt": 0,
    "emblemCount": 0,
    "followerCount": 0,
    "gamerId": 1,
    "id": 1,
    "inventory": {
      "avatars": []
    },
    "lastLoginAt": 0,
    "levelCount": 0,
    "nickname": "(deleted)",
    "playerPt": 0,
    "visibleAt": 0
}

# made this a function so it gets a updated master if changed without restarting the api
def get_master():
    with open("master.json", 'r', encoding="utf-8") as file:
        master = json.load(file)

        return master

    return None

def getAvatars():
    return get_master()["avatar"]

def getGachas():
    return get_master()["gacha"]

def getGacha(gachaId):
    return getGachas().get(str(gachaId))

def getGachaItemIds(gachaId):
    gacha = getGacha(gachaId)
    return gacha["items"] if gacha else []

def getValidAvatars(gamer, gachaId=None):
    avatars = getAvatars()

    if gachaId is None:
        avatarIds = sorted(int(key) for key in avatars.keys())
    else:
        avatarIds = sorted(getGachaItemIds(gachaId))

    inventory = json.loads(gamer.inventory)
    ownedAvatars = set(inventory.get("avatars", []))

    result = []
    for avatarId in avatarIds:
        avatar = avatars.get(str(avatarId))
        if avatar is None:
            continue

        if avatar.get("ispublic") == 0:
            continue

        if avatarId in ownedAvatars:
            continue

        result.append(avatar)

    return result

def isGamerBanned(visibleAt):
    now = round(datetime.timestamp(datetime.now()))
    return visibleAt > now

def GetShopItem(category, id):
    master = get_master()

    for data in master["shop"][category]:
        if data["id"] == id:
            return data
    
    return None

def getDifficultyReward(difficulty: int):
    master = get_master()

    rewards = []
    for reward in master["clearreward"][str(difficulty)]:
        rewards.extend([reward] * reward['weight'])

    ran = random.choice(rewards)

    return {
        'id': ran["id"],
        'quantity': ran['quantity'],
        'type': ran['type']
    }

def calculateDifficulty(playUU, clearUU):
    if playUU == 0:
        return 2 
    
    clearUU = min(clearUU, playUU)
    
    rate = (clearUU / playUU) * 100
    
    if rate >= 80:
        return 1  # easy
    elif rate >= 31:
        return 2  # medium
    elif rate >= 11:
        return 3  # hard
    else:
        return 4  # hardcore

def decodeBlock(value):
    return {
        "attr": value >> 12,
        "blockType": (value & int("111111110000", 2)) >> 4,
        "dirType": value & int("1111", 2),
    }

def getActiveEventsByType(type):
    events = []

    master = get_master()["event"]
    for event in master:
        if event["type"] == type:
            startat = event["startat"]
            endat = event["endat"]
            now = round(datetime.timestamp(datetime.now()))

            if startat <= now <= endat:
                events.append(event)
            
    return events

def gachaAvailableTime(gachaid):
    gacha = getGacha(gachaid)
    if gacha is None:
        return 0
    
    events = getActiveEventsByType("gacha")
    if len(events) == 0:
        return 0
    
    event = events[0]
    activeGachaId = event["value"]
    if str(activeGachaId) != str(gachaid):
        return 0

    return event["endat"] - round(datetime.timestamp(datetime.now()))

def getActiveEventGachaId(): 
    gachas = getGachas()
    for id, gacha in gachas.items():
       if gachaAvailableTime(id) > 0:
           return gacha['id']

def randomGachaWeighted(gamer, gachaId):
    avatars = getValidAvatars(gamer, gachaId)
    if not avatars:
        return None

    weights = [av.get("weight", 1) for av in avatars]
    return random.choices(avatars, weights=weights, k=1)[0]

def loginRewardAmount():
    date = datetime.now()
    master = get_master()

    if date.month == 2 and 23 <= date.day <= 28:
        return master["config"]["boost_login_bonus_gem"]
    elif date.month == 3 and 23 <= date.day <= 28:
        return master["config"]["boost_login_bonus_gem"]
    elif date.month == 5 and 23 <= date.day <= 28:
        return master["config"]["boost_login_bonus_gem"]
    elif date.month == 6 and 23 <= date.day <= 28:
        return master["config"]["boost_login_bonus_gem"]
    elif date.month == 7 and 23 <= date.day <= 28:
        return master["config"]["boost_login_bonus_gem"]
    elif date.month == 8 and 23 <= date.day <= 28:
        return master["config"]["boost_login_bonus_gem"]
    elif date.month == 9 and 23 <= date.day <= 28:
        return master["config"]["boost_login_bonus_gem"]
    elif date.month == 12 and 9 <= date.day <= 15:
        return master["config"]["boost_login_bonus_gem"]
    else:
        return master["config"]["login_bonus_gem"]

def sortStringify(obj, indent=None):
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False)