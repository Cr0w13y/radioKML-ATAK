import urllib3
from bs4 import BeautifulSoup as BS
import datetime as dt
import xml.etree.ElementTree as ET
import socket
import time

print(
'''
===================================================                                  .       
#      .              .   .'.                     #
#    \   /      .'. .' '.'   ' ______________     #
#  -=  o  =-  .'   '          ||            ||    #
#    / | \                    ||            ||    #
#      |                      ||            ||    #
#      |                      ||            ||    #
#      |                      ||____________||    #
#      |=====.                |______________|    #
#      |.---.|                \\\############\\\    #
#      ||=o=||                 \\\############\\\   #
#      ||   ||                  \      ____    \  #
#      ||   ||                   \_____\___\____\ #
#      ||___||                                    #
#      |[:::]|                                    #
#      '-----'                                    #
=================================================== 
radio KML to Cots point convertor

created by Dunnett''')
urllib3.disable_warnings()
DATETIME_FMT = "%Y-%m-%dT%H:%M:%SZ"
'''
CHANGE radio_ip to gateway address of radio
'''


radio_ip="192.168.100.4"
var_stale =5

url=("https://"+radio_ip+"/situationalawareness.kml")
http = urllib3.PoolManager(cert_reqs = 'CERT_NONE')

def main():

        # GET Data from radio
        r = http.request('GET', url, preload_content=False)
        data=r.data

        #seperate lat,long,alt into searchable tabs 
        def replace_nth(s, sub, repl, n=1):
                chunks = s.split(sub)
                size = len(chunks)
                rows = size // n + (0 if size % n == 0 else 1)
                return repl.join([
                sub.join([chunks[i * n + j]
                for j in range(n if (i + 1) * n < size else size - i * n)]) for i in range(rows)])
        data=data.replace(b'<coordinates>', b'<long>',)
        data=data.replace(b'</coordinates>',b'</alt>',)
        data=replace_nth(data,b',',b'</lat><alt>',2)
        data=data.replace(b',',b'</long><lat>')

        #seperate tags
        soup = BS(data,'xml')
        lat=soup.find_all('lat')
        long=soup.find_all('long')
        identity=soup.find_all('name')
        uid=soup.findAll("Data", {"name" : "sourceType"})
        heading=soup.findAll("Data", {"name" : "heading"})
        velocity=soup.findAll("Data", {"name" : "velocity"})
        vdate=soup.findAll("Data", {"name" : "date"})
        vtime=soup.findAll("Data", {"name" : "time"})
        
        #construct cots messages from var
        data=[]
        for i in range (0,len(identity)):
                 #timecode convert and get stale
                date_time={
                "ldate":vdate[i].get_text(),
                "ltime":vtime[i].get_text()
                }
                dat=date_time["ldate"][:]
                tim=date_time["ltime"][:]
                timestamp=(dat+tim)
                radtime=dt.datetime.strptime(str(timestamp),'%d%m%y%H%M%S')
                timer = dt.datetime
                zulu = radtime.strftime(DATETIME_FMT)
                stale_now = radtime+dt.timedelta(minutes=var_stale)
                stale = stale_now.strftime(DATETIME_FMT)
               
                #add event tags
                evt_attr = {
	            "version": "2.0",
	            "uid": str(identity[i].get_text()),
	            "how": "m-g",
	            "type": "a-f-G-U-C",
	            "time": zulu,
	            "start": zulu,
	            "stale": stale
	          
	        }
                #add point tags
                pt_attr = {
	        "le": "5",     #unit["le"]
	        "ce": "3.020586",    #unit["ce"],
	        "hae": "0",   #unit["hae"], 
	        "lon":  str(long[i].get_text()),
	        "lat": str(lat[i].get_text())
	        }
                #add atak group tag 
                pt_det_group={
			"name": "Blue",
			"role":"Team Member"
			}
                #add atak track tag
                pt_det_track={
                        "speed":str(velocity[i].get_text()),
                        "course":str(heading[i].get_text())
                        }
                """
                code put in to test extra functionaity can change icon to any in atak library
                pt_det_usericon={
                        "iconsetpath":'34ae1613-9645-4222-a9d2-e5f243dea2865/Military/soldier6.png'
                        }
                """
                
                #build COTS message
                cot = ET.Element('event', attrib=evt_attr)
                s1=ET.SubElement(cot, 'detail')
                ET.SubElement(s1,'__group', attrib=pt_det_group)
                ET.SubElement(s1,'track',attrib=pt_det_track)
                
                #addin for icon change
                #ET.SubElement(s1,'usericon',attrib=pt_det_usericon)

                ET.SubElement(cot,'point', attrib=pt_attr)
	        
                cot_xml = '<?xml version="1.0"?>'.encode('utf-8') 
                cot_xml += ET.tostring(cot)
                #send to multicast points 
                o_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) 
                o_sock.sendto(cot_xml, ('127.0.0.1', 8087)) 
                o_sock.close()
                o_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) 
                o_sock.sendto(cot_xml, ('239.2.3.1', 6969)) 
                o_sock.close()
	               
while(True):
	main()
	#change sleep time if network becoming congested
	time.sleep(3)
	
