from typing import Any, Text, Dict, List
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
#  Send mail function
def SendEmail(toaddr,subject,message):
    fromaddr = "666anonymailer999@gmail.com"
    msg = MIMEMultipart()
    msg['From'] = fromaddr
    msg['To'] = toaddr
    msg['Subject'] = subject
    body = message
    msg.attach(MIMEText(body, 'html'))
    s = smtplib.SMTP('smtp.gmail.com', 587)
    s.starttls()

    try:
        s.login(fromaddr, "kxwapeedoljoghol")
        text = msg.as_string()
        s.sendmail(fromaddr, toaddr, text)
        return 1
    except:
        return 0
    finally:
        s.quit()
