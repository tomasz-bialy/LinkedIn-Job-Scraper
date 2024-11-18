from scripts.create_db import create_tables
from scripts.database_scripts import insert_job_postings
from scripts.fetch import JobSearchRetriever
import sqlite3
import time


conn = sqlite3.connect('linkedin_jobs.db')
cursor = conn.cursor()
create_tables(conn, cursor)
job_searcher = JobSearchRetriever()

GEOID = '101355337' # Japan
KEYWORDS = ['data%20science','data%20scientist','data%20engineer','analyst','python','machine%20learning','deep%20learning','mlops','ai%20engineer','business%20intelligence','credit','risk','quantitative']
EXPERIENCE = ['2','3','4']
REMOTE = ['1','2,3']
# EXPERIENCE = ['2,3,4']
# REMOTE = ['1,2,3']

for keyword in KEYWORDS:
    for experience in EXPERIENCE:
        for remote in REMOTE:
            print(f'Keyword: {keyword}, Experience: {experience}, Remote: {remote}')
            for page in range(0, 1050, 75):
                print(f'Page {page}...')
                all_results = job_searcher.get_jobs(page=page, keywords=keyword, experience=experience, remote=remote, geoid=GEOID)
                if all_results is None:
                    break
                if len(all_results) == 0:
                    break
                query = "SELECT job_id FROM jobs WHERE job_id IN ({})".format(','.join(['?'] * len(all_results)))
                cursor.execute(query, list(all_results.keys()))
                result = cursor.fetchall()
                result = [r[0] for r in result]
                new_results = {job_id: job_info for job_id, job_info in all_results.items() if job_id not in result}
                insert_job_postings(new_results, conn, cursor)
                no_new_posting = len([x for x in new_results.values()])
                print(f'New postings: {no_new_posting}')
                time.sleep(3)
