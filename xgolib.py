import serial
import struct
import time

__version__ = '1.1.16'
__last_modified__ = '2022/11/01'

"""
XGOorder 用来存放命令地址和对应数据
XGOorder is used to store the command address and corresponding data
"""
XGOorder = {
    "BATTERY": [0x01, 100],
    "PERFORM": [0x03, 0],
    "CALIBRATION": [0x04, 0],
    "UPGRADE": [0x05, 0],
    "MOVE_TEST": [0x06, 1],
    "FIRMWARE_VERSION": [0x07],
    "GAIT_TYPE": [0x09, 0x00],
    "BT_NAME": [0x13, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    "UNLOAD_MOTOR": [0x20, 0],
    "LOAD_MOTOR": [0x20, 0],
    "VX": [0x30, 128],
    "VY": [0x31, 128],
    "VYAW": [0x32, 128],
    "TRANSLATION": [0x33, 0, 0, 0],
    "ATTITUDE": [0x36, 0, 0, 0],
    "PERIODIC_ROT": [0x39, 0, 0, 0],
    "MarkTime": [0x3C, 0],
    "MOVE_MODE": [0x3D, 0],
    "ACTION": [0x3E, 0],
    "PERIODIC_TRAN": [0x80, 0, 0, 0],
    "MOTOR_ANGLE": [0x50, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128, 128],
    "MOTOR_SPEED": [0x5C, 1],
    "LEG_POS": [0x40, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    "IMU": [0x61, 0],
    "ROLL": [0x62, 0],
    "PITCH": [0x63, 0],
    "YAW": [0x64, 0],
    "CLAW": [0x71, 0],
    "ARM_MODE": [0x72, 0],
    "ARM_X": [0x73, 0],
    "ARM_Z": [0x74, 0]
}

"""
XGOparam 用来存放机器狗的参数限制范围
Xgoparam is used to store the parameter limit range of the robot dog
"""

XGOparam = {
    "TRANSLATION_LIMIT": [35, 18, [75, 115]],  # X Y Z 平移范围
    "ATTITUDE_LIMIT": [20, 15, 11],  # Roll Pitch Yaw 姿态范围
    "LEG_LIMIT": [35, 18, [75, 115]],  # 腿长范围
    "MOTOR_LIMIT": [[-73, 57], [-66, 93], [-31, 31], [-30, 30], [-60, 70], [-90, 105]],  # 下 中 上 舵机范围
    "PERIOD_LIMIT": [[1.5, 8]],
    "MARK_TIME_LIMIT": [10, 35],  # 原地踏步高度范围
    "VX_LIMIT": 25,  # X速度范围
    "VY_LIMIT": 18,  # Y速度范围
    "VYAW_LIMIT": 100  # 旋转速度范围
}


def search(data, list):
    for i in range(len(list)):
        if data == list[i]:
            return i + 1
    return -1


def conver2u8(data, limit, mode=0):
    """
    将实际参数转化为0到255的单字节数据
    Convert the actual parameters to single byte data from 0 to 255
    """
    max = 0xff
    if mode == 0:
        min = 0x00
    else:
        min = 0x01

    if not isinstance(limit, list):
        if data >= limit:
            return max
        elif data <= -limit:
            return min
        else:
            return int(128 + 128 * data / limit)
    else:
        limitmin = limit[0]
        limitmax = limit[1]
        if data >= limitmax:
            return max
        elif data <= limitmin:
            return min
        else:
            return int(255 / (limitmax - limitmin) * (data - limitmin))


def conver2float(data, limit):
    if not isinstance(limit, list):
        return (data - 128.0) / 255.0 * limit
    else:
        limitmin = limit[0]
        limitmax = limit[1]
        return data / 255.0 * (limitmax - limitmin) + limitmin


def Byte2Float(rawdata):
    a = bytearray()
    a.append(rawdata[3])
    a.append(rawdata[2])
    a.append(rawdata[1])
    a.append(rawdata[0])
    return struct.unpack("!f", a)[0]
    pass


def changePara(version):
    global XGOparam
    if version == 'xgomini':
        XGOparam = {
            "TRANSLATION_LIMIT": [35, 18, [75, 115]],  # X Y Z 平移范围
            "ATTITUDE_LIMIT": [20, 15, 11],  # Roll Pitch Yaw 姿态范围
            "LEG_LIMIT": [35, 18, [75, 115]],  # 腿长范围
            "MOTOR_LIMIT": [[-73, 57], [-66, 93], [-31, 31]],  # 下 中 上 舵机范围
            "PERIOD_LIMIT": [[1.5, 8]],
            "MARK_TIME_LIMIT": [10, 35],  # 原地踏步高度范围
            "VX_LIMIT": 25,  # X速度范围
            "VY_LIMIT": 18,  # Y速度范围
            "VYAW_LIMIT": 100,  # 旋转速度范围
            "ARM_LIMIT": [[-80, 155], [-95, 155]]
        }
    elif version == 'xgolite':
        XGOparam = {
            "TRANSLATION_LIMIT": [25, 18, [60, 110]],
            "ATTITUDE_LIMIT": [20, 10, 12],
            "LEG_LIMIT": [25, 18, [60, 110]],
            "MOTOR_LIMIT": [[-70, 50], [-70, 90], [-30, 30], [-30, 30], [-70, 60], [-90, 105]],
            "PERIOD_LIMIT": [[1.5, 8]],
            "MARK_TIME_LIMIT": [10, 25],
            "VX_LIMIT": 25,
            "VY_LIMIT": 18,
            "VYAW_LIMIT": 100,
            "ARM_LIMIT": [[-80, 155], [-95, 155]]
        }


class XGO():
    """
    在实例化XGO时需要指定上位机与机器狗的串口通讯接口
    When instantiating XGO, you need to specify the serial
    communication interface between the upper computer and the machine dog
    """

    def __init__(self, port, baud=115200, version='xgomini'):
        self.ser = serial.Serial(port, baud, timeout=0.5)
        self.rx_FLAG = 0
        self.rx_COUNT = 0
        self.rx_ADDR = 0
        self.rx_LEN = 0
        self.rx_data = bytearray(50)
        changePara(version)
        pass

    def __send(self, key, index=1, len=1):
        mode = 0x01
        order = XGOorder[key][0] + index - 1
        value = []
        value_sum = 0
        for i in range(0, len):
            value.append(XGOorder[key][index + i])
            value_sum = value_sum + XGOorder[key][index + i]
        sum_data = ((len + 0x08) + mode + order + value_sum) % 256
        sum_data = 255 - sum_data
        tx = [0x55, 0x00, (len + 0x08), mode, order]
        tx.extend(value)
        tx.extend([sum_data, 0x00, 0xAA])
        self.ser.write(tx)
        print("tx_data: ",tx)

    def __read(self, addr, read_len=1):
        mode = 0x02
        sum_data = (0x09 + mode + addr + read_len) % 256
        sum_data = 255 - sum_data
        tx = [0x55, 0x00, 0x09, mode, addr, read_len, sum_data, 0x00, 0xAA]
        time.sleep(0.1)
        self.ser.flushInput()
        self.ser.write(tx)
        print("tx_data: ",tx)

    def stop(self):
        self.move_x(0)
        self.move_y(0)
        self.mark_time(0)
        self.turn(0)

    def move(self, direction, step):
        if direction in ['x', 'X']:
            self.move_x(step)
        elif direction in ['y', 'Y']:
            self.move_y(step)
        else:
            print("ERROR!Invalid direction!")

    def move_x(self, step):
        XGOorder["VX"][1] = conver2u8(step, XGOparam["VX_LIMIT"])
        self.__send("VX")

    def move_y(self, step):
        XGOorder["VY"][1] = conver2u8(step, XGOparam["VY_LIMIT"])
        self.__send("VY")

    def turn(self, step):
        XGOorder["VYAW"][1] = conver2u8(step, XGOparam["VYAW_LIMIT"])
        self.__send("VYAW")

    def forward(self, step):
        self.move_x(abs(step))

    def back(self, step):
        self.move_x(-abs(step))

    def left(self, step):
        self.move_y(abs(step))

    def right(self, step):
        self.move_y(-abs(step))

    def turnleft(self, step):
        self.turn(abs(step))

    def turnright(self, step):
        self.turn(-abs(step))

    def __translation(self, direction, data):
        index = search(direction, ['x', 'y', 'z'])
        if index == -1:
            print("ERROR!Direction must be 'x', 'y' or 'z'")
            return
        XGOorder["TRANSLATION"][index] = conver2u8(data, XGOparam["TRANSLATION_LIMIT"][index - 1])
        self.__send("TRANSLATION", index)

    def translation(self, direction, data):
        """
        使机器狗足端不动，身体进行三轴平动
        Keep the robot's feet stationary and the body makes three-axis translation
        """
        if (isinstance(direction, list)):
            if (len(direction) != len(data)):
                print("ERROR!The length of direction and data don't match!")
                return
            for i in range(len(data)):
                self.__translation(direction[i], data[i])
        else:
            self.__translation(direction, data)

    def __attitude(self, direction, data):
        index = search(direction, ['r', 'p', 'y'])
        if index == -1:
            print("ERROR!Direction must be 'r', 'p' or 'y'")
            return
        XGOorder["ATTITUDE"][index] = conver2u8(data, XGOparam["ATTITUDE_LIMIT"][index - 1])
        self.__send("ATTITUDE", index)

    def attitude(self, direction, data):
        """
        使机器狗足端不动，身体进行三轴转动
        Keep the robot's feet stationary and the body makes three-axis rotation
        """
        if (isinstance(direction, list)):
            if (len(direction) != len(data)):
                print("ERROR!The length of direction and data don't match!")
                return
            for i in range(len(data)):
                self.__attitude(direction[i], data[i])
        else:
            self.__attitude(direction, data)

    def action(self, action_id):
        """
        使机器狗狗指定的预设动作
        Make the robot do the specified preset action
        """
        if action_id <= 0 or action_id > 255:
            print("ERROR!Illegal Action ID!")
            return
        XGOorder["ACTION"][1] = action_id
        self.__send("ACTION")

    pass

    def reset(self):
        """
        机器狗停止运动，所有参数恢复到初始状态
        The robot dog stops moving and all parameters return to the initial state
        """
        self.action(255)
        time.sleep(0.2)

    def leg(self, leg_id, data):
        """
        控制机器狗的单腿的三轴移动
        Control the three-axis movement of a single leg of the robot
        """
        value = [0, 0, 0]
        if leg_id not in [1, 2, 3, 4]:
            print("Error!Illegal Index!")
            return
        if len(data) != 3:
            message = "Error!Illegal Value!"
            return
        for i in range(3):
            try:
                value[i] = conver2u8(data[i], XGOparam["LEG_LIMIT"][i])
            except:
                print("Error!Illegal Value!")
        for i in range(3):
            index = 3 * (leg_id - 1) + i + 1
            XGOorder["LEG_POS"][index] = value[i]
            self.__send("LEG_POS", index)

    def __motor(self, index, data):
        if index < 13:
            XGOorder["MOTOR_ANGLE"][index] = conver2u8(data, XGOparam["MOTOR_LIMIT"][index % 3 - 1])
        elif index == 13:
            self.claw(conver2u8(data, XGOparam["MOTOR_LIMIT"][3]))
        else:
            XGOorder["MOTOR_ANGLE"][index] = conver2u8(data, XGOparam["MOTOR_LIMIT"][index - 10])
        self.__send("MOTOR_ANGLE", index)

    def motor(self, motor_id, data):
        """
        控制机器狗单个舵机转动
        Control the rotation of a single steering gear of the robot
        """
        MOTOR_ID = [11, 12, 13, 21, 22, 23, 31, 32, 33, 41, 42, 43, 51, 52, 53]
        if motor_id == 51:
            self.claw(data)
            return

        if isinstance(motor_id, list):
            if len(motor_id) != len(data):
                print("Error!Length Mismatching!")
                return
            index = []
            for i in range(len(motor_id)):
                temp_index = search(motor_id[i], MOTOR_ID)
                if temp_index == -1:
                    print("Error!Illegal Index!")
                    return
                index.append(temp_index)
            for i in range(len(index)):
                self.__motor(index[i], data[i])
        else:
            index = search(motor_id, MOTOR_ID)
            self.__motor(index, data)

    def unload_motor(self, leg_id):
        if leg_id not in [1, 2, 3, 4, 5]:
            print('ERROR!leg_id must be 1, 2, 3 ,4 or 5')
            return
        XGOorder["UNLOAD_MOTOR"][1] = 0x10 + leg_id
        self.__send("UNLOAD_MOTOR")

    def unload_allmotor(self):
        XGOorder["UNLOAD_MOTOR"][1] = 0x01
        self.__send("UNLOAD_MOTOR")

    def load_motor(self, leg_id):
        if leg_id not in [1, 2, 3, 4, 5]:
            print('ERROR!leg_id must be 1, 2, 3 ,4 or 5')
            return
        XGOorder["LOAD_MOTOR"][1] = 0x20 + leg_id
        self.__send("LOAD_MOTOR")

    def load_allmotor(self):
        XGOorder["LOAD_MOTOR"][1] = 0x00
        self.__send("LOAD_MOTOR")

    def __periodic_rot(self, direction, period):
        index = search(direction, ['r', 'p', 'y'])
        if index == -1:
            print("ERROR!Direction must be 'r', 'p' or 'y'")
            return
        if period == 0:
            XGOorder["PERIODIC_ROT"][index] = 0
        else:
            XGOorder["PERIODIC_ROT"][index] = conver2u8(period, XGOparam["PERIOD_LIMIT"][0], mode=1)
        self.__send("PERIODIC_ROT", index)

    def periodic_rot(self, direction, period):
        """
        使机器狗周期性转动
        Make the robot rotate periodically
        """
        if (isinstance(direction, list)):
            if (len(direction) != len(period)):
                print("ERROR!The length of direction and data don't match!")
                return
            for i in range(len(period)):
                self.__periodic_rot(direction[i], period[i])
        else:
            self.__periodic_rot(direction, period)

    def __periodic_tran(self, direction, period):
        index = search(direction, ['x', 'y', 'z'])
        if index == -1:
            print("ERROR!Direction must be 'x', 'y' or 'z'")
            return
        if period == 0:
            XGOorder["PERIODIC_TRAN"][index] = 0
        else:
            XGOorder["PERIODIC_TRAN"][index] = conver2u8(period, XGOparam["PERIOD_LIMIT"][0], mode=1)
        self.__send("PERIODIC_TRAN", index)

    def periodic_tran(self, direction, period):
        """
        使机器狗周期性平动
        Make the robot translate periodically
        """
        if (isinstance(direction, list)):
            if (len(direction) != len(period)):
                print("ERROR!The length of direction and data don't match!")
                return
            for i in range(len(period)):
                self.__periodic_tran(direction[i], period[i])
        else:
            self.__periodic_tran(direction, period)

    def mark_time(self, data):
        """
        使机器狗原地踏步
        Make the robot marks time
        """
        if data == 0:
            XGOorder["MarkTime"][1] = 0
        else:
            XGOorder["MarkTime"][1] = conver2u8(data, XGOparam["MARK_TIME_LIMIT"], mode=1)
        self.__send("MarkTime")

    def pace(self, mode):
        """
        改变机器狗的踏步频率
        Change the step frequency of the robot
        """
        if mode == "normal":
            value = 0x00
        elif mode == "slow":
            value = 0x01
        elif mode == "high":
            value = 0x02
        else:
            print("ERROR!Illegal Value!")
            return
        XGOorder["MOVE_MODE"][1] = value
        self.__send("MOVE_MODE")

    def gait_type(self, mode):
        if mode == "trot":
            value = 0x00
        elif mode == "walk":
            value = 0x01
        elif mode == "high_walk":
            value = 0x02
        XGOorder["GAIT_TYPE"][1] = value
        self.__send("GAIT_TYPE")

    def imu(self, mode):
        """
        开启/关闭机器狗自稳状态
        Turn on / off the self stable state of the robot dog
        """
        if mode != 0 and mode != 1:
            print("ERROR!Illegal Value!")
            return
        XGOorder["IMU"][1] = mode
        self.__send("IMU")

    def perform(self, mode):
        """
        开启/关闭机器狗循环做动作状态
        Turn on / off the action status of the robot dog cycle
        """
        if mode != 0 and mode != 1:
            print("ERROR!Illegal Value!")
            return
        XGOorder["PERFORM"][1] = mode
        self.__send("PERFORM")

    def motor_speed(self, speed):
        """
        调节舵机转动速度，只在单独控制舵机的情况下有效
        Adjust the steering gear rotation speed,
        only effective when control the steering gear separately
        """
        if speed < 0 or speed > 255:
            print("ERROR!Illegal Value!The speed parameter needs to be between 0 and 255!")
            return
        if speed == 0:
            speed = 1
        XGOorder["MOTOR_SPEED"][1] = speed
        self.__send("MOTOR_SPEED")

    def bt_rename(self, name):
        if type(name) != str:
            print("ERROR!The input value must be of string type!")
            return
        len_name = len(name)
        if len_name > 10:
            print("ERROR!The length of the input string cannot be longer than 10!")
            return
        try:
            XGOorder["BT_NAME"][1:len_name + 1] = list(name.encode('ascii'))
            self.__send("BT_NAME", len=len_name)
        except:
            print("ERROR!Name only supports characters in ASCII code!")

    def read_motor(self):
        """
        读取12个舵机的角度
        """
        self.__read(XGOorder["MOTOR_ANGLE"][0], 15)
        self.ser.read_all()
        angle = []
        if self.__unpack():
            for i in range(self.rx_COUNT + 1):
                if i < 12:
                    angle.append(round(conver2float(self.rx_data[i], XGOparam["MOTOR_LIMIT"][i % 3]), 2))
                else:
                    angle.append(round(conver2float(self.rx_data[i], XGOparam["MOTOR_LIMIT"][i - 9]), 2))
        return angle

    def read_battery(self):
        self.ser.read_all()
        self.__read(XGOorder["BATTERY"][0], 1)
        battery = 0
        if self.__unpack():
            battery = int(self.rx_data[0])
        return battery

    def read_firmware(self):
        self.__read(XGOorder["FIRMWARE_VERSION"][0], 10)
        self.ser.read_all()
        firmware_version = 'Null'
        if self.__unpack():
            data = self.rx_data[0:10]
            firmware_version = data.decode("utf-8").strip('\0')
        return firmware_version

    def read_roll(self):
        self.__read(XGOorder["ROLL"][0], 4)
        self.ser.read_all()
        roll = 0
        if self.__unpack():
            roll = Byte2Float(self.rx_data)
        return round(roll, 2)

    def read_pitch(self):
        self.__read(XGOorder["PITCH"][0], 4)
        self.ser.read_all()
        pitch = 0
        if self.__unpack():
            pitch = Byte2Float(self.rx_data)
        return round(pitch, 2)

    def read_yaw(self):
        self.__read(XGOorder["YAW"][0], 4)
        self.ser.read_all()
        yaw = 0
        if self.__unpack():
            yaw = Byte2Float(self.rx_data)
        return round(yaw, 2)

    def __unpack(self):
        t = time.time()
        rx_data = []
        while time.time() - t < 1:
            n = self.ser.inWaiting()
            rx_CHECK = 0
            if n:
                data = self.ser.read(n)
                for num in data:
                    rx_data.append(num)
                    if self.rx_FLAG == 0:
                        if num == 0x55:
                            self.rx_FLAG = 1
                        else:
                            self.rx_FLAG = 0

                    elif self.rx_FLAG == 1:
                        if num == 0x00:
                            self.rx_FLAG = 2
                        else:
                            self.rx_FLAG = 0

                    elif self.rx_FLAG == 2:
                        self.rx_LEN = num
                        self.rx_FLAG = 3

                    elif self.rx_FLAG == 3:
                        self.rx_TYPE = num
                        self.rx_FLAG = 4

                    elif self.rx_FLAG == 4:
                        self.rx_ADDR = num
                        self.rx_FLAG = 5
                        self.rx_COUNT = 0

                    elif self.rx_FLAG == 5:
                        if self.rx_COUNT == (self.rx_LEN - 9):
                            self.rx_data[self.rx_COUNT] = num
                            self.rx_FLAG = 6
                        elif self.rx_COUNT < self.rx_LEN - 9:
                            self.rx_data[self.rx_COUNT] = num
                            self.rx_COUNT = self.rx_COUNT + 1

                    elif self.rx_FLAG == 6:
                        for i in self.rx_data[0:(self.rx_LEN - 8)]:
                            rx_CHECK = rx_CHECK + i
                        rx_CHECK = 255 - (self.rx_LEN + self.rx_TYPE + self.rx_ADDR + rx_CHECK) % 256
                        if num == rx_CHECK:
                            self.rx_FLAG = 7
                        else:
                            self.rx_FLAG = 0
                            self.rx_COUNT = 0
                            self.rx_ADDR = 0
                            self.rx_LEN = 0

                    elif self.rx_FLAG == 7:
                        if num == 0x00:
                            self.rx_FLAG = 8
                        else:
                            self.rx_FLAG = 0
                            self.rx_COUNT = 0
                            self.rx_ADDR = 0
                            self.rx_LEN = 0

                    elif self.rx_FLAG == 8:
                        if num == 0xAA:
                            self.rx_FLAG = 0
                            print("rx_data: ",rx_data)
                            return True
                        else:
                            self.rx_FLAG = 0
                            self.rx_COUNT = 0
                            self.rx_ADDR = 0
                            self.rx_LEN = 0
        print("rx_data: ",rx_data)
        return False

    def upgrade(self, filename):
        """
        处于测试阶段，请勿使用
        """
        XGOorder["UPGRADE"][1] = 1
        self.__send("UPGRADE")
        time.sleep(5)
        self.upload_bin(filename)

    def read_version(self):
        """
        处于测试阶段，请勿使用
        """
        self.__read(XGOorder["VERSION"][0], 10)
        time.sleep(1)
        if self.__unpack():
            version = self.rx_data.decode('utf-8')
        return version

    def upload_bin(self, filename):
        """
        处于测试阶段，请勿使用
        """
        try:
            with open(filename, 'rb') as f:
                file = f.read()
            count = self.ser.write(file)
            print("更新成功，共发送字节数：", count)
        except Exception as e:
            print("---更新错误---")
            print(e)

    def calibration(self, state):
        """
        用于软件标定，请谨慎使用！！！
        """
        XGOorder["CALIBRATION"][1] = state
        self.__send("CALIBRATION")

    def arm(self, arm_x, arm_z):
        """
        控制机器狗的机械臂的前后和上下移动
        Control the movement of the arm of the robot
        """
        try:
            arm_x_u8 = conver2u8(arm_x, XGOparam["ARM_LIMIT"][0])
            arm_z_u8 = conver2u8(arm_z, XGOparam["ARM_LIMIT"][1])
        except:
            print("Error!Illegal Value!")
            return
        XGOorder["ARM_X"][1] = arm_x_u8
        XGOorder["ARM_Z"][1] = arm_z_u8
        self.__send("ARM_X")
        self.__send("ARM_Z")

    def arm_mode(self, mode):
        if mode != 0x01 and mode != 0x00:
            print("Error!Illegal Value!")
            return
        XGOorder["ARM_MODE"][1] = mode
        self.__send("ARM_MODE")

    def claw(self, pos):
        try:
            claw_pos = conver2u8(pos, [0, 255])
        except:
            print("Error!Illegal Value!")
            return
        XGOorder["CLAW"][1] = claw_pos
        self.__send("CLAW")
