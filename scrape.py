from scripts.create_db import create_tables
from scripts.database_scripts import insert_job_postings
from scripts.database_scripts import insert_data
from scripts.fetch import JobSearchRetriever
from scripts.fetch import JobDetailRetriever
from scripts.helpers import clean_job_postings
import sqlite3
import time
import random


conn = sqlite3.connect('linkedin_jobs.db')
cursor = conn.cursor()
create_tables(conn, cursor)
job_searcher = JobSearchRetriever()
job_detail_retriever = JobDetailRetriever()

GEOID = '101355337' # Japan
KEYWORDS = ['data%20science','data%20scientist','data%20engineer','analyst','python','machine%20learning','deep%20learning','mlops','ai%20engineer','business%20intelligence','credit','risk','quantitative']
EXPERIENCE = ['2','3','4']
REMOTE = ['1','2,3']
# EXPERIENCE = ['2,3,4']
# REMOTE = ['1,2,3']



