import json


class ArticleObject(object):

    def __init__(self, **context):
        self.data = context
        self.fields = list(context.keys())
        for k, v in context.items():
            setattr(self, k, v)

    def to_json(self, **kwargs):
        return json.dumps(self.data, ensure_ascii=False, **kwargs)

    def __getitem__(self, item):
        if item in self.data:
            return self.data[item]
        return f'no such attribute: {item}'

    def __str__(self):
        return f'Article<{self.pmid}>'

    __repr__ = __str__
