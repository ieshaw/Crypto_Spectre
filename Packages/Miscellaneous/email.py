import smtplib

def load_credentials(json_path,key_name):
    '''
    :param json_path: dictionary
    :param key_name: string
    return: email address, password
    '''
    import json
    import os
    with open(json_path) as secrets_file:
        secrets = json.load(secrets_file)
        secrets_file.close()
    key_dict = secrets[key_name]
    return key_dict['email'],key_dict['password']

def send_gmail(body,subj,to_addrs,from_addr,password):
    '''
    :param body: string, body of email
    :param subj: string, subject of email
    :param toaddrs: list of strings, addresses of email recipients
    :param from_addr: string, sender email address
    :param password: password of sender
    '''
    # put your host and port here
    # Import the email modules we'll need
    from email.mime.text import MIMEText

    msg = MIMEText(body)

    msg['Subject'] = subj 
    msg['From'] = from_addr
    msg['To'] = ', '.join(to_addrs)

    s = smtplib.SMTP_SSL('smtp.gmail.com',465)
    s.login(from_addr, password)
    s.send_message(msg)
    s.quit()

def send_email(json_path,key_name,body,subj,to_addrs):
    '''
    :param json_path: dictionary
    :param key_name: string
    :param body: string, body of email
    :param subj: string, subject of email
    :param toaddrs: list of strings, addresses of email recipients
    '''
    from_addr,password = load_credentials(json_path,key_name)
    send_gmail(body,subj,to_addrs,from_addr,password)
