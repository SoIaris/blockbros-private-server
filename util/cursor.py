import base64
import hashlib
import hmac
import json

tagLength = 12

def sign(body, secret):
    return hmac.new(secret.encode(), body, hashlib.sha256).digest()[:tagLength]

def makeCursor(data, secret):
    body = json.dumps(data, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(sign(body, secret) + body).decode().rstrip("=")

def readCursor(cursor, secret):
    try:
        raw = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4))
        tag, body = raw[:tagLength], raw[tagLength:]
        if not hmac.compare_digest(tag, sign(body, secret)):
            raise ValueError
        return json.loads(body)
    except ValueError:
        raise ValueError("Invalid cursor")