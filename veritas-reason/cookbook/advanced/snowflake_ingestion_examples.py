"""
Snowflake Ingestion Examples

This module provides comprehensive examples of using the Snowflake ingestor.
"""

import os
from datetime import datetime, timedelta

from veritasreason.ingest import SnowflakeIngestor
from veritasreason.utils.logging import get_logger

logger = get_logger("snowflake_examples")


def example_basic_ingestion():
    """Example: Basic table ingestion."""
    print("\n=== Example 1: Basic Table Ingestion ===\n")

    # Initialize ingestor with password authentication
    ingestor = SnowflakeIngestor(
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        warehouse="COMPUTE_WH",
        database="SAMPLE_DB",
        schema="PUBLIC",
    )

    # Ingest a table
    data = ingestor.ingest_table("CUSTOMERS", limit=10)

    print(f"Retrieved {data.row_count} rows")
    print(f"Columns: {data.columns}")
    print(f"\nFirst row:")
    print(data.data[0])

    ingestor.close()


def example_query_execution():
    """Example: Execute custom SQL queries."""
    print("\n=== Example 2: Query Execution ===\n")

    ingestor = SnowflakeIngestor()

    # Execute aggregation query
    query = """
        SELECT 
            COUNTRY,
            COUNT(*) AS CUSTOMER_COUNT,
            SUM(TOTAL_PURCHASES) AS TOTAL_REVENUE
        FROM CUSTOMERS
        GROUP BY COUNTRY
        ORDER BY TOTAL_REVENUE DESC
        LIMIT 10
    """

    data = ingestor.ingest_query(query)

    print(f"Top 10 countries by revenue:")
    for row in data.data:
        print(
            f"  {row['COUNTRY']}: {row['CUSTOMER_COUNT']} customers, "
            f"${row['TOTAL_REVENUE']:,.2f} revenue"
        )

    ingestor.close()


def example_parameterized_query():
    """Example: Parameterized queries."""
    print("\n=== Example 3: Parameterized Queries ===\n")

    ingestor = SnowflakeIngestor()

    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)

    # Execute parameterized query
    query = """
        SELECT 
            ORDER_ID,
            CUSTOMER_ID,
            PRODUCT_NAME,
            AMOUNT,
            ORDER_DATE
        FROM ORDERS
        WHERE ORDER_DATE BETWEEN %(start_date)s AND %(end_date)s
          AND AMOUNT > %(min_amount)s
        ORDER BY ORDER_DATE DESC
    """

    data = ingestor.ingest_query(
        query,
        params={
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "min_amount": 100.0,
        },
    )

    print(f"Found {data.row_count} orders in the last 30 days over $100")

    ingestor.close()


def example_schema_introspection():
    """Example: Table schema introspection."""
    print("\n=== Example 4: Schema Introspection ===\n")

    ingestor = SnowflakeIngestor()

    # Get table schema
    schema = ingestor.get_table_schema("CUSTOMERS")

    print("Table schema for CUSTOMERS:")
    print(f"Primary keys: {schema['primary_keys']}\n")

    print("Columns:")
    for col in schema["columns"]:
        nullable = "NULL" if col["nullable"] else "NOT NULL"
        default = f" DEFAULT {col['default']}" if col["default"] else ""
        print(f"  {col['name']}: {col['type']} {nullable}{default}")

    ingestor.close()


def example_list_tables():
    """Example: List all tables in a schema."""
    print("\n=== Example 5: List Tables ===\n")

    ingestor = SnowflakeIngestor()

    # List tables in current schema
    tables = ingestor.list_tables()

    print(f"Found {len(tables)} tables:")
    for table in tables:
        print(f"  - {table}")

    ingestor.close()


def example_pagination():
    """Example: Paginate large result sets."""
    print("\n=== Example 6: Pagination ===\n")

    ingestor = SnowflakeIngestor()

    PAGE_SIZE = 100
    total_rows = 0

    # Paginate through large table
    page = 0
    while True:
        data = ingestor.ingest_table(
            "LARGE_TABLE", limit=PAGE_SIZE, offset=page * PAGE_SIZE
        )

        if data.row_count == 0:
            break

        total_rows += data.row_count
        print(f"Page {page + 1}: {data.row_count} rows")

        # Process page
        process_page(data)

        page += 1

    print(f"\nTotal rows processed: {total_rows}")

    ingestor.close()


def example_batch_processing():
    """Example: Batch processing with fetchmany."""
    print("\n=== Example 7: Batch Processing ===\n")

    ingestor = SnowflakeIngestor()

    # Execute query with batching
    data = ingestor.ingest_query(
        "SELECT * FROM LARGE_TABLE WHERE STATUS = 'ACTIVE'", batch_size=1000
    )

    print(f"Retrieved {data.row_count} rows in batches of 1000")

    ingestor.close()


def example_export_documents():
    """Example: Export to VeritasReason document format."""
    print("\n=== Example 8: Export as Documents ===\n")

    ingestor = SnowflakeIngestor()

    # Ingest product data
    data = ingestor.ingest_table("PRODUCTS", limit=10)

    # Convert to documents
    documents = ingestor.export_as_documents(
        data, id_field="PRODUCT_ID", text_fields=["PRODUCT_NAME", "DESCRIPTION"]
    )

    print(f"Exported {len(documents)} documents")
    print("\nFirst document:")
    print(f"  ID: {documents[0]['id']}")
    print(f"  Text: {documents[0]['text'][:100]}...")
    print(f"  Metadata: {documents[0]['metadata']}")

    ingestor.close()


def example_key_pair_auth():
    """Example: Key-pair authentication."""
    print("\n=== Example 9: Key-Pair Authentication ===\n")

    ingestor = SnowflakeIngestor(
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        user=os.getenv("SNOWFLAKE_USER"),
        private_key_path=os.getenv("SNOWFLAKE_PRIVATE_KEY_PATH"),
        warehouse="COMPUTE_WH",
    )

    data = ingestor.ingest_table("CUSTOMERS", limit=5)
    print(f"Successfully authenticated and retrieved {data.row_count} rows")

    ingestor.close()


def example_context_manager():
    """Example: Using context manager."""
    print("\n=== Example 10: Context Manager ===\n")

    with SnowflakeIngestor() as ingestor:
        data = ingestor.ingest_table("CUSTOMERS", limit=5)
        print(f"Retrieved {data.row_count} rows")

    # Connection automatically closed
    print("Connection closed automatically")


def example_multi_schema():
    """Example: Multi-schema ingestion."""
    print("\n=== Example 11: Multi-Schema Ingestion ===\n")

    ingestor = SnowflakeIngestor()

    # Ingest from different schemas
    prod_customers = ingestor.ingest_table(
        "CUSTOMERS", database="PROD_DB", schema="PUBLIC", limit=10
    )

    staging_customers = ingestor.ingest_table(
        "CUSTOMERS", database="STAGING_DB", schema="PUBLIC", limit=10
    )

    print(f"Production customers: {prod_customers.row_count}")
    print(f"Staging customers: {staging_customers.row_count}")

    ingestor.close()


def example_error_handling():
    """Example: Error handling."""
    print("\n=== Example 12: Error Handling ===\n")

    from veritasreason.utils.exceptions import ProcessingError, ValidationError

    try:
        # Try to connect with invalid credentials
        ingestor = SnowflakeIngestor(
            account="invalid_account", user="invalid_user", password="invalid_password"
        )

        data = ingestor.ingest_table("CUSTOMERS")

    except ValidationError as e:
        print(f"Validation error: {e}")

    except ProcessingError as e:
        print(f"Processing error: {e}")

    except Exception as e:
        print(f"Unexpected error: {e}")


def example_incremental_load():
    """Example: Incremental data loading."""
    print("\n=== Example 13: Incremental Loading ===\n")

    ingestor = SnowflakeIngestor()

    # Get last load timestamp (from your metadata store)
    last_load = get_last_load_timestamp()  # Your function

    # Query only new/updated records
    query = """
        SELECT *
        FROM CUSTOMERS
        WHERE UPDATED_AT > %(last_load)s
        ORDER BY UPDATED_AT ASC
    """

    data = ingestor.ingest_query(query, params={"last_load": last_load})

    print(f"Loaded {data.row_count} new/updated records since {last_load}")

    # Update last load timestamp
    if data.row_count > 0:
        update_last_load_timestamp(datetime.now())

    ingestor.close()


def example_etl_pipeline():
    """Example: Full ETL pipeline."""
    print("\n=== Example 14: ETL Pipeline ===\n")

    # Extract
    ingestor = SnowflakeIngestor()

    sales_query = """
        SELECT 
            s.ORDER_ID,
            s.CUSTOMER_ID,
            c.CUSTOMER_NAME,
            s.PRODUCT_ID,
            p.PRODUCT_NAME,
            s.AMOUNT,
            s.ORDER_DATE
        FROM SALES s
        JOIN CUSTOMERS c ON s.CUSTOMER_ID = c.ID
        JOIN PRODUCTS p ON s.PRODUCT_ID = p.ID
        WHERE s.ORDER_DATE >= CURRENT_DATE - 7
    """

    data = ingestor.ingest_query(sales_query)
    print(f"Extracted {data.row_count} sales records")

    # Transform
    documents = ingestor.export_as_documents(
        data, id_field="ORDER_ID", text_fields=["CUSTOMER_NAME", "PRODUCT_NAME"]
    )
    print(f"Transformed to {len(documents)} documents")

    # Load (into VeritasReason)
    from veritasreason.pipeline import Pipeline

    pipeline = Pipeline()

    for doc in documents:
        pipeline.process_document(doc)

    print("Loaded documents into VeritasReason pipeline")

    ingestor.close()


# Utility functions for examples
def process_page(data):
    """Process a page of data."""
    # Your processing logic here
    pass


def get_last_load_timestamp():
    """Get the last load timestamp from metadata store."""
    # Your implementation here
    return (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")


def update_last_load_timestamp(timestamp):
    """Update the last load timestamp in metadata store."""
    # Your implementation here
    pass


def main():
    """Run all examples."""
    examples = [
        example_basic_ingestion,
        example_query_execution,
        example_parameterized_query,
        example_schema_introspection,
        example_list_tables,
        example_export_documents,
        example_context_manager,
        example_error_handling,
    ]

    for example_func in examples:
        try:
            example_func()
        except Exception as e:
            logger.error(f"Example {example_func.__name__} failed: {e}")


if __name__ == "__main__":
    # Set up environment variables
    # export SNOWFLAKE_ACCOUNT=your_account
    # export SNOWFLAKE_USER=your_user
    # export SNOWFLAKE_PASSWORD=your_password
    # export SNOWFLAKE_WAREHOUSE=COMPUTE_WH
    # export SNOWFLAKE_DATABASE=SAMPLE_DB
    # export SNOWFLAKE_SCHEMA=PUBLIC

    main()
