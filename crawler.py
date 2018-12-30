import sys
import time
import concurrent.futures
import requests
import urllib3
import os
import uuid
from bs4 import BeautifulSoup

urllib3.disable_warnings()


class PttSpider:
    rs = requests.session()
    ptt_head = 'https://www.ptt.cc'
    ptt_middle = 'bbs'
    parser_page_count = 5

    def __init__(self, **kwargs):
        self._board = kwargs.get('board', None)
        self.parser_page = int(kwargs.get('parser_page', self.parser_page_count))
        self.push_rate = int(kwargs.get('push_rate', 10))

        self._soup = None
        self._index_seqs = []
        self._articles = []
        self._data = []

    @property
    def info(self):
        return self._data

    @property
    def board(self):
        return self._board

    def run(self):
        self._soup = self.check_board()
        self._index_seqs = self.parser_index()
        self._articles = self.parser_per_article_url()
        self._data = self.analyze_articles()
        self.crawler_img_urls()

    def run_specific_article(self, article):
        self._board = article.url.split('/')[-2]
        self.check_board_over18()
        self._articles = [article]
        self._data = self.analyze_articles()
        self.crawler_img_urls(True)

    def check_board(self):
        print('check board......')
        if self._board:
            return self.check_board_over18()
        else:
            print("請輸入看版名稱")
            sys.exit()

    def check_board_over18(self):
        res = self.rs.get('{}/{}/{}/index.html'.format(self.ptt_head, self.ptt_middle, self._board),
                          verify=False)
        # 先檢查網址是否包含'over18'字串 ,如有則為18禁網站
        if 'over18' in res.url:
            print("18禁網頁")
            load = {
                'from': '/{}/{}/index.html'.format(self.ptt_middle, self._board),
                'yes': 'yes'
            }
            res = self.rs.post('{}/ask/over18'.format(self.ptt_head), verify=False, data=load)
        return BeautifulSoup(res.text, 'html.parser')

    def parser_index(self):
        print('parser index......')
        max_page = self.get_max_page(self._soup.select('.btn.wide')[1]['href'])
        return [
            '{}/{}/{}/index{}.html'.format(self.ptt_head, self.ptt_middle, self._board, page)
            for page in range(max_page - self.parser_page + 1, max_page + 1, 1)
        ]

    def parser_per_article_url(self):
        print('parser per article url......')
        articles = []
        while self._index_seqs:
            index = self._index_seqs.pop(0)
            res = self.rs.get(index, verify=False)
            # 如網頁忙線中,則先將網頁加入 _index_seqs 並休息1秒後再連接
            if res.status_code != 200:
                self._index_seqs.append(index)
                time.sleep(1)
            else:
                article = self.crawler_info(res, self.push_rate)
                if article:
                    articles += article
            time.sleep(0.05)
        return articles

    def analyze_articles(self):
        print('analyze articles......')
        # 進入每篇文章分析內容
        articles = []
        while self._articles:
            article = self._articles.pop(0)
            res = self.rs.get('{}{}'.format(self.ptt_head, article.url), verify=False)
            print('{}{} ing......'.format(self.ptt_head, article.url))
            # 如網頁忙線中,則先將網頁加入 self._articles 並休息1秒後再連接
            if res.status_code != 200:
                self._articles.append(article)
                time.sleep(1)
            else:
                article.res = res
                articles.append(article)
            time.sleep(0.05)
        return articles

    def crawler_img_urls(self, is_content_parser=False):
        for data in self._data:
            print('crawler image urls......')
            soup = BeautifulSoup(data.res.text, 'html.parser')
            title = str(uuid.uuid4())
            if is_content_parser:
                # 避免有些文章會被使用者自行刪除標題列
                try:
                    title = soup.select('.article-meta-value')[2].text
                except Exception as e:
                    print(e)
                finally:
                    data.title = title

            # 抓取圖片URL(img tag )
            for img in soup.find_all("a", rel='nofollow'):
                img_url = self.image_url(img['href'])
                if img_url:
                    data.img_urls.append(img_url)

    @staticmethod
    def image_url(link):
        # 符合圖片格式的網址
        images_format = ['.jpg', '.png', '.jpeg']
        for image in images_format:
            if link.endswith(image):
                return link
        # 有些網址會沒有檔案格式， "https://imgur.com/xxx"
        if ('imgur' in link) and ('.gif' not in link):
            return '{}.jpg'.format(link)
        return ''

    @staticmethod
    def crawler_info(res, push_rate):
        print('crawler_info......{}'.format(res.url))
        soup = BeautifulSoup(res.text, 'html.parser')
        articles = []
        for r_ent in soup.find_all(class_="r-ent"):
            try:
                # 先得到每篇文章的 url
                url = r_ent.find('a')['href']
                if not url:
                    continue
                title = r_ent.find(class_="title").text.strip()
                rate_text = r_ent.find(class_="nrec").text
                author = r_ent.find(class_="author").text

                if rate_text:
                    if rate_text.startswith('爆'):
                        rate = 100
                    elif rate_text.startswith('X'):
                        rate = -1 * int(rate_text[1])
                    else:
                        rate = rate_text
                else:
                    rate = 0

                # 比對推文數
                if int(rate) >= push_rate:
                    articles.append(ArticleInfo(
                        title=title, author=author, url=url, rate=rate))
            except Exception as e:
                print('本文已被刪除', e)
        return articles

    @staticmethod
    def get_max_page(content):
        start_index = content.find('index')
        end_index = content.find('.html')
        page_number = content[start_index + 5: end_index]
        return int(page_number) + 1


class ArticleInfo:
    def __init__(self, **kwargs):
        self.title = kwargs.get('title', None)
        self.author = kwargs.get('author', None)
        self.url = kwargs.get('url', None)
        self.rate = kwargs.get('rate', None)
        self.img_urls = []
        self.path = kwargs.get('path', None)
        self.res = None

    @staticmethod
    def data_process(info, crawler_time):
        result = []
        for data in info:
            if not data.img_urls:
                continue
            dir_name = '{}'.format(ArticleInfo.remove_special_char(data.title, '\/:*?"<>|.'))
            dir_name += '_{}'.format(data.rate) if data.rate else ''
            relative_path = os.path.join(crawler_time, dir_name)
            path = os.path.abspath(relative_path)
            try:
                if not os.path.exists(path):
                    os.makedirs(path)
                    result += [(url, path) for url in data]
            except Exception as e:
                print(e)
        return result

    @staticmethod
    def remove_special_char(value, deletechars):
        # 移除特殊字元（移除Windows上無法作為資料夾的字元）
        for c in deletechars:
            value = value.replace(c, '')
        return value.rstrip()

    def __iter__(self):
        for url in self.img_urls:
            yield url


class Download:
    rs = requests.session()

    def __init__(self, info):
        self.info = info

    def run(self):
        with concurrent.futures.ProcessPoolExecutor() as executor:
            executor.map(self.download, self.info)

    def download(self, image_info):
        url, path = image_info
        print('download image......', url)
        res_img = self.rs.get(url, stream=True, verify=False)
        file_name = url.split('/')[-1]
        file = os.path.join(path, file_name)
        try:
            with open(file, 'wb') as out_file:
                out_file.write(res_img.content)
        except Exception as e:
            print(e)
