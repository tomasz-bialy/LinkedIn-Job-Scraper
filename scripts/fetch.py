import random
from selenium import webdriver
from selenium.webdriver.common.by import By
import undetected_chromedriver as uc
import time
import requests
import pandas as pd
import pickle
from scripts.helpers import strip_val, get_value_by_path


BROWSER = 'chrome'

def create_session(email, password):
    driver = uc.Chrome()
    time.sleep(1)
    driver.get('https://www.linkedin.com/')
    time.sleep(1)
    cookie_name = email.split('@')[0].replace('.', '_')
    try:
        with open("scripts/"+cookie_name+".pkl", "rb") as f:
            cookies = pickle.load(f)
        for cookie in cookies:
            driver.add_cookie(cookie)
        time.sleep(1)
        driver.refresh()
        yn_cookies = input('Managed to login? "yes" or "no": ')
    except:
        print('No cookies found for {}'.format(email))
        yn_cookies = 'no'
    if yn_cookies == 'no':
        driver.get('https://www.linkedin.com/checkpoint/rm/sign-in-another-account')
        time.sleep(1)
        driver.find_element(By.ID, 'username').send_keys(email)
        driver.find_element(By.ID, 'password').send_keys(password)
        input('Press ENTER after a successful login for "{}": '.format(email))
    driver.get('https://www.linkedin.com/jobs/search/?')
    time.sleep(1)
    cookies = driver.get_cookies()
    if yn_cookies == 'no':
        with open("scripts/"+cookie_name+".pkl", "wb") as f:
            pickle.dump(cookies, f)
    driver.quit()
    session = requests.Session()
    for cookie in cookies:
        session.cookies.set(cookie['name'], cookie['value'])
    return session

def get_logins(method):
    logins = pd.read_csv('logins.csv')
    logins = logins[logins['method'] == method]
    emails = logins['emails'].tolist()
    passwords = logins['passwords'].tolist()
    return emails, passwords

class JobSearchRetriever:
    def __init__(self):
        self.job_search_link = (
        'https://www.linkedin.com/voyager/api/voyagerJobsDashJobCards?decorationId=com.linkedin.voyager.dash.deco.jobs.search.JobSearchCardsCollection-187&count=100&q=jobSearch&query=('
        'origin:JOB_SEARCH_PAGE_OTHER_ENTRY,'
        'keywords:{keywords},'
        'locationUnion:(geoId:{geoid}),'
        'selectedFilters:('
            'sortBy:List(DD),'
            'jobType:List(F),'
            'experience:List({experience}),'
            'workplaceType:List({remote})' # 1 = on-site, 2,3 = remote + hybrid
            '),'
        'spellCorrectionEnabled:true)&start={page}'
        )
        emails, passwords = get_logins('search')
        self.sessions = [create_session(email, password) for email, password in zip(emails, passwords)]
        self.session_index = 0
        self.headers = [{
            'Authority': 'www.linkedin.com',
            'Method': 'GET',
            'Path': 'voyager/api/voyagerJobsDashJobCards?decorationId=com.linkedin.voyager.dash.deco.jobs.search.JobSearchCardsCollection-187&count=25&q=jobSearch&query=(origin:JOB_SEARCH_PAGE_OTHER_ENTRY,selectedFilters:(sortBy:List(DD)),spellCorrectionEnabled:true)&start=0',
            'Scheme': 'https',
            'Accept': 'application/vnd.linkedin.normalized+json+2.1',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.9',
            'Cookie': "; ".join([f"{key}={value}" for key, value in session.cookies.items()]),
            'Csrf-Token': session.cookies.get('JSESSIONID').strip('"'),
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
            'X-Li-Track': '{"clientVersion":"1.13.25238","mpVersion":"1.13.25238","osName":"web","timezoneOffset":9,"timezone":"Asia/Tokyo","deviceFormFactor":"DESKTOP","mpName":"voyager-web","displayDensity":1,"displayWidth":1920,"displayHeight":1080}'
        } for session in self.sessions]

    def get_jobs(self, page, keywords, experience, remote, geoid):
        results = self.sessions[self.session_index].get(self.job_search_link.format(page=page, experience=experience, keywords=keywords, remote=remote, geoid=geoid), headers=self.headers[self.session_index])
        self.session_index = (self.session_index + 1) % len(self.sessions)
        if results.status_code == 500:
            return None
        if results.status_code != 200:
            raise Exception('Status code {} for search\nText: {}'.format(results.status_code, results.text))
        results = results.json()
        job_ids = {}

        for r in results['included']:
            if r['$type'] == 'com.linkedin.voyager.dash.jobs.JobPostingCard' and 'referenceId' in r:
                job_id = int(strip_val(r['jobPostingUrn'], 1))
                job_ids[job_id] = {'sponsored': False}
                job_ids[job_id]['title'] = r.get('jobPostingTitle')
                for x in r['footerItems']:
                    if x.get('type') == 'PROMOTED':
                        job_ids[job_id]['sponsored'] = True
                        break

        return job_ids

class JobDetailRetriever:
    def __init__(self):
        self.error_count = 0
        self.job_details_link = "https://www.linkedin.com/voyager/api/jobs/jobPostings/{}?decorationId=com.linkedin.voyager.deco.jobs.web.shared.WebFullJobPosting-65"
        emails, passwords = get_logins('details')
        self.emails = emails
        self.sessions = [create_session(email, password) for email, password in zip(emails, passwords)]
        self.session_index = 0
        self.variable_paths = pd.read_csv('json_paths/data_variables.csv')
        self.headers = [{
            'Authority': 'www.linkedin.com',
            'Method': 'GET',
            'Path': '/voyager/api/search/hits?decorationId=com.linkedin.voyager.deco.jserp.WebJobSearchHitWithSalary-25&count=25&filters=List(sortBy-%3EDD,resultType-%3EJOBS)&origin=JOB_SEARCH_PAGE_JOB_FILTER&q=jserpFilters&queryContext=List(primaryHitType-%3EJOBS,spellCorrectionEnabled-%3Etrue)&start=0&topNRequestedFlavors=List(HIDDEN_GEM,IN_NETWORK,SCHOOL_RECRUIT,COMPANY_RECRUIT,SALARY,JOB_SEEKER_QUALIFIED,PRE_SCREENING_QUESTIONS,SKILL_ASSESSMENTS,ACTIVELY_HIRING_COMPANY,TOP_APPLICANT)',
            'Scheme': 'https',
            'Accept': 'application/vnd.linkedin.normalized+json+2.1',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.9',
            'Cookie': "; ".join([f"{key}={value}" for key, value in session.cookies.items()]),
            'Csrf-Token': session.cookies.get('JSESSIONID').strip('"'),
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
            'X-Li-Track': '{"clientVersion":"1.13.25238","mpVersion":"1.13.25238","osName":"web","timezoneOffset":9,"timezone":"Asia/Tokyo","deviceFormFactor":"DESKTOP","mpName":"voyager-web","displayDensity":1,"displayWidth":1920,"displayHeight":1080}'
        } for session in self.sessions]

        # self.proxies = [{'http': f'http://{proxy}', 'https': f'http://{proxy}'} for proxy in []]


    def get_job_details(self, job_ids):
        job_details = {}
        for job_id in job_ids:
            error = False
            try:
                details = self.sessions[self.session_index].get(self.job_details_link.format(job_id), headers=self.headers[self.session_index])#, proxies=self.proxies[self.session_index], timeout=5)
            except requests.exceptions.Timeout:
                print('Timeout for job {}'.format(job_id))
                error = True
            if details.status_code != 200:
                job_details[job_id] = -1
                print('Status code {} for job {} with account {}\nText: {}'.format(details.status_code, job_id, self.emails[self.session_index], details.text))
                error = True
            if error:
                self.error_count += 1
                if self.error_count > 10:
                    raise Exception('Too many errors')
            else:
                self.error_count = 0
                job_details[job_id] = details.json()
                print('Job {} done'.format(job_id))
            self.session_index = (self.session_index + 1) % len(self.sessions)
            time.sleep(.3)
        return job_details

# https://proxy2.webshare.io/register?

