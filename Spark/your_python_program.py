# Import the necessary modules
from pyspark.sql import SparkSession

# Create a SparkSession
spark = SparkSession.builder \
    .appName("My App") \
    .master("local") \
    .getOrCreate()

try:
    # Use the existing SparkSession to create an RDD
    rdd = spark.sparkContext.parallelize(range(1,100))

    print("THE SUM IS HERE: ", rdd.sum())
finally:
    # Stop the SparkSession
    spark.stop()
