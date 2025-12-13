"""
Load Raw Match Results to Databricks
This script uploads your CSV file to Databricks as a raw table
"""

from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, DateType

def load_match_results_to_databricks(csv_path: str, catalog: str = "afl_analytics_dev"):
    """
    Load match results CSV to Databricks raw schema
    
    Args:
        csv_path: Path to your local CSV file
        catalog: Databricks catalog name
    """
    
    # Initialize Spark (this works in Databricks notebooks)
    spark = SparkSession.builder.getOrCreate()
    
    # Define expected schema (adjust based on your CSV structure)
    schema = StructType([
        StructField("match_id", StringType(), True),
        StructField("match_date", StringType(), True),  # Will be cast to DATE in dbt
        StructField("home_team", StringType(), True),
        StructField("away_team", StringType(), True),
        StructField("home_score", StringType(), True),  # Will be cast to INT in dbt
        StructField("away_score", StringType(), True),  # Will be cast to INT in dbt
        StructField("venue", StringType(), True),
        StructField("round", StringType(), True),
        StructField("season", StringType(), True)       # Will be cast to INT in dbt
    ])
    
    # Read CSV
    print(f"Reading CSV from: {csv_path}")
    df = spark.read \
        .option("header", "true") \
        .option("inferSchema", "false") \
        .schema(schema) \
        .csv(csv_path)
    
    print(f"Loaded {df.count()} rows")
    
    # Create raw schema if it doesn't exist
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {catalog}.raw")
    
    # Write to raw table (overwrite each time for idempotency)
    table_name = f"{catalog}.raw.match_results_raw"
    print(f"Writing to: {table_name}")
    
    df.write \
        .mode("overwrite") \
        .format("delta") \
        .saveAsTable(table_name)
    
    print(f"✅ Successfully loaded data to {table_name}")
    print(f"Next step: Run 'dbt run --select stg_match_results'")
    
    return df

# Example usage in Databricks notebook:
# df = load_match_results_to_databricks("/Workspace/Users/your.email@company.com/match_results.csv")

# Or if you uploaded to DBFS:
# df = load_match_results_to_databricks("dbfs:/FileStore/tables/match_results.csv")
