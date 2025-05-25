from kafka import KafkaProducer
import json
import time

producer = KafkaProducer(
    bootstrap_servers='localhost:9092',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

# Example messages to send
messages = [
    {"sensor": "temperature", "value": 23.5, "unit": "C"},
    {"sensor": "humidity", "value": 60, "unit": "%"},
    {"sensor": "pressure", "value": 1012, "unit": "hPa"}
]

try:
    for msg in messages:
        print(f"Sending message: {msg}")
        producer.send('test-topic', msg)
        producer.flush()  # Make sure message is sent
        time.sleep(1)      # Sleep 1 second before sending next message
finally:
    producer.close()
