import json
import uuid
import datetime
import sys
import os

def send_message(recipient_id, text, sender_id):
    message_id = str(uuid.uuid4())
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    
    payload = {
        "id": message_id,
        "recipient": recipient_id,
        "sender": sender_id,
        "priority": "MESSAGE_PRIORITY_HIGH",
        "timestamp": timestamp,
        "content": text,
        "sourceMetadata": {
            "tool": {
                "conversationId": sender_id,
                "stepIndex": 1,
                "toolCall": {
                    "id": "call_123456",
                    "name": "send_message",
                    "argumentsJson": "{}"
                }
            }
        }
    }
    
    home = os.path.expanduser("~")
    messages_dir = os.path.join(home, ".gemini", "antigravity-cli", "brain", recipient_id, ".system_generated", "messages")
    os.makedirs(messages_dir, exist_ok=True)
    
    filepath = os.path.join(messages_dir, f"{message_id}.json")
    with open(filepath, "w") as f:
        json.dump(payload, f)
        
    print(f"Message dropped at {filepath}")

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python t12_send.py <recipient_id> <sender_id> <message>")
        sys.exit(1)
    
    send_message(sys.argv[1], sys.argv[3], sys.argv[2])
