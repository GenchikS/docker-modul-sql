from http.server import HTTPServer, BaseHTTPRequestHandler
import os
import mimetypes
from urllib.parse import urlparse, parse_qs
import uuid
import re
import logging
import psycopg
import time
from db.postgres import insert_image_metadata
from db.pagination import get_images_metadata
from db.deleteimage import delete_image_metadata

# пошук, вичитування та завантаження index.html
# file = open("static/index.html", "r")
# html = file.read()
# file.close()
file = None
file_upload = None
file_local_path = None

logging.basicConfig(
    filename="/project/logs/app.log",
    level=logging.INFO,
    format="[%(asctime)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

logger = logging.getLogger(__name__)



connwction = None

for attempt in range(10):
    try:
        connection = psycopg.connect("postgresql://images_backend:123456789@db:5432/images_hosting")
        logger.info("З'єднання з БД - ОК!")
        break
    except psycopg.OperationalError as e:
        logger.warning(
            "БД ще недоступна. Спроба %d/10: %s",
            attempt + 1,
            e
        )
        time.sleep(2)

if connection is None:
    logger.error("Не вдалося підключитися до БД!")
    raise RuntimeError("PostgreSQL недоступний")


# створення таблиці. Додано NOT EXISTS - щоб не створювалася нова таблиця, якщо вона вже існує
with connection.cursor() as cursor:
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS images (
            id SERIAL PRIMARY KEY,
            filename TEXT NOT NULL,
            original_name TEXT NOT NULL,
            size INTEGER NOT NULL,
            upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            file_type TEXT NOT NULL
        );
        """
    )
connection.commit()
connection.close()
logger.info("Таблиця images готова!")


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        logger.info("Сервер запущено.")
        try:
            parsed_url = urlparse(self.path)
            params = parse_qs(parsed_url.query)
            if parsed_url.path == "/":
                logger.info("Успіх: перехід на головну сторінку виконано!")
                file_path = "./static/index.html"
            elif parsed_url.path == "/upload":
                logger.info("Успіх: перехід на сторінку завантаження виконано!")
                file_path = "./static/upload.html"
            elif parsed_url.path == "/images-list":
                logger.info("Успіх: перехід до списку зображень!")
                file_path = "./static/imageslist.html"
            elif parsed_url.path == "/error":
                logger.error("Помилка: недопустимий файл!")
                file_path = "./static/error.html"
            else:
                file_path = "./static" + parsed_url.path

            # завантаження css
            if os.path.isfile(file_path):
                with open(file_path, "rb") as file:
                    content = file.read()
                    
                content_type = mimetypes.guess_type(file_path)[0]

                if content_type is None:
                    content_type = "application/octet-stream"

                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.end_headers()

                self.wfile.write(content)

            else:
                self.send_response(404)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(b"404 - File not found")

        except Exception as e:
            logger.exception(f"Помилка: {e}")
            self.send_response(500)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"500 - Internal Server Error")
  
  
    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length"))
            body = self.rfile.read(length)
            # flush=True - вивід відразу, щоб не було буферізації
            # print("Розмір:", len(body), flush=True)

            # перевірка на розмір файлу (5Мб)
            size_photo = len(body)
            if size_photo > 5000000:
                logger.error("Помилка: недопустимо великий розмір файлу!")
                self.send_response(303)
                self.send_header("Location", "/?error=1")
                self.end_headers()
                return

            # код опрацювання завантаження файлу
            boundary = self.headers["Content-Type"].split("boundary=")[-1].encode()
            # відділення headers від body
            start = body.find(b"\r\n\r\n") + 4
            end = body.find(b"\r\n--" + boundary, start)

            data = body[start:end]

            upload_match = re.search(
                rb'filename="([^"]*)"', body
                )

            # файл не знайдено
            if not upload_match:
                logger.error("Помилка: файл не обрано!")
                self.send_response(303)
                self.send_header("Location", "/?error=1")
                self.end_headers()
                return

            # отримання імені файлу
            upload_name = upload_match.group(1).decode()

            # якщо відсутня назва файлу
            if not upload_name:
                logger.error("Помилка: файл не обрано!")
                self.send_response(303)
                self.send_header("Location", "/?error=1")
                self.end_headers()
                return
            
            # створення нової назви файлу
            new_name = uuid.uuid4().hex
        
            # отримання розширення файлу
            expansion_name = str(upload_name.split(".")[-1])

            # перевірка на розширення
            if expansion_name in {"jpg", "jpeg", "png", "gif"}:
                file_name = new_name + "." + expansion_name
            else:
                logger.error("Помилка: недопустиме розширення файлу %s.", expansion_name)
                self.send_response(303)
                self.send_header("Location", "/?error=1")
                self.end_headers()
                return
            
            path_local = f"./images/{file_name}"
            # створення шляху для передачі в html
            path_local_http = path_local[1:]
            
            # запис унікальної назви файлу
            # with open(f"{path_local}", "wb") as file_upload:
            #     file_upload.write(data)

            # завантаження фото
            f = open(path_local, "wb")
            f.write(data)
            f.close()
            # print(f"f", f, flush=True)

            connection = psycopg.connect("postgresql://images_backend:123456789@db:5432/images_hosting")

            # передача даних в функцію додавання даних до таблиці та збереження id
            inserted_id = insert_image_metadata(
                connection,
                new_name,
                upload_name,
                len(data),
                expansion_name
            )
            logger.info(f"Успіх: файл з id {inserted_id} завантажено до db!")
            connection.close()

            # передача шляху в html, для відображення
            self.send_response(303)
            self.send_header("Location", f"/upload?file={path_local_http}")
            logger.info("Успіх: посилання на файл згенеровано!")
            self.end_headers()
    
            # self.send_response(200)
            # self.send_header("Content-Type", "text/plain")
            # self.end_headers()
            # self.wfile.write(f"http://locolhost:8080/{path_local}".encode())
        
        except Exception as e:
            logger.exception(f"Помилка: {e}")
            self.send_response(500)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"500 - Internal Server Error")


server = HTTPServer(("0.0.0.0", 8080), Handler)
server.serve_forever()
