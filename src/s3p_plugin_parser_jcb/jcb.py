import datetime
import time

from s3p_sdk.plugin.payloads.parsers import S3PParserBase
from s3p_sdk.types import S3PRefer, S3PDocument, S3PPlugin, S3PPluginRestrictions
from selenium.common import NoSuchElementException
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait
import dateutil
import re

class JCB(S3PParserBase):
    """
    A Parser payload that uses S3P Parser base class.
    """
    HOST = 'https://www.global.jcb/en/press/index.html'
    YEAR_BEGIN = 2023
    HOME_URL = 'https://www.global.jcb/en/press/index.html'
    TEMPLATE_URL = 'https://www.global.jcb/en/press/index.html?year={year}'

    def __init__(self, refer: S3PRefer, plugin: S3PPlugin, restrictions: S3PPluginRestrictions, web_driver: WebDriver):
        super().__init__(refer, plugin, restrictions)

        # Тут должны быть инициализированы свойства, характерные для этого парсера. Например: WebDriver
        self._driver = web_driver
        self._wait = WebDriverWait(self._driver, timeout=20)

    def _parse(self):
        """
        Метод, занимающийся парсингом. Он добавляет в _content_document документы, которые получилось обработать
        :return:
        :rtype:
        """
        # HOST - это главная ссылка на источник, по которому будет "бегать" парсер
        self.logger.debug(F"Parser enter to {self.HOST}")

        # ========================================
        # Тут должен находится блок кода, отвечающий за парсинг конкретного источника
        # -

        self._driver.set_page_load_timeout(60)

        # Получения списка страниц по годам
        current_years: list[int] = self._years_for_parsing()
        news_hrefs: list[str] = []

        for year in current_years:
            self._driver.get(self.TEMPLATE_URL.format(year=str(year)))
            time.sleep(3)
            self._agree_cookie_pass()
            news_list = self._driver.find_elements(By.XPATH,
                                                  '//*[@id="press"]/div[1]/div[1]/div/ul/li')  # список новостей за год

            for news in news_list:
                news_href = news.find_element(By.CLASS_NAME, 'news_href').get_attribute(
                    'href')  # ссылка на страницу новости
                news_hrefs.append(news_href)


        for url in news_hrefs:
            try:
                document = self._parse_news_page(url)  # парсинг страницы новости
                self._find(document)
            except Exception as e:
                # При ошибке парсинга новости, парсер продолжает свою работу
                self.logger.debug(f'news by link:{url} done parse with error {e}')
        # ---
        # ========================================

    def _years_for_parsing(self) -> list[int]:
        """
        Метод собирает все доступные года публикаций на сайте и сохраняет только те, которые больше начального года (self.YEAR_BEGIN)
        """
        # Получения списка страниц по года
        current_years: list[int] = []

        self._driver.get(self.HOME_URL)
        time.sleep(3)
        self._agree_cookie_pass()
        _year_list_elements = self._driver.find_elements(By.XPATH,
                                                        '//*[@id="news-category"]/div[1]/ul/li')  # бар с выбором года публикации
        for _year_el in _year_list_elements:
            innerText = _year_el.find_element(By.TAG_NAME, 'a').get_attribute(
                'innerText')  # выбор елемента с годом публикации
            if len(innerText) == 4 and re.match(r"^\d{4}$", innerText) and int(innerText) >= self.YEAR_BEGIN:
                current_years.append(int(innerText))  # Содержится год. Добавляем в список

        return current_years

    def _agree_cookie_pass(self):
        """
        Метод прожимает кнопку agree на модальном окне
        """
        cookie_agree_xpath = '//*[@id="gdpr_i_agree_button"]'

        try:
            cookie_button = self._driver.find_element(By.XPATH, cookie_agree_xpath)
            if WebDriverWait(self._driver, 5).until(ec.element_to_be_clickable(cookie_button)):
                cookie_button.click()
                self.logger.debug(F"Parser pass cookie modal on page: {self._driver.current_url}")
        except NoSuchElementException as e:
            self.logger.debug(f'modal agree not found on page: {self._driver.current_url}')

    def _parse_news_page(self, url: str) -> S3PDocument:
        self._driver.get(url)
        time.sleep(1)
        self._agree_cookie_pass()

        _document: S3PDocument = S3PDocument(None, None, None, None, url, None, {}, None, None)

        try:  # Парсинг даты публикации. Обязательная информация
            # _pub_date_text: str = self._driver.find_element(By.XPATH,'//*[@id="press"]/div[1]/div/div/div[2]/div/div/p/span[contains(class, "news-list--date")]').get_attribute('innerText')
            _pub_date_text: str = WebDriverWait(self._driver, 3).until(ec.presence_of_element_located((By.CLASS_NAME, 'news-list--date'))).get_attribute("innerText")
            _pub_date: datetime.datetime = dateutil.parser.parse(_pub_date_text)
            _document.published = _pub_date
        except Exception as e:
            self.logger.error(f'Page {self._driver.current_url} do not contain a publication date of news. Throw error: {e}')
            raise e

        try:  # Категория новости
            # _category_text: str = self._driver.find_element(By.XPATH,
            #                                                '//*[@id="press"]/div[1]/div/div/div[2]/div/div/p/span[contains(class, "news-list--category")]').get_attribute(
            #     'innerText')
            _category_text: str = WebDriverWait(self._driver, 3).until(
                ec.presence_of_element_located((By.CLASS_NAME, 'news-list--category'))).get_attribute("innerText")
            _document.other['category'] = _category_text
        except Exception as e:
            self.logger.error(f'Page {self._driver.current_url} do not contain a category of news. Throw error: {e}')

        try:  # Заголовок новости
            # _title = self._driver.find_element(By.XPATH,
            #                                   '//*[@id="press"]/div[1]/div/div/div[2]/div/div/h1[contains(class, "news_title")]').get_attribute(
            #     'innterText')
            _title: str = WebDriverWait(self._driver, 3).until(
                ec.presence_of_element_located((By.CLASS_NAME, 'news_title'))).get_attribute("innerText")
            _document.title = _title
        except Exception as e:
            self.logger.error(f'Page {self._driver.current_url} do not contain a title of news. Throw error: {e}')
            raise e

        try:  # Аннотация новости
            # _abstract: str = self._driver.find_element(By.XPATH, '//*[@id="press"]/div[1]/div/div/div[2]/div/div/div/p[contains(class, "txtAC")]').get_attribute('innerText')
            _abstract: str = WebDriverWait(self._driver, 3).until(
                ec.presence_of_element_located((By.CLASS_NAME, 'txtAC'))).get_attribute("innerText")
            _document.abstract = _abstract
        except Exception as e:
            self.logger.error(f'Page {self._driver.current_url} do not contain a abstract of news. Throw error: {e}')

        try:  # Text новости
            _text = WebDriverWait(self._driver, 3).until(ec.presence_of_element_located((By.XPATH, '//*[@id="press"]/div[1]/div/div/div[2]/div/div/div'))).get_attribute("innerText")
            _document.text = _text
        except Exception as e:
            self.logger.error(f'Page {self._driver.current_url}. Error parse main text of news. Throw error: {e}')
            raise e

        return _document
