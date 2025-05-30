from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json
from pyspark.sql.types import StructType, StructField, StringType, IntegerType
import base64
from PIL import Image
import io
import websockets
import asyncio
import json

# Initialize WebSocket server
async def websocket_handler(websocket, path):
    while True:
        try:
            # Wait for messages from the Kafka stream
            await asyncio.sleep(0.1)  # Prevent CPU overload
        except websockets.exceptions.ConnectionClosed:
            break

# Start WebSocket server
async def start_websocket_server():
    server = await websockets.serve(websocket_handler, "localhost", 8765)
    await server.wait_closed()

# Initialize Spark session with Kafka support
spark = SparkSession.builder \
    .appName("MRI Slice Stream") \
    .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.2.0") \
    .config("spark.executor.memory", "2g") \
    .config("spark.driver.memory", "2g") \
    .getOrCreate()

# Define schema to match producer.py
schema = StructType([
    StructField("folder_name", StringType(), True),
    StructField("slice_index", IntegerType(), True),
    StructField("slice_data", StringType(), True)
])

# Read from Kafka topic
kafka_stream = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "localhost:9092") \
    .option("subscribe", "mri-slices") \
    .option("startingOffsets", "earliest") \
    .load()

# Extract and parse JSON message
slices_df = kafka_stream.selectExpr("CAST(value AS STRING) AS json_str") \
    .select(from_json(col("json_str"), schema).alias("data")) \
    .select("data.*")

# Store active WebSocket connections
active_connections = set()

# Process the slices
async def process_slice(slice_data, slice_index, folder_name):
    if slice_data is None:
        print(f"[WARN] No data received for slice index: {slice_index}")
        return

    try:
        # Create message with image data and metadata
        message = {
            "folder_name": folder_name,
            "slice_index": slice_index,
            "image_data": slice_data
        }
        
        # Send to all connected clients
        for websocket in active_connections:
            try:
                await websocket.send(json.dumps(message))
            except websockets.exceptions.ConnectionClosed:
                active_connections.remove(websocket)
                
    except Exception as e:
        print(f"[ERROR] Failed to process slice {slice_index}: {e}")

# Use foreachBatch to apply processing logic
async def process_batch(batch_df, _):
    for row in batch_df.collect():
        await process_slice(row.slice_data, row.slice_index, row.folder_name)

# Start WebSocket server in a separate thread
import threading
websocket_thread = threading.Thread(target=lambda: asyncio.run(start_websocket_server()))
websocket_thread.start()

# Start Kafka stream processing
query = slices_df.writeStream \
    .foreachBatch(lambda batch_df, _: asyncio.run(process_batch(batch_df, _))) \
    .start()

query.awaitTermination()
