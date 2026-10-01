from psycopg import Connection
import logging

logger = logging.getLogger(__name__)

# функція пагінації
def get_images_metadata(connection: Connection, page=1):
    offset = 10 * (page - 1)
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT * FROM images ORDER BY id DESC OFFSET %s LIMIT 10;",
            [offset]
        )

        images = cursor.fetchall()

        logger.info("Пагінація, сторінка: %s", page)
        logger.info("Отримано записів: %s", len(images))
        return images