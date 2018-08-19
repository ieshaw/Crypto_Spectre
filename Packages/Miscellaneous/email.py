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

def send_gmail(msg,subj,to_addrs,from_addr,password):
    '''
    :param msg: string, body of email
    :param subj: string, subject of email
    :param toaddrs: list of strings, addresses of email recipients
    :param from_addr: string, sender email address
    :param password: password of sender
    '''
    # put your host and port here
    s = smtplib.SMTP_SSL('smtp.gmail.com',465)
    s.login(from_addr, password)
    email_text = """  
    From: %s \r\n 
    To: %s  \r\n
    Subject: %s \r\n

    %s
    """ % (from_addr, ", ".join(to_addrs), subj, msg)
    s.sendmail(from_addr, to_addrs, email_text)
    s.quit()

def send_email(json_path,key_name,msg,subj,to_addrs):
    '''
    :param json_path: dictionary
    :param key_name: string
    :param msg: string, body of email
    :param subj: string, subject of email
    :param toaddrs: list of strings, addresses of email recipients
    '''
    from_addr,password = load_credentials(json_path,key_name)
    send_gmail(msg,subj,to_addrs,from_addr,password)
