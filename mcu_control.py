import  serial 
import  time
import  csv
from datetime import datetime
import serial.tools.list_ports



# ================= 設定區 (Baud Rate ) =================
DEFAULT_BAUD_RATE = 115200 # 預設的 Baud Rate
CMD_TO_SEND = bytes([0x24,0x02, 0x01, 0x01])  # 要送出的指令
TIMEOUT = 2                # 等待 MCU 回應的秒數
# ====================================================================
def list_all_port():
    ports = serial.tools.list_ports.comports()
    port_map = {}
    if not ports:
        print(" 找不到任何 COM Port")

    else:
        print(" 發現以下裝置：")
        for i, port in enumerate(ports):
            if "CP210x" in port.description:
                port_map[i+1] = port.device
                print(f"✅ {i+1}-[{port.device}] {port.description}")
            # 未來你可以寫程式自動判斷：
            # if "J-Link" in port.description:
            #     target_port = port.device
    
    while True:
            try:
                choice = input(f"請輸入編號 (1-{len(port_map)})：")
                
                # 檢查輸入是否為數字且在範圍內
                choice_num = int(choice)
                if choice_num in port_map:
                    selected_port_name = port_map[choice_num]
                    
                    # (進階功能) 確認 Baud Rate
                    baud_rate_input = input(f"請輸入 Baud Rate (預設: {DEFAULT_BAUD_RATE})：")
                    baud_rate = int(baud_rate_input) if baud_rate_input else DEFAULT_BAUD_RATE
                    
                    print(f"✅ 已選擇 Port: {selected_port_name}, Baud Rate: {baud_rate}")
                    return selected_port_name, baud_rate
                else:
                    print(f"輸入錯誤，請輸入 1 到 {len(port_map)} 之間的數字。")
            except ValueError:
                print("輸入錯誤，請輸入一個有效的數字。")    
            

def send_CDM(com_port, baud_rate):
    
    """執行連線、送指令、接收 Log 的主要功能。"""
    print(f"-----嘗試連線{com_port} (baud_rate({baud_rate}))-------")
    try:
            # 1. 建立連線
            ser = serial.Serial(com_port, baud_rate, timeout=1)
            print("成功連接！等待 2 秒讓訊號穩定...")
            time.sleep(2) 

            # 2. 清空緩衝區
            ser.reset_input_buffer()

            # 3. 送出指令
            print(f"送出指令: {format_hex_with_spaces(CMD_TO_SEND)}")
            ser.write(CMD_TO_SEND)

            # 4. 接收回應並存檔
            print("開始接收回應...")
            start_time = time.time()
            
            log_filename = f"mcu_log_{datetime.now():%Y%m%d_%H%M%S}.txt"
            
            with open(log_filename, 'w', encoding='utf-8') as f:
                f.write(f"測試時間: {datetime.now()}\n")
                f.write(f"Port: {com_port}, Baud Rate: {baud_rate}\n")
                f.write("=============================\n")
                
                # 在 timeout 內持續讀取
                while (time.time() - start_time) < TIMEOUT:
                    if ser.in_waiting > 0:
                        line = ser.readline().decode('utf-8', errors='ignore').strip()
                        
                        if line:
                            print(f"[MCU]: {line}")
                            f.write(line + '\n')
                
                f.write("=============================\n")
                print(f"\n--- 測試結束，Log 已儲存至 {log_filename} ---")

            # 關閉連線
            ser.close()

    except serial.SerialException as e:
        print(f"\n❌ 錯誤: 無法連線到 {com_port}。請確認：")
        print("1. 該 Port 沒有被 Tera Term 或其他軟體佔用。")
        print("2. Baud Rate 是否正確。")
        print(f"詳細錯誤: {e}")
    except Exception as e:
        print(f"\n❌ 發生未預期的錯誤: {e}")


def format_hex_with_spaces(byte_data):
    """
    將 bytes 物件轉換成以空格分隔的十六進位字串 (例如：b'\x24\x02' -> '24 02')
    """
    # 1. 取得連續的十六進位字串 (例如：'24020101')
    hex_string = byte_data.hex() 
    
    # 2. 使用 list comprehension 和 join() 來每隔兩個字元插入一個空格
    spaced_hex = ' '.join(hex_string[i:i+2] for i in range(0, len(hex_string), 2))
    
    return spaced_hex


if __name__ == "__main__":
    select_port, baud_rate = list_all_port()
    if select_port:
        send_CDM(select_port, baud_rate)