import datetime
import time
import sys
from crawler import PttSpider, Download, ArticleInfo


def main():
    # python beauty_spider2.py [版名] [爬幾頁] [推文多少以上]
    # python beauty_spider2.py beauty 3 10
    board, page_term, push_rate = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    # board, page_term, push_rate = 'beauty', 5, 10  # for debugger
    start_time = time.time()
    datetime_format = '%Y%m%d%H%M%S'
    crawler_time = '{}_PttImg_{:{}}'.format(board, datetime.datetime.now(), datetime_format)
    print('start crawler ptt {}...'.format(board))
    spider = PttSpider(board=board,
                       parser_page=page_term,
                       push_rate=push_rate)
    spider.run()
    info = ArticleInfo.data_process(spider.info, crawler_time)
    download = Download(info)
    download.run()
    print("下載完畢...")
    times = time.time() - start_time
    print('execution time: {}'.format(datetime.timedelta(seconds=times)))


if __name__ == '__main__':
    main()
