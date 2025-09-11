from util.bad_words import words
import re

def filterText(message):
    for word in words:
        word = word.lower()
        message = re.sub(r'\b' + re.escape(word) + r'\b', "I love unicorn", message, flags=re.IGNORECASE)

    return message
