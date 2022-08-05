import selenium
from selenium import webdriver
from tempfile import mkdtemp
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from retrying import retry
import boto3
import pandas as pd
from datetime import date
from datetime import timedelta

import ECW
import DataConfig as dict_Config
import requests
import os
import time


def retry_if_timeout_exception(exception):
    """
    For the retry decorator...
    Return True if we should retry (in this case when it's an TimeoutException), False otherwise
    """
    return isinstance(exception, selenium.common.exceptions.TimeoutException)

def site_is_up(dict_Config):
    """
    Test to make sure the site is up.
    If site is reachable returns true, else false
    """
    res = requests.get(dict_Config['EBO_URL'])
    if res.status_code == 200:
        return True
    else:
        return False

def file_is_downloaded(default_download_dir):
    """Test to see if the download is findable. If not found returns false, else true."""
    print(f"Checking to see if file is found in the {default_download_dir} folder...")
    if not os.listdir(default_download_dir):
        return False
    else:
        return True

@retry(retry_on_exception=retry_if_timeout_exception, stop_max_attempt_number=7, wait_fixed=20000)
def click_clickdrop(driver):
    """Series of selenium navigation steps..."""
    print("trying click_clickdrop...")
    click_ok = WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.CLASS_NAME, "mc_2707393951")))
    click_ok.click()
    click_drop = WebDriverWait(driver, 60).until(EC.element_to_be_clickable((By.XPATH,
                                                                             "/html/body/form[1]/table/tbody/tr[2]/td/table/tbody/tr/td[2]/table/tbody/tr/td/table/tbody/tr/td[5]/div/table/tbody/tr/td[1]/img")))
    click_drop.click()
    click_drop = WebDriverWait(driver, 10).until(EC.presence_of_element_located(
        (By.XPATH, " /html/body/div[3]/table/tbody/tr[4]/td/div/table/tbody/tr/td[2]")))
    click_drop.click()
    click_drop = WebDriverWait(driver, 10).until(EC.presence_of_element_located(
        (By.XPATH, " /html/body/div[4]/table/tbody/tr[1]/td/div/table/tbody/tr/td[2]")))
    click_drop.click()  # TODO is this where the actual download button gets clicked?
    time.sleep(20)  # how long do we need to wait for a download? I changed from 5 to 20...

@retry(retry_on_exception=retry_if_timeout_exception, stop_max_attempt_number=7, wait_fixed=20000)
def set_daterange(Previous_Date, driver):
    """Series of selenium navigation steps..."""
    print("trying set_daterange...")
    From_DateRange = WebDriverWait(driver, 30).until(
        EC.element_to_be_clickable((By.CLASS_NAME, "clsSelectDateEditBox")))
    print("from daterange element found...")
    From_DateRange.click()
    print("clicked from daterange...")
    From_DateRange.send_keys(Keys.LEFT_SHIFT + Keys.HOME + Keys.DELETE)
    time.sleep(2)
    From_DateRange.send_keys(Previous_Date)
    time.sleep(2)
    print("Entered Previous date:", Previous_Date)
    select_all = WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.XPATH,
                                                                                 "/html/body/form[1]/table/tbody/tr[3]/td/div/div/table/tbody/tr[2]/td/div/table/tbody/tr/td[1]/table/tbody/tr[2]/td[2]/div/table/tbody/tr/td[2]/div[2]/a[1]")))
    select_all.click()
    print("clicked select all...")
    UnCheck_Summary = WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.XPATH,
                                                                                      "/html/body/form[1]/table/tbody/tr[3]/td/div/div/table/tbody/tr[2]/td/div/table/tbody/tr/td[1]/table/tbody/tr[3]/td[2]/div/table/tbody/tr/td[2]/div[1]/div/div[1]/div/input")))
    UnCheck_Summary.click()
    print("clicked uncheck summary...")
    Check_Detail = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH,
                                                                                   "/html/body/form[1]/table/tbody/tr[3]/td/div/div/table/tbody/tr[2]/td/div/table/tbody/tr/td[1]/table/tbody/tr[3]/td[2]/div/table/tbody/tr/td[2]/div[1]/div/div[2]/div/input")))
    Check_Detail.click()
    print("clicked check detail...")

@retry(retry_on_exception=retry_if_timeout_exception, stop_max_attempt_number=7, wait_fixed=20000)
def sign_in(self, dict_Config, driver):
    # get username
    Username = WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.XPATH, '//*[@id="CAMUsername"]')))
    Username.send_keys(dict_Config['EBO_Username'])
    # get password
    Password = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '//*[@id="CAMPassword"]')))
    Password.send_keys(dict_Config['EBO_Password'])
    # click submit
    Submit = driver.find_element(By.CLASS_NAME, 'loginButton')
    Submit.send_keys("\n")
    print("login successful...")
    time.sleep(5)

def upload_to_aws(self, local_file, bucket, s3_file, dict_config):
    s3 = boto3.client('s3', aws_access_key_id=dict_config["ACCESS_KEY"], aws_secret_access_key=dict_config["SECRET_KEY"])
    try:
        s3.upload_file(local_file, bucket, s3_file)
        print("Upload Successful")
        return True
    except FileNotFoundError:
        print("The file was not found")
        return False
    except NoCredentialsError:
        print("Credentials not available")
        return False

def migrate_405_Report(local_file):
    try:
        dict_Config = dc.dataconfig
        now = datetime.now()
        date_time = now.strftime("%Y-%m-%d %H:%M:%S")

        df = pd.read_excel(local_file)
        list_in = ['None', 'Referral To Direct Address', 'Appointment Encounter ID']
        my_list = list(df)
        for item in my_list:
            if any(map(str.isdigit, item)):
                del df[item]
            else:
                for otheritem in list_in:
                    if otheritem == item:
                        del df[item]
        col = len(df.columns)
        print(col)
        df = df.replace(np.nan, 0)
        # SQL Connection
        con = pymysql.connect(
            host=dict_Config['DB_ServerName'],
            user=dict_Config["DB_Username"],
            password=dict_Config['DB_Password'],
            db=dict_Config['DB_Name']
        )
        cur = con.cursor()
        DB_Name = dict_Config['DB_Name']
        DB_Table_Name = dict_Config['DB_Table_Name']
        s_list = []
        for i in range(col):
            s_list.append('%s')
        s_list.append('%s')
        s_list = ', '.join(s_list)
        dt = str(date_time)
        # select_stmt="select count(*) from Optima.OutboundReferralReport_405 where Creation_Date like "%date_time%""
        stmt = "INSERT INTO Optima.OutboundReferralReport_405 values({})"
        for index, row in df.iterrows():
            list_of_elems = []
            for i in range(col):
                list_of_elems.append(row[i])
            list_of_elems.append(dt)
            cur.execute(stmt.format(s_list), list_of_elems)
            con.commit()
    except pymysql.MySQLError as e:
        print(e)

def download_405_Report():
    """This method is the driver -- calls other methods."""
    # set some vars
    dict_Config = dc.dataconfig
    Today_Date = date.today()
    Previous_Date = Today_Date - timedelta(days=1)
    Previous_Date = Previous_Date.strftime('%d %b %Y')
    Today_Date = Today_Date.strftime('%d %b %Y')  # TODO duplicate Today_Date... why? overwrites Today_Date above...
    print("Today's date:", Today_Date)

    # method calls here
    if site_is_up(dict_Config):
        driver = setup_driver(dict_Config)
        self.sign_in(dict_Config, driver)
        self.set_daterange(Previous_Date, driver)
        self.click_clickdrop(driver)
        if self.file_is_downloaded(self.default_download_dir):
            print("download found")
            local_file = os.path.join(self.current_dir, "downloads", "4.05 - Outgoing Referral.xlsx")
            print(f"local file is {local_file}")
            df = pd.read_excel(local_file)  # just testing...
            print(df.head())  # just testing...

            # TODO Design Decision: use intermediate s3 bucket or just go ahead with the migration. Exec time ~2 minutes at this point so I think we have plenty of room to write the migration in here..

            # send that file to S3?
            # TODO make a bucket named "report_downloads"
            # uploaded = self.upload_to_aws(local_file, 'report_downloads', 'new_report_405')

            # or just put the merge right here? I think we have plenty of time...
            # self.migrate_405_Report(local_file)

        else:
            # TODO decide what to do if the download is not found/executed...
            print("download not found")
            exit()

def handler(event=None, context=None):
    options = webdriver.ChromeOptions()
    options.binary_location = '/opt/chrome/chrome'
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280x1696")
    options.add_argument("--single-process")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-dev-tools")
    options.add_argument("--no-zygote")
    options.add_argument(f"--user-data-dir={mkdtemp()}")
    options.add_argument(f"--data-path={mkdtemp()}")
    options.add_argument(f"--disk-cache-dir={mkdtemp()}")
    options.add_argument("--remote-debugging-port=9222")
    driver = webdriver.Chrome("/opt/chromedriver", options=options)

    # nav to login page
    if site_is_up(dict_Config):
        driver.get(dict_Config['EBO_URL'])
        driver.maximize_window()

        Today_Date = date.today()
        Previous_Date = Today_Date - timedelta(days=1)
        Previous_Date = Previous_Date.strftime('%d %b %Y')
        Today_Date = Today_Date.strftime('%d %b %Y')  # TODO duplicate Today_Date... why? overwrites Today_Date above...
        print("Today's date:", Today_Date)

        sign_in(dict_Config, driver)
        set_daterange(Previous_Date, driver)
        click_clickdrop(driver)
        if file_is_downloaded("/tmp/"):
            print("download found")
            local_file = "/tmp/4.05 - Outgoing Referral.xlsx"
            print(f"local file is {local_file}")
            df = pd.read_excel(local_file)  # just testing...
            print(df.head())



    driver.get("https://example.com/")
    return driver.find_element(by=By.XPATH, value="//html").text
