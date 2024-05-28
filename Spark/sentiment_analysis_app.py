from pyspark.sql import SparkSession
from pyspark.sql.functions import udf
from pyspark.sql.types import StringType
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer

# Specifica un percorso alternativo per il download
nltk.data.path.append('/tmp/nltk_data')
nltk.download('vader_lexicon', download_dir='/tmp/nltk_data')

# Creare la sessione Spark
spark = SparkSession.builder \
    .appName("KafkaSparkElasticsearch") \
    .getOrCreate()

# Inizializzare il SentimentIntensityAnalyzer
sid = SentimentIntensityAnalyzer()

# Definire la funzione di sentiment analysis
def sentiment_analysis(text):
    if text:
        scores = sid.polarity_scores(text)
        #take only the compound score
        scores = scores['compound']
        return str(scores)
    else:
        return str(0.0)

# Creare la UDF
sentiment_udf = udf(sentiment_analysis, StringType())

# Leggere i dati da Kafka
df = spark \
    .readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "kafka:9092") \
    .option("subscribe", "old-data") \
    .load()

# Convertire il valore da byte a stringa
df = df.selectExpr("CAST(value AS STRING) AS value")

# Definire lo schema del JSON
schema = "id STRING, name STRING, lyrics STRING, artist STRING, topic STRING"

# Convertire il JSON in dataframe con lo schema definito
json_df = df.selectExpr("get_json_object(value, '$.id') as id",
                        "get_json_object(value, '$.name') as name",
                        "get_json_object(value, '$.lyrics') as lyrics",
                        "get_json_object(value, '$.artist') as artist",
                        "get_json_object(value, '$.topic') as topic")

# Applicare la funzione di sentiment analysis sul campo lyrics
result_df = json_df.withColumn("sentiment", sentiment_udf(json_df.lyrics))

# Stampa il dataframe risultante con il sentiment
query = result_df \
    .writeStream \
    .outputMode("append") \
    .format("console") \
    .start()

query.awaitTermination()
