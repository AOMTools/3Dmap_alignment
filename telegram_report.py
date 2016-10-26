import subprocess as sp
user='Huan_Nguyen'
message='new'+ '\\n line #############'
sp.call(['./telegram_report.sh',user,message])
