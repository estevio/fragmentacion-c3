import sys
import socket
from routerTTL import PaqueteIP, create_packet, fragment_ip_packet, reassemble_ip_packet

if len(sys.argv) != 4:
    sys.exit("Modo de uso: prueba_router.py [IP_destino];[Puerto_destino];[TTL] " +
             "[IP_router_inicial] [puerto_router_inicial]")

headers, ip_inicial, puerto_inicial = sys.argv[1:]
headers = headers.split(";")

archivo = input("Ruta del archivo txt a enviar: ")

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# prueba reassemble
pack1 = PaqueteIP(headers[0], int(headers[1]), int(headers[2]), 111, 0, 0, "aaaa no se que escribir deberia irme a mimir dio mio")
pack2 = PaqueteIP(headers[0], int(headers[1]), int(headers[2]), 222, 0, 0, "WNNN TENGO DEMASIADO TUTOOOO QUE TERMINE YA ESTA V X FAVOR")

frags1 = fragment_ip_packet(pack1, 21)
frags2 = fragment_ip_packet(pack2, 25)
print([x.msg for x in frags1])

res = reassemble_ip_packet(frags1)
print(res.msg)

frags = []
for i in range(len(frags2)):
    frags.append(frags1.pop(0))
    frags.append(frags2[i])
frags = frags + frags1
frags = [create_packet(f) for f in frags]
for f in frags:
    sock.sendto(f, (ip_inicial, int(puerto_inicial)))

with open(archivo) as txt:
    line = txt.readline()
    while line:

        pack = create_packet(PaqueteIP(headers[0], int(headers[1]), int(headers[2]), 2, 0, 0, line))
        sock.sendto(pack, (ip_inicial, int(puerto_inicial)))
        line = txt.readline()