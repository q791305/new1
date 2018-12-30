import datetime
import time
import sys
from crawler import ArticleInfo, PttSpider, Download


def process(article):
    datetime_format = '%Y%m%d%H%M%S'
    ptt_spider = PttSpider()
    ptt_spider.run_specific_article(article)
    crawler_time = '{}_PttImg_{:{}}'.format(ptt_spider.board, datetime.datetime.now(), datetime_format)
    info = ArticleInfo.data_process(ptt_spider.info, crawler_time)
    download = Download(info)
    download.run()


def main():
    start_time = time.time()
    # 從.txt檔案中讀取 urls
    with open(sys.argv[1]) as lines:
        for url in lines:
            if PttSpider.ptt_head in url.strip():
                url = url.split(PttSpider.ptt_head)[-1].replace('\n', '')
                process(ArticleInfo(url=url))

    print('下載完畢...')
    times = time.time() - start_time
    print('execution time: {}'.format(datetime.timedelta(seconds=times)))


if __name__ == '__main__':
    main()
