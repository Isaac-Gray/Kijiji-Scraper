import email, imaplib, sys, uuid, socket, json
from bs4 import BeautifulSoup

import KScraper as ks

def submit_page_mon_request(msg, uid):
    try:
        # extract the email sender info
        email_from = msg['from']
        print('From : ' + email_from + '\n')

        # extract the email body and turn it into a dict
        if msg.is_multipart():
            for payload in msg.get_payload():
                if payload.get_content_type() == "text/html":
                    body = payload.get_payload(decode=True)
        else:
            body = msg.get_payload(decode=True)
        soup = BeautifulSoup(body, "html.parser")
        url = soup.find('a').get('href')

        request = {}
        for line in soup.findAll(text=True):
            for line2 in line.strip().split("\n"):
                if line and ':' in line:
                    typ,data = line.split(':')
                    request[typ.lower()] = data

        exclude_list = request["exclude"].split(',')
        # remove trailing spaces
        exclude_list = list(map(lambda x: x.strip(' '), exclude_list))

        message = '{"url": "%s","exclude": "%s","uid": "%s","sender": "%s"}' % (url, ','.join(exclude_list), uid, email_from)

        # Create a TCP/IP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Connect the socket to the port where the server is listening
        server_address = ('localhost', 10000)
        print('connecting to {} port {}'.format(*server_address))
        sock.connect(server_address)

        try:
            # Send data
            data = json.dumps(message)
            sock.sendall(data.encode('utf-8'))
        finally:
            sock.close()
    except Exception as e:
        print("[Error] Unable to submit monitor request: " + str(e))
        raise e


if __name__ == '__main__':
    full_msg = sys.stdin.readlines()
    msg = email.message_from_string(''.join(full_msg))
    print("email received")
    if "new request" in msg['subject']:
        submit_page_mon_request(msg, uuid.uuid4().hex)
