import io
import json
import os
import plistlib
import re

from PIL import Image
import extensions

GRID_WIDTH = 20
GRID_HEIGHT = 20
CELL_SIZE = 32
BLOCK_TYPE_MASK = 0xFF0
FALLBACK_BACKGROUND = (40, 44, 52, 255)
RESOURCE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "thumbnail")
BLOCK_DEFINITIONS = {
    1: [(0, "block1")],
    2: [(0, "block2")],
    3: [(0, "block3"), (1, "block3_1")],
    4: [(0, "block4"), (1, "block4_1"), (2, "block4_2"), (3, "block4_3"),
        (4, "block4_4"), (5, "block4_5"), (6, "block4_6"), (7, "block4_7")],
    5: [(0, "block5"), (1, "block5_1")],
    6: [(0, "block6"), (1, "block6_1"), (2, "block6_2"), (3, "block6_3")],
    7: [(0, "block7"), (1, "block7_1"), (2, "block7_2"), (3, "block7_3"),
        (4, "block7_4"), (5, "block7_5"), (6, "block7_6")],
    8: [(0, "block8")],
    9: [(0, "block9"), (1, "block9_1"), (2, "block9_2")],
    10: [(0, "block10"), (1, "block10_1"), (2, "block10_2"), (3, "block10_3"),
         (4, "block10_4"), (5, "block10_5")],
    11: [(0, "block11_0"), (1, "block11_1")],
    12: [(0, "block12")],
    13: [(0, "block13"), (1, "block13_1")],
    14: [(0, "block14"), (1, "block14_1"), (2, "block14_2"), (3, "block14_3"),
         (4, "block14_4"), (5, "block14_5"), (6, "block14_6")],
    15: [(0, "block15"), (1, "block15_2")],
    16: [(0, "block16_0_0"), (1, "block16_1_0")],
    17: [(0, "block17"), (2, "block17_2"), (1, "block17_1"), (3, "block17_3")],
    18: [(0, "block18_1"), (1, "block18_2")],
}

NUMBER_PATTERN = re.compile(r"-?\d+(?:\.\d+)?")
BLOCK_ATLAS = None

def fetchResource(relativePath):
    path = os.path.join(RESOURCE_DIR, *relativePath.split("/"))
    print(path)
    with open(path, "rb") as handle:
        return handle.read()

class SpriteAtlas:
    def __init__(self, plistData, imageData):
        self.frames = plistlib.loads(plistData)["frames"]
        self.image = Image.open(io.BytesIO(imageData)).convert("RGBA")
        self.cache = {}

    def getFrame(self, name):
        if name not in self.cache:
            entry = self.frames.get(name)
            if entry is None:
                self.cache[name] = None
            else:
                x, y, width, height = (int(value) for value in NUMBER_PATTERN.findall(entry["frame"]))
                sprite = self.image.crop((x, y, x + width, y + height))
                if entry.get("rotated"):
                    sprite = sprite.transpose(Image.ROTATE_90)

                width, height = sprite.size
                sourceWidth, sourceHeight = (int(value) for value in NUMBER_PATTERN.findall(entry["sourceSize"]))
                offsetX, offsetY = (float(value) for value in NUMBER_PATTERN.findall(entry["offset"]))
                padded = Image.new("RGBA", (sourceWidth, sourceHeight), (0, 0, 0, 0))
                left = round((sourceWidth - width) / 2 + offsetX)
                top = round((sourceHeight - height) / 2 - offsetY)
                padded.alpha_composite(sprite, (left, top))
                self.cache[name] = padded

        return self.cache[name]

def loadBlockAtlas():
    global BLOCK_ATLAS

    if BLOCK_ATLAS is None:
        BLOCK_ATLAS = SpriteAtlas(fetchResource("main.plist"), fetchResource("main.png"))

    return BLOCK_ATLAS

def resolveFileId(blockType, attr):
    definitions = BLOCK_DEFINITIONS.get(blockType)
    if not definitions:
        return None
    
    for defAttr, fileId in definitions:
        if defAttr == attr:
            return fileId
        
    return definitions[0][1]

def loadThemeBackground(themeId, size):
    try:
        image = Image.open(io.BytesIO(fetchResource("theme/{0}.png".format(themeId)))).convert("RGBA")
    except OSError:
        return Image.new("RGBA", size, FALLBACK_BACKGROUND)
    
    ratio = max(size[0] / image.width, size[1] / image.height)
    scaled = image.resize((round(image.width * ratio), round(image.height * ratio)), Image.NEAREST)
    left = (scaled.width - size[0]) // 2
    top = (scaled.height - size[1]) // 2

    return scaled.crop((left, top, left + size[0], top + size[1]))

def generateThumbnail(levelMap, themeId):
    canvasSize = CELL_SIZE * GRID_WIDTH
    canvas = Image.new("RGBA", (canvasSize, canvasSize), (0, 0, 0, 0))
    canvas.alpha_composite(loadThemeBackground(themeId, (canvasSize, canvasSize)))
    blockAtlas = loadBlockAtlas()

    for index, value in enumerate(levelMap[:GRID_WIDTH * GRID_HEIGHT]):
        if not value:
            continue

        decodedBlock = extensions.decodeBlock(value)
        fileId = resolveFileId(decodedBlock["blockType"], decodedBlock["attr"])
        sprite = blockAtlas.getFrame("{0}.png".format(fileId)) if fileId else None
        if sprite is None:
            continue

        column = index // GRID_WIDTH
        row = index % GRID_WIDTH

        canvas.alpha_composite(
            sprite.resize((CELL_SIZE, CELL_SIZE), Image.NEAREST),
            (column * CELL_SIZE, (GRID_HEIGHT - 1 - row) * CELL_SIZE),
        )

    return canvas