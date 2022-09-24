import threading
from multiprocessing import Manager, Process, Pool
from queue import Empty
import logging

import psycopg2 as psycopg2
import requests

loglevel = logging.INFO


def fill_queue(queue, database_config):
    logging.basicConfig(level=loglevel)
    conn = psycopg2.connect(**database_config)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id,document_id,content_type,size,content_text,content_text_ocr,author,creation_date,last_modified,last_saved from documents"
    )
    names = ["id",
             "document_id",
             "content_type",
             "size",
             "content",
             "content_ocr",
             "author",
             "creation_date",
             "last_modified",
             "last_saved"]
    for idx, row in enumerate(cursor):
        doc = dict(zip(names, row))

        # 1972-05-20T17:33:18Z
        for d in ["last_modified", "last_saved", "creation_date"]:
            if doc[d] is not None:
                doc[d] = doc[d].strftime("%Y-%m-%dT%H:%M:%SZ")

        # join consultaton data
        consultation_cursor = conn.cursor()
        consultation_qry ="SELECT consultations.consultation_id,name,topic,type,text FROM document_consultation INNER JOIN consultations ON document_consultation.consultation_id=consultations.id WHERE document_consultation.document_id = '" + str(doc["id"]) + "';"
        consultation_cursor.execute(consultation_qry
        consultation = consultation_cursor.fetchone()
        if consultation is not None:
            doc["consultation_id"] = consultation[0]
            doc["consultation_name"] = consultation[1]
            doc["consultation_topic"] = consultation[2]
            doc["consultation_type"] = consultation[3]
            doc["consultation_text"] = consultation[4]
        doc['doc_type'] = "ris.document"

        queue.put(doc)
        # print(f"queued {idx} ({queue.qsize()})")


def solr_post_url(solr_config, commit=False):
    return f"http://{solr_config['host']}:{solr_config['port']}/solr/{solr_config['core']}/update?commit={str(commit).lower()}"


def post(docs, solr_config, commit=False):
    url = solr_post_url(solr_config, commit)
    logging.info(f"{threading.get_ident()}: Posting {len(docs)} documents to {url}")
    response = requests.post(url, json=docs)
    if response.status_code != 200:
        logging.error(response.text)


def post_worker(queue, solr_config, batch_size=1):
    logging.basicConfig(level=loglevel)
    docs = []
    while True:
        try:
            doc = queue.get(timeout=1)
            docs.append(doc)
            # print(docs)
            if len(docs) >= batch_size:
                post(docs, solr_config, commit=False)
                docs = []
        except Empty:
            post(docs, solr_config, commit=True)
            logging.info("Queue Empty. Exiting")
            break


database_config = dict(
    host="localhost",
    database="riscraper",
    user="riscraper",
    password="riscraper"
)

solr_config = dict(
    host="127.0.0.1",
    port="8983",
    core="ris"
)

threads = 10
batch_size = 100

if __name__ == "__main__":
    logging.basicConfig(level=loglevel)
    logging.info(f"Processing data. Threads={threads}, Batch Size={batch_size}")
    manager = Manager()
    queue = manager.Queue(threads)  # kinda a queue

    filler = Process(target=fill_queue, args=(queue, database_config))
    filler.start()

    # give queue some time to post
    worker_pool = Pool(threads)
    worker = []
    for i in range(threads):
        worker.append(worker_pool.apply_async(post_worker, (queue, solr_config, batch_size)))

    filler.join()
    logging.info("filler done")
    [w.get() for w in worker]
    logging.info("worker done")

    result = requests.get(solr_post_url(solr_config, commit=True))
    logging.info(result.content)
    if result.status_code == 200:
        logging.info("Commited")
    else:
        logging.info("Commit failed? " + str(result.status_code))