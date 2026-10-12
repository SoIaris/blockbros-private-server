import json
import random
import hashlib

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
},

# made this a function so it gets a updated master if changed without restarting the api
def get_master():
    with open("master.json", 'r', encoding="utf-8") as file:
        master = json.load(file)

        return master

    return None

def isGamerBanned(gamer):
    now = round(datetime.timestamp(datetime.now()))
    return gamer.visibleAt > now

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

def getGacha(gachaid):
    return get_master()["avatar"][gachaid]

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
        return
    
    events = getActiveEventsByType("gacha")
    if len(events) == 0:
        return 0
    
    event = events[0]
    activeGachaId = event["value"]
    if activeGachaId != gachaid:
        return 0

    return event["endat"] - round(datetime.timestamp(datetime.now()))

def getActiveEventGachaId(): 
    master = get_master()
    gachas = master["avatar"] 
    for id, gacha in gachas.items():
       if gachaAvailableTime(id) > 0:
           return gacha['id']

def randomAvatar(inventory):
    master = get_master()
    avatars = {id: av for id, av in master["avatar"].items() if av.get("ispublic", False) and id not in inventory}

    total = sum(av["weight"] for av in avatars.values())
    probs = {id: av["weight"] / total for id, av in avatars.items()}

    r = random.uniform(0, 1)
    cp = 0

    for id, p in probs.items():
        cp += p
        if r <= cp:
            return avatars[id]
        
    return 1

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

print(getActiveEventGachaId())