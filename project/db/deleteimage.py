from psycopg import Connection
import logging
from pathlib import Path

logger = logging.getLogger(__name__)
IMAGES_DIR = Path(__file__).resolve().parent.parent / "images"

# функція видалення данний з таблиці
def delete_image_metadata(connection: Connection, id: int) -> bool:
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM images WHERE id = %s RETURNING filename;",
                [id]
            )
            result = cursor.fetchone()

        if result is None:
            logger.warning("Зображення з id=%s не знайдено", id)
            return False

        filename = result[0]

        connection.commit()

        # Захист від спроби вказати шлях за межами images
        if filename:
            image_name = Path(filename).name
            image_path = IMAGES_DIR / image_name

            # Якщо точного імені немає, шукаємо з розширенням
            if not image_path.is_file():
                matches = list(IMAGES_DIR.glob(f"{image_name}.*"))

                if matches:
                    image_path = matches[0]

            if image_path.is_file():
                image_path.unlink()
                logger.info("Файл %s успішно видалено", image_path.name)
            else:
                logger.warning("Файл %s не знайдено в images", filename)

        logger.info("Видалення даних з id=%s завершено", id)
        return True

    except Exception:
        connection.rollback()
        logger.exception("Помилка видалення зображення з id=%s", id)
        raise

    # image_path = os.path.join("images", filename)

    # if os.path.isfile(image_path):
    #     os.remove(image_path)
    #     print(f"Фото {filename} успішно видалено.")
    # else:
    #     print(f"Файл {filename} не знайдено.")
    # logger.info("Видалення даних - OK!")
