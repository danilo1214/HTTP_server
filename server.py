"""An example of a simple HTTP server."""
import json
import mimetypes
import pickle
import socket
from os.path import isdir
from urllib.parse import unquote_plus

# Pickle file for storing data
PICKLE_DB = "db.pkl"

# Directory containing www data
WWW_DATA = "www-data"

# Header template for a successful HTTP request
HEADER_RESPONSE_200 = """HTTP/1.1 200 OK\r
content-type: %s\r
content-length: %d\r
connection: Close\r
\r
"""

# Represents a table row that holds user data
TABLE_ROW = """
<tr>
    <td>%d</td>
    <td>%s</td>
    <td>%s</td>
</tr>
"""

# Template for a 404 (Not found) error
RESPONSE_404 = """HTTP/1.1 404 Not found\r
content-type: text/html\r
connection: Close\r
\r
<!doctype html>
<h1>404 Page not found</h1>
<p>Page cannot be found.</p>
"""

# Template for a 404 (Not found) error
RESPONSE_400 = """HTTP/1.1 400 Bad Request\r
content-type: text/html\r
connection: Close\r
\r
<!doctype html>
<h1>Bad request</h1>
<p>Your Browser sent a request that I cannot understand.</p>
"""

RESPONSE_405 = """HTTP/1.1 405 Method Not Allowed\r
content-type: text/html\r
allow: GET, POST\r
connection: Close\r
\r
<!doctype html>
<h1>Not Allowed</h1>
<p>Your Browser sent a request that is not allowed.</p>
"""


HEADER_RESPONSE_301 = """HTTP/1.1 301 Moved permanently\r
content-type: text/html\r
location: %s\r
\r
<!doctype html>
<h1>Moved permanently</h1>
<p>The page your browser has requested, has been moved permanently.</p>
"""


def save_to_db(first, last):
    """Create a new user with given first and last name and store it into
    file-based database.

    For instance, save_to_db("Mick", "Jagger"), will create a new user
    "Mick Jagger" and also assign him a unique number.

    Do not modify this method."""

    existing = read_from_db()
    existing.append({
        "number": 1 if len(existing) == 0 else existing[-1]["number"] + 1,
        "first": first,
        "last": last
    })
    with open(PICKLE_DB, "wb") as handle:
        pickle.dump(existing, handle)


def read_from_db(criteria=None):
    """Read entries from the file-based DB subject to provided criteria

    Use this method to get users from the DB. The criteria parameters should
    either be omitted (returns all users) or be a dict that represents a query
    filter. For instance:
    - read_from_db({"number": 1}) will return a list of users with number 1
    - read_from_db({"first": "bob"}) will return a list of users whose first
    name is "bob".

    Do not modify this method."""
    if criteria is None:
        criteria = {}
    else:
        # remove empty criteria values
        for key in ("number", "first", "last"):
            if key in criteria and criteria[key] == "":
                del criteria[key]

        # cast number to int
        if "number" in criteria:
            criteria["number"] = int(criteria["number"])

    try:
        with open(PICKLE_DB, "rb") as handle:
            data = pickle.load(handle)

        filtered = []
        for entry in data:
            predicate = True

            for key, val in criteria.items():
                if val != entry[key]:
                    predicate = False

            if predicate:
                filtered.append(entry)

        return filtered
    except (IOError, EOFError):
        return []
def send_default_response(client, resp):
    full = resp
    client.write(full.encode("utf-8"))
    client.close()

def process_request(connection, address):
    """Process an incoming socket request.

    :param connection is a socket of the client
    :param address is a 2-tuple (address(str), port(int)) of the client
    """

    client = connection.makefile("wrb")
    line =client.readline().decode("utf-8").strip()
    headers = {}
    full = ""
    headers["Request"] = line

    isvalid = len(line.split(" ")) == 3
    while line != "" and isvalid:
        line = client.readline().decode("utf-8").strip()
        if line != "":
            field, value = line.split(":", maxsplit=1)
            headers[field] = value.strip()

    if len(headers["Request"].split(" ")) != 3 or ("Host" not in headers and "host" not in headers):
        send_default_response(client, RESPONSE_400)
        return

    method,file,version = headers["Request"].split(" ")

    if version != "HTTP/1.1":
        send_default_response(client, RESPONSE_400)
        return
    if method not in ["GET", "POST"]:
        send_default_response(client, RESPONSE_405)
        return

    endpoint = file[1:].split("/")[0]

    if endpoint == "app-add" and method == "POST":
        length = int(headers["Content-Length"])
        content = client.read(length)
        url = content.decode("utf-8")
        try:
            first, last = url.split("&")
            data = {}
            k1,v1 = first.split("=")
            k2,v2 = last.split("=")
            data[k1] = v1
            data[k2] = v2
            save_to_db(data["first"], data["last"])

            with open("./www-data/app_add.html", 'rb') as content_file:
                html_bytes = content_file.read()
                html = html_bytes.decode("utf-8")
                full = HEADER_RESPONSE_200 % ("index/html", len(html))
                full += html
                client.write(full.encode("utf-8"))
                client.close()
                return
        except:
            send_default_response(client, RESPONSE_400)
            return
    if endpoint == "app-add" and method != "POST":
        full = RESPONSE_405
        client.write(full.encode("utf-8"))
        client.close()
        return


    if endpoint == "app-json" and method == "GET":
        students = json.dumps(read_from_db())
        full = HEADER_RESPONSE_200 % ("application/json", len(students))
        full += students
        client.write(full.encode("utf-8"))
        client.close()
        return
    if endpoint == "app-json" and method != "GET":
        send_default_response(client, RESPONSE_405)
        return

    if "app-index" in endpoint and method != "GET":
        send_default_response(client, RESPONSE_405)
        return
    if "app-index" in endpoint and method == "GET":
        paramstrings = endpoint.split("app-index")[1][1:].split("&")
        params = {}
        for p in paramstrings:
            if len(p.split("=")) == 2:
                key, val = p.split("=")
                params[key] = val
        query = {}
        for p in params.keys():
            if len(params[p]) != 0:
                query[p] = params[p]
        users = read_from_db(query)
        with open("./www-data/app_list.html", 'rb') as content_file:
            content = content_file.read()
            html = content.decode("utf-8")
            users_string = ""
            for user in users:
                users_string += TABLE_ROW % (user["number"], user["first"], user["last"])
            html = html.replace("{{students}}", users_string)
            hdr = (HEADER_RESPONSE_200 % ("text/html", len(html)))
            full = hdr + html
            client.write(full.encode("utf-8"))
            client.close()
            return

    if file[0] == "/":
        file = "www-data" + file
    else:
        file = "www-data/" + file

    if method == "GET":
        try:
            if file[-1] == "/":
                if isdir(file):
                    file += "index.html"
                    ip,port =headers["Host"].split(":")
                    full = (HEADER_RESPONSE_301 % ("http://localhost" + ":" + str(port) + file[8:]) )
                    client.write(full.encode("utf-8"))
                    client.close()
                    return
            type = mimetypes.guess_type(file)
            with open( file, 'rb') as content_file:
                content = content_file.read()
                full = (HEADER_RESPONSE_200 % (type[0], len(content)))
            if type == "text/html":
                full += content.decode("utf-8")
                client.write(full.encode("utf-8"))
            else:
                client.write(full.encode("utf-8"))
                client.write(content)
            client.close()
            return
        except:
            send_default_response(client, RESPONSE_404)
            return

    client.write(full.encode("utf-8"))
    client.close()

def main(port):
    """Starts the server and waits for connections."""

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("", port))
    server.listen(1)

    print("Listening on %d" % port)

    while True:
        connection, address = server.accept()
        print("[%s:%d] CONNECTED" % address)
        process_request(connection, address)
        connection.close()
        print("[%s:%d] DISCONNECTED" % address)


if __name__ == "__main__":
    main(8080)
