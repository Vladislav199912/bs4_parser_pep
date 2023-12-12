import logging
import re
from urllib.parse import urljoin

import requests_cache
from bs4 import BeautifulSoup
from configs import configure_argument_parser, configure_logging
from constants import (BASE_DIR, EXPECTED_STATUS, LATEST_VERSIONS_RESULT_TABLE,
                       MAIN_DOC_URL, PEP, PEP_TABLE, WHATS_NEW_RESULT_TABLE)
from outputs import control_output
from tqdm import tqdm
from utils import find_tag, get_response


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
    downloads_url = urljoin(MAIN_DOC_URL, 'download.html')
    response = get_response(session, downloads_url)
    if response is None:
        return
    soup = BeautifulSoup(response.text, features='lxml')
    main_div = find_tag(soup, 'table', attrs={'class': 'docutils'})
    pdf_a4_tag = find_tag(
        main_div, 'a', attrs={'href': re.compile(r'.+pdf-a4\.zip$')}
    )
    pdf_a4_link = urljoin(downloads_url, pdf_a4_tag['href'])
    filename = pdf_a4_link.split('/')[-1]
    downloads_dir = BASE_DIR / 'downloads'
    downloads_dir.mkdir(exist_ok=True)
    archive_path = downloads_dir / filename
    download = session.get(pdf_a4_link)
    with open(archive_path, mode='wb') as file:
        file.write(download.content)
    logging.info(f"Архив был загружен и сохранён: {archive_path}")


def pep(session):
    response = get_response(session, PEP_TABLE)
    result = [('Статус', 'Количество')]
    soup = BeautifulSoup(response.text, features='lxml')
    all_tables = soup.find('section', id='numerical-index')
    all_tables = all_tables.find_all('tr')
    pep_count = 0
    status_count = {}
    for table in tqdm(all_tables, desc='Parsing'):
        rows = table.find_all('td')
        all_status = None
        link = None
        for i, row in enumerate(rows):
            if i == 0 and len(row.text) == 2:
                all_status = row.text[1]
                continue
            if i == 1:
                link_tag = find_tag(row, 'a')
                link = link_tag['href']
                break
        link = urljoin(PEP, link)
        response = get_response(session, link)
        soup = BeautifulSoup(response.text, features='lxml')
        dl = find_tag(soup, 'dl', attrs={'class': 'rfc2822 field-list simple'})
        pattern = (
                r'.*(?P<status>Active|Draft|Final|Provisional|Rejected|'
                r'Superseded|Withdrawn|Deferred|April Fool!|Accepted)'
            )
        re_text = re.search(pattern, dl.text)
        status = None
        if re_text:
            status = re_text.group('status')
        if all_status and EXPECTED_STATUS.get(all_status) != status:
            logging.info(
                f'Несовпадающие статусы:\n{link}\n'
                f'Статус в карточке: {status}\n'
                f'Ожидаемый статус: {EXPECTED_STATUS[all_status]}'
            )
        if not all_status and status not in ('Active', 'Draft'):
            logging.info(
                f'Несовпадающие статусы:\n{link}\n'
                f'Статус в карточке: {status}\n'
                f'Ожидаемые статусы: ["Active", "Draft"]'
            )
        pep_count += 1
        status_count[status] += 1
    result.extend(status_count.items())
    result.append(('Total', pep_count))
    return result


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
    session = requests_cache.CachedSession()
    if args.clear_cache:
        session.cache.clear()
    parser_mode = args.mode
    results = MODE_TO_FUNCTION[parser_mode](session)
    if results is not None:
        control_output(results, args)
    logging.info('Парсер завершил работу.')


if __name__ == '__main__':
    main()
