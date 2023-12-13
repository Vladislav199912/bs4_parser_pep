import logging
import re
from urllib.parse import urljoin
from collections import defaultdict

import requests_cache
from bs4 import BeautifulSoup
from configs import configure_argument_parser, configure_logging
from constants import (BASE_DIR, EXPECTED_STATUS, LATEST_VERSIONS_RESULT_TABLE,
                       MAIN_DOC_URL, PEP, WHATS_NEW_RESULT_TABLE,
                       DOWNLOADS_DIR, DOWNLOADS_URL, DOWNLOAD_COMPLETE_FORMAT)
from outputs import control_output
from tqdm import tqdm
from utils import find_tag, get_response, cook_soup, get_soup

PARSER_ERROR = ('Сбой в работе программы: {error}')
INCONGRUITY_STATUSES_FORMAT = (
    '{packet_url}'
    ' Статус в карточке: {card_status} '
    'Ожидаемые статусы: {expected}'
)
STATUS_MISSMATCH_ERROR = (
    'Несовпадающие статусы:\n'
    '{pep_link}\n'
    'Статус в картрочке {status}\n'
    'Ожидаемые статусы: {preview_status}'
)
FILE_UPLOAD_LOG = ('Архив был загружен и сохранён: {archive_path}')


def whats_new(session):
    whats_new_url = urljoin(MAIN_DOC_URL, 'whatsnew/')
    response = get_response(session, whats_new_url)
    if response is None:
        return
    soup = BeautifulSoup(response.text, features='lxml')
    main_div = find_tag(soup, 'section', attrs={'id': 'what-s-new-in-python'})
    div_with_ul = find_tag(main_div, 'div', attrs={'class': 'toctree-wrapper'})
    sections_by_python = div_with_ul.find_all(
        'li', attrs={'class': 'toctree-l1'}
    )
    results = WHATS_NEW_RESULT_TABLE
    for section in tqdm(sections_by_python):
        version_a_tag = find_tag(section, 'a')
        href = version_a_tag['href']
        version_link = urljoin(whats_new_url, href)
        response = get_response(session, version_link)
        if response is None:
            continue
        soup = BeautifulSoup(response.text, features='lxml')
        h1 = find_tag(soup, 'h1')
        dl = find_tag(soup, 'dl')
        dl_text = dl.text.replace('\n', ' ')
        results.append((version_link, h1.text, dl_text))
    return results


def latest_versions(session):
    response = get_response(session, MAIN_DOC_URL)
    if response is None:
        return
    soup = BeautifulSoup(response.text, 'lxml')
    sidebar = find_tag(soup, 'div', attrs={'class': 'sphinxsidebarwrapper'})
    ul_tags = sidebar.find_all('ul')
    for ul in ul_tags:
        if 'All versions' in ul.text:
            a_tags = ul.find_all('a')
            break
    else:
        raise Exception('Ничего не нашлось')
    results = LATEST_VERSIONS_RESULT_TABLE
    pattern = r'Python (?P<version>\d\.\d+) \((?P<status>.*)\)'
    for a_tag in a_tags:
        link = a_tag['href']
        text_match = re.search(pattern, a_tag.text)
        if text_match is not None:
            version, status = text_match.groups()
        else:
            version, status = a_tag.text, ''
        results.append(
            (link, version, status)
        )
    return results


def download(session):
    soup = get_soup(session, DOWNLOADS_URL)
    pdf_a4_link = soup.select_one('table.docutils a[href$="pdf-a4.zip"]')[
        'href'
    ]
    archive_url = urljoin(DOWNLOADS_URL, pdf_a4_link)
    filename = archive_url.split('/')[-1]
    response = session.get(archive_url)
    downloads_dir = BASE_DIR / DOWNLOADS_DIR
    downloads_dir.mkdir(exist_ok=True)
    with open(downloads_dir / filename, 'wb') as file:
        file.write(response.content)
    logging.info(DOWNLOAD_COMPLETE_FORMAT.format(archive_path=downloads_dir))


def pep(session):
    soup = cook_soup(session, PEP)
    section_block = find_tag(soup, 'section', attrs={'id': 'numerical-index'})
    table = find_tag(section_block, 'tbody')
    status_sum = defaultdict()
    logs = []
    for table_line in tqdm(table.find_all('tr')):
        main_table_status = find_tag(table_line, 'td').text[1:]
        url = find_tag(table_line, 'a').get('href')
        packet_url = urljoin(PEP, url)
        try:
            packet_soup = cook_soup(session, packet_url)
            packet_info = find_tag(
                packet_soup, 'dl', attrs={'class': 'rfc2822 field-list simple'}
            )
            card_status = (
                packet_info.find(text=re.compile('Status.*'))
                .parent.find_next_sibling()
                .text
            )
            expected = EXPECTED_STATUS.get(main_table_status)
            if card_status not in expected:
                logs.append(
                    INCONGRUITY_STATUSES_FORMAT.format(
                        packet_url=packet_url,
                        card_status=card_status,
                        expected=expected,
                    )
                )
            packet_status = (
                packet_info.find(text=re.compile('Status.*'))
                .parent.find_next_sibling()
                .text
            )
            status_sum[packet_status] += 1
        except ConnectionError as error:
            logs.append(error)
    for log in logs:
        logging.info(log)
    return [
        ('Статус', 'Количество'),
        *status_sum.items(),
        ('Итого', sum(status_sum.values())),
    ]


MODE_TO_FUNCTION = {
    'whats-new': whats_new,
    'latest-versions': latest_versions,
    'download': download,
    'pep': pep,
}


def main():
    configure_logging()
    logging.info('Парсер запущен!')
    arg_parser = configure_argument_parser(MODE_TO_FUNCTION.keys())
    args = arg_parser.parse_args()
    logging.info(f'Аргументы командной строки: {args}')
    try:
        session = requests_cache.CachedSession()
        if args.clear_cache:
            session.cache.clear()
        parser_mode = args.mode
        results = MODE_TO_FUNCTION[parser_mode](session)
        if results is not None:
            control_output(results, args)
    except Exception as error:
        error_msg = PARSER_ERROR.format(error=error)
        logging.error(error_msg, exc_info=True)
    logging.info('Парсер завершил работу.')


if __name__ == '__main__':
    main()
