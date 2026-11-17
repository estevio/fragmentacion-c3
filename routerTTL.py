import sys
import socket
from math import ceil

class PaqueteIP():

    def __init__(self, ip: str, puerto: int, ttl: int, id_pack: int, 
                 offset: int, flag:int, msg: str, size = -1):
        self.ip = ip
        self.puerto = puerto
        self.ttl = ttl
        self.id_pack = id_pack
        self.offset = offset
        self.flag = flag
        self.msg = msg

        if size == -1:
            self.size = len(msg)
        else:
            self.size = size

def parse_packet(ip_packet: bytes):
    """
    Parsea un paquete de bytes que contiene una dirección ip y puerto.
    El paquete debe contener al menos 16 bytes, 
    bytes 0 a 3: representan la dirección ip,
    bytes 4 y 5: el puerto asociado
    byte 6: representa el TTL (time to live)
    bytes 7 y 8: corresponden al id
    bytes 9 a 12: offset
    bytes 13 a 16: tamaño del mensaje (sin headers)
    byte 17: flag
    bytes 18 en adelante: mensaje

    Args:
        ip_packet (bytes): el paquete en bytes

    Returns:
        PaqueteIP: estructura que contiene una dirección ip y un puerto
    """

    if len(ip_packet) < 18:
        print("paquete no tiene el tamaño adecuado")
        return

    ip_numbers = []
    for i in range(4):
        ip_numbers.append(str(ip_packet[i]))

    ip = ".".join(ip_numbers)
    puerto = int.from_bytes(ip_packet[4:6])
    ttl = ip_packet[6]
    id_pack = int.from_bytes(ip_packet[7:9])
    offset = int.from_bytes(ip_packet[9:13])
    size = int.from_bytes(ip_packet[13:17])
    flag = ip_packet[17]
    msg = ip_packet[18:18+size].decode()

    return PaqueteIP(ip, puerto, ttl, id_pack, offset, flag, msg, size)


def create_packet(data: PaqueteIP):
    """
    Crea un paquete de bytes a partir de un objeto PaqueteIP

    Args:
        data (PaqueteIP): la informacion del paquete
    
    Returns:
        bytes: el paquete de bytes
    """
    ip_numbers = data.ip.split(".")
    res = b""
    for n in ip_numbers:
        res += int(n).to_bytes()
    res += data.puerto.to_bytes(2)
    res += data.ttl.to_bytes()
    res += data.id_pack.to_bytes(2)
    res += data.offset.to_bytes(4)
    res += data.size.to_bytes(4)
    res += data.flag.to_bytes()
    res += data.msg.encode()

    return res

def check_routes(routes_file_name: str, destination_address: tuple[str, int]):
    """
    Busca la dirección de destino destination_address en la tabla de rutas almacenada
    en el archivo txt routes_file_name

    Args: 
        routes_file_name (str): nombre del archivo de la tabla de rutas
        destination_address (tuple[str, int]): par que representa la dirección de destino (IP, puerto)

    Returns:
        tuple[str, int]: tupla que representa la dirección del siguiente salto
        None: si no se encuentra la dirección solicitada
    """

    with open(routes_file_name) as tabla:
        row = tabla.readline()
        ips_posibles = []
        while row:

            try:
                ip_destino, i, j, ip_salto, puerto_salto, mtu = row.split(" ")
                puerto_salto = int(puerto_salto)
                ip_destino = ip_destino.split("/")[0]
            except:
                print("error al leer linea")
                return

            if (ip_destino == destination_address[0] and int(i) <= destination_address[1] <= int(j)):
                ips_posibles.append(((ip_salto, int(puerto_salto)), int(mtu)))
                #print(f"puerto salto: {puerto_salto}\tpuerto destino: {destination_address[1]}\n")
                if ip_salto == destination_address[0] and puerto_salto == destination_address[1]:
                    return ((ip_salto, puerto_salto), int(mtu))
            
            row = tabla.readline()

        if not ips_posibles:
            return None

        # ips posibles que no estan dentro de cola ips
        # no_visitadas = filter(lambda x: x not in cola_ips, ips_posibles)
        no_visitadas = [x for x in ips_posibles if x not in cola_ips]
        if no_visitadas:
            return no_visitadas[0]
        # ips posibles que estan en la cola de ips
        visitadas = [x for x in cola_ips if x in ips_posibles]
        if visitadas:
            return visitadas.pop(0)

def fragment_ip_packet(ip_packet: PaqueteIP, mtu: int):
    """
    Fragmenta el paquete ip_packet si su tamaño excede el Maximum Transfer Unit

    Args:
        ip_packet (PaqueteIP): la información del paquete
        mtu (int): Maximum Transfer Unit

    Returns:
        list[PaqueteIP]: lista de fragmentos en PaqueteIPs
    """

    if ip_packet.size + 18 > mtu:
        max_msg_len = mtu - 18
        n_frags = ceil(ip_packet.size / max_msg_len)
        msgs = [ip_packet.msg[i*max_msg_len:(i+1)*max_msg_len] for i in range(n_frags)]

        offset = ip_packet.offset
        frags: list[PaqueteIP] = []
        for m in msgs:
            d = PaqueteIP(ip_packet.ip, ip_packet.puerto, ip_packet.ttl, ip_packet.id_pack,
                          offset, 1, m)
            frags.append(d)
            offset += max_msg_len
        if ip_packet.flag == 0:
            frags[-1].flag = 0
        return frags
    else:
        return [ip_packet]
    

if __name__ == "__main__":

    if len(sys.argv) != 4:
        sys.exit("Modo de uso: router.py [router_IP] [router_puerto] [router_rutas].txt")

    ip = sys.argv[1]
    puerto = int(sys.argv[2])
    rutas = sys.argv[3]
    buff_size = 1000
    #global cola_ips
    cola_ips = []

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        sock.bind((ip, puerto))
    except Exception as e:
        print(f"error en bind: {e}")

    while True:
        try:
            bts, ip_paquete = sock.recvfrom(buff_size)
            data = parse_packet(bts)
            if data.ttl <= 0:
                print("Se recibió un paquete con TTL menor o igual a 0")
                continue
            # el paquete es para mi?
            if data.ip == ip and data.puerto == puerto:
                print(data.msg)
            else:
                next_addr, mtu = check_routes(rutas, (data.ip, data.puerto))
                if next_addr:
                    # print(f"redirigiendo paquete {ip_paquete} con destino final {data.ip}:{data.puerto} " +
                    #       f"desde {ip}:{puerto} hacia {next_addr[0]}:{next_addr[1]}")
                    print(f"redirigiendo paquete con destino final {data.puerto} " +
                            f"desde {puerto} hacia {next_addr[1]}")
                    if next_addr in cola_ips:
                        cola_ips.remove(next_addr)
                    cola_ips.append(next_addr)
                    data.ttl -= 1
                    frags = fragment_ip_packet(data, mtu)
                    for f in frags:
                        sock.sendto(create_packet(f), next_addr)
                else:
                    print(f"No hay rutas hacia {ip}:{puerto} para paquete {ip_paquete}")

        except KeyboardInterrupt:
            sys.exit()
    