import json

class SerializableContext(object):
    def __init__(self, context):
        self.serializable = context.get_serializeable()

    def add_state_data_from(self, context):
        try:
            self.serializable.state = context.state.data
        except AttributeError:
            pass

    def json_dumps(self):
        return json.dumps(self.serializable)

    def state(self):
        return self.serializable['state']
