import json

class MetaDataItem:
    def __init__(self, id, title, link, collision_type, description, location):
        self.id = id
        self.title = title
        self.link = link
        self.collision_type = collision_type
        self.description = description
        self.location = location

    def to_json(self) -> str:
        obj = {
            'title': self.title,
            'link': self.link,
            'collision_type': self.collision_type,
            'description': self.description,
            'location': self.location
        }
        # Write the output to disk
        with open(self.id + '_metadata.json', 'w') as outfile:
            json.dump(obj, outfile, sort_keys=True, indent=4)
        return obj