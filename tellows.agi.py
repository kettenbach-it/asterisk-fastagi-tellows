"""
Fast AGI service to lookup callerids in the tellows database
"""
import datetime
import os
import socketserver
import sys

import requests
import yaml
from asterisk.agi import AGI

config = {}

config["apikeyMd5"] = os.environ.get("APIKEYMD5")
config["host"] = os.environ.get("HOST")
config["port"] = os.environ.get("PORT")
config["timeout"] = os.environ.get("TIMEOUT")

if config["apikeyMd5"] is not None \
        and config["host"] is not None \
        and config["port"] is not None \
        and config["timeout"] is not None:

    print("Got configuration from environment")
    print(config)

else:
    print("Loading config file config.yaml")
    with open("config.yaml", 'r') as stream:
        try:
            config = yaml.safe_load(stream)
            print("Got configuration from config.yaml")
            print(config)
        except yaml.YAMLError as exc:
            print("Error opening config.yaml")
            print(exc)

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
            if callerid != "anonymous":
                # https://www.tellows.de/apidoc/#api-Live_Number_API
                agi_request = requests.request(url="https://www.tellows.de/basic/num/%s" % callerid,
                                               method="GET",
                                               params={
                                                   "json": 1
                                               },
                                               headers={
                                                   "X-Auth-Token": config["apikeyMd5"]
                                               })
                if agi_request.status_code == 200:
                    print(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), end=": ")
                    print(callerid, end=", ")
                    print("Numb.: " + agi_request.json()["tellows"]["number"], end=", ")
                    print("Norm.Numb.: " + agi_request.json()["tellows"]["normalizedNumber"],
                          end=", ")
                    print("Score: " + agi_request.json()["tellows"]["score"], end=", ")
                    print("Searches: " + agi_request.json()["tellows"]["searches"], end=", ")
                    print("Comments: " + agi_request.json()["tellows"]["comments"], end=", ")

                    # agi.set_variable("TELLOWS_SCORE", request.json()["tellows"]["score"])
                    # agi.set_variable seems to be broken, so we write to stdout instead:
                    self.wfile.write(b"SET VARIABLE TELLOWS_SCORE %d" %
                                     int(agi_request.json()["tellows"]["score"]))

        except TypeError as exception:
            sys.stderr.write('Unable to connect to agi://{} {}\n'.
                             format(self.client_address[0], str(exception)))
        except socketserver.socket.timeout as exception:
            sys.stderr.write('Timeout receiving data from {}\n'.
                             format(self.client_address))
        except socketserver.socket.error as exception:
            sys.stderr.write('Could not open the socket. '
                             'Is someting else listening on this port?\n')
        except Exception as exception:  # pylint: disable=broad-except
            sys.stderr.write('An unknown error: {}\n'.
                             format(str(exception)))


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
