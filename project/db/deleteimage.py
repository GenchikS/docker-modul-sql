from psycopg import Connection
import logging

logger = logging.getLogger(__name__)

# функція видалення данний з таблиці
def delete_image_metadata(connection: Connection, id: int):
    with connection.cursore() as cursor:
        cursor.execute(
            "DELETE FROM images WHERE id = %s;",
            [id]
        )
    logger.info("Видалення даних - OK!")