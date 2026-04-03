"""
Author: Patan Musthakheem
Date & Time: 2026-04-03 13:06
"""
from email.message import EmailMessage
import json
import requests
import socket
import logging
import smtplib
import load_dotenv
import os

load_dotenv.load_dotenv()

logging.basicConfig(filename='service_monitor.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def load_services():
    try:
        with open('services.json', 'r') as f:
            services = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        services = {}
    return services 


def check_internet():
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return True
    except OSError:
        return False


def load_state():
    try:
        with open('state.json', 'r') as f:        
            state = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        state = {}
    return state


def update_state(new_state):
    with open('state.json', 'w') as f:
        json.dump(new_state, f, indent=4)

    
def send_email(recipients: list, name, is_up=False):
    subject = f"Service Alert - {name} is {'UP' if is_up else 'DOWN'}"

    body = f"""
<html>
<body style="font-family: Arial, sans-serif;">

<p>Dear User,</p>

<p>This is an automated notification from <b>MiniMinds Server Monitor Team</b>.</p>

<p>
We would like to inform you that the service 
<b>{name}</b> is currently 
<b style="color: {'green' if is_up else 'red'};">
{"UP" if is_up else "DOWN"}
</b>.
</p>

<p><b>Status Update:</b><br>
{"✅ The service is now operational and functioning normally."
 if is_up else
 "⚠️ The service is currently experiencing downtime. The team is investigating the issue and will fix soon."}
</p></b>

<hr>

<p><b>Service Details:</b></p>
    <b>Service Name:</b> {name}
    <br>
    <b>Status:</b> {"UP" if is_up else "DOWN"}
<hr>

<p>
Best Regards,<br>
<b>MiniMinds Server Team</b>
</p>

</body>
</html>
"""

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = os.getenv("EMAIL_USER")
    
    msg.add_alternative(body, subtype='html')

    try:
        with smtplib.SMTP(os.getenv("SMTP_SERVER"), int(os.getenv("SMTP_PORT"))) as server:
            server.starttls()
            server.login(os.getenv("EMAIL_USER"), os.getenv("EMAIL_PASSWORD"))

            for recipient in recipients:
                msg["To"] = recipient
                server.send_message(msg)
                del msg["To"]  

        return True

    except Exception as e:
        return str(e)

def main():
    logging.info('-'*25 + ' Cron Job Started ' + '-'*25)
    logging.info("Starting service monitor...") 
    logging.info("Checking Internet connectivity...")
    internet = check_internet()
    if not internet:
        logging.error("No Internet connectivity.")
        return
    logging.info("Internet connectivity is up.")
    logging.info("Loading services...")
    services = load_services()
    if not services:
        # In future will send a mail to admin
        logging.warning("No services to monitor. Exiting.")
        return
    state = load_state()
    
    for key in services:
        service = services[key]
        name = service['name']
        if name not in state:
            state[name] = {"status": "down", "fail_count": 0, "is_mail_sent": False}
            
        try:
            logging.info(f"Checking {name} at {service['url']}...")
            resp = requests.get(service['url'], timeout=10)
            is_up = resp.status_code == 200
        except requests.RequestException:
            logging.error(f"[-] {name} is down (Request failed)")
            is_up = False
        
        prev_status = state[name]['status']
        
        if not is_up:
            state[name]['fail_count'] += 1
        else:
            state[name]['fail_count'] = 0   
        
        
        if not is_up and prev_status == 'up':
            if state[name]['fail_count'] >= 3:
                logging.info(f"[-] {name} has been down for 3 consecutive checks. Sending email alert...")
                if not state[name]['is_mail_sent']:
                    res = send_email(service['emails'], name, is_up=False)
                    if res:
                        logging.info(f"[+] Email alert sent for {name}.")
                    else:
                        logging.error(f"[-] Failed to send email alert for {name}.\n Error: {res}")
                state[name]['is_mail_sent'] = True
                state[name]['status'] = 'down'
        elif is_up and prev_status == 'down':
            logging.info(f"[+] {name} recovered.")
            send_email(service['emails'], name, is_up=True)
            state[name]['status'] = 'up'
            state[name]['is_mail_sent'] = False
            
            
    logging.info("Service checks completed. Updating state...")
    update_state(state)
    logging.info("State updated successfully.")
    logging.info("Service monitor finished.")
if __name__ == '__main__':
    main()
    