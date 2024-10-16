# CopyFlow - A web application for transferring text to your Smart TV
CopyFlow is an app that lets you easily transfer any text to your Smart TV's clipboard — no extra software needed, just a browser.
<p align="center">
  <img width="75%" src="https://github.com/aiovin/CopyFlow/blob/main/preview.png">
</p>

## Why?
Originally, this application was designed to simplify entering VPN keys on a Smart TV by avoiding manual input.

## How to Use
- Download the source code from the [Releases page](https://github.com/aiovin/CopyFlow/releases).
  - Or use `git clone https://github.com/aiovin/CopyFlow.git`
- Install dependencies: `pip install -r requirements.txt`
- Run `python setup.py` once on the first run to generate the encryption key.
- Start the server: `python main.py`
### Once running, the application will be accessible at http://localhost:1212
Data base and log files:
- Database
`cf_data/cf_data.json`
- System Logs
`cf_data/system.log`
- Usage Logs
`cf_data/data_history.log`
