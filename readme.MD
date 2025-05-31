# Brain Tumor MRIs Volumetric Data Preprocessing and Streaming
## Advance Big Data Analytics – Course Project


start hadoop ->
    start-all.cmd

start kafka zookeeper (inside bin/windows) ->
    zookeeper-server-start.bat C:\kafka\config\zookeeper.properties

start kafka server ->
    kafka-server-start.bat C:\kafka\config\server.properties

kafka consumer log ->
    kafka-console-consumer.bat --bootstrap-server localhost:9092 --topic mri-slices --from-beginning

activate backend venv ->
    .\\venv\Scripts\activate

run backend ->
    python app.py

start consumer (backend) ->
    python consumer.py

start producer (backend) ->
    python producer.py


