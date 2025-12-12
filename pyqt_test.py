import sys
import serial
import threading
import queue
import time
import pyqtgraph as pg
from PyQt6.QtWidgets import (QApplication, QMainWindow, QMessageBox, 
                             QPushButton, QVBoxLayout, QWidget) # 引入需要的元件
from PyQt6.QtCore import QTimer

# --- 設定區 ---
COM_PORT = 'COM6'      # 請修改為你的 Port
BAUD_RATE = 115200     # 請修改為你的鮑率 (電表常見是 9600 或 115200)
REFRESH_RATE_MS = 100   # GUI 刷新頻率 (建議比取樣率快一點，例如 50ms)
# ser = serial.Serial(COM_PORT, BAUD_RATE, timeout=1)


class RealTimePlotWindow(QMainWindow):
    def __init__(self):
        super().__init__()

# 1. 視窗設定
        self.setWindowTitle(f"PyQtGraph 累積圖表 + 清除功能")
        self.resize(1000, 600)

        # --- 2. 佈局設定 (Layout Setup) ---
        # 建立一個主要容器 (Main Widget)
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)

        # 建立垂直佈局 (由上往下排)
        self.layout = QVBoxLayout()
        self.main_widget.setLayout(self.layout)

        # --- 3. 加入元件 ---
        
        # A. 圖表元件
        self.graphWidget = pg.PlotWidget()
        self.graphWidget.setBackground('k')
        self.graphWidget.showGrid(x=True, y=True)
        self.graphWidget.setLabel('left', 'Value')
        self.graphWidget.setLabel('bottom', 'Time (Points)')
        self.graphWidget.setClipToView(True)
        self.graphWidget.setDownsampling(mode='peak')
        self.data_line = self.graphWidget.plot([], [], pen=pg.mkPen('c', width=2))
        
        # 把圖表加入佈局 (這會佔據大部分空間)
        self.layout.addWidget(self.graphWidget)

        # B. 按鈕元件
        self.clear_btn = QPushButton("🗑️ 清除圖表 (Clear Data)")
        self.clear_btn.setStyleSheet("font-size: 16px; padding: 10px; font-weight: bold;") # 加一點樣式比較好看
        self.clear_btn.clicked.connect(self.clear_data) # 連接訊號：按下 -> 執行 clear_data
        
        # 把按鈕加入佈局
        self.layout.addWidget(self.clear_btn)

        # 3. 資料儲存區
        self.data_queue = queue.Queue() # 線程安全的傳輸通道
        self.data_list = []             # 儲存所有歷史數據 (Y軸)
        self.time_list = []             # 儲存對應的索引 (X軸)
        self.counter = 0                # 點數計數器

        # 4. 初始化 Serial 與 Thread
        self.ser = None
        self.stop_event = threading.Event()
        self.init_serial()

        # 5. 設定 GUI 更新計時器 (QTimer)
        self.timer = QTimer()
        self.timer.setInterval(REFRESH_RATE_MS)
        self.timer.timeout.connect(self.update_plot_from_queue)
        self.timer.start()

    def init_serial(self):
        """ 初始化 Serial Port 並啟動讀取執行緒 """
        try:
            self.ser = serial.Serial(COM_PORT, BAUD_RATE, timeout=1)
            print(f"✅ 成功連接 {COM_PORT}")
            
            # 啟動背景執行緒
            self.thread = threading.Thread(target=self.serial_read_thread, daemon=True)
            self.thread.start()
            
        except serial.SerialException as e:
            QMessageBox.critical(self, "連線錯誤", f"無法開啟 {COM_PORT}\n請檢查是否被佔用。\n\n錯誤訊息: {e}")

    def clear_data(self):
            """ 清除所有歷史資料，重置圖表 """
            print("使用者執行清除動作...")
            
            # 1. 清空儲存數據的列表
            self.data_list.clear()
            self.time_list.clear()
            
            # 2. 重置 X 軸計數器 (如果你想從 0 開始)
            self.counter = 0 
            
            # 3. 重要：清空還在 Queue 裡面排隊的舊資料
            # 這是為了避免清除後，瞬間又跳出幾筆舊的資料
            with self.data_queue.mutex:
                self.data_queue.queue.clear()

            # 4. 更新圖表為空
            self.data_line.setData([], [])
            
            print("圖表已重置")

    def serial_read_thread(self):
        """ 背景執行緒：只負責讀資料，不碰 GUI """
        print("--- 背景讀取執行緒啟動 ---")
        while not self.stop_event.is_set() :
            try:
                if self.ser.in_waiting:
                    # 讀取一行 (假設電表送的是 ASCII 文字，如 "12.345\n")
                    temp = self.ser.read(self.ser.in_waiting)
                    temp = abs(float(temp) * 1000)*100
                    self.data_queue.put(temp)
                else:
                    # 如果沒資料，稍微睡一下避免 CPU 飆高
                    time.sleep(0.01)
                    
            except Exception as e:
                print(f"讀取錯誤: {e}")
                break

    def update_plot_from_queue(self):
        """ 主執行緒：定期去 Queue 把資料拿出來畫 """
        has_new_data = False
        command_to_send = "val?"+ '\r\n'
        self.ser.write(command_to_send.encode('utf-8'))
        # 把目前 Queue 裡面所有的資料一次拿光 (Batch Processing)
        while not self.data_queue.empty():
            val = self.data_queue.get()
            
            # 存入列表
            self.data_list.append(val)
            self.time_list.append(self.counter)
            self.counter += 1
            has_new_data = True

        # 只有真的有新資料時才更新圖表，節省效能
        if has_new_data:
            self.data_line.setData(self.time_list, self.data_list)

    def closeEvent(self, event):
        """ 視窗關閉時的清理動作 """
        print("正在關閉程式...")
        self.stop_event.set() # 通知執行緒停止
        if self.ser and self.ser.is_open:
            self.ser.close()
        event.accept()

# --- 啟動程式 ---
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = RealTimePlotWindow()
    window.show()
    sys.exit(app.exec())