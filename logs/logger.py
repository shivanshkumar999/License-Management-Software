from datetime import datetime


def create_log(username,system_ip,message,message_type,role):
    f = open('logs/system_logs.log','a')
    f.write('\n')
    f.write('-----------------------------')
    f.write('\n')
    f.write(f'{role} : {datetime.now()} : {system_ip} : {message_type} :: "{username}" {message}')
    return "Log Created"

def display_logs():
    logs = []
    f = open('logs/system_logs.log','r')
    lines = f.read()
    logs = lines.split('--')
    # logs.reverse()
    return logs