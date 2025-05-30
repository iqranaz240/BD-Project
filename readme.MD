activate backend venv 
    .\\venv\Scripts\activate

run backend
    python app.py

start hadoop 
    start-all.cmd

start kafka zookeeper (inside bin/windows)
    zookeeper-server-start.bat C:\kafka\config\zookeeper.properties

start kafka server
    kafka-server-start.bat C:\kafka\config\server.properties

kafka consumer log
    kafka-console-consumer.bat --bootstrap-server localhost:9092 --topic mri-slices --from-beginning

start consumer (backend)
    python consumer.py

start producer (backend)
    python producer.py


