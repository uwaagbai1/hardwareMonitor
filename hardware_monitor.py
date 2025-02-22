import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
import psutil
import platform
import time
from datetime import datetime, timedelta
from typing import Dict, Optional
from collections import deque
import subprocess
from pushbullet import Pushbullet
import curses
import asyncio
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import json
from dataclasses import dataclass
from fault_detection.models import Alert

@dataclass
class AlertState:
    last_notification_time: datetime = None
    current_status: str = 'ok'
    notification_count: int = 0

class EnhancedHardwareMonitor:
    def __init__(self, pushbullet_api_key: Optional[str] = None):
        self.thresholds = {
            'cpu_usage': {'warning': 80, 'critical': 90},  # CPU usage percentage
            'ram_usage': {'warning': 80, 'critical': 90},  # RAM usage percentage
            'disk_usage': {'warning': 85, 'critical': 95},  # Disk usage percentage
            'temperature': {'warning': 75, 'critical': 85},  # CPU temperature in Celsius
            'network_latency': {'warning': 150, 'critical': 300},  # Network latency in ms
            'disk_read_speed': {'warning': 10, 'critical': 5},  # MB/s
            'disk_write_speed': {'warning': 10, 'critical': 5},  # MB/s
            'battery_level': {'warning': 20, 'critical': 10}  # Battery percentage
        }

        self.notification_cooldowns = {
            'warning': 15,
            'critical': 5
        }
        
        self.alert_states = {
            'cpu': AlertState(),
            'ram': AlertState(),
            'disk': AlertState(),
            'temperature': AlertState(),
            'network': AlertState(),
            'battery': AlertState()
        }
        
        self.history = {
            'cpu': deque(maxlen=1440),
            'ram': deque(maxlen=1440),
            'disk': deque(maxlen=1440),
            'network_speed': deque(maxlen=1440),
            'temperature': deque(maxlen=1440),
            'battery': deque(maxlen=1440)
        }
        
        self.previous_network_bytes = {'sent': 0, 'recv': 0}
        self.previous_disk_bytes = {'read': 0, 'write': 0}
        self.previous_time = time.time()
        
        self.pushbullet = None
        if pushbullet_api_key:
            try:
                self.pushbullet = Pushbullet(pushbullet_api_key)
                print("Pushbullet initialized successfully.")
            except Exception as e:
                print(f"Failed to initialize Pushbullet: {e}")
        
        self.channel_layer = get_channel_layer()

    def should_send_notification(self, metric: str, status: str) -> bool:
        alert_state = self.alert_states[metric]
        current_time = datetime.now()
        
        if (alert_state.last_notification_time is None or 
            alert_state.current_status != status):
            alert_state.current_status = status
            alert_state.last_notification_time = current_time
            alert_state.notification_count = 1
            return True
        
        cooldown = timedelta(minutes=self.notification_cooldowns[status])
        if current_time - alert_state.last_notification_time >= cooldown:
            alert_state.last_notification_time = current_time
            alert_state.notification_count += 1
            return True
            
        return False

    def send_notification(self, message: str, status: str, metric: str):
        if not self.should_send_notification(metric, status):
            return
        
        Alert.objects.create(metric=metric, status=status, message=message)
        
        if self.pushbullet:
            try:
                if status == 'critical':
                    self.pushbullet.push_note(
                        "Hardware Monitor Critical Alert", 
                        message
                    )
                
                async_to_sync(self.channel_layer.group_send)(
                    "hardware_monitor",
                    {
                        "type": "hardware_update",
                        "data": {
                            "metric": metric,
                            "status": status,
                            "message": message,
                            "timestamp": datetime.now().isoformat(),
                            "notification_count": self.alert_states[metric].notification_count
                        }
                    }
                )
            except Exception as e:
                print(f"Failed to send notification: {e}")

    def update_history(self, metric: str, value: float):
        self.history[metric].append({
            'timestamp': datetime.now().isoformat(),
            'value': value
        })

    def get_history(self, metric: str, minutes: int = 60) -> list:
        if metric not in self.history:
            return []
        
        current_time = datetime.now()
        cutoff_time = current_time - timedelta(minutes=minutes)
        
        return [
            data for data in self.history[metric]
            if datetime.fromisoformat(data['timestamp']) > cutoff_time
        ]

    def check_metric(self, metric: str, value: float, thresholds: Dict) -> Dict:
        if metric == 'battery':
            # For battery, trigger alerts when the value drops below the thresholds
            if value < thresholds['critical']:
                status = 'critical'
                message = f"Critical: Low {metric}: {value:.1f}%"
            elif value < thresholds['warning']:
                status = 'warning'
                message = f"Warning: Low {metric}: {value:.1f}%"
            else:
                status = 'ok'
                message = None
        else:
            # For other metrics, trigger alerts when the value rises above the thresholds
            if value > thresholds['critical']:
                status = 'critical'
                message = f"Critical: High {metric}: {value:.1f}"
            elif value > thresholds['warning']:
                status = 'warning'
                message = f"Warning: High {metric}: {value:.1f}"
            else:
                status = 'ok'
                message = None

        if message:
            self.send_notification(message, status, metric)

        return {
            'value': value,
            'status': status,
            'message': message
        }

    def check_battery(self) -> Optional[Dict]:
        if hasattr(psutil, 'sensors_battery'):
            battery = psutil.sensors_battery()
            if battery:
                print(f"Battery Level: {battery.percent}%")
                print(f"Thresholds: {self.thresholds['battery_level']}")
                self.update_history('battery', battery.percent)
                
                result = self.check_metric(
                    'battery',
                    battery.percent,
                    self.thresholds['battery_level']
                )
                
                return {
                    'percent': battery.percent,
                    'power_plugged': battery.power_plugged,
                    'status': result['status'],
                    'message': result['message']
                }
        return None



    def get_system_info(self) -> Dict:
        return {
            'system': platform.system(),
            'node': platform.node(),
            'release': platform.release(),
            'version': platform.version(),
            'machine': platform.machine(),
            'processor': platform.processor()
        }

    def check_cpu(self) -> Dict:
        cpu_usage = psutil.cpu_percent(interval=0.5)
        cpu_freq = psutil.cpu_freq()
        cpu_count = psutil.cpu_count()
        cpu_per_core = psutil.cpu_percent(interval=0.5, percpu=True)
        
        self.update_history('cpu', cpu_usage)
        
        result = self.check_metric(
            'cpu',
            cpu_usage,
            self.thresholds['cpu_usage']
        )
        
        return {
            'usage': cpu_usage,
            'frequency': cpu_freq.current if cpu_freq else 0,
            'cores': cpu_count,
            'per_core_usage': cpu_per_core,
            'status': result['status'],
            'message': result['message']
        }

    def check_ram(self) -> Dict:
        ram = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        self.update_history('ram', ram.percent)
        
        result = self.check_metric(
            'ram',
            ram.percent,
            self.thresholds['ram_usage']
        )
        
        return {
            'total': ram.total,
            'used': ram.used,
            'free': ram.available,
            'percent': ram.percent,
            'swap_total': swap.total,
            'swap_used': swap.used,
            'swap_percent': swap.percent,
            'status': result['status'],
            'message': result['message']
        }

    def check_disk(self) -> Dict:
        disk = psutil.disk_usage('/')
        disk_io = psutil.disk_io_counters()
        current_time = time.time()
        time_diff = current_time - self.previous_time

        read_speed = (disk_io.read_bytes - self.previous_disk_bytes['read']) / (time_diff * 1024 * 1024)
        write_speed = (disk_io.write_bytes - self.previous_disk_bytes['write']) / (time_diff * 1024 * 1024)

        self.previous_disk_bytes = {'read': disk_io.read_bytes, 'write': disk_io.write_bytes}
        self.update_history('disk', disk.percent)

        result = self.check_metric(
            'disk',
            disk.percent,
            self.thresholds['disk_usage']
        )

        partitions = psutil.disk_partitions()
        partition_info = {}
        for partition in partitions:
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                partition_info[partition.mountpoint] = {
                    'total': usage.total,
                    'used': usage.used,
                    'free': usage.free,
                    'percent': usage.percent,
                    'device': partition.device,
                    'fstype': partition.fstype
                }
            except (PermissionError, OSError):
                continue

        return {
            'total': disk.total,
            'used': disk.used,
            'free': disk.free,
            'percent': disk.percent,
            'read_speed': read_speed,
            'write_speed': write_speed,
            'partitions': partition_info,
            'io_counters': {
                'read_count': disk_io.read_count,
                'write_count': disk_io.write_count,
                'read_bytes': disk_io.read_bytes,
                'write_bytes': disk_io.write_bytes,
                'read_time': disk_io.read_time,
                'write_time': disk_io.write_time
            },
            'status': result['status'],
            'message': result['message']
        }

    def check_temperature(self) -> Optional[Dict]:
        try:
            temperatures = psutil.sensors_temperatures()
            if temperatures:
                max_temp = max([temp.current for temp in temperatures.get('coretemp', [])])
                self.update_history('temperature', max_temp)
                
                result = self.check_metric(
                    'temperature',
                    max_temp,
                    self.thresholds['temperature']
                )
                
                return {
                    'current': max_temp,
                    'status': result['status'],
                    'message': result['message']
                }
        except Exception:
            return None

    def check_battery(self) -> Optional[Dict]:
        if hasattr(psutil, 'sensors_battery'):
            battery = psutil.sensors_battery()
            if battery:
                self.update_history('battery', battery.percent)
                
                result = self.check_metric(
                    'battery',
                    battery.percent,
                    self.thresholds['battery_level']
                )
                
                return {
                    'percent': battery.percent,
                    'power_plugged': battery.power_plugged,
                    'status': result['status'],
                    'message': result['message']
                }
        return None
                
 

    def get_network_stats(self) -> Dict:
        try:
            ping_result = subprocess.run(['ping', '-c', '1', '8.8.8.8'], 
                                       capture_output=True, timeout=2)
            latency = float(ping_result.stdout.decode().split('time=')[1].split()[0])
        except:
            latency = None

        net_io = psutil.net_io_counters()
        current_time = time.time()
        time_diff = current_time - self.previous_time

        sent_speed = (net_io.bytes_sent - self.previous_network_bytes['sent']) / time_diff
        recv_speed = (net_io.bytes_recv - self.previous_network_bytes['recv']) / time_diff

        self.update_history('network_speed', (sent_speed + recv_speed) / 2)
        
        self.previous_network_bytes = {'sent': net_io.bytes_sent, 'recv': net_io.bytes_recv}
        self.previous_time = current_time

        result = self.check_metric(
            'network',
            latency if latency else 0,
            self.thresholds['network_latency']
        ) if latency else {'status': 'ok', 'message': None}

        return {
            'latency': latency,
            'bytes_sent': net_io.bytes_sent,
            'bytes_recv': net_io.bytes_recv,
            'send_speed': sent_speed,
            'recv_speed': recv_speed,
            'packets_sent': net_io.packets_sent,
            'packets_recv': net_io.packets_recv,
            'status': result['status'],
            'message': result['message']
        }

    def check_all(self) -> Dict:
        data = {
            'timestamp': datetime.now().isoformat(),
            'cpu': self.check_cpu(),
            'ram': self.check_ram(),
            'disk': self.check_disk(),
            'network': self.get_network_stats(),
            'temperature': self.check_temperature(),
            'battery': self.check_battery(),
            'system_info': self.get_system_info()
        }
        
        async_to_sync(self.channel_layer.group_send)(
            "hardware_monitor",
            {
                "type": "hardware_update",
                "data": data
            }
        )
        
        for metric, value in data.items():
            if isinstance(value, dict) and value.get('message') and value.get('status'):
                async_to_sync(self.channel_layer.group_send)(
                    "hardware_monitor",
                    {
                        "type": "hardware_update",
                        "message": value['message'],
                        "status": value['status']
                    }
                )
        
        return data

    def run_monitor(self):
        while True:
            try:
                self.check_all()
                time.sleep(5)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error in monitoring loop: {e}")
                time.sleep(5)

if __name__ == "__main__":
    PUSHBULLET_API_KEY = ""
    monitor = EnhancedHardwareMonitor(PUSHBULLET_API_KEY)
    monitor.run_monitor()