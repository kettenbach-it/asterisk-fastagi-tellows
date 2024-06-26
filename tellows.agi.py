"""
Fast AGI service to lookup callerids in the tellows database
"""
import datetime
import json
import os
import socketserver
import sys

import phonenumbers
import requests
import yaml
from asterisk.agi import AGI
import redis

config = {"apikeyMd5": os.environ.get("APIKEYMD5"),
          "host": os.environ.get("HOST"),
          "port": os.environ.get("PORT"),
          "timeout": os.environ.get("TIMEOUT"),
          "redis_host": os.environ.get("REDIS_HOST", None),
          "redis_port": int(os.environ.get("REDIS_PORT", None)),
          }

if config["apikeyMd5"] is not None \
        and config["host"] is not None \
        and config["port"] is not None \
        and config["timeout"] is not None:

    print("Got configuration from environment", end=": ")
    print(config)

else:
    print("Loading config file config.yaml")
    try:
        with open("config.yaml", 'r') as stream:
            try:
                config = yaml.safe_load(stream)
                print("Got configuration from config.yaml", end=": ")
                print(config)
            except yaml.YAMLError as exc:
                print("Error opening config.yaml")
                print(exc)
    except FileNotFoundError:
        print("config.yaml not found and environment not set. Can't continue. Exiting.")
        sys.exit(-1)

if not config["apikeyMd5"] or not config["host"] or not config["port"] or not config["timeout"]:
    print(config)
    print("Missing config option(s). Exiting.")
    sys.exit(-1)


class FastAGI(socketserver.StreamRequestHandler):
    """
    FastAGI request handler for socketserver
    """
    # Close connections not finished in 5seconds.
    timeout = int(config["timeout"])

    def handle(self):
        try:
            agi = AGI(stdin=self.rfile, stdout=self.wfile, stderr=sys.stderr)
            callerid = agi.env["agi_callerid"]
            print(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), end=": ")
            print(f"Checking caller: {callerid}")
            if callerid != "anonymous":
                # Check if the number is in redis, if yes => whitelisted
                if config["redis_host"] and config["redis_port"]:
                    e164 = phonenumbers.parse(callerid, "DE")
                    fullnumber = "+" + str(e164.country_code) + str(e164.national_number)
                    print(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), end=": ")
                    print(f"Checking if {fullnumber} is listed in Redis "
                          f"on {config['redis_host']}:{config['redis_port']}")
                    redis_client = redis.Redis(host=config["redis_host"], port=config["redis_port"])
                    result = redis_client.get(fullnumber)
                    if result:
                        print(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), end=": ")
                        print(f"{fullnumber} found in Redis. Not checking tellows!")
                        self.wfile.write(b"SET VARIABLE TELLOWS_SCORE 1\n")
                        return
                    else:
                        print(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), end=": ")
                        print(f"{fullnumber} not found in Redis. Checking tellows!")

                # Check if the number is in tellows:
                # https://www.tellows.de/apidoc/#api-Live_Number_API
                agi_request = requests.request(url="https://www.tellows.de/basic/num/%s" % callerid,
                                               method="GET",
                                               params={
                                                   "json": 1
                                               },
                                               #headers={
                                               #    "X-Auth-Token": config["apikeyMd5"]
                                               #}
                                               )
                #print(agi_request.url)
                #print(agi_request.headers)
                #print(agi_request.text)
                reply = json.loads(agi_request.text.replace("Partner Data not correct", ""))
                if agi_request.status_code == 200:
                    print(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), end=": ")
                    print("Response from tellows: ", end=" ")
                    print("Numb.: " + reply["tellows"]["number"], end=", ")
                    print("Norm.Numb.: " + reply["tellows"]["normalizedNumber"],
                          end=", ")
                    print("Score: " + reply["tellows"]["score"], end=", ")
                    print("Searches: " + reply["tellows"]["searches"], end=", ")
                    print("Comments: " + reply["tellows"]["comments"], end=", ")

                    # agi.set_variable("TELLOWS_SCORE", request.json()["tellows"]["score"])
                    # agi.set_variable seems to be broken, so we write to stdout instead:
                    self.wfile.write(b"SET VARIABLE TELLOWS_SCORE %d\n" %
                                     int(reply["tellows"]["score"]))

        except TypeError as exception:
            sys.stderr.write('Unable to connect to agi://{} {}\n'.
                             format(self.client_address[0], str(exception)))
        except socketserver.socket.timeout as exception:
            sys.stderr.write('Timeout receiving data from {}\n'.
                             format(self.client_address))
        except socketserver.socket.error as exception:
            sys.stderr.write('Could not open the socket. '
                             'Is someting else listening on this port?\n')
        # except Exception as exception:  # pylint: disable=broad-except
        #     sys.stderr.write('An unknown error: {}\n'.
        #                      format(str(exception)))


if __name__ == "__main__":
    # Connecting to API
    # https://www.tellows.de/apidoc/#api-Account-GetPartnerInfo
    request = requests.request(url="https://www.tellows.de/api/getpartnerinfo",
                               method="GET",
                               headers={
                                   "X-Auth-Token": config["apikeyMd5"]
                               })

    if request.status_code == 200:
        print("Successfully connected to tellows-api", end=": ")
        print(request.json()["partnerinfo"]["info"], end="")
        try:
            print(" | Company: " + request.json()["partnerinfo"]["company"], end="")
        except KeyError:
            pass
        print(" | Allowscorelist: " + request.json()["partnerinfo"]["allowscorelist"], end="")
        print(" | Premium: " + request.json()["partnerinfo"]["premium"], end="")
        print(" | Valid until: " + request.json()["partnerinfo"]["validuntil"], end="")
        print(" | Requests: " + request.json()["partnerinfo"]["requests"], end="")
        print()
    else:
        print("Error connecting to tellows-api: " + str(request.status_code)
              + " " + request.json()['error'], end=", ")
        print(request.json()["message"])
        sys.exit(-2)

    # Create socketServer
    server = socketserver.ForkingTCPServer((config["host"], int(config["port"])), FastAGI)
    print("Starting FastAGI server on " + config["host"] + ":" + str(config["port"]))

    # Keep server running until CTRL-C is pressed.
    server.serve_forever()
