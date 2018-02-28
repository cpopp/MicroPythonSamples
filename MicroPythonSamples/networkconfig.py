import network
import socket
import ure

wlan_ap = network.WLAN(network.AP_IF)
wlan_sta = network.WLAN(network.STA_IF)

server_socket = None

def send_response(client, payload, status_code=200):
    client.sendall("HTTP/1.0 {} OK\r\n".format(status_code))
    client.sendall("Content-Type: text/html\r\n")
    client.sendall("Content-Length: {}\r\n".format(len(payload)))
    client.sendall("\r\n")
    
    if len(payload) > 0:
        client.sendall(payload)

def handle_root(client):
    response_header = """
        <h1>Wi-Fi Client Setup</h1>
        <form action="configure" method="post">
          <label for="ssid">SSID</label>
          <select name="ssid" id="ssid">
    """
    
    response_variable = ""
    for ssid, *_ in wlan_sta.scan():
        response_variable += '<option value="{0}">{0}</option>'.format(ssid.decode("utf-8"))
    
    response_footer = """
           </select> <br/>
           Password: <input name="password" type="password"></input> <br />
           <input type="submit" value="Submit">
         </form>
    """
    send_response(client, response_header + response_variable + response_footer)

def handle_configure(client, request):
    match = ure.search("ssid=([^&]*)&password=(.*)", request)
    
    if match is None:
        send_response(client, "Parameters not found", status_code=400)
        return
    
    ssid = match.group(1)
    password = match.group(2)
    
    if len(ssid) == 0:
        send_response(client, "SSID must be provided", status_code=400)
        return
    
    wlan_sta.active(True)
    wlan_sta.connect(ssid, password)
    
    send_response(client, "Wi-Fi configured for SSID {}".format(ssid))
    

def handle_not_found(client, url):
    send_response(client, "Path not found: {}".format(url), status_code=404)

def stop():
    global server_socket
    
    if server_socket:
        server_socket.close()

def start(port=80):
    addr = socket.getaddrinfo('0.0.0.0', port)[0][-1]
    
    global server_socket
    
    stop()
    
    server_socket = socket.socket()
    server_socket.bind(addr)
    server_socket.listen(1)

    print('listening on', addr)
    
    while True:
        client, addr = server_socket.accept()
        client.settimeout(5.0)
        print('client connected from', addr)
        
        request = b""
        try:
            while not "\r\n\r\n" in request:
                request += client.recv(512)
        except OSError:
            pass
        
        print("Request is: {}".format(request))
        if "HTTP" not in request:
            # skip invalid requests
            client.close()
            continue
        
        url = ure.search("(?:GET|POST) /(.*?)(?:\\?.*?)? HTTP", request.decode('ascii')).group(1).rstrip("/")
        print("URL is {}".format(url))

        if url == "":
            handle_root(client)
        elif url == "configure":
            handle_configure(client, request)
        else:
            handle_not_found(client, url)
        
        client.close()
