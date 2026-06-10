"""Small RabbitMQ consumer wrapper used by eval_logic workers."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import Any

from workers.config import WorkerConfig

LOGGER = logging.getLogger(__name__)
MessageHandler = Callable[[dict[str, Any]], None]


class RabbitWorker:
    def __init__(self, config: WorkerConfig, queue_name: str, handler: MessageHandler) -> None:
        self.config = config
        self.queue_name = queue_name
        self.handler = handler

    def _connection_parameters(self) -> Any:
        try:
            import pika
        except Exception as exc:
            raise RuntimeError("pika is required to run RabbitMQ workers. Install eval_logic requirements.") from exc

        credentials = pika.PlainCredentials(
            self.config.rabbitmq_username,
            self.config.rabbitmq_password,
        )
        return pika.ConnectionParameters(
            host=self.config.rabbitmq_host,
            port=self.config.rabbitmq_port,
            virtual_host=self.config.rabbitmq_virtual_host,
            credentials=credentials,
            heartbeat=self.config.rabbitmq_heartbeat,
            blocked_connection_timeout=self.config.rabbitmq_blocked_connection_timeout,
        )

    def run_forever(self) -> None:
        try:
            import pika
        except Exception as exc:
            raise RuntimeError("pika is required to run RabbitMQ workers. Install eval_logic requirements.") from exc

        connection = pika.BlockingConnection(self._connection_parameters())
        channel = connection.channel()
        channel.basic_qos(prefetch_count=self.config.prefetch_count)
        channel.queue_declare(queue=self.queue_name, durable=True)

        def on_message(ch: Any, method: Any, properties: Any, body: bytes) -> None:
            try:
                payload = json.loads(body.decode("utf-8"))
                if not isinstance(payload, dict):
                    raise ValueError("RabbitMQ payload must be a JSON object.")
                self.handler(payload)
            except ValueError:
                LOGGER.exception("Discarding invalid RabbitMQ payload from %s", self.queue_name)
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return
            except Exception:
                LOGGER.exception("Failed to process RabbitMQ message from %s", self.queue_name)
                ch.basic_nack(
                    delivery_tag=method.delivery_tag,
                    requeue=self.config.requeue_on_callback_failure,
                )
                return
            ch.basic_ack(delivery_tag=method.delivery_tag)

        channel.basic_consume(queue=self.queue_name, on_message_callback=on_message)
        LOGGER.info("Consuming RabbitMQ queue=%s host=%s", self.queue_name, self.config.rabbitmq_host)
        channel.start_consuming()
