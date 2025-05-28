import json

class MessagePayload:

    def __init__(self, binary_message: bytes):

        json_message = json.loads(binary_message)
        self.message_json = json_message
        self.vin = json_message.get('vin', None)
        self.event_time = json_message.get('event_time', None)
        self.updated_at = json_message.get('updatedAt', None)
        
        
    

    def __str__(self):
        return f"MessagePayload(vin={self.vin})"