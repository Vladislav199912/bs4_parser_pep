from pathlib import Path
from urllib.parse import urljoin

MAIN_DOC_URL = 'https://docs.python.org/3/'
BASE_DIR = Path(__file__).parent
DATETIME_FORMAT = '%Y-%m-%d_%H-%M-%S'
LOG_FORMAT = '"%(asctime)s - [%(levelname)s] - %(message)s"'
DT_FORMAT = '%d.%m.%Y %H:%M:%S'
DOWNLOADS_URL = urljoin(MAIN_DOC_URL, 'download.html')
DOWNLOADS_DIR = 'downloads'
DOWNLOAD_COMPLETE_FORMAT = 'Архив был загружен и сохранён: {archive_path}'
PEP = 'https://peps.python.org/'
EXPECTED_STATUS = {
    'A': ('Active', 'Accepted'),
    'D': ('Deferred',),
    'F': ('Final',),
    'P': ('Provisional',),
    'R': ('Rejected',),
    'S': ('Superseded',),
    'W': ('Withdrawn',),
    '': ('Draft', 'Active'),
}
PEP_TABLE = [('Статус', 'Количество')]
WHATS_NEW_RESULT_TABLE = [('Ссылка на статью', 'Заголовок', 'Редактор, Автор')]
LATEST_VERSIONS_RESULT_TABLE = [('Ссылка на документацию', 'Версия', 'Статус')]
