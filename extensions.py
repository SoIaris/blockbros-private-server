import json
import random
import hashlib

from PIL import Image
from flask import request
from datetime import datetime
from io import BytesIO

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

with open("static/master.json", 'r') as file:
    master = json.load(file)

def GetShopItem(category, id):
    for data in master["shop"][category]:
        if data["id"] == id:
            return data
    
    return None

def getDifficultyReward(difficulty: int):
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

def randomAvatar():
    avatars = {id: av for id, av in master["avatar"].items() if av.get("ispublic", False)}

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
    
def get_coordinates(index):
    y = (index // 20) * 32
    x = (index - ((index // 20) * 20)) * 32
    return {"x": x, "y": y}

def pil_to_png_bytes(img):
    with BytesIO() as buffer:
        img.save(buffer, format="PNG")
        return buffer.getvalue()
    
def render_map(map: dict[int]):
    newMap = map
    img = Image.new('RGBA', (640, 640), (0, 0, 0, 0))
    
    for i in range(len(newMap)):
        block_value = newMap[i]
        if not block_value:
            continue
        
        decoded_block = decodeBlock(block_value)
        cords = get_coordinates(i)
        path = f"static/blocks/block{decoded_block['blockType']}_{decoded_block["attr"]}.png"
        blockimg = Image.open(path).rotate(-90)
        img.paste(blockimg, (cords['x'], cords['y']), blockimg)

    return img.rotate(-270, expand=True)

def sortStringify(obj, indent=None):
    def sorted_dict(d):
        if not isinstance(d, dict):
            return d
        return {k: sorted_dict(v) for k, v in sorted(d.items())}
    
    return json.dumps(sorted_dict(obj), indent=indent, separators=(',', ':'), ensure_ascii=False)
 
def jsonToCrc(table: dict, token: str):
    string = table
    if token != "undefined":
        string += token

    crc = hashlib.md5((string).encode()).hexdigest()
    return crc

loginRewardAmount()