from pyspark.sql import SparkSession
# Creare la sessione Spark
spark = SparkSession.builder \
    .appName("KafkaSparkElasticsearch") \
    .getOrCreate()

# Leggere i dati da Kafka
df = spark \
    .readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "kafka:9092") \
    .option("subscribe", "old-data") \
    .load()

# Convertire il valore da byte a stringa
df = df.selectExpr("CAST(value AS STRING)")

# Definire lo schema del JSON
schema = "id STRING, name STRING, lyrics STRING, artist STRING"

# Convertire il JSON in dataframe con lo schema definito
json_df = df.selectExpr("get_json_object(value, '$.id') as id",
                        "get_json_object(value, '$.name') as name",
                        "get_json_object(value, '$.lyrics') as lyrics",
                        "get_json_object(value, '$.artist') as artist")

# Stampa il campo lyrics
query = json_df \
    .writeStream \
    .outputMode("append") \
    .format("console") \
    .start()

query.awaitTermination()
