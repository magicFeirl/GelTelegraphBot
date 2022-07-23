import os
import json

from typing import Union

path = os.path.join(*os.path.split(__file__)[:-1])

def get_model_formatter(filename: str):
    fullpath = os.path.join(path, filename)

    with open(fullpath, encoding='utf-8') as f:
        model = f.read()

    def formatter(**kwargs):
        _model = model

        for key, value in kwargs.items():
            _model = _model.replace('$' + key, value)

        return json.loads(_model)

    return formatter

def Image(src: str, caption: str = ''):
    return {
        'type': 'image',
        'caption': caption,
        'src': src
    }

def Link(href: str, text: str = ''):
    if not text:
        text = href
    
    return {
        'type': 'link',
        'href': href,
        'text': text
    }