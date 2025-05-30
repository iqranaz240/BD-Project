from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json
from pyspark.sql.types import StructType, StructField, StringType, IntegerType
import base64
from PIL import Image
import io

# Initialize Spark session with Kafka support
spark = SparkSession.builder \
    .appName("MRI Slice Stream") \
    .config("spark.jars.packages", "org.apache.spark:spark-sql-kafka-0-10_2.12:3.2.0") \
    .config("spark.executor.memory", "2g") \
    .config("spark.driver.memory", "2g") \
    .getOrCreate()

# Define schema to match producer.py
schema = StructType([
    StructField("slice_index", IntegerType(), True),
    StructField("slice_data", StringType(), True)  # Change to StringType for base64 data
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

# Process the slices
def process_slice(slice_data, slice_index):
    if slice_data is None:
        print(f"[WARN] No data received for slice index: {slice_index}")
        return  # Skip processing if there's no data

    # Decode the base64 string back to bytes
    try:
        img_bytes = base64.b64decode(slice_data)
    except Exception as e:
        print(f"[ERROR] Failed to decode base64 for slice index {slice_index}: {e}")
        return

    # Convert bytes to an image
    try:
        image = Image.open(io.BytesIO(img_bytes))
        # Display or process the image as needed
        print(f"Received slice index: {slice_index}, image size: {image.size}")
        image.show()  # This will display the image; you can also save or process it further
    except Exception as e:
        print(f"[ERROR] Failed to open image for slice index {slice_index}: {e}")

# Use foreachBatch to apply processing logic
query = slices_df.writeStream \
    .foreachBatch(lambda batch_df, _: batch_df.rdd.foreach(
        lambda row: process_slice(row.slice_data, row.slice_index)
    )) \
    .start()

query.awaitTermination()
