from psycopg import Connection
import logging

logger = logging.getLogger(__name__)

# функція додавання данний до таблиці
def insert_image_metadata(connection: Connection, filename: str, original_name: str, size: int, file_type: str):
    with connection.cursor() as cursor:
        cursor.execute(
            "INSERT INTO images (filename, original_name, size, file_type) VALUES (%s, %s, %s, %s) RETURNING id, filename;",
            [filename, original_name, size, file_type]
        )
        connection.commit()
        logger.info("Завантаження даних - OK!")
        return cursor.fetchone()