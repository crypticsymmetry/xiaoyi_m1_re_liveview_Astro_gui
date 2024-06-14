import socket
import os
from prot_http.const_wifi import UDP_PORT_LIVEVIEW

def initialize_socket():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('', UDP_PORT_LIVEVIEW))
    sock.settimeout(2)
    return sock

def process_packet(packet, data, frame_info):
    if len(packet) < 12:
        return False

    idx_frame = int.from_bytes(packet[:4], byteorder='big')
    len_packet_frame = int.from_bytes(packet[4:8], byteorder='big')
    idx_packet_frame = int.from_bytes(packet[8:12], byteorder='big')

    if frame_info['data_idx_frame'] != idx_frame:
        frame_info.update({
            'data': bytearray(),
            'data_idx_frame': idx_frame,
            'data_idx_last_packet': -1,
            'data_valid': True,
        })

    if frame_info['data_valid']:
        if (idx_packet_frame - 1) == frame_info['data_idx_last_packet']:
            frame_info['data'].extend(packet[12:])
            frame_info['data_idx_last_packet'] = idx_packet_frame
        else:
            frame_info['data_valid'] = False
            return False

        if frame_info['data_idx_last_packet'] == len_packet_frame - 1:
            save_frame(frame_info['data'], frame_info['data_idx_frame'])
            return True

    return False

def save_frame(data, idx_frame):
    if len(data) > 2048:
        jpg_data = data[2048:]
        file_name = f"packet_{idx_frame}.jpg"
        with open(file_name, 'wb') as f:
            f.write(jpg_data)
        print(f"Frame saved as {file_name}")
    else:
        raw_data = data
        file_name = f"packet_unk_{idx_frame}.raw"
        with open(file_name, 'wb') as f:
            f.write(raw_data)
        print(f"Frame saved as {file_name}")

def receive_packets():
    with initialize_socket() as sock:
        print("Started receiver!")
        frame_info = {
            'data': bytearray(),
            'data_idx_frame': None,
            'data_idx_last_packet': -1,
            'data_valid': True,
        }

        try:
            while True:
                try:
                    packet, _ = sock.recvfrom(1024000)
                    process_packet(packet, frame_info['data'], frame_info)
                except socket.timeout:
                    print("Timed out...")
        except KeyboardInterrupt:
            pass

if __name__ == "__main__":
    receive_packets()
