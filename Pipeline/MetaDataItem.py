import json

class MetaDataItem:
    def __init__(self, id, title, url, collision_type, description, location):
        self.id = id
        self.title = title
        self.url = url
        self.collision_type = collision_type
        self.description = description
        self.location = location
        self.obj = {
            'title': self.title,
            'url': self.url,
            'collision_type': self.collision_type,
            'description': self.description,
            'location': self.location
        }

    def to_json_str(self) -> str:
        return json.dumps(self.obj, sort_keys=True, indent=2)
    
    def to_file(self):
        # Write the output to disk
        with open(self.id + '_metadata.json', 'w') as outfile:
            json.dump(self.obj, outfile, sort_keys=True, indent=2)