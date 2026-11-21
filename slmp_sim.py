import socket
import struct
import threading

zr = [0] * 1000
zr[0] = 100  # 초기 테스트 값 (ZR0 = 100)

def handle_client(conn):
    with conn:
        while True:
            hdr = conn.recv(9)
            if len(hdr) < 9:
                break
            data_len = struct.unpack("<H", hdr[7:9])[0]
            body = b""
            while len(body) < data_len:
                chunk = conn.recv(data_len - len(body))
                if not chunk:
                    break
                body += chunk
            if len(body) < data_len:
                break

            cmd, subcmd = struct.unpack("<HH", body[2:6])
            if subcmd == 0x0000:
                addr = int.from_bytes(body[6:9], "little")
                count = struct.unpack("<H", body[10:12])[0]
                offset = 12
            else:  # 0x0002 (32-bit 확장 주소)
                addr = struct.unpack("<I", body[6:10])[0]
                count = struct.unpack("<H", body[12:14])[0]
                offset = 14

            if cmd == 0x0401:  # 일괄 읽기 (Word)
                words = [zr[addr + i] & 0xFFFF if (addr + i) < len(zr) else 0 for i in range(count)]
                res_data = b"\x00\x00" + struct.pack(f"<{count}H", *words)
            elif cmd == 0x1401:  # 일괄 쓰기 (Word)
                vals = struct.unpack(f"<{count}H", body[offset:offset + count * 2])
                for i, v in enumerate(vals):
                    if (addr + i) < len(zr):
                        zr[addr + i] = v
                print(f"\n[CIMON 쓰기] ZR{addr}~ZR{addr + count - 1} = {list(vals)}")
                res_data = b"\x00\x00"
            else:
                res_data = b"\x00\x00"

            res = b"\xD0\x00" + hdr[2:7] + struct.pack("<H", len(res_data)) + res_data
            conn.sendall(res)

def server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("127.0.0.1", 4999))
        s.listen(5)
        print("SLMP 3E 가상 PLC 대기 중 (127.0.0.1:4999)...")
        while True:
            conn, addr = s.accept()
            print(f"\nCIMON 연결됨: {addr}")
            threading.Thread(target=handle_client, args=(conn,), daemon=True).start()

threading.Thread(target=server, daemon=True).start()
print("값 변경: '번지 값' 입력 후 Enter (예: 0 250 -> ZR0=250, 종료: q)")
while True:
    line = input("> ").strip()
    if line.lower() == "q":
        break
    parts = line.split()
    if len(parts) == 2 and parts[0].isdigit():
        idx, val = int(parts[0]), int(parts[1]) & 0xFFFF
        zr[idx] = val
        print(f"ZR{idx} = {val} 반영 완료")