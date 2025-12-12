import serial
import threading
import time

import sys
from PyQt6.QtWidgets import QApplication

COM_PORT = 'COM6'
BAUD_RATES = 115200
ser = serial.Serial(COM_PORT, BAUD_RATES, timeout=1)

# ⚠️ 1. 建立一個停止旗標 (Stop Flag)
stop_event = threading.Event()

# --- 修正後的接收執行緒 ---
def read_from_port(ser, stop_flag):
    # ⚠️ 迴圈條件：當停止旗標沒有被設置時，才繼續執行
    while not stop_flag.is_set():
        try:
            if ser.in_waiting:
                temp = ser.read(ser.in_waiting)
                data = temp.decode('utf-8', errors='ignore')
                temp = abs(float(temp) * 1000)*100
                
                print(data, end=''+"\r\n", flush=True) 
                print(f"data2 = {temp:.3f} mA", end=''+"\r\n")
        
        # ⚠️ 2. 捕獲並處理你的錯誤
        except serial.serialutil.SerialException as e:
            # 如果發生「控制代碼無效」或斷線錯誤，立即設定停止旗標並跳出迴圈
            if '控制代碼無效' in str(e) or 'Device not configured' in str(e):
                print("\n[錯誤] 偵測到 Serial Port 連線中斷或控制代碼無效，自動停止讀取執行緒。")
                stop_flag.set()
                break
            else:
                # 處理其他 Serial 錯誤
                print(f"\n[錯誤] 發生其他 Serial 錯誤: {e}")
                
        except Exception as e:
            # 處理其他非 Serial 錯誤
            print(f"\n[錯誤] 執行緒中發生未知錯誤: {e}")

        time.sleep(0.01)



# --- 主程式 ---
def main():
    print(f"--- 已連接 {COM_PORT} (輸入 'exit' 離開) ---")

    # 啟動背景執行緒，將 stop_event 傳入
    t = threading.Thread(target=read_from_port, args=(ser, stop_event,), daemon=True)
    t.start()

    while True:
        user_input = input()
        
        if user_input.lower() == 'exit':
            break
        
        command_to_send = user_input + '\r\n' 
        ser.write(command_to_send.encode('utf-8'))

    # ⚠️ 3. 關鍵步驟：在關閉 Port 前，先通知背景執行緒停止
    print("[主程式] 通知背景讀取執行緒停止...")
    stop_event.set()
    t.join(timeout=1) # 等待執行緒結束 (最多等 1 秒)

    if ser.is_open:
        ser.close()
    print("[主程式] Port 已安全關閉，程式結束。")

if __name__ == "__main__":
    main()