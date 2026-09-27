from http.server import HTTPServer, BaseHTTPRequestHandler
import os
import mimetypes
from urllib.parse import urlparse, parse_qs
import uuid
import re
import logging

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

logger.info("Сервер запущено.")

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            parsed_url = urlparse(self.path)
            params = parse_qs(parsed_url.query)
            if parsed_url.path == "/":
                if "uploaded" in params:
                    logger.info("Успіх: перехід на сторінку завантаження виконано!")
                    file_path = "./static/uploaded.html"
                elif "error" in params:
                    logger.error("Помилка: недопустимий файл!")
                    file_path = "./static/error.html"
                else: 
                    logger.info("Успіх: перехід на головну сторінку виконано!")
                    file_path = "./static/index.html"
            else:
                file_path = "./static" + self.path

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
        
            # отримання розширення файлу
            expansion_name = str(upload_name.split(".")[-1])

            # перевірка на розширення
            if expansion_name in {"jpg", "jpeg", "png", "gif"}:
                file_name = uuid.uuid4().hex + "." + expansion_name
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
            logger.info("Успіх: зображення %s завантажено. Розмір: %d байт.", upload_name, len(data))
            f.close()
            # print(f"f", f, flush=True)

            # передача шляху в html, для відображення
            self.send_response(303)
            self.send_header("Location", f"/?uploaded=1&file={path_local_http}")
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
