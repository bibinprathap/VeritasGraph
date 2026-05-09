"""
Stream Ingestion Module

This module provides comprehensive real-time data stream processing capabilities
for the VeritasReason framework, supporting multiple streaming platforms and
protocols.

Key Features:
    - Kafka stream processing
    - Apache Pulsar integration
    - RabbitMQ message handling
    - AWS Kinesis stream processing
    - Real-time data transformation and validation
    - Stream health monitoring and metrics
    - Error handling and retry logic

Main Classes:
    - StreamIngestor: Main stream ingestion class
    - StreamProcessor: Base stream data processor
    - KafkaProcessor: Kafka-specific processor
    - RabbitMQProcessor: RabbitMQ-specific processor
    - KinesisProcessor: AWS Kinesis-specific processor
    - PulsarProcessor: Apache Pulsar-specific processor
    - StreamMonitor: Stream health monitoring

Example Usage:
    >>> from veritasreason.ingest import StreamIngestor
    >>> ingestor = StreamIngestor()
    >>> processor = ingestor.ingest_kafka("topic", ["localhost:9092"])
    >>> processor.set_message_handler(lambda msg: print(msg))
    >>> processor.start_consuming()

Author: VeritasReason Contributors
License: MIT
"""

import json
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from ..utils.exceptions import ProcessingError, ValidationError
from ..utils.logging import get_logger


@dataclass
class StreamMessage:
    """
    Stream message representation.

    This dataclass represents a message from a streaming source with its
    content, metadata, and position information.

    Attributes:
        content: Message content (any type)
        metadata: Message metadata dictionary
        timestamp: Message timestamp
        source: Source identifier
        partition: Partition number (for partitioned streams, optional)
        offset: Message offset (optional)
    """

    content: Any
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = ""
    partition: Optional[int] = None
    offset: Optional[int] = None


class StreamProcessor:
    """
    Generic stream data processor.

    This is the base class for processing data from various streaming sources
    with common functionality including message transformation, validation,
    error handling, and statistics tracking.

    Subclasses should implement `_consume_loop()` for source-specific
    consumption logic.
    """

    def __init__(self, source_config: Dict[str, Any], **options):
        """
        Initialize stream processor.

        Sets up the processor with source configuration and processing options.

        Args:
            source_config: Source-specific configuration dictionary
            **options: Processing options:
                - transform: Optional transformation function for messages
                - validate: Optional validation function for messages
        """
        self.logger = get_logger("stream_processor")
        self.source_config = source_config
        self.options = options
        self.message_handler: Optional[Callable] = None
        self.error_handler: Optional[Callable] = None
        self.running: bool = False
        self.thread: Optional[threading.Thread] = None
        self._processed_count: int = 0
        self._error_count: int = 0

    def process_message(self, message: Any) -> Dict[str, Any]:
        """
        Process individual stream message.

        Args:
            message: Stream message to process

        Returns:
            ProcessedData: Processed message data
        """
        try:
            # Parse message content
            if isinstance(message, bytes):
                content = json.loads(message.decode("utf-8"))
            elif isinstance(message, str):
                content = json.loads(message)
            elif isinstance(message, dict):
                content = message
            else:
                content = {"raw": str(message)}

            # Extract metadata
            metadata = content.get("metadata", {})

            # Apply transformations if configured
            if self.options.get("transform"):
                transform_fn = self.options["transform"]
                content = transform_fn(content)

            # Validate data if configured
            if self.options.get("validate"):
                validate_fn = self.options["validate"]
                if not validate_fn(content):
                    raise ValidationError("Message validation failed")

            self._processed_count += 1

            return {
                "content": content,
                "metadata": metadata,
                "processed_at": datetime.now().isoformat(),
            }

        except Exception as e:
            self._error_count += 1
            self.logger.error(f"Failed to process message: {e}")

            if self.error_handler:
                self.error_handler(message, e)
            else:
                raise ProcessingError(f"Failed to process message: {e}")

    def start_consuming(self):
        """Start consuming from stream."""
        if self.running:
            self.logger.warning("Processor already running")
            return

        self.running = True
        self.thread = threading.Thread(target=self._consume_loop, daemon=True)
        self.thread.start()
        self.logger.info("Stream processor started")

    def stop_consuming(self):
        """Stop consuming from stream."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        self.logger.info("Stream processor stopped")

    def set_message_handler(self, handler: Callable):
        """Set message processing handler."""
        self.message_handler = handler

    def set_error_handler(self, handler: Callable):
        """Set error handling function."""
        self.error_handler = handler

    def _consume_loop(self):
        """Main consumption loop (to be overridden by subclasses)."""
        while self.running:
            try:
                # This will be implemented by specific processors
                time.sleep(0.1)
            except Exception as e:
                self.logger.error(f"Error in consumption loop: {e}")
                if not self.running:
                    break

    def get_stats(self) -> Dict[str, Any]:
        """Get processor statistics."""
        return {
            "processed": self._processed_count,
            "errors": self._error_count,
            "running": self.running,
        }


class KafkaProcessor(StreamProcessor):
    """Kafka stream processor."""

    def __init__(self, topic: str, bootstrap_servers: List[str], **options):
        """
        Initialize Kafka processor.

        Args:
            topic: Kafka topic name
            bootstrap_servers: List of Kafka broker addresses
            **options: Processing options
        """
        from kafka import KafkaConsumer

        source_config = {
            "type": "kafka",
            "topic": topic,
            "bootstrap_servers": bootstrap_servers,
        }
        super().__init__(source_config, **options)

        self.topic = topic
        self.consumer = KafkaConsumer(
            topic,
            bootstrap_servers=bootstrap_servers,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            **options.get("consumer_config", {}),
        )

    def _consume_loop(self):
        """Kafka consumption loop."""
        while self.running:
            try:
                message_pack = self.consumer.poll(timeout_ms=1000)
                for topic_partition, messages in message_pack.items():
                    for message in messages:
                        processed = self.process_message(message.value)
                        if self.message_handler:
                            self.message_handler(processed)
            except Exception as e:
                self.logger.error(f"Error consuming from Kafka: {e}")
                if not self.running:
                    break


class RabbitMQProcessor(StreamProcessor):
    """RabbitMQ stream processor."""

    def __init__(self, queue: str, connection_url: str, **options):
        """
        Initialize RabbitMQ processor.

        Args:
            queue: RabbitMQ queue name
            connection_url: RabbitMQ connection URL
            **options: Processing options
        """
        import pika

        source_config = {
            "type": "rabbitmq",
            "queue": queue,
            "connection_url": connection_url,
        }
        super().__init__(source_config, **options)

        self.queue = queue
        self.connection = pika.BlockingConnection(pika.URLParameters(connection_url))
        self.channel = self.connection.channel()
        self.channel.queue_declare(queue=queue, durable=options.get("durable", True))

    def _consume_loop(self):
        """RabbitMQ consumption loop."""

        def callback(ch, method, properties, body):
            try:
                processed = self.process_message(body)
                if self.message_handler:
                    self.message_handler(processed)
                ch.basic_ack(delivery_tag=method.delivery_tag)
            except Exception as e:
                self.logger.error(f"Error processing RabbitMQ message: {e}")
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

        self.channel.basic_consume(queue=self.queue, on_message_callback=callback)

        try:
            while self.running:
                self.connection.process_data_events(time_limit=1)
        except Exception as e:
            self.logger.error(f"Error in RabbitMQ consumption: {e}")
        finally:
            if self.channel:
                self.channel.close()
            if self.connection:
                self.connection.close()


class KinesisProcessor(StreamProcessor):
    """AWS Kinesis stream processor."""

    def __init__(self, stream_name: str, region: str, **options):
        """
        Initialize Kinesis processor.

        Args:
            stream_name: Kinesis stream name
            region: AWS region
            **options: Processing options
        """
        import boto3

        source_config = {
            "type": "kinesis",
            "stream_name": stream_name,
            "region": region,
        }
        super().__init__(source_config, **options)

        self.stream_name = stream_name
        self.kinesis = boto3.client("kinesis", region_name=region)
        self.shard_iterator = None

        # Get shard iterator
        response = self.kinesis.get_shard_iterator(
            StreamName=stream_name,
            ShardId=options.get("shard_id", "0"),
            ShardIteratorType=options.get("shard_iterator_type", "LATEST"),
        )
        self.shard_iterator = response["ShardIterator"]

    def _consume_loop(self):
        """Kinesis consumption loop."""
        while self.running:
            try:
                response = self.kinesis.get_records(ShardIterator=self.shard_iterator)

                for record in response["Records"]:
                    processed = self.process_message(record["Data"])
                    if self.message_handler:
                        self.message_handler(processed)

                self.shard_iterator = response["NextShardIterator"]
                time.sleep(1)  # Avoid throttling

            except Exception as e:
                self.logger.error(f"Error consuming from Kinesis: {e}")
                if not self.running:
                    break
                time.sleep(5)


class PulsarProcessor(StreamProcessor):
    """Apache Pulsar stream processor."""

    def __init__(self, topic: str, service_url: str, **options):
        """
        Initialize Pulsar processor.

        Args:
            topic: Pulsar topic name
            service_url: Pulsar service URL
            **options: Processing options
        """
        import pulsar

        source_config = {"type": "pulsar", "topic": topic, "service_url": service_url}
        super().__init__(source_config, **options)

        self.topic = topic
        self.client = pulsar.Client(service_url)
        self.consumer = self.client.subscribe(
            topic,
            subscription_name=options.get("subscription_name", "veritasreason-consumer"),
            consumer_type=pulsar.ConsumerType.Shared,
        )

    def _consume_loop(self):
        """Pulsar consumption loop."""
        while self.running:
            try:
                msg = self.consumer.receive(timeout_millis=1000)
                try:
                    processed = self.process_message(msg.data())
                    if self.message_handler:
                        self.message_handler(processed)
                    self.consumer.acknowledge(msg)
                except Exception as e:
                    self.logger.error(f"Error processing Pulsar message: {e}")
                    self.consumer.negative_acknowledge(msg)
            except Exception as e:
                if "timeout" not in str(e).lower():
                    self.logger.error(f"Error consuming from Pulsar: {e}")
                if not self.running:
                    break


class StreamMonitor:
    """
    Stream health and performance monitoring.

    Monitors stream processing health, performance
    metrics, and error rates.
    """

    def __init__(self, **config):
        """
        Initialize stream monitor.

        Args:
            **config: Monitor configuration
        """
        self.logger = get_logger("stream_monitor")
        self.config = config
        self.processors: Dict[str, StreamProcessor] = {}
        self.metrics: Dict[str, Dict[str, Any]] = {}
        self.alert_thresholds = config.get(
            "alert_thresholds",
            {
                "error_rate": 0.1,  # 10% error rate
                "max_lag": 1000,  # Maximum message lag
            },
        )

    def monitor_processor(self, processor: StreamProcessor, name: str = None):
        """
        Monitor specific stream processor.

        Args:
            processor: Stream processor to monitor
            name: Processor name (optional)
        """
        if name is None:
            name = processor.source_config.get("type", "unknown")

        self.processors[name] = processor
        self.metrics[name] = {
            "last_check": datetime.now(),
            "processed": 0,
            "errors": 0,
            "healthy": True,
        }
        self.logger.info(f"Started monitoring processor: {name}")

    def get_metrics(self, processor_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get monitoring metrics.

        Args:
            processor_name: Specific processor name

        Returns:
            dict: Monitoring metrics
        """
        if processor_name:
            if processor_name not in self.processors:
                return {}
            processor = self.processors[processor_name]
            stats = processor.get_stats()
            return {processor_name: {**self.metrics.get(processor_name, {}), **stats}}
        else:
            # Return all metrics
            all_metrics = {}
            for name, processor in self.processors.items():
                stats = processor.get_stats()
                all_metrics[name] = {**self.metrics.get(name, {}), **stats}
            return all_metrics

    def check_health(self) -> Dict[str, Any]:
        """
        Check overall stream health.

        Returns:
            dict: Health status
        """
        health_status = {
            "overall": "healthy",
            "processors": {},
            "timestamp": datetime.now().isoformat(),
        }

        unhealthy_count = 0

        for name, processor in self.processors.items():
            stats = processor.get_stats()
            metrics = self.metrics.get(name, {})

            # Calculate error rate
            total = stats.get("processed", 0) + stats.get("errors", 0)
            error_rate = stats.get("errors", 0) / total if total > 0 else 0

            is_healthy = (
                processor.running and error_rate < self.alert_thresholds["error_rate"]
            )

            if not is_healthy:
                unhealthy_count += 1

            health_status["processors"][name] = {
                "healthy": is_healthy,
                "running": processor.running,
                "error_rate": error_rate,
                "processed": stats.get("processed", 0),
                "errors": stats.get("errors", 0),
            }

        if unhealthy_count > 0:
            health_status["overall"] = (
                "unhealthy" if unhealthy_count == len(self.processors) else "degraded"
            )

        return health_status


class StreamIngestor:
    """
    Real-time stream ingestion handler.

    This class provides comprehensive stream ingestion capabilities, processing
    data streams from various sources with support for different streaming
    protocols (Kafka, Pulsar, RabbitMQ, Kinesis).

    Features:
        - Multiple streaming platform support
        - Stream health monitoring
        - Error handling and recovery
        - Message transformation and validation

    Example Usage:
        >>> ingestor = StreamIngestor()
        >>> kafka_proc = ingestor.ingest_kafka("topic", ["localhost:9092"])
        >>> kafka_proc.set_message_handler(process_message)
        >>> ingestor.start_streaming()
        >>> health = ingestor.monitor.check_health()
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        """
        Initialize stream ingestor.

        Sets up the ingestor with stream monitor. Processors are created
        dynamically when ingesting from specific sources.

        Args:
            config: Optional stream ingestion configuration dictionary
            **kwargs: Additional configuration parameters (merged into config)
        """
        self.logger = get_logger("stream_ingestor")
        self.config = config or {}
        self.config.update(kwargs)

        # Initialize stream processors dictionary
        self.processors: Dict[str, StreamProcessor] = {}

        # Setup stream monitor
        self.monitor = StreamMonitor(**self.config)

        self.logger.debug("Stream ingestor initialized")

    def ingest_kafka(
        self, topic: str, bootstrap_servers: List[str], **options
    ) -> KafkaProcessor:
        """
        Ingest data from Kafka topic.

        Args:
            topic: Kafka topic name
            bootstrap_servers: List of Kafka broker addresses
            **options: Processing options

        Returns:
            KafkaProcessor: Kafka stream processor
        """
        processor = KafkaProcessor(topic, bootstrap_servers, **options)
        self.processors[f"kafka_{topic}"] = processor
        self.monitor.monitor_processor(processor, f"kafka_{topic}")
        return processor

    def ingest_pulsar(self, topic: str, service_url: str, **options) -> PulsarProcessor:
        """
        Ingest data from Pulsar topic.

        Args:
            topic: Pulsar topic name
            service_url: Pulsar service URL
            **options: Processing options

        Returns:
            PulsarProcessor: Pulsar stream processor
        """
        processor = PulsarProcessor(topic, service_url, **options)
        self.processors[f"pulsar_{topic}"] = processor
        self.monitor.monitor_processor(processor, f"pulsar_{topic}")
        return processor

    def ingest_rabbitmq(
        self, queue: str, connection_url: str, **options
    ) -> RabbitMQProcessor:
        """
        Ingest data from RabbitMQ queue.

        Args:
            queue: RabbitMQ queue name
            connection_url: RabbitMQ connection URL
            **options: Processing options

        Returns:
            RabbitMQProcessor: RabbitMQ stream processor
        """
        processor = RabbitMQProcessor(queue, connection_url, **options)
        self.processors[f"rabbitmq_{queue}"] = processor
        self.monitor.monitor_processor(processor, f"rabbitmq_{queue}")
        return processor

    def ingest_kinesis(
        self, stream_name: str, region: str, **options
    ) -> KinesisProcessor:
        """
        Ingest data from Kinesis stream.

        Args:
            stream_name: Kinesis stream name
            region: AWS region
            **options: Processing options

        Returns:
            KinesisProcessor: Kinesis stream processor
        """
        processor = KinesisProcessor(stream_name, region, **options)
        self.processors[f"kinesis_{stream_name}"] = processor
        self.monitor.monitor_processor(processor, f"kinesis_{stream_name}")
        return processor

    def start_streaming(self, processors: Optional[List[StreamProcessor]] = None):
        """
        Start processing multiple streams.

        Args:
            processors: List of stream processors (if None, starts all)
        """
        if processors is None:
            processors = list(self.processors.values())

        for processor in processors:
            try:
                processor.start_consuming()
                self.logger.info(
                    f"Started stream processor: {processor.source_config.get('type')}"
                )
            except Exception as e:
                self.logger.error(f"Failed to start processor: {e}")
                raise ProcessingError(f"Failed to start stream processor: {e}")

    def stop_streaming(self):
        """Stop all stream processors."""
        for name, processor in self.processors.items():
            try:
                processor.stop_consuming()
                self.logger.info(f"Stopped stream processor: {name}")
            except Exception as e:
                self.logger.error(f"Error stopping processor {name}: {e}")
