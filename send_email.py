from Packages.Miscellaneous.email import load_credentials,send_email

msg = 'Test Message'
subj = 'Test'
to_addrs = ['ian@spectre.engineering']
json_path='.keys.json'
key_name='Email'

send_email(json_path,key_name,msg,subj,to_addrs)
