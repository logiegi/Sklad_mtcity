import gspread
from oauth2client.service_account import ServiceAccountCredentials
from config import SCOPE, SHEET_NAME, ARCHIVE_SHEET_NAME
from datetime import datetime

client = gspread.authorize(ServiceAccountCredentials.from_json_keyfile_name("credentials.json", SCOPE))

# Подключение к таблицам
stock_sheet = client.open(SHEET_NAME).sheet1
history_sheet = client.open(SHEET_NAME).worksheet("История операций")
edan_sheet = client.open(SHEET_NAME).worksheet("Edan")
getein_sheet = client.open(SHEET_NAME).worksheet("Getein")
try:
    archive_doc = client.open(ARCHIVE_SHEET_NAME)
    archive_sheet = archive_doc.sheet1
except gspread.SpreadsheetNotFound:
    archive_doc = client.create(ARCHIVE_SHEET_NAME)
    archive_sheet = archive_doc.sheet1
    archive_sheet.append_row(["Кто", "Куда", "Зачем", "GEM", "Тесты", "Количество", "Срок", "Дата операции", "Тип операции"])

def update_stock(gem: str, test: str, expiry: str, qty_change: int = 1):
    """Обновляет остатки в таблице склада."""
    col_map = {
        "3500": {"date": 1, "150": 2, "300": 3, "450": 4, "600": 5},
        "4000": {"date": 6, "150": 7, "300": 8, "450": 9, "600": 10},
        "5000": {"date": 11, "150": 12, "300": 13, "450": 14, "600": 15}
    }
    date_col = col_map[gem]["date"]
    test_col = col_map[gem][test]
    try:
        date_obj = datetime.strptime(expiry, "%Y-%m-%d")
        expiry_formatted = date_obj.strftime("%d.%m.%Y")
    except ValueError:
        expiry_formatted = expiry

    for row in range(9, 201):
        cell_value = stock_sheet.cell(row, date_col).value
        if not cell_value:
            stock_sheet.update_cell(row, date_col, expiry_formatted)
            stock_sheet.update_cell(row, test_col, qty_change if test == test else 0)
            break
        if cell_value.strip() == expiry_formatted:
            current_qty = int(stock_sheet.cell(row, test_col).value or 0)
            stock_sheet.update_cell(row, test_col, max(0, current_qty + qty_change))
            break

async def archive_history():
    """Архивирует старые записи из истории операций."""
    ARCHIVE_THRESHOLD = 1000
    history_rows = history_sheet.get_all_values()
    if len(history_rows) > ARCHIVE_THRESHOLD:
        old_rows = history_rows[1:len(history_rows) - 100]
        archive_sheet.append_rows(old_rows)
        history_sheet.delete_rows(2, len(old_rows))

# Кэш данных
preloaded_data = {}

async def refresh_preloaded_data():
    """Обновляет кэш данных из Google Sheets."""
    global preloaded_data
    while True:
        col_map = {
            "3500": {"date": 1, "150": 2, "300": 3, "450": 4, "600": 5},
            "4000": {"date": 6, "150": 7, "300": 8, "450": 9, "600": 10},
            "5000": {"date": 11, "150": 12, "300": 13, "450": 14, "600": 15}
        }
        new_data = {}
        for gem, mapping in col_map.items():
            gem_data = {}
            for key, col in mapping.items():
                values = stock_sheet.col_values(col)[8:108]
                gem_data[key] = values
            new_data[gem] = gem_data
        preloaded_data = new_data
        await asyncio.sleep(300)  # Обновление каждые 5 минут