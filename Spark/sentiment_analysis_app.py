from pyspark.sql import SparkSession
from pyspark.sql.functions import udf, col, concat_ws
from pyspark.sql.types import StringType
import nltk
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import re

# Specifica un percorso alternativo per il download
nltk.data.path.append('/tmp/nltk_data')
nltk.download('vader_lexicon', download_dir='/tmp/nltk_data')

# Creare la sessione Spark
spark = SparkSession.builder \
    .appName("KafkaSparkElasticsearch") \
    .getOrCreate()

# Inizializzare il SentimentIntensityAnalyzer
sid = SentimentIntensityAnalyzer()

# Definire la funzione di preprocessing
def preprocess_text(text):
    if text:
        # Convertire tutto in minuscolo
        text = text.lower()
        # Rimuovere la punteggiatura
        text = re.sub(r'[^\w\s]', '', text)
        # Rimuovere spazi bianchi extra
        text = re.sub(r'\s+', ' ', text).strip()
    return text

# Definire la funzione di sentiment analysis
def sentiment_analysis(text):
    if text:
        scores = sid.polarity_scores(text)
        return str(scores['compound'])
    else:
        return str(0.0)

# Definire la funzione per categorizzare il sentimento
def categorize_sentiment(lyrics, compound_score):
    if lyrics == "Lyrics not found":
        return "not applicable"
    score = float(compound_score)
    if score > 0.5:
        return 'positive'
    elif score > 0.0:
        return 'slightly positive'
    elif score == 0.0:
        return 'neutral'
    elif score > -0.5:
        return 'slightly negative'
    else:
        return 'negative'

# Creare le UDF
preprocess_udf = udf(preprocess_text, StringType())
sentiment_udf = udf(sentiment_analysis, StringType())
categorize_udf = udf(lambda lyrics, sentiment: categorize_sentiment(lyrics, sentiment), StringType())

# Leggere i dati da Kafka
df = spark \
    .readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "kafka:9092") \
    .option("subscribe", "data") \
    .load()

# Convertire il valore da byte a stringa e includere il timestamp
df = df.selectExpr("CAST(value AS STRING) AS value", "timestamp")

# Definire lo schema del JSON
schema = "id STRING, name STRING, lyrics STRING, artist STRING, topic STRING"

# Convertire il JSON in dataframe con lo schema definito
json_df = df.selectExpr("get_json_object(value, '$.id') as id",
                        "get_json_object(value, '$.name') as name",
                        "get_json_object(value, '$.lyrics') as lyrics",
                        "get_json_object(value, '$.artist') as artist",
                        "get_json_object(value, '$.topic') as topic",
                        "timestamp")

# Applicare la funzione di preprocessing sul campo lyrics
preprocessed_df = json_df.withColumn("cleaned_lyrics", preprocess_udf(col("lyrics")))

# Applicare la funzione di sentiment analysis sul campo cleaned_lyrics
sentiment_df = preprocessed_df.withColumn("sentiment", sentiment_udf(col("cleaned_lyrics")))

# Applicare la funzione di categorizzazione del sentimento sul campo sentiment
result_df = sentiment_df.withColumn("sentiment_category", categorize_udf(col("lyrics"), col("sentiment")))

# Creare una colonna per il nuovo id combinando id e timestamp
result_df = result_df.withColumn("combined_id", concat_ws("_", col("id"), col("timestamp").cast("string")))

# Configura Elasticsearch writer
es_write_config = {
    "es.nodes": "elastic:9200",  # Replace with your Elasticsearch host
    "es.index.auto.create": True,  # Create index if it doesn't exist
    "es.mapping.id": "combined_id",  # Define the document ID field
    "es.resource": "music_analysis"  # Specify the Elasticsearch resource
}

checkpoint_location = "/opt/spark/data/checkpoint"  # Sostituisci con la posizione desiderata

result_df.writeStream \
    .outputMode("append") \
    .format("es") \
    .options(**es_write_config) \
    .option("checkpointLocation", checkpoint_location) \
    .start() \
    .awaitTermination()
