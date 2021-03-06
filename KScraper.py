#!/usr/bin/env python3

import requests, json, datetime, time, sys, os
from bs4 import BeautifulSoup
import psycopg2 as pg 


with open(os.path.join('config','config.json'),encoding='utf-8') as json_data:
    data=json.loads(json_data.read())

# Fill in the variables below with your info
#------------------------------------------
data_sender = data["sender"]
passwd = data["passwd"]
smtp_server = 'smtp.gmail.com'
smtp_port = 465
#------------------------------------------

conn = pg.connect("dbname='kijijidb'\
 user='pi'\
 host='localhost'\
 password='{}'".format(passwd))
cur = conn.cursor()

def ParseAd(html):  # Parses ad html trees and sorts relevant data into a dictionary
    ad_info = {}
    #description = html.find('div', {"class": "description"}).text.strip()
    #description = description.replace(html.find('div', {"class": "details"}).text.strip(), '')
    #print(description)
    try:
        ad_info["Title"] = html.find('a', {"class": "title"}).text.strip()
    except:
        print('[Error] Unable to parse Title data.')
        
    try:
        ad_info["Image"] = str(html.find('img'))
    except:
        print('[Error] Unable to parse Image data')

    try:
        ad_info["Url"] = 'http://www.kijiji.ca' + html.get("data-vip-url")
    except:
        print('[Error] Unable to parse URL data.')
        
    try:
        ad_info["Details"] = html.find('div', {"class": "details"}).text.strip()
    except:
        print('[Error] Unable to parse Details data.')   
        
    try:
        description = html.find('div', {"class": "description"}).text.strip()
        description = description.replace(ad_info["Details"], '')
        ad_info["Description"] = description
    except:
        print('[Error] Unable to parse Description data.')    

    try:
        ad_info["Date"] = html.find('span', {"class": "date-posted"}).text.strip()
    except:
        print('[Error] Unable to parse Date data.')    
    
    try:
        location = html.find('div', {"class": "location"}).text.strip()
        location = location.replace(ad_info["Date"], '')        
        ad_info["Location"] = location
    except:
        print('[Error] Unable to parse Location data.')

    try:
        ad_info["Price"] = html.find('div', {"class": "price"}).text.strip()
    except:
        print('[Error] Unable to parse Price data.')

    return ad_info


def writeAds(ad_dict, filename):  # Writes ads from given dictionary to given file
    try:
        file = open(filename, 'a')
        for ad_id in ad_dict:
            file.write(ad_id)
            file.write(str(ad_dict[ad_id]) + "\n")
            query = """INSERT INTO ads (ad_id, request_id, url, title)\
 VALUES(%s, %s, %s, %s)"""
            vals = (ad_id, 0, ad_dict[ad_id]["Url"], ad_dict[ad_id]["Title"])
            cur.execute(query, vals)
        conn.commit()
        file.close()
    except Exception as e:
        print('[Error] Unable to write ad(s) to file.')
        print(e)


def readAds(filename):  # Reads given file and creates a dict of ads in file
    import ast
    if not os.path.exists(filename):  # If the file doesn't exist, it makes it.
        file = open(filename, 'w')
        file.close()

    ad_dict = {}
    with open(filename, 'r') as file:
        for line in file:
            if line.strip() != '':
                index = line.find('{')
                ad_id = line[:index]
                dictionary = line[index:]
                dictionary = ast.literal_eval(dictionary)
                ad_dict[ad_id] = dictionary
    return ad_dict

def mailAd(ad_dict, email_title, receiver):  # Sends an email with a link and info of new ads
    import smtplib
    from email.mime.text import MIMEText
    from email.header import Header

    count = len(ad_dict)
    if count > 1:
        subject = str(count) + ' New ' + email_title + ' Ads Found!'
    if count == 1:
        subject = 'One New ' + email_title + ' Ad Found!'

    body = '<!DOCTYPE html> \n<html> \n<body>'
    try:
        for ad_id in ad_dict:
            body += '<p><b>' + ad_dict[ad_id]['Title'] + '</b>' + ' - ' + ad_dict[ad_id]['Location']
            body += ' - ' + ad_dict[ad_id]['Date'] + '<br /></p>'
            body += '<a href="' + ad_dict[ad_id]['Url'] + '">'
            body += ad_dict[ad_id]['Image'] + '</a>'
            body += '<p>' + ad_dict[ad_id]['Description'] + '<br />'
            if ad_dict[ad_id]['Details'] != '':
                body += ad_dict[ad_id]['Details'] + '<br />' + ad_dict[ad_id]['Price'] + '<br /><br /><br /><br /></p>'
            else:
                body += ad_dict[ad_id]['Price'] + '<br /><br /><br /><br /></p>'
    except:
        body +='<p>' +  ad_dict[ad_id]['Title'] + '<br />'
        body += ad_dict[ad_id]['Url'] + '<br /><br />' + '</p>'
        print('[Error] Unable to create body for email message')

    body += '<p>This is an automated message, please do not reply to this message.</p>'
    msg = MIMEText(body, 'html', 'utf-8')
    msg['Subject'] = Header(subject, header_name="Subject")
    msg['From'] = data_sender
    msg['To'] = receiver

    try:
        server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        server.ehlo()
    except:
        print('[Error] Unable to connect to email server.')
    try:
        server.login(data_sender, passwd)
    except:
        print('[Error] Unable to login to email server.')
    try:
        server.send_message(msg)
        server.quit()
        print('[Okay] Email message successfully delivered.')
    except:
        print('[Error] Unable to send message.')


def scrape(url, exclude_list, uid, sendr):  # Pulls page data from a given kijiji url and finds all ads on each page
    # Initialize variables for loop
    filename = 'mon_files/%s.txt' % uid
    old_ad_dict = readAds(filename)
    print("[Okay] Ad database succesfully loaded.")

    email_title = None
    ad_dict = {}
    third_party_ad_ids = []
    
    while url: 
    
        try:
            page = requests.get(url) # Get the html data from the URL
        except:
            print("[Error] Unable to load " + url)
            sys.exit(1)
    
        soup = BeautifulSoup(page.content, "html.parser")
        
        if not email_title: # If the email title doesnt exist pull it form the html data
            #email_title = soup.find('div', {'class': 'message'}).find('strong').text.strip('"')
            email_title = soup.title.string
            email_title = email_title.split('|')[0]
            email_title = toUpper(email_title)
            
        kijiji_ads = soup.find_all("div", {"class": "regular-ad"})  # Finds all ad trees in page html.
        
        third_party_ads = soup.find_all("div", {"class": "third-party"}) # Find all third-party ads to skip them
        for ad in third_party_ads:
            third_party_ad_ids.append(ad['data-ad-id'])
            
    
        exclude_list = toLower(exclude_list) # Make all words in the exclude list lower-case
        #checklist = ['miata']
        for ad in kijiji_ads:  # Creates a dictionary of all ads with ad id being the keys.
            ad_id = ad['data-ad-id'] # Get the ad id
            # Skip third-party ads and ads already found
            if (ad_id in old_ad_dict or ad_id in third_party_ad_ids):
                continue
            title = ad.find('a', {"class": "title"}).text.strip() # Get the ad title
            # If any of the title words match the exclude list then skip
            if not [False for match in exclude_list if match in title.lower()]:
                print('[Okay] New ad found! Ad id: ' + ad_id)
                ad_dict[ad_id] = ParseAd(ad) # Parse data from ad
        url = soup.find('a', {'title' : 'Next'})
        if url:
            url = 'https://www.kijiji.ca' + url['href']

    if ad_dict != {}:  # If dict not emtpy, write ads to text file and send email.
        writeAds(ad_dict, filename) # Save ads to file
        #mailAd(ad_dict, email_title, sendr) # Send out email with new ads
            
def toLower(input_list): # Rturns a given list of words to lower-case words
    output_list = list()
    for word in input_list:
        output_list.append(word.lower())
    return output_list

def toUpper(title): # Makes the first letter of every word upper-case
    new_title = list()
    title = title.split()
    for word in title:
        new_word = ''
        new_word += word[0].upper()
        if len(word) > 1:
            new_word += word[1:]
        new_title.append(new_word)
    return ' '.join(new_title)
