from flask import Flask, jsonify
from kafka import KafkaConsumer
import threading
import json

app = Flask(__name__)
messages = []
messages_lock = threading.Lock()

def consume_kafka():
    consumer = KafkaConsumer(
        'test-topic',
        bootstrap_servers='localhost:9092',
        auto_offset_reset='earliest',
        group_id='my-group',
        value_deserializer=lambda m: m.decode('utf-8') if m else None  # Decode bytes to str, don't parse JSON here
    )
    for msg in consumer:
        raw_value = msg.value
        if raw_value:
            try:
                # Attempt to parse JSON here with error handling
                data = json.loads(raw_value)
                with messages_lock:
                    messages.append(data)
                    if len(messages) > 1000:
                        messages.pop(0)
            except json.JSONDecodeError:
                # Skip invalid JSON messages silently or log them if you want
                print(f"Warning: skipping invalid JSON message: {raw_value}")

@app.route('/data')
def get_data():
    with messages_lock:
        recent_msgs = messages[-10:]
    return jsonify(recent_msgs)

if __name__ == '__main__':
    threading.Thread(target=consume_kafka, daemon=True).start()
    app.run(port=4000, debug=True)
