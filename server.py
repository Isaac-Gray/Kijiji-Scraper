import time, os, socket, sys, json
from pytz import utc
from apscheduler.schedulers.background import BackgroundScheduler

import KScraper as ks

if __name__ == '__main__':
        sched = BackgroundScheduler(timezone=utc)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_address = ('localhost', 10000)
        print('starting up on {} port {}'.format(*server_address))
        sock.bind(server_address)

        #listen for incoming conections
        sock.listen(1)

        print('Press Ctrl+{0} to exit'.format('Break' if os.name == 'nt' else 'C'))
        sched.start()

        try:
            while True:
                connection, client_address = sock.accept()
                print('connection from', client_address)

                # Receive the data in small chunks and retransmit it
                data = b''
                while True:
                    temp = connection.recv(1024)
                    if temp:
                        data += temp
                    else:
                        print('no data from', client_address)
                        break
                    job = json.loads(data.decode('utf-8'))
                    # second call to load into dictionary
                    # kludgey work-around
                    job = json.loads(job)
                    excludes = job['exclude'].split(',')
                    print("job request from %s submitted" % job['sender'])
                    sched.add_job(lambda: ks.scrape(job['url'],
                                                    excludes,
                                                    job['uid'],
                                                    job['sender']),
                                  'interval',
                                  seconds=int(job['seconds']))

                # Clean up the connection
                connection.close()
                time.sleep(5)
        except (KeyboardInterrupt, SystemExit):
            pass
        except Exception as e:
            print("[Error] " + str(e))
            raise e
        finally:
            sock.shutdown(1)
            sock.close()
            sched.shutdown()


