# Asterisk FastAGI Integration of Tellows Blacklist API

Fast-AGI service built with Python to use the
[Tellows Blacklist API Service](https://www.tellows.de/c/about-tellows-uk/tellows-api-partnership-program/)
within Asterisk.

It requires an API-Key which can be obtained in the [Tellows Shop.](https://shop.tellows.de/de/anrufschutz-zuhause/sperrlisten-api-key.html)

## Installation
This service was developed with the aim of running in docker.
It will also work without docker, but docker is the recommended way.

### Using docker
The latest docker-image can be found on  [DockerHub](https://hub.docker.com/r/vkettenbach/asterisk-fastagi-tellows).

Use [docker-compose.example.yml](docker-compose.example.yml) to run your container.

Running in docker, the configuration of the service is done in envrionment variables
as shown below:

```
version: "3.7"
services:
  asterisk-fastagi-tellows:
    image: vkettenbach/asterisk-fastagi-tellows:latest
    container_name: asterisk-fastagi-tellows
    restart: unless-stopped
    network_mode: host
    environment:
      APIKEYMD5: "<your api key as md5 hash>"
      HOST: "0.0.0.0"  # Listen on all interfaces
      PORT: 4573  # Listen on asterisk agi port
      TIMEOUT: 2  # Timeout 
```

### Not using docker
If not all of the four environment variables are supplied, the service will
fall back to read the file "config.yaml" - see [config.example.yaml](config.example.yaml).

So if you want to checkout the code from git an run it using python
you need to create a virtual env to run the code. The service was
developed sing Python 3.9. It will probaly work down to 3.7. It won't
work with Python 2.

Here is an example of how this is done - somewhat:


```
git pull https://github.com/kettenbach-it/asterisk-fastagi-tellows
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp config.example.yaml config.yaml
# now edit config.yaml accoring to your needs
python3 tellows.agi.py
```



## Usage in Asterisk
Here's an example how you can use this FastAGI service in Asterisk
(in a Macro) assuming you deployed it to the same host Asterisk is running
at. You can deploy it to any other docker host having internet access
reachable by your asterisk host - just adjust the hostname accordingly.  
Calls will be checked using the Tellows service and calls with score > 6  
will be sent to the "blacklistedtellows" priority and then handled by "Zapateller"
```
; Tellows check via FastAGI
exten => s,n,AGI(agi://localhost/)
exten => s,n,GotoIf($[ ${TELLOWS_SCORE} > 6 ]?blacklistedtellows)

....

; Blacklist Tellows
exten => s,n(blacklistedtellows),Set(CHANNEL(accountcode)=blacklisted-tellows)
exten => s,n(blacklistedtellows),Zapateller(answer)
exten => s,n(blacklistedtellows),Congestion()

```

## References

### Source Code
Can be found on [GitHub](https://github.com/kettenbach-it/asterisk-fastagi-tellows)

### Docker Container Image
Can be found on  [DockerHub](https://hub.docker.com/r/vkettenbach/asterisk-fastagi-tellows).

### Tellows API Documentation
[https://www.tellows.de/apidoc]() (Username: tellowskey, Password: <your_api_key>

## License
GNU AGPL v3

Fore more, see [LICENSE](LICENSE)
