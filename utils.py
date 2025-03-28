import time
import logging
import re
from PIL import Image
import io
import pytesseract


def log_time(func):
    """Логирует время выполнения функции."""

    async def wrapper(*args, **kwargs):
        start_time = time.time()
        result = await func(*args, **kwargs)
        elapsed = time.time() - start_time
        logging.info(f"Handler {func.__name__} processed in {elapsed:.3f} seconds")
        return result

    return wrapper


def extract_gem_info(ocr_text: str) -> tuple[str | None, str | None, str | None]:
    """Извлекает информацию о GEM из OCR-текста."""
    # Улучшенные паттерны для распознавания
    gem = re.search(r'(?:GEM Premier|GP)\s*(\d{4,5})', ocr_text, re.IGNORECASE)
    expiry = re.search(r'(?:\d{4}-\d{2}-\d{2})|(?:\d{2}\.\d{2}\.\d{4})|(?:\d{2}/\d{2}/\d{4})', ocr_text)
    tests = (
            re.search(r'(?:Samples|Tests|y\s*ta)\s*[:\-]?\s*(\d{3,4})', ocr_text, re.IGNORECASE) or
            re.search(r'(\d{3,4})\s*(?:Samples|Tests)', ocr_text, re.IGNORECASE)
    )

    gem_value = gem.group(1) if gem else None
    expiry_value = expiry.group(0) if expiry else None
    tests_value = tests.group(1) if tests else None

    # Корректировка формата даты
    if expiry_value:
        for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
            try:
                from datetime import datetime
                expiry_value = datetime.strptime(expiry_value, fmt).strftime("%d.%m.%Y")
                break
            except ValueError:
                continue

    # Приведение тестов к стандартным значениям
    if tests_value and tests_value in {"150", "300", "450", "600"}:
        return gem_value, expiry_value, tests_value
    elif tests_value:
        tests_int = int(tests_value)
        if 0 <= tests_int - 150 <= 50:
            return gem_value, expiry_value, "150"
        elif 0 <= tests_int - 300 <= 50:
            return gem_value, expiry_value, "300"
        elif 0 <= tests_int - 450 <= 50:
            return gem_value, expiry_value, "450"
        elif 0 <= tests_int - 600 <= 50:
            return gem_value, expiry_value, "600"

    return gem_value, expiry_value, tests_value


async def process_image(image: bytes) -> str:
    """Обрабатывает изображение и возвращает распознанный текст."""
    img = Image.open(io.BytesIO(image))
    # Предобработка изображения для улучшения OCR
    img = img.convert("L")  # Черно-белое изображение
    img = img.point(lambda x: 0 if x < 128 else 255, "1")  # Бинаризация
    return pytesseract.image_to_string(img, lang="eng+rus")