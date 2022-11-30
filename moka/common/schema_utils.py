import datetime

def to_camel(string: str) -> str:
    words = string.split('_')
    return words[0] + ''.join(word.capitalize() for word in words[1:])

def datetime_encoder(v: datetime.datetime):
    return v.strftime('%Y-%m-%dT%H:%M:%SZ')