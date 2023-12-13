import logging
from bs4 import BeautifulSoup
from exceptions import ParserFindTagException
from requests import RequestException


def get_response(session, url):
    try:
        response = session.get(url)
        response.encoding = 'utf-8'
        return response
    except RequestException:
        logging.exception(
            f'Возникла ошибка при загрузке страницы {url}',
            stack_info=True
        )


def find_tag(soup, tag, attrs=None):
    searched_tag = soup.find(tag, attrs=(attrs or {}))
    if searched_tag is None:
        error_msg = f'Не найден тег {tag} {attrs}'
        logging.error(error_msg, stack_info=True)
        raise ParserFindTagException(error_msg)
    return searched_tag


def cook_soup(session, url, encoding='UTF-8', features='lxml'):
    return BeautifulSoup(
        get_response(session, url, encoding).text, features=features
    )


def get_soup(session, url):
    return BeautifulSoup(get_response(session, url).text, features='lxml')
